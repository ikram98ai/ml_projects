from agents import Agent, Runner, function_tool, ModelSettings
from ai.rag import get_index, query_index
from dotenv import load_dotenv

load_dotenv()

def get_content_list(base64_urls: list[str]):
    content_list = []
    
    for base64_data_uri in base64_urls:
        content_list.append({
            "type": "input_image", 
            "detail": "auto", 
            "image_url": base64_data_uri
        })
    return content_list

@function_tool
def pinecone_search_documents(query: str) -> str:
    """
    Search for relevant licensing rules using semantic query
    
    Args:
        query: Natural language query for the vector database
        
    Returns:
        Search results from the vector database
    """
    try:
        if not query.strip():
            raise ValueError("Query cannot be empty")
            
        print(f"Querying index with: {query}")
        index = get_index()
        results = query_index(index, query)
        
        preview = results[:200]
        print(f"Search Result Preview:\n{preview}...")
        
        return results
        
    except Exception as e:
        print(f"Error in pinecone_search_documents: {str(e)}")
        return f"Error searching documents: {str(e)}"

# Compliance Verification Agent
compliance_instruction = """You are a licensing compliance expert specifically for university and Greek organization apparel. 
Your task is to evaluate designs against established licensing guidelines using the `pinecone_search_documents` tool.

IMPORTANT: You must respond in exactly this format:
Compliance Status: [Compliant/Non-compliant]
Violation Reason: [None/Brief explanation]

Base your evaluation solely on actual violations present in the image, not hypothetical concerns."""

compliance_agent = Agent(
    name="Compliance Verifier",
    model='gpt-4o',
    tools=[pinecone_search_documents],
    instructions=compliance_instruction,
    model_settings=ModelSettings(
        tool_choice="auto", 
        temperature=0.1
    ),    
)

# Trademark Detection Agent
trademark_instruction = """You are an expert in trademark identification for apparel designs. 
Analyze images to identify licensed trademarks such as Greek organization letters or collegiate marks.

IMPORTANT: You must respond in exactly this format:
Licensed trademarks detected: [Yes/No]
Organization: [Specific organization name(s)/None]"""

trademark_agent = Agent(
    name="Trademark Detector",
    model='gpt-4o',
    instructions=trademark_instruction,    
    model_settings=ModelSettings( temperature=0.1 ),
)

async def compliance_agent_runner(base64_urls: list[str]) -> str:

    try:
        if not base64_urls:
            raise ValueError("No images provided for compliance verification")
            
        content_list = get_content_list(base64_urls)
        
        result = await Runner.run(compliance_agent, input=[
            {
                "role": "user",
                "content": content_list,
            }, 
            {
                "role": "user",
                "content": "Review this apparel design for compliance with licensing rules. Provide compliance status and violation reason, if any.",
            },
        ])
        
        print(f"Compliance verification completed: {result.final_output}")
        return result.final_output
        
    except Exception as e:
        print(f"Error in compliance_agent_runner: {str(e)}")
        return f"Error during compliance verification: {str(e)}"

async def trademark_agent_runner(base64_urls: list[str]) -> str:

    try:
        if not base64_urls:
            raise ValueError("No images provided for trademark detection")
            
        content_list = get_content_list(base64_urls)
        
        result = await Runner.run(trademark_agent, input=[
            {
                "role": "user",
                "content": content_list,
            },
            {
                "role": "user",
                "content": "Examine these apparel images and identify licensed marks or Greek letters. If yes, name the organization or university.",
            },
        ])
        
        print(f"Trademark detection completed: {result.final_output}")
        return result.final_output
        
    except Exception as e:
        print(f"Error in trademark_agent_runner: {str(e)}")
        return f"Error during trademark detection: {str(e)}"
    
