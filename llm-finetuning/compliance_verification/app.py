from fastapi import FastAPI
from mangum import Mangum
from typing import List
from ai.ai_agents import compliance_agent_runner, trademark_agent_runner


app = FastAPI()
handler = Mangum(app)


@app.post("/compliance")
async def compliance_verification(urls:List[str]):
    print(f"Received URLs: {urls}")

    output = await compliance_agent_runner(urls)

    return {
        "output": output
    }

@app.post("/trademark")
async def trademark_detection(urls:List[str]):
    print(f"Received URLs: {urls}")

    output = await trademark_agent_runner(urls)

    return {
        "output": output
    }