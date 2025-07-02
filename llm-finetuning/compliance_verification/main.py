from fastapi import FastAPI, UploadFile, HTTPException,File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from mangum import Mangum
from typing import List
from ai.ai_agents import compliance_agent_runner, trademark_agent_runner, compliance_flow
from ai.rag import get_index, upsert_data
from utils import get_base64_urls, get_docx_contents
import traceback


app = FastAPI(version="2.9.2")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return RedirectResponse("/docs")



@app.post("/compliance_flow")
async def compliance_verification_flow(images: List[UploadFile] = File(..., description="Upload one or two image files for compliance verification.")):
    try:
        base64_urls = await get_base64_urls(images[:2])
        # output = await compliance_agent_runner(base64_urls)
        output = compliance_flow(base64_urls)

    except HTTPException as e:
        traceback.print_exc()
        raise e
    except Exception as e:
        print(f"Error during compliance verification: {e}")
        traceback.print_exc()
        raise HTTPException(500,str(e))
    return output


@app.post("/compliance_agent")
async def compliance_verification_agent(images: List[UploadFile] = File(..., description="Upload one or two image files for compliance verification.")):
    try:
        base64_urls = await get_base64_urls(images[:2])
        output = await compliance_agent_runner(base64_urls)
        # output = compliance(base64_urls)

    except HTTPException as e:
        traceback.print_exc()
        raise e
    except Exception as e:
        print(f"Error during compliance verification: {e}")
        traceback.print_exc()
        raise HTTPException(500,str(e))
    return output



@app.post("/trademark")
async def trademark_detection(images: List[UploadFile] = File(..., description="Upload one or two image files for trademark detection.")):
    try:
        base64_urls = await get_base64_urls(images[:2])
        output = await trademark_agent_runner(base64_urls)

    except HTTPException as e:
        traceback.print_exc()
        raise e
    except Exception as e:
        print(f"Error during trademark detection: {e}")
        traceback.print_exc()
        raise HTTPException(500,str(e))
    return {"output": output }


@app.post("/upsert")
async def upsert_into_pinecone(docs: List[UploadFile] = File(..., description="Upload one or more docx files to upsert into the pinecone index.")):
    try:
        contents = await get_docx_contents(docs)
        index = get_index()

        output = upsert_data(index, contents)

    except HTTPException as e:
        traceback.print_exc()
        raise e

    except Exception as e:
        print(f"Error during upserting data to pinecone index: {e}")
        traceback.print_exc()
        raise HTTPException(500,str(e))
    return output



handler = Mangum(app)