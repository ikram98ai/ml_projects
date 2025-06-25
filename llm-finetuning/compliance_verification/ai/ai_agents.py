from agents import Agent, Runner, ModelSettings, function_tool
from openai.types.chat import ParsedChatCompletion
from ai.rag import get_index, query_index
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Literal
from openai import OpenAI
from ai.prompt import compliance_instruction, trademark_instruction, design_analysis_prompt, system_prompt, general_rules_prompt
import math
load_dotenv()

client = OpenAI()
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

def clean_response(resp:ParsedChatCompletion['ComplianceOutput']):
    output = {}
    choice = resp.choices[0]

    structured: ComplianceOutput = choice.message.parsed
    print("Compliance status:", structured.compliance_status)
    print("Violation reason:", structured.violation_reason)
    output["compliance_status"] = structured.compliance_status
    output["violation_reason"] = structured.violation_reason
 
    token_logps = [tok.logprob for tok in choice.logprobs.content]

    # Option A: average‐token confidence
    avg_logp = sum(token_logps) / len(token_logps)
    avg_confidence = math.exp(avg_logp)

    # Option B: joint‐string confidence
    sum_logp = sum(token_logps)
    joint_confidence = math.exp(sum_logp)
    

    print(f"Avg-token confidence: {avg_confidence:.2%}")
    print(f"Joint-string confidence: {joint_confidence:.2%}")
 
    output["confidence_score"] = int(avg_confidence * 100)
    # output["joint_confidence"] = int(joint_confidence * 100)

    return output

#############################################################Compliance Verification Agent#############################################################

class ComplianceOutput(BaseModel):
    compliance_status: Literal["Compliant", "Non-compliant"]
    violation_reason: str | None

@function_tool
def search_licensing_rules(query: str) -> str:
    """
    Search for relevant licensing rules using the semantic query.
    Args:
        query: Extracted information from apparel design to search for compliance rules.
    Returns:
        Search results from the vector database
    """
    index = get_index()
    score, result = query_index(index, query)

    return result

def compliance_flow(base64_urls: list[str]):
    design_analysis =  client.responses.create(
        model="gpt-4o-mini",
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
  
    general_rule_evaluation =  client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[{
            "role": "assistant",
            "content": general_rules_prompt
        },
        {
            "role": "user",
            "content": analysis 
        }],
        response_format= ComplianceOutput,
        logprobs=True,
        top_logprobs= 5,
        temperature=0.1,  # Lower temperature
        top_p=0.1         # Lower top_p
    )

    print("General rule evaluation response: ")
    output = clean_response(general_rule_evaluation)

    if output["compliance_status"] == "Non-compliant":
        return  output


    context = query_index(pinecone_index,analysis)

    licensing_rule_evaluation =  client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[{
            "role": "assistant",
            "content": system_prompt.format(analysis,context[1])
        },
        {
            "role": "user",
            "content": "Review this apparel design for compliance with licensing rules. Provide compliance status and violation reason, if any."
        }],
        response_format= ComplianceOutput,
        logprobs=True,
        top_logprobs= 5,
        temperature=0.0,  # Lower temperature
        top_p=0.1         # Lower top_p
    )

    print("Licensing rule evaluation response: ")
    output = clean_response(licensing_rule_evaluation)

    return  output


async def compliance_agent_runner(base64_urls: list[str]):
    # design_analysis =  client.responses.create(
    #     model="gpt-4o",
    #     input=[{
    #         "role": "user",
    #         "content": get_content_list(base64_urls)
    #     },
    #     {
    #         "role": "user",
    #         "content": design_analysis_prompt
    #     }],
    # )

    # analysis = design_analysis.output_text
    
    compliance_agent = Agent(
        name="Compliance verifier",
        model="gpt-4o",
        tools= [search_licensing_rules],
        instructions=compliance_instruction,
        output_type=ComplianceOutput,
        model_settings=ModelSettings(tool_choice="auto", temperature=0.1, top_p=0.1),    
    )

    result = await Runner.run(compliance_agent, input=[
        {
            "role": "user",
            "content": get_content_list(base64_urls)
        },
    ])
 
    return result.final_output

#############################################################Trademark Detection Agent#############################################################

class TrademarkOutput(BaseModel):
    trademark_detected: Literal["Yes", "No"]
    organization: str | None


async def trademark_agent_runner(base64_urls: list[str]):

    trademark_agent = Agent(
        name="Trademark detector",
        model="gpt-4o-mini",
        output_type= TrademarkOutput,
        instructions=trademark_instruction,    
        # model_settings=ModelSettings(temperature=0.1),
    )
    
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
