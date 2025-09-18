import fastapi
from fastapi import Request
from fastapi.responses import RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.base_client.errors import OAuthError
from urllib.parse import quote
import secrets

from src.config.manager import settings
from src.api.dependencies.repository import get_repository
from src.repository.crud.user import UserCRUDRepository
from src.repository.crud.session import SessionCRUDRepository
from src.utilities.exceptions.database import EntityDoesNotExist
from src.securities.authorizations.jwt import jwt_generator


router = fastapi.APIRouter(prefix="/auth/cognito", tags=["users"])


def _get_oauth(request: Request) -> OAuth:
    oauth = OAuth()
    region = settings.COGNITO_REGION
    userpool_id = settings.COGNITO_USERPOOL_ID
    authority = f"https://cognito-idp.{region}.amazonaws.com/{userpool_id}"

    oauth.register(
        name="cognito",
        client_id=settings.COGNITO_CLIENT_ID,
        client_secret=settings.COGNITO_CLIENT_SECRET,
        server_metadata_url=f"{authority}/.well-known/openid-configuration",
        client_kwargs={"scope": settings.COGNITO_SCOPES},
    )
    return oauth


@router.get("/login")
async def login(request: Request):
    oauth = _get_oauth(request)
    redirect_uri = request.url_for("auth_cognito_authorize")
    return await oauth.cognito.authorize_redirect(request, redirect_uri)


@router.get("/authorize", name="auth_cognito_authorize")
async def authorize(
    request: Request,
    user_repo: UserCRUDRepository = fastapi.Depends(get_repository(repo_type=UserCRUDRepository)),
    session_repo: SessionCRUDRepository = fastapi.Depends(get_repository(repo_type=SessionCRUDRepository)),
):
    oauth = _get_oauth(request)
    # If Cognito redirected back with an error, surface it gracefully
    err = request.query_params.get("error")
    if err:
        desc = request.query_params.get("error_description") or err
        target_err = settings.COGNITO_POST_LOGIN_REDIRECT_URL or "/"
        return RedirectResponse(url=f"{target_err}#error={quote(desc)}")

    try:
        token = await oauth.cognito.authorize_access_token(request)
    except OAuthError as exc:
        # Redirect back with error message instead of 500
        target_err = settings.COGNITO_POST_LOGIN_REDIRECT_URL or "/"
        message = exc.description or str(exc)
        return RedirectResponse(url=f"{target_err}#error={quote(message)}")

    userinfo = token.get("userinfo") or {}
    email = userinfo.get("email")
    name = userinfo.get("name") or (email.split("@")[0] if email else None)

    # Persist/fetch local user and mint JWT
    if not email:
        target_err = settings.COGNITO_POST_LOGIN_REDIRECT_URL or "/"
        return RedirectResponse(url=f"{target_err}?error={quote('Missing email in userinfo')}")

    try:
        user = await user_repo.get_user_by_email(email=email)
    except EntityDoesNotExist:
        random_password = secrets.token_urlsafe(16)
        user = await user_repo.create_user(email=email, password=random_password, name=name or email)
        await session_repo.create_session(user_id=user.id)

    # Mint existing JWT and store in session for retrieval
    jwt_token = jwt_generator.generate_access_token_for_user(user=user)
    request.session["jwt"] = jwt_token
    request.session["user"] = {"email": email, "sub": userinfo.get("sub"), "name": name or email}

    # Optional: redirect to configured URL (frontend) or default
    target = settings.COGNITO_POST_LOGIN_REDIRECT_URL or "/"
    # Return token via URL fragment to reduce CSRF exposure
    return RedirectResponse(url=f"{target}#token={quote(jwt_token)}")


@router.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    target = settings.COGNITO_POST_LOGOUT_REDIRECT_URL or "/"
    return RedirectResponse(url=target)


@router.get("/session")
async def get_session_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise fastapi.HTTPException(status_code=401, detail="Not authenticated")
    return {"user": user}


@router.get("/jwt")
async def get_session_jwt(request: Request):
    token = request.session.get("jwt")
    if not token:
        raise fastapi.HTTPException(status_code=401, detail="Not authenticated")
    return {"token": token}


