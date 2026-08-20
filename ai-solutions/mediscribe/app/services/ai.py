import google.generativeai as genai
from app.config import settings
import logging
import json
import typing_extensions as typing

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.GEMINI_API_KEY)


class SoapNote(typing.TypedDict):
    subjective: str
    objective: str
    assessment: str
    plan: str


class ConsultationResult(typing.TypedDict):
    transcript: str
    soap_note: SoapNote


def upload_to_gemini(path, mime_type="audio/mp3"):
    """Uploads the given file to Gemini."""
    file = genai.upload_file(path, mime_type=mime_type)
    return file


def process_audio(audio_file_path) -> ConsultationResult | None:
    """Transcribes audio and generates SOAP note using Gemini."""
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")

        gemini_file = upload_to_gemini(audio_file_path)

        prompt = """
        You are an expert medical scribe assisting a doctor. 
        1. Transcribe the audio of this medical consultation verbatim.
        2. Create a structured SOAP note (Subjective, Objective, Assessment, Plan) based on the consultation.
        """

        response = model.generate_content(
            [prompt, gemini_file],
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=ConsultationResult,
            ),
        )

        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        return None


def ask_question(transcript: str, question: str, history: list = None):
    """Asks a question about the transcript."""
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")

        system_instruction = f'You are a helpful medical assistant. You have access to the following consultation transcript: "{transcript}". Answer the doctor\'s questions based strictly on this context.'

        chat = model.start_chat(history=history or [])

        # If history is empty, we might want to inject the system instruction or context in the first message
        # But for simplicity with the SDK, we can just prepend context to the question if it's a single turn,
        # or rely on the system instruction if supported by the specific model instantiation way.
        # simpler approach for this function:

        prompt = f"{system_instruction}\n\nQuestion: {question}"
        response = chat.send_message(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        return None
