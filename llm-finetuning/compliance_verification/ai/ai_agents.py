from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool, ModelSettings
from ai.rag import get_index, query_index
from pydantic import BaseModel, model_validator
from typing import  Literal
import asyncio, os

gemini_client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.getenv("GEMINI_API_KEY")
)

model = OpenAIChatCompletionsModel(
    openai_client=gemini_client,
    model="gemini-2.0-flash"
)


def get_content_list(base64_urls: list[str]):
    content_list = []
    
    for base64_data_uri in base64_urls:
        content_list.append({
            "type": "input_image", 
            "detail": "auto", 
            "image_url": base64_data_uri
        })
    return content_list

#############################################################Compliance Verification Agent#############################################################


@function_tool
def pinecone_search_documents(query: str) -> str:
    """
    Search for relevant licensing rules based on the apparel design information that is stored within the vector database using a semantic query.
    Args:
        query (str): The natural language query to search the vector database.
    Returns:
        str: The search results from the vector database.
    """
    print(f"Querying index with: {query}")
    index = get_index()
    results = query_index(index, query)
    return results  


compliance_instruction = """You are a licensing compliance expert specifically for university and Greek organization apparel. 
Your task is to evaluate designs against the established licensing guidelines of these specific organizations.
Determine if a design meets all requirements or violates any rules. For each evaluation, you must respond in a strict two-line format: 
first indicating 'Compliance Status: Compliant' or 'Compliance Status: Non-compliant', followed by 'Violation Reason:' with either 'None' for compliant designs or a brief explanation for non-compliant designs. 
Never elaborate beyond this format. Base your evaluation solely on actual violations present in the image, not hypothetical concerns."""

  
compliance_agent = Agent(
    name="Compliance verifier",
    model= model,
    tools= [pinecone_search_documents],
    instructions=compliance_instruction,
    model_settings=ModelSettings(tool_choice="auto" ),
    
)



async def compliance_agent_runner(base64_urls: list[str]):

    result = await Runner.run(compliance_agent, input=[
        {
            "role": "user",
            "content": get_content_list(base64_urls),
        }, {
            "role": "user",
            "content": "Review this apparel design information for compliance with licensing rules. Provide compliance status and violation reason, if any.",
        },
    ])
    return result.final_output

#############################################################Trademark Detection Agent#############################################################

class TrademarkOutput(BaseModel):
    trademark_detected: Literal["Yes", "No"]
    organization: str | None

    @model_validator(mode='after')
    def validate_trademark_detection(self) -> 'TrademarkOutput':
        if self.trademark_detected == "No" and self.organization is not None:
            raise ValueError("organization must be None when trademark_detected is 'No'")
        if self.trademark_detected == "Yes" and not self.organization:
            raise ValueError("organization must be a non-empty string when trademark_detected is 'Yes'")
        return self
  


trademark_instruction = """You are an expert in trademark identification for apparel designs. Your task is to analyze images of apparel and determine
if they contain licensed trademarks such as Greek organization letters (fraternities/sororities) or collegiate/university marks. Your response
must strictly follow this two-line format: first indicating 'Licensed trademarks detected: Yes' or 'Licensed trademarks detected: No', followed
by 'Organization:' with either the specific organization/university name(s) identified or 'None' if no trademarks are detected."""

  
trademark_agent = Agent(
    name="Trademark detector",
    model= model,
    output_type= TrademarkOutput,
    instructions=trademark_instruction,    
)

async def trademark_agent_runner(base64_urls: list[str]):
    
    result = await Runner.run(trademark_agent, input=[
        {
            "role": "user",
            "content": get_content_list(base64_urls),
        },{
            "role": "user",
            "content": "Examine these apparel images and identify if they contain licensed marks or Greek letters. If yes, name the Greek organization or university associated.",
        },
    ])
    return result.final_output


if __name__ == "__main__":
    urls = ["https://res.cloudinary.com/dsnai3oon/image/upload/v1740658670/cropped_images/9a3003a295bf13d10d2e1f0f7091e245_1740658669.jpg"]
    asyncio.run(compliance_agent_runner(urls))
