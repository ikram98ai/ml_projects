from agents import Agent, Runner, function_tool, ModelSettings
from ai.rag import get_index, query_index
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Literal
from openai import OpenAI
from ai.prompt import compliance_instruction, system_prompt, design_analysis_prompt, general_rules_prompt
from agents import AsyncOpenAI, OpenAIChatCompletionsModel
import os

load_dotenv()

client = OpenAI()

def get_gemini_model(model_name:str="gemini-2.0-flash"):
    gemini_client = AsyncOpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=os.getenv("GEMINI_API_KEY")
    )
    
    model = OpenAIChatCompletionsModel(
        openai_client=gemini_client,
        model=model_name
    )

    return model


pinecone_index = get_index()

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

class ComplianceOutput(BaseModel):
    compliance_status: Literal["Compliant", "Non-compliant"]
    violation_reason: str | None
    # confidence_score: int = Field(description="Confidence score from `search_licensing_rules` tool or around 99 if `search_licensing_rules` tool is not used.")

  
def compliance_flow(base64_urls: list[str]):
    design_analysis =  client.responses.create(
        model="o3",
        input=[{
            "role": "user",
            "content": get_content_list(base64_urls)
        },
        {
            "role": "user",
            "content": design_analysis_prompt
        }],
    )
    analysis = design_analysis.output_text
    print("Design analysis response: ", analysis)
  
    general_rule_evaluation =  client.responses.parse(
        model="o3",
        input=[{
            "role": "assistant",
            "content": general_rules_prompt
        },
        {
            "role": "user",
            "content": analysis 
        }],
        text_format= ComplianceOutput
    )

    evaluation = general_rule_evaluation.output_parsed

    print("General rule evaluation response: ", evaluation)
    if evaluation.compliance_status == "Non-compliant":
        return   {"compliance_status": evaluation.compliance_status, "violation_reason": evaluation.violation_reason, "confidence_score" : int(context[0]*100)}


    context = query_index(pinecone_index,analysis)

    licensing_rule_evaluation =  client.responses.parse(
        model="o3",
        input=[{
            "role": "assistant",
            "content": system_prompt.format(analysis,context[1])
        },
        {
            "role": "user",
            "content": "Review this apparel design for compliance with licensing rules. Provide compliance status and violation reason, if any."
        }],
        text_format= ComplianceOutput
    )

    evaluation = licensing_rule_evaluation.output_parsed

    print("Licensing rule evaluation response: ", evaluation)

    return  {"compliance_status": evaluation.compliance_status, "violation_reason": evaluation.violation_reason, "confidence_score" : int(context[0]*100)}


@function_tool
def search_licensing_rules(query: str) -> str:
    """
    Search for relevant licensing rules using semantic query
    Args:
        query: Natural language query for the vector database
    Returns:
        Search results from the vector database
    """
    try:
        if not query.strip():
            return "Query cannot be empty"   
        results = query_index(pinecone_index, query)
        return f"`search_licensing_rules` tool's result with confidence score of {results[0]}: {results[1]}"
    except Exception as e:
        print(f"Error in search_licensing_rules: {str(e)}")
        return f"Error searching documents: {str(e)}"

compliance_agent = Agent(
    name="Compliance verifier",
    model=get_gemini_model('gemini-2.5-flash'),#"o3",
    # tools= [search_licensing_rules],
    instructions=compliance_instruction,
    output_type=ComplianceOutput,
    # model_settings=ModelSettings(tool_choice="auto", temperature=0.1),    
)


async def compliance_agent_runner(base64_urls: list[str]):

    design_analysis =  client.responses.create(
        model="o4-mini",
        input=[{
            "role": "user",
            "content": get_content_list(base64_urls)
        },
        {
            "role": "user",
            "content": design_analysis_prompt
        }],
    )

    analysis = design_analysis.output_text

    score, context = query_index(pinecone_index,analysis)

    result = await Runner.run(compliance_agent, input=[
        {
            "role": "system",
            "content":"Licensing rules: " + context,
        }, {
            "role": "user",
            "content": "Review the following apperal design analysis for compliance with licensing rules. Provide compliance status and violation reason, if any." + "\nApperal design analysis: "+ analysis ,
        },
    ])
    print(f"Compliance verification result: {result.final_output}")
 
    return  {"compliance_status": result.final_output.compliance_status, 
             "violation_reason": result.final_output.violation_reason, 
             "confidence_score" : int(score*100)}

#############################################################Trademark Detection Agent#############################################################

class TrademarkOutput(BaseModel):
    trademark_detected: Literal["Yes", "No"]
    organization: str | None


trademark_instruction = """You are an expert in trademark identification for apparel designs. Your task is to analyze images of apparel and determine
if they contain licensed trademarks such as Greek organization letters (fraternities/sororities) or collegiate/university marks. Your response
must strictly follow this two-line format: first indicating 'Licensed trademarks detected: Yes' or 'Licensed trademarks detected: No', followed
by 'Organization:' with either the specific organization/university name(s) identified or 'None' if no trademarks are detected."""

  
trademark_agent = Agent(
    name="Trademark detector",
    model="o3",
    output_type= TrademarkOutput,
    instructions=trademark_instruction,    
    # model_settings=ModelSettings(temperature=0.1),
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
