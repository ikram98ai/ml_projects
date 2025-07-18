from agents import Agent, Runner, ModelSettings, function_tool
from openai.types.chat import ParsedChatCompletion
from ai.rag import get_index, query_index
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Literal
from openai import AsyncOpenAI
from ai.prompt import trademark_instruction, apparel_analysis_prompt, system_prompt, general_rules
import math
load_dotenv()

client = AsyncOpenAI()
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

class ImageAnalysisOutput(BaseModel):
    image_analysis: list[str] = Field(desc= "A list of analysis of the apparel design images, include the organization name and type in each sentence, write only one sencence per organization analysis in the apparel design.")

async def image_analysis(base64_urls):
    design_analysis =  await client.responses.parse(
        model="gpt-4o-mini",
        input=[{
            "role": "user",
            "content": get_content_list(base64_urls)
        },
        {
            "role": "user",
            "content": apparel_analysis_prompt
        }],
        text_format=ImageAnalysisOutput
    )

    analysis = design_analysis.output_parsed.image_analysis
    return analysis


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

async def compliance_flow(base64_urls: list[str]):
    
    analysis = await image_analysis(base64_urls)
  
    licensing_rules = "\n".join([query_index(pinecone_index,sentence)[1] for sentence in analysis[:3]])

    licensing_rule_evaluation = await client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": system_prompt.format(analysis, general_rules, licensing_rules)
        },{
            "role": "user",
            "content": "Review this apparel design for compliance with general and licensing rules. Provide compliance status and violation reason, if any."
        }],
        response_format= ComplianceOutput,
        logprobs=True,
        top_logprobs= 5,
        temperature=0.0,  
        top_p=0.1
    )

    print("Licensing rule evaluation response: ")
    output = clean_response(licensing_rule_evaluation)

    return  output



#############################################################Trademark Detection Agent#############################################################

class TrademarkOutput(BaseModel):
    trademark_detected: Literal["Yes", "No"] =Field(desc= "Trademark detection whether there is any organization or university/collegiate mention on apparel or not.")
    organization: str | None = Field(desc= "Name of the organization or university/collegiate on the apparel design.")
    org_type: Literal["Greek", "University"] | None =Field(desc= "Organization type whether the detected trademark is greek organization or university/collegiate.")


async def trademark_agent_runner(base64_urls: list[str]):

    trademark_agent = Agent(
        name="Trademark detector",
        model="gpt-4o-mini",
        output_type= TrademarkOutput,
        instructions=trademark_instruction,    
        model_settings=ModelSettings(temperature=0.1),
    )
    
    result = await Runner.run(trademark_agent, input=[
        {
            "role": "user",
            "content": get_content_list(base64_urls),
        },{
            "role": "user",
            "content": "Examine these apparel images and identify if they contain licensed marks or Greek letters. If yes, name the University or Greek organization associated and it's org_type.",
        },
    ])
    print(f"Trademark detection result: {result.final_output}")
    return dict(result.final_output)
