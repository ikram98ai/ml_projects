from fastapi import UploadFile, HTTPException
from typing import List
import base64, logging, io
from docx import Document

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



async def get_base64_urls(images: List[UploadFile] ) -> str:
    base64_urls = []
    # If UploadFile instances are provided, convert to base64
    logger.info("Processing images as UploadFile instances.")
    for file in images:
        try:
            logger.info(f"Processing file: {file.filename}")
            content = await file.read()
            media_type = file.content_type or 'image/jpeg'
            base64_image = base64.b64encode(content).decode('utf-8')
            base64_urls.append(f"data:{media_type};base64,{base64_image}")

        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {e}")
            raise HTTPException(400, f"Error processing file {file.filename}: {str(e)}")
            
    return base64_urls



async def get_docx_contents(docs: List[UploadFile]) -> List[str]:
    contents = []
    # If UploadFile instances are provided, read their contents
    for file in docs:
        if file.content_type != "application/vnd.openxmlformats-officedocument.wordprocessingml.document" and not file.filename.endswith(".docx"):
            logger.error(f"File type must be document(.docx), current file type is {file.content_type}")
            raise HTTPException(403, f"File type must be document(.docx), current file type is {file.content_type}")
        try:
            logger.info(f"Processing file: {file.filename}")
            file_bytes = await file.read()
            buffer = io.BytesIO(file_bytes)
            doc = Document(buffer)
            content = "\n".join([para.text for para in doc.paragraphs])
            fname = file.filename.split('.doc')[0]
            contents.append(fname+", "+content)  

        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {e}")
            raise HTTPException(400, f"Error processing file {file.filename}: {str(e)}")
    return contents
