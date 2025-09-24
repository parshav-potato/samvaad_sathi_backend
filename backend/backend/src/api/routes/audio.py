import fastapi
from fastapi import Form, UploadFile, File

from src.api.dependencies.auth import get_current_user
from src.api.dependencies.repository import get_repository
from src.models.schemas.audio import AudioTranscriptionResponse
from src.repository.crud.question import QuestionAttemptCRUDRepository
from src.services.audio_processor import validate_audio_file, save_audio_file, get_audio_duration_estimate, cleanup_temp_audio_file
from src.services.whisper import transcribe_audio_with_whisper, validate_transcription_language, extract_word_count, strip_word_level_data


router = fastapi.APIRouter(prefix="", tags=["audio"])


@router.post(
    path="/transcribe-whisper",
    name="audio:transcribe-whisper", 
    response_model=AudioTranscriptionResponse,
    status_code=fastapi.status.HTTP_202_ACCEPTED,
    summary="Upload audio answer and transcribe with Whisper",
    description=(
        "Accepts audio files (.mp3, .wav, .m4a, .flac) up to 25MB and transcribes them using OpenAI Whisper API. "
        "Returns word-level transcription with timestamps. Requires valid question_attempt_id that belongs to the authenticated user."
    ),
)
async def transcribe_audio_answer(
    question_attempt_id: str = Form(..., description="ID of the question attempt this audio answer belongs to"),
    language: str = Form(default="en", description="Language code for transcription (e.g., 'en', 'es', 'fr')"),
    file: UploadFile = File(..., description="Audio file to transcribe. Supported: .mp3, .wav, .m4a, .flac (max 25MB)"),
    current_user = fastapi.Depends(get_current_user),
    question_repo: QuestionAttemptCRUDRepository = fastapi.Depends(get_repository(repo_type=QuestionAttemptCRUDRepository)),
) -> AudioTranscriptionResponse:
    """
    Main endpoint for audio transcription workflow:
    1. Validate user owns the question attempt
    2. Validate and process audio file
    3. Transcribe with Whisper API
    4. Save audio file and update database
    5. Return transcription results
    """
    
    # Step 1: Verify question attempt exists and belongs to current user
    try:
        question_attempt_id_int = int(question_attempt_id)
    except ValueError:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid question_attempt_id format. Must be a valid integer."
        )
    
    question_attempt = await question_repo.get_by_id_and_user(
        question_attempt_id=question_attempt_id_int,
        user_id=current_user.id
    )
    
    if not question_attempt:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Question attempt not found or access denied"
        )

    # Step 2: Validate audio file
    try:
        audio_bytes, file_metadata = await validate_audio_file(file)
    except fastapi.HTTPException:
        raise  # Re-raise validation errors as-is
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Audio file validation failed: {str(e)}"
        )

    # Step 3: Estimate audio duration
    duration_seconds = get_audio_duration_estimate(audio_bytes, file_metadata["content_type"])

    # Step 4: Validate and normalize language
    validated_language = validate_transcription_language(language)

    # Step 5: Transcribe with Whisper API
    transcription, whisper_error, whisper_latency_ms, whisper_model = await transcribe_audio_with_whisper(
        audio_bytes=audio_bytes,
        filename=file_metadata["filename"], 
        language=validated_language
    )

    # Step 6: Create temporary file for processing
    temp_file_path = ""
    audio_url = ""
    save_error = None
    try:
        temp_file_path, audio_url = await save_audio_file(
            audio_bytes=audio_bytes,
            filename=file_metadata["filename"],
            user_id=current_user.id,
            question_attempt_id=question_attempt_id_int
        )
        # Note: audio_url is just a reference name for database storage
        # temp_file_path is the actual temporary file that will be cleaned up
    except Exception as e:
        save_error = str(e)

    # Step 7: Update question attempt in database (only metadata, no file storage)
    saved = False
    db_save_error = None
    if audio_url and transcription and not save_error:
        try:
            updated_qa = await question_repo.update_audio_transcription(
                question_attempt_id=question_attempt_id_int,
                audio_url=audio_url,  # Just a reference name, not a real file path
                transcription=transcription
            )
            saved = updated_qa is not None
        except Exception as e:
            db_save_error = str(e)
            saved = False

    # Step 8: Clean up temporary file
    if temp_file_path:
        await cleanup_temp_audio_file(temp_file_path)

    # Step 9: Extract metadata for response
    word_count = extract_word_count(transcription)
    
    # Determine overall save status and error message
    final_save_error = save_error or db_save_error
    final_saved = saved and not final_save_error
    
    # Generate status message
    if final_saved:
        message = "Audio uploaded and transcribed successfully"
    elif transcription and not whisper_error:
        message = "Audio transcribed but failed to save"
    elif whisper_error:
        message = f"Audio uploaded but transcription failed: {whisper_error}"
    else:
        message = "Audio upload failed"

    return AudioTranscriptionResponse(
        question_attempt_id=question_attempt_id_int,
        filename=file_metadata["filename"],
        content_type=file_metadata["content_type"],
        size=file_metadata["size"],
        duration_seconds=duration_seconds,
        audio_url=audio_url,
        transcription=strip_word_level_data(transcription),
        word_count=word_count,
        whisper_model=whisper_model,
        whisper_latency_ms=whisper_latency_ms,
        whisper_error=whisper_error,
        message=message,
        saved=final_saved,
        save_error=final_save_error,
    )
