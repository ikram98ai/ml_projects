from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException
from app.api.deps import get_current_user
from app.models import User, Transcript, Chat
from app.services.storage import upload_file, upload_text, get_text_from_s3
from app.services.ai import process_audio, ask_question
import json
import shutil
import os
import uuid

router = APIRouter()


def process_audio_task(transcript_id: str, file_path: str):
    try:
        transcript_record = Transcript.get(transcript_id)

        # 1. Process audio (transcribe + generate SOAP note)
        result = process_audio(file_path)
        if not result:
            transcript_record.status = "failed"
            transcript_record.save()
            return

        # 2. Save transcript to S3
        transcript_key = f"transcripts/{transcript_id}.txt"
        upload_text(result["transcript"], transcript_key)

        # 3. Update DB with transcript, SOAP note, and summary
        transcript_record.s3_transcript_key = transcript_key
        transcript_record.soap_note = json.dumps(result["soap_note"])
        # Keep summary for backward compatibility (can be removed later)
        transcript_record.summary = f"S: {result['soap_note']['subjective']}\nO: {result['soap_note']['objective']}\nA: {result['soap_note']['assessment']}\nP: {result['soap_note']['plan']}"
        transcript_record.status = "completed"
        transcript_record.save()

        # Cleanup local file
        if os.path.exists(file_path):
            os.remove(file_path)

    except Exception as e:
        print(f"Error processing audio: {e}")
        try:
            transcript_record = Transcript.get(transcript_id)
            transcript_record.status = "failed"
            transcript_record.save()
        except Exception as e:
            print(f"Also failed to update transcript status: {e}")


@router.post("/upload")
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    # Save temp file
    file_id = str(uuid.uuid4())
    ext = file.filename.split(".")[-1]
    temp_filename = f"temp_{file_id}.{ext}"

    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Upload to S3
    s3_key = f"audio/{file_id}.{ext}"
    with open(temp_filename, "rb") as f:
        upload_file(f, s3_key)

    # Create DB record
    transcript = Transcript(
        id=file_id,
        user_id=current_user.username,
        s3_audio_key=s3_key,
        status="processing",
    )
    transcript.save()

    # Trigger background processing
    background_tasks.add_task(process_audio_task, file_id, temp_filename)

    return {"id": file_id, "status": "processing"}


@router.get("/transcripts")
async def list_transcripts(current_user: User = Depends(get_current_user)):
    # PynamoDB scan is expensive, but for POC it's fine.
    # Ideally use a GSI on user_id.
    # For now, we will just scan and filter (inefficient but simple for POC).
    # Or better, if we had a GSI.
    # Let's assume we scan.
    results = []
    for item in Transcript.scan(Transcript.user_id == current_user.username):
        results.append(
            {
                "id": item.id,
                "status": item.status,
                "created_at": item.created_at,
                "summary": item.summary[:100] + "..." if item.summary else None,
            }
        )
    return results


@router.get("/{transcript_id}")
async def get_transcript(
    transcript_id: str, current_user: User = Depends(get_current_user)
):
    try:
        transcript = Transcript.get(transcript_id)
        # Check ownership
        if transcript.user_id != current_user.username:
            raise HTTPException(status_code=403, detail="Not authorized")

        soap_note = None
        if transcript.soap_note:
            try:
                soap_note = json.loads(transcript.soap_note)
            except Exception as e:
                print("Failed to parse SOAP note JSON", str(e))

        # Load recent 20 chat messages
        chats = []
        for chat in Chat.scan(Chat.transcript_id == transcript_id, limit=20):
            chats.append(
                {
                    "id": chat.id,
                    "role": chat.role,
                    "message": chat.message,
                    "created_at": chat.created_at,
                }
            )

        # Sort by created_at and get last 20
        chats.sort(key=lambda x: x["created_at"])
        chats = chats[-20:]

        return {
            "id": transcript.id,
            "status": transcript.status,
            "summary": transcript.summary,
            "soap_note": soap_note,
            "created_at": transcript.created_at,
            "chats": chats,
        }
    except Transcript.DoesNotExist:
        raise HTTPException(status_code=404, detail="Transcript not found")


@router.post("/{transcript_id}/regenerate")
async def regenerate_summary(
    transcript_id: str, current_user: User = Depends(get_current_user)
):
    # In a real app, we would fetch the transcript text from S3 first
    # For now, let's assume we can't easily regenerate without fetching S3 content
    # This is a placeholder for the logic
    return {"message": "Not implemented in POC yet"}


@router.post("/{transcript_id}/ask")
async def ask_transcript_question(
    transcript_id: str, question: str, current_user: User = Depends(get_current_user)
):
    try:
        transcript = Transcript.get(transcript_id)

        # Check ownership
        if transcript.user_id != current_user.username:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Check if transcript is ready
        if transcript.status != "completed":
            raise HTTPException(status_code=400, detail="Transcript not ready yet")

        # Get transcript text from S3
        if not transcript.s3_transcript_key:
            raise HTTPException(status_code=400, detail="Transcript text not available")

        transcript_text = get_text_from_s3(transcript.s3_transcript_key)
        if not transcript_text:
            raise HTTPException(status_code=500, detail="Failed to retrieve transcript")

        # Ask question
        answer = ask_question(transcript_text, question)
        if not answer:
            raise HTTPException(status_code=500, detail="Failed to generate answer")

        # Store user question in Chat model
        user_chat = Chat(
            user_id=current_user.username,
            transcript_id=transcript_id,
            role="user",
            message=question,
        )
        user_chat.save()

        # Store assistant answer in Chat model
        assistant_chat = Chat(
            user_id=current_user.username,
            transcript_id=transcript_id,
            role="assistant",
            message=answer,
        )
        assistant_chat.save()

        return {"answer": answer}
    except Transcript.DoesNotExist:
        raise HTTPException(status_code=404, detail="Transcript not found")
