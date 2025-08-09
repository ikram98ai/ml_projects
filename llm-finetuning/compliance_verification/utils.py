from fastapi import UploadFile, HTTPException
from typing import List
import base64, io
from markitdown import MarkItDown



async def get_base64_urls(images: List[UploadFile] ) -> str:
    base64_urls = []
    # If UploadFile instances are provided, convert to base64
    for file in images:
        try:
            print(f"Processing file: {file.filename}")
            content = await file.read()
            media_type = file.content_type or 'image/jpeg'
            base64_image = base64.b64encode(content).decode('utf-8')
            base64_urls.append(f"data:{media_type};base64,{base64_image}")

        except Exception as e:
            print(f"Error processing file {file.filename}: {e}")
            raise HTTPException(400, f"Error processing file {file.filename}: {str(e)}")
            
    return base64_urls



async def get_docx_contents(doc: UploadFile) -> str:
    md = MarkItDown()
    # If UploadFile instances are provided, read their contents
    if doc.content_type != "application/vnd.openxmlformats-officedocument.wordprocessingml.document" and not doc.filename.endswith(".docx"):
        print(f"File type must be document(.docx), current file type is {doc.content_type}")
        raise HTTPException(403, f"File type must be document(.docx), current file type is {doc.content_type}")
    try:
        print(f"Processing file: {doc.filename}")
        file_bytes = await doc.read()
        buffer = io.BytesIO(file_bytes)
        result = md.convert(buffer)
        fname = doc.filename.split('.doc')[0]
        return fname+", "+ result.text_content

    except Exception as e:
        print(f"Error processing file {doc.filename}: {e}")
        raise HTTPException(400, f"Error processing file {doc.filename}: {str(e)}")
