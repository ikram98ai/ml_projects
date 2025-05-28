from fastapi import FastAPI, UploadFile, HTTPException,File
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from typing import List
import logging
from ai.ai_agents import compliance_agent_runner, trademark_agent_runner
from ai.rag import get_index, upsert_data
from utils import get_base64_urls, get_docx_contents

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


@app.post("/upsert")
async def upsert_into_pinecone(docs: List[UploadFile] = File(..., description="Upload one or more docx files to upsert into the pinecone index.")):
    try:
        contents = await get_docx_contents(docs)
        index = get_index()

        output = upsert_data(index, contents)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error during upserting data to pinecone index: {e}")
        raise HTTPException(500,str(e))
    return {"output": output }



handler = Mangum(app)