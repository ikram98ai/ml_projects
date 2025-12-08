import boto3
from botocore.exceptions import ClientError
from app.config import settings
import logging

logger = logging.getLogger(__name__)

s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION,
)


def upload_file(file_obj, object_name):
    """Upload a file to an S3 bucket"""
    try:
        s3_client.upload_fileobj(file_obj, settings.S3_BUCKET_NAME, object_name)
    except ClientError as e:
        logger.error(e)
        return False
    return True


def get_presigned_url(object_name, expiration=3600):
    """Generate a presigned URL to share an S3 object"""
    try:
        response = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET_NAME, "Key": object_name},
            ExpiresIn=expiration,
        )
    except ClientError as e:
        logger.error(e)
        return None
    return response


def upload_text(content, object_name):
    """Upload text content to S3"""
    try:
        s3_client.put_object(
            Body=content, Bucket=settings.S3_BUCKET_NAME, Key=object_name
        )
    except ClientError as e:
        logger.error(e)
        return False
    return True


def get_text_from_s3(object_name):
    """Download text content from S3"""
    try:
        response = s3_client.get_object(Bucket=settings.S3_BUCKET_NAME, Key=object_name)
        return response["Body"].read().decode("utf-8")
    except ClientError as e:
        logger.error(e)
        return None
