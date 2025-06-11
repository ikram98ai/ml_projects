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

#############################################################Compliance Verification Agent#############################################################



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
        print(f"Search Result\n##Start## \n{results[:200]}...\n##End##")
        return results
    except Exception as e:
        print(f"Error in pinecone_search_documents: {str(e)}")
        return f"Error searching documents: {str(e)}"

# class ComplianceOutput(BaseModel):
#     compliance_verification: Literal["Compliant", "Non-compliant"]
#     violation_reason: str | None



compliance_instruction = """You are a licensing compliance expert specifically for university and Greek organization apparel. 
Your task is to evaluate designs against the established licensing guidelines of these specific organizations by using `pinecone_search_documents` tool.
Determine if a design meets all requirements or violates any rules. For each evaluation, you must respond in a strict two-line format: 
first indicating 'Compliance Status: Compliant' or 'Compliance Status: Non-compliant', followed by 'Violation Reason:' with either 'None' for compliant designs or a brief explanation for non-compliant designs. 
Never elaborate beyond this format. Base your evaluation solely on actual violations present in the image, not hypothetical concerns."""

  
compliance_agent = Agent(
    name="Compliance verifier",
    # model= model,
    model="gpt-4o",
    tools= [pinecone_search_documents],
    instructions=compliance_instruction,
    # output_type=ComplianceOutput,
    model_settings=ModelSettings(tool_choice="auto", temperature=0.1),    
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
    print(f"Compliance verification result: {result.final_output}")
    return result.final_output

#############################################################Trademark Detection Agent#############################################################

# class TrademarkOutput(BaseModel):
#     trademark_detected: Literal["Yes", "No"]
#     organization: str | None


trademark_instruction = """You are an expert in trademark identification for apparel designs. Your task is to analyze images of apparel and determine
if they contain licensed trademarks such as Greek organization letters (fraternities/sororities) or collegiate/university marks. Your response
must strictly follow this two-line format: first indicating 'Licensed trademarks detected: Yes' or 'Licensed trademarks detected: No', followed
by 'Organization:' with either the specific organization/university name(s) identified or 'None' if no trademarks are detected."""

  
trademark_agent = Agent(
    name="Trademark detector",
    # model= model,
    model="gpt-4o",
    # output_type= TrademarkOutput,
    instructions=trademark_instruction,    
    model_settings=ModelSettings(temperature=0.1),
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
    print(f"Trademark detection result: {result.final_output}")
    return result.final_output
