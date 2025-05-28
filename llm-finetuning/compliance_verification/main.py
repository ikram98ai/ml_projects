from fastapi import FastAPI, UploadFile, HTTPException,File
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from typing import List
import base64, logging
from ai.ai_agents import compliance_agent_runner, trademark_agent_runner

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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

@app.get("/")
async def root():
    return {"message": "Welcome to Fresh Prints' app!"}


@app.post("/compliance")
async def compliance_verification(images: List[UploadFile] = File(..., description="Upload one or two image files for compliance verification.")):
    try:
        base64_urls = await get_base64_urls(images[:2])
        output = await compliance_agent_runner(base64_urls)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error during compliance verification: {e}")
        raise HTTPException(500,str(e))
    return { "output": output }


@app.post("/trademark")
async def trademark_detection(images: List[UploadFile] = File(..., description="Upload one or two image files for trademark detection.")):
    try:
        base64_urls = await get_base64_urls(images[:2])
        output = await trademark_agent_runner(base64_urls)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error during trademark detection: {e}")
        raise HTTPException(500,str(e))
    return {"output": output }


handler = Mangum(app)