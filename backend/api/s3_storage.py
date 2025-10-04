import boto3
import os
import uuid
from django.conf import settings
from botocore.exceptions import NoCredentialsError, ClientError
import logging
import sentry_sdk

logger = logging.getLogger(__name__)

class S3DocumentStorage:
    """
    Utility class for uploading and downloading documents to/from AWS S3
    """
    
    def __init__(self):
        self.s3_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize S3 client with credentials from settings"""
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            sentry_sdk.capture_exception(e, extras={
                "component": "s3_storage",
                "method": "_initialize_client"
            })
            self.s3_client = None
    
    def upload_document(self, file_path: str, user_id: str, filename: str) -> str:
        """
        Upload document to S3 and return the S3 key
        
        Args:
            file_path: Local file path to upload
            user_id: User ID for organizing files
            filename: Original filename
            
        Returns:
            S3 object key if successful, None if failed
        """
        if not self.s3_client or not settings.AWS_S3_BUCKET:
            logger.error("S3 client not initialized or bucket not configured")
            return None
            
        try:
            # Create a unique S3 key: users/{user_id}/documents/{uuid}_{filename}
            file_extension = os.path.splitext(filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            s3_key = f"users/{user_id}/documents/{unique_filename}"
            
            # Upload file to S3
            self.s3_client.upload_file(
                file_path,
                settings.AWS_S3_BUCKET,
                s3_key,
                ExtraArgs={
                    'ServerSideEncryption': 'AES256',
                    'Metadata': {
                        'user_id': user_id,
                        'original_filename': filename
                    }
                }
            )
            
            logger.info(f"Successfully uploaded {filename} to S3 with key: {s3_key}")
            return s3_key
            
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            sentry_sdk.capture_message(
                "AWS credentials not found",
                level="error",
                extras={"component": "s3_storage", "method": "upload_document"}
            )
            return None
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}")
            sentry_sdk.capture_exception(e, extras={
                "component": "s3_storage",
                "method": "upload_document",
                "user_id": user_id,
                "filename": filename
            })
            return None
        except Exception as e:
            logger.error(f"Unexpected error uploading to S3: {e}")
            sentry_sdk.capture_exception(e, extras={
                "component": "s3_storage",
                "method": "upload_document",
                "user_id": user_id,
                "filename": filename
            })
            return None
    
    def download_document(self, s3_key: str, local_path: str) -> bool:
        """
        Download document from S3 to local path
        
        Args:
            s3_key: S3 object key
            local_path: Local path to save the file
            
        Returns:
            True if successful, False if failed
        """
        if not self.s3_client or not settings.AWS_S3_BUCKET:
            logger.error("S3 client not initialized or bucket not configured")
            return False
            
        try:
            self.s3_client.download_file(
                settings.AWS_S3_BUCKET,
                s3_key,
                local_path
            )
            logger.info(f"Successfully downloaded {s3_key} from S3")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to download from S3: {e}")
            sentry_sdk.capture_exception(e, extras={
                "component": "s3_storage",
                "method": "download_document",
                "s3_key": s3_key
            })
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading from S3: {e}")
            sentry_sdk.capture_exception(e, extras={
                "component": "s3_storage",
                "method": "download_document",
                "s3_key": s3_key
            })
            return False
    
    def delete_document(self, s3_key: str) -> bool:
        """
        Delete document from S3
        
        Args:
            s3_key: S3 object key to delete
            
        Returns:
            True if successful, False if failed
        """
        if not self.s3_client or not settings.AWS_S3_BUCKET:
            logger.error("S3 client not initialized or bucket not configured")
            return False
            
        try:
            self.s3_client.delete_object(
                Bucket=settings.AWS_S3_BUCKET,
                Key=s3_key
            )
            logger.info(f"Successfully deleted {s3_key} from S3")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete from S3: {e}")
            sentry_sdk.capture_exception(e, extras={
                "component": "s3_storage",
                "method": "delete_document",
                "s3_key": s3_key
            })
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting from S3: {e}")
            sentry_sdk.capture_exception(e, extras={
                "component": "s3_storage",
                "method": "delete_document",
                "s3_key": s3_key
            })
            return False

# Module-level instance
s3_storage = S3DocumentStorage()