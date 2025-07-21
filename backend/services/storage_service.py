import os
from fastapi import UploadFile
from typing import Optional
from pathlib import Path
import logging
from google.cloud import storage

logger = logging.getLogger(__name__)

class StorageService:
    """통합 스토리지 서비스 - GCS 및 로컬 파일 시스템 지원"""
    
    def __init__(self):
        self.storage_type = os.getenv('STORAGE_TYPE', 'local')  # local, gcs
        self.gcs_bucket_name = os.getenv('GCS_BUCKET_NAME')
        self.gcs_credentials = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        if self.storage_type == 'gcs':
            self.gcs_client = storage.Client()
            self.bucket = self.gcs_client.bucket(self.gcs_bucket_name)
            logger.info(f"GCS 스토리지 초기화 완료: {self.gcs_bucket_name}")
        else:
            logger.info("로컬 스토리지 사용")
    
    async def upload_file(self, file: UploadFile, folder: str, filename: str) -> str:
        """파일을 스토리지에 업로드"""
        try:
            if self.storage_type == 'gcs':
                return await self._upload_gcs(file, folder, filename)
            else:
                return await self._upload_local(file, folder, filename)
        except Exception as e:
            logger.error(f"파일 업로드 실패: {str(e)}")
            raise
    
    async def _upload_local(self, file: UploadFile, folder: str, filename: str) -> str:
        """로컬 파일 시스템에 업로드"""
        upload_dir = Path(f"./uploads/{folder}")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / filename
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"로컬 업로드 완료: {file_path}")
        return f"uploads/{folder}/{filename}"
    
    async def _upload_gcs(self, file: UploadFile, folder: str, filename: str) -> str:
        """Google Cloud Storage에 업로드"""
        key = f"{folder}/{filename}"
        content = await file.read()
        blob = self.bucket.blob(key)
        blob.upload_from_string(content, content_type=file.content_type)
        # GCS 퍼블릭 URL
        gcs_url = f"https://storage.googleapis.com/{self.gcs_bucket_name}/{key}"
        logger.info(f"GCS 업로드 완료: {gcs_url}")
        return gcs_url
    
    def get_file_url(self, file_path: str) -> str:
        """파일 URL 반환"""
        if self.storage_type == 'gcs':
            if file_path.startswith('http'):
                return file_path
            return f"https://storage.googleapis.com/{self.gcs_bucket_name}/{file_path}"
        else:
            return f"/uploads/{file_path}"
    
    def delete_file(self, file_path: str) -> bool:
        """파일 삭제"""
        try:
            if self.storage_type == 'gcs':
                # GCS URL에서 키 추출
                if file_path.startswith('http'):
                    key = file_path.split(f"{self.gcs_bucket_name}/")[-1]
                else:
                    key = file_path
                blob = self.bucket.blob(key)
                blob.delete()
                logger.info(f"GCS 파일 삭제 완료: {key}")
                return True
            else:
                local_path = Path(f"./uploads/{file_path}")
                if local_path.exists():
                    local_path.unlink()
                    logger.info(f"로컬 파일 삭제 완료: {local_path}")
                    return True
        except Exception as e:
            logger.error(f"파일 삭제 실패: {str(e)}")
            return False
        
        return False
    
    def file_exists(self, file_path: str) -> bool:
        """파일 존재 여부 확인"""
        try:
            if self.storage_type == 'gcs':
                if file_path.startswith('http'):
                    key = file_path.split(f"{self.gcs_bucket_name}/")[-1]
                else:
                    key = file_path
                blob = self.bucket.blob(key)
                return blob.exists()
            else:
                local_path = Path(f"./uploads/{file_path}")
                return local_path.exists()
        except Exception as e:
            logger.error(f"파일 존재 확인 실패: {str(e)}")
            return False

# 전역 스토리지 서비스 인스턴스
storage_service = StorageService() 