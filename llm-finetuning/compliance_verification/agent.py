from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool, ModelSettings
from rag import get_index, query_index
from pydantic import BaseModel, model_validator
from typing import  Literal
import asyncio, os, base64, requests

gemini_client = AsyncOpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.getenv("GEMINI_API_KEY")
)

model = OpenAIChatCompletionsModel(
    openai_client=gemini_client,
    model="gemini-2.0-flash"
)

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

class AgentOutput(BaseModel):
    compliance_status: Literal["Compliant", "Non-compliant"]
    violation_reason: str | None

    @model_validator(mode='after')
    def validate_violation_reason(self) -> 'AgentOutput':
        if self.compliance_status == "Compliant" and self.violation_reason is not None:
            raise ValueError("violation_reason must be None when compliance_status is 'Compliant'")
        if self.compliance_status == "Non-compliant" and not self.violation_reason:
            raise ValueError("violation_reason must be a non-empty string when compliance_status is 'Non-compliant'")
        return self
  


instruction = """You are a licensing compliance expert specifically for university and Greek organization apparel. 
Your task is to evaluate designs against the established licensing guidelines of these specific organizations.
Determine if a design meets all requirements or violates any rules. For each evaluation, you must respond in a strict two-line format: 
first indicating 'Compliance Status: Compliant' or 'Compliance Status: Non-compliant', followed by 'Violation Reason:' with either 'None' for compliant designs or a brief explanation for non-compliant designs. 
Never elaborate beyond this format. Base your evaluation solely on actual violations present in the image, not hypothetical concerns."""

  
verifier_agent = Agent(
    name="Compliance verifier",
    model= model,
    tools= [pinecone_search_documents],
    # output_type= AgentOutput,
    instructions=instruction,
    model_settings=ModelSettings(tool_choice="auto" ),
    
)


def download_and_encode_image(url: str) -> str:
    """Download image from URL and encode it as base64."""
    response = requests.get(url)
    if response.status_code == 200:
        image_data = response.content
        # Detect image format from URL or content-type
        content_type = response.headers.get('content-type', 'image/jpeg')
        if 'jpeg' in content_type or 'jpg' in url.lower():
            media_type = 'image/jpeg'
        elif 'png' in content_type or 'png' in url.lower():
            media_type = 'image/png'
        elif 'webp' in content_type or 'webp' in url.lower():
            media_type = 'image/webp'
        else:
            media_type = 'image/jpeg'  # default
        
        base64_image = base64.b64encode(image_data).decode('utf-8')
        return f"data:{media_type};base64,{base64_image}"
    else:
        raise Exception(f"Failed to download image: {response.status_code}")

async def main(urls):
    # Convert URLs to base64 data URIs and create content list
    content_list = []
    
    for url in urls:
        try:
            base64_data_uri = download_and_encode_image(url)
            content_list.append({
                "type": "input_image", 
                "detail": "auto", 
                "image_url": base64_data_uri
            })
        except Exception as e:
            print(f"Error processing image {url}: {e}")
            return
    
    result = await Runner.run(verifier_agent, input=[
        {
            "role": "user",
            "content": content_list,
        },
        {
            "role": "user",
            "content": "Review this apparel design information for compliance with licensing rules. Provide compliance status and violation reason, if any.",
        },
    ])
    print(result.final_output)

if __name__ == "__main__":
    urls = ["https://res.cloudinary.com/dsnai3oon/image/upload/v1740658670/cropped_images/9a3003a295bf13d10d2e1f0f7091e245_1740658669.jpg"]
    asyncio.run(main(urls))
