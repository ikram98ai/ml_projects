from pynamodb.models import Model
from pynamodb.attributes import UnicodeAttribute
from app.config import settings

class User(Model):
    class Meta:
        table_name = "healthcare_poc_users"
        region = settings.AWS_REGION
        aws_access_key_id = settings.AWS_ACCESS_KEY_ID
        aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY

    username = UnicodeAttribute(hash_key=True)
    password_hash = UnicodeAttribute()
    role = UnicodeAttribute(default="clinician")
