from fastapi import FastAPI
from mangum import Mangum
from typing import List
from ai.ai_agents import verifier_agent_runner


app = FastAPI()
handler = Mangum(app)


@app.post("/compliance")
async def compliance_verification(urls:List[str]):
    print(f"Received URLs: {urls}")

    output = await verifier_agent_runner(urls)

    return {
        "output": output
    }