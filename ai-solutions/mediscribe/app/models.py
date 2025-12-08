from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute
from app.config import settings
from datetime import datetime
import uuid


class User(Model):
    class Meta:
        table_name = "healthcare_poc_users"
        region = settings.AWS_REGION
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY

    username = UnicodeAttribute(hash_key=True)
    password_hash = UnicodeAttribute()
    role = UnicodeAttribute(default="clinician")


class Transcript(Model):
    class Meta:
        table_name = "healthcare_poc_transcripts"
        region = settings.AWS_REGION
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY

    id = UnicodeAttribute(hash_key=True, default=lambda: str(uuid.uuid4()))
    user_id = UnicodeAttribute()
    s3_audio_key = UnicodeAttribute()
    s3_transcript_key = UnicodeAttribute(null=True)
    summary = UnicodeAttribute(null=True)
    soap_note = UnicodeAttribute(null=True)  # JSON-serialized SOAP note
    created_at = UTCDateTimeAttribute(default=datetime.now)
    status = UnicodeAttribute(default="processing")  # processing, completed, failed


class Chat(Model):
    class Meta:
        table_name = "chats"
        region = settings.AWS_REGION
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY

    id = UnicodeAttribute(hash_key=True, default=lambda: str(uuid.uuid4()))
    user_id = UnicodeAttribute()
    transcript_id = UnicodeAttribute()
    role = UnicodeAttribute()  # 'user' or 'assistant'
    message = UnicodeAttribute()
    created_at = UTCDateTimeAttribute(default=datetime.now)
