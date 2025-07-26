from agents import Agent, Runner, ModelSettings
from ai.rag import query_index
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Literal, List
from openai import AsyncOpenAI
from ai.prompt import TRADEMARK_INSTRUCTION, APPAREL_ANALYSIS_PROMPT, SYSTEM_PROMPT, GENERAL_RULES
load_dotenv()

client = AsyncOpenAI()

def get_content_list(base64_urls: List[str]):
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


class ImageAnalysisOutput(BaseModel):
    school_mark_detected: bool
    school_names: str | None
    school_analysis: str | None = Field(desc= "If school/university marks detected, analyze the apparel design images, include the school name and type in each sentence, write only one sencence per organization analysis in the apparel design.")
    org_mark_detected: bool
    organization_names: str | None
    org_analysis: str | None = Field(desc= "If greek organization marks detected, analyze the apparel design images, include the organization name and type in each sentence, write only one sencence per organization analysis in the apparel design.")

async def image_analysis(base64_urls) -> ImageAnalysisOutput:
    design_analysis =  await client.responses.parse(
        model="gpt-4o-mini",
        input=[{
            "role": "system",
            "content": APPAREL_ANALYSIS_PROMPT
        },{
            "role": "user",
            "content": get_content_list(base64_urls)
        },{
            "role": "user",
            "content": "Analyse the given images to extract informations"
        }],
        text_format=ImageAnalysisOutput
    )

    analysis = design_analysis.output_parsed
    return analysis


CONTEXT = """
**RULES CONTEXT**

Established General Rules:
<General Rules>
{}
</General Rules>

Established Licensing Rules: 
<Licensing Rules from RAG>
{} 
</Licensing Rules from RAG>
"""

async def compliance_flow(base64_urls: List[str]):
    
    analysis = await image_analysis(base64_urls)

    school_score, school_licensing_rules = 0.0, ''
    if analysis.school_mark_detected:
        school_score, school_licensing_rules = query_index(f'{analysis.school_names}, {analysis.school_analysis}')   

    org_score, org_licensing_rules = 0.0, ''
    if analysis.org_mark_detected:
        org_score, org_licensing_rules = query_index(f'{analysis.organization_names}, {analysis.org_analysis}')

    licensing_rules = org_licensing_rules + school_licensing_rules

    response = await client.responses.parse(
        model="gpt-4o-mini",
        input=[{
            "role": "system",
            "content": SYSTEM_PROMPT
        },{
            "role": "assistant",
            "content": CONTEXT.format(GENERAL_RULES, licensing_rules)
        },{
            "role": "user",
            "content": """Apparel Design Analysis: {}\nReview the apparel design analysis for compliance with following general and licensing rules. 
            Provide compliance status and violation reason, if any.""".format(analysis) 
        }],
        text_format= ComplianceOutput,
        temperature=0.0,  
        top_p=0.1
    )

    result = response.output_parsed

    output = {
        "compliance_status": result.compliance_status,
        "violation_reason" : result.violation_reason,
        "school_mark_detected": analysis.school_mark_detected,
        "org_mark_detected": analysis.org_mark_detected,
        "organization": analysis.organization_names,
        "school": analysis.school_names,
        "school_analysis": analysis.school_analysis,
        "org_analysis": analysis.org_analysis,
        "org_confidence_score": org_score,
        "school_confidence_score": school_score,
    }
    return  output



#############################################################Trademark Detection Agent#############################################################

class TrademarkOutput(BaseModel):
    trademark_detected: Literal["Yes", "No"] =Field(desc= "Trademark detection whether there is any organization or university/collegiate mention on apparel or not.")
    organization: str | None = Field(desc= "Name of the organization or university/collegiate on the apparel design.")
    org_type: Literal["Greek", "University"] | None =Field(desc= "Organization type whether the detected trademark is greek organization or university/collegiate.")


async def trademark_agent_runner(base64_urls: List[str]):

    trademark_agent = Agent(
        name="Trademark detector",
        model="gpt-4o-mini",
        output_type= TrademarkOutput,
        instructions=TRADEMARK_INSTRUCTION,    
        model_settings=ModelSettings(temperature=0.1),
    )
    
    result = await Runner.run(trademark_agent, input=[{
            "role": "user",
            "content": "Examine these apparel images and identify if they contain licensed marks or Greek letters. If yes, name the University or Greek organization associated and it's org_type.",
        }, {
            "role": "user",
            "content": get_content_list(base64_urls),
        }
    ])
    print(f"Trademark detection result: {result.final_output}")
    return dict(result.final_output)
