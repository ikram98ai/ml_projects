# Healthcare AI Audio POC

This is a Proof of Concept for a healthcare application that integrates AI and audio processing.

## Features
- **Audio Recording/Upload**: Record patient consultations or upload audio files.
- **AI Transcription & Summarization**: Uses Google Gemini to transcribe and summarize audio.
- **Secure Storage**: Stores audio and transcripts in AWS S3 and metadata in PynamoDB.
- **Modern UI**: Apple-like aesthetic using simple HTML/CSS/JS.

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**:
   Copy `.env.example` to `.env` and fill in your credentials:
   - AWS Credentials (for S3 and DynamoDB)
   - Google Gemini API Key

3. **Run the Application**:
   ```bash
   uvicorn app.main:app --reload
   ```

4. **Access the App**:
   Open `http://localhost:8000` in your browser.

## Usage
1. **Login**: Use any username/password (User creation is manual in DB for POC, or use the registration endpoint if added. *Note: For this POC, you might need to manually create a user in DynamoDB or add a register endpoint. Wait, I didn't add a register endpoint. I should probably add a script to create a user.*)

## Creating a User
Since there is no registration UI, use the provided script `create_user.py` (to be created) or add a user to the DynamoDB table `healthcare_poc_users` with `username` and `password_hash`.

## Tech Stack
- **Backend**: FastAPI
- **Database**: PynamoDB (DynamoDB)
- **Storage**: AWS S3
- **AI**: Google Gemini
- **Frontend**: Jinja2 Templates + Vanilla JS/CSS
