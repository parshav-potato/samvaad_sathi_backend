import os
import uuid
import logging
from typing import Optional
from decouple import config
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Initialize boto3 client lazily or handle missing creds gracefully
try:
    # Explicitly pass credentials from .env via config()
    s3_client = boto3.client(
        's3',
        aws_access_key_id=config("AWS_ACCESS_KEY_ID", default=None),
        aws_secret_access_key=config("AWS_SECRET_ACCESS_KEY", default=None),
        region_name=config("AWS_REGION", default="ap-south-1")
    )
    BUCKET_NAME = config("AWS_S3_BUCKET_NAME", default="barabari-edtech-service-staging")
except Exception as e:
    logger.warning(f"Could not initialize S3 client: {e}")
    s3_client = None
    BUCKET_NAME = None


def upload_audio_to_s3(audio_bytes: bytes, question_id: int) -> Optional[str]:
    """
    Uploads the TTS audio byte stream to the S3 bucket.
    
    Args:
        audio_bytes: The raw MP3 byte data from ElevenLabs.
        question_id: The ID of the question (used for naming the file).
        
    Returns:
        The public S3 URL of the uploaded file, or None if the upload failed.
    """
    if not s3_client or not BUCKET_NAME:
        logger.error("S3 client is not configured. Ensure AWS credentials are in .env.")
        return None

    # Generate a predictable filename using the text hash ID.
    s3_file_path = f"Samvaad-Saathi/tts-audio/question_{question_id}.mp3"

    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_file_path,
            Body=audio_bytes,
            ContentType="audio/mpeg",
        )
        
        region = config("AWS_REGION", default="ap-south-1")
        # Construct the public URL
        public_url = f"https://{BUCKET_NAME}.s3.{region}.amazonaws.com/{s3_file_path}"
        logger.info(f"Successfully uploaded TTS audio to S3: {public_url}")
        
        return public_url
        
    except ClientError as e:
        logger.error(f"Failed to upload audio to S3: {e}")
        return None

def upload_resume_to_s3(file_bytes: bytes, user_id: int, filename: str, content_type: str = "application/pdf") -> Optional[str]:
    """
    Uploads a resume file byte stream to the S3 bucket.
    
    Args:
        file_bytes: The raw file data.
        user_id: The ID of the user uploading the resume.
        filename: The original filename.
        content_type: The MIME type of the file.
        
    Returns:
        The S3 object key if successful, or None if failed.
    """
    if not s3_client or not BUCKET_NAME:
        logger.error("S3 client is not configured. Ensure AWS credentials are in .env.")
        return None

    unique_suffix = str(uuid.uuid4())[:8]
    # Keep the original extension
    import os
    _, ext = os.path.splitext(filename)
    if not ext:
        ext = ".pdf" if "pdf" in content_type.lower() else ".txt"
        
    # The key (path) inside the bucket
    s3_object_key = f"Samvaad-Saathi/resumes/user_{user_id}_{unique_suffix}{ext}"

    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_object_key,
            Body=file_bytes,
            ContentType=content_type,
        )
        logger.info(f"Successfully uploaded resume to S3: {s3_object_key}")
        return s3_object_key
        
    except ClientError as e:
        logger.error(f"Failed to upload resume to S3: {e}")
        return None

def get_presigned_url(object_key: str, expiration: int = 3600) -> Optional[str]:
    """
    Generates a short-lived presigned URL to securely download a file.
    
    Args:
        object_key: The S3 object key (e.g. 'Samvaad-Saathi/resumes/...').
        expiration: How many seconds the URL should be valid for (default 1 hr).
        
    Returns:
        The presigned URL string, or None if failed.
    """
    if not s3_client or not BUCKET_NAME:
        logger.error("S3 client is not configured. Ensure AWS credentials are in .env.")
        return None

    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': object_key},
            ExpiresIn=expiration
        )
        return url
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        return None

async def _background_upload_resume(file_bytes: bytes, user_id: int, filename: str, content_type: str):
    """
    Background task to upload a resume and save the key to the User profile.
    """
    import asyncio
    import logging
    from src.repository.database import async_db
    from src.repository.crud.user import UserCRUDRepository

    logger = logging.getLogger(__name__)

    try:
        loop = asyncio.get_event_loop()
        s3_key = await loop.run_in_executor(
            None, 
            upload_resume_to_s3, 
            file_bytes, user_id, filename, content_type
        )
        
        if s3_key:
            async with async_db.get_session() as session:
                repo = UserCRUDRepository(session)
                await repo.update_original_resume_s3_key(user_id=user_id, s3_key=s3_key)
                logger.info(f"Saved original_resume_s3_key {s3_key} for user {user_id}")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed background S3 resume upload: {e}")
