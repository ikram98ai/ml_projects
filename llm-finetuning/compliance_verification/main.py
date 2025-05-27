from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from typing import List
from ai.ai_agents import compliance_agent_runner, trademark_agent_runner
import logging

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
    return {"message": "FastAPI + OpenAI Lambda App is running!"}


@app.post("/compliance")
async def compliance_verification(urls:List[str]):
    logger.info(f"Received URLs: {urls}")
    try:
        output = await compliance_agent_runner(urls)
    except Exception as e:
        logger.error(f"Error during compliance verification: {e}")
        return {"error": str(e)}
    
    return {
        "output": output
    }

@app.post("/trademark")
async def trademark_detection(urls:List[str]):
    logger.info(f"Received URLs: {urls}")
    try:
        output = await trademark_agent_runner(urls)
    except Exception as e:
        logger.error(f"Error during trademark detection: {e}")
        return {"error": str(e)}
    
    return {
        "output": output
    }

handler = Mangum(app)
