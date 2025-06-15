from agents import Agent, Runner, function_tool, ModelSettings
from ai.rag import get_index, query_index
from dotenv import load_dotenv

load_dotenv()

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
            raise ValueError("Query cannot be empty")      
        print(f"Querying index with: {query}")
        results = query_index(pinecone_index, query)
        print(f"Search Result\n##Start## \n{results[:200]}...\n##End##")
        return "`search_licensing_rules` tool's result:" + results
    except Exception as e:
        print(f"Error in search_licensing_rules: {str(e)}")
        return f"Error searching documents: {str(e)}"

# class ComplianceOutput(BaseModel):
#     compliance_verification: Literal["Compliant", "Non-compliant"]
#     violation_reason: str | None



compliance_instruction = """You are a licensing compliance expert specifically for university and Greek organization apparel. 
Your task is to complete the following steps for each apparel design images (back and front<) provided:
1. Detect either the apperal design is for a specific university or greek organization. 
2. Evaluate designs against the following general rules for the detected GREEK ORGANIZATION or UNIVERSITY.
3. Also evaluate designs against the established licensing guidelines of the detected GREEK ORGANIZATION or UNIVERSITY by using `search_licensing_rules` tool.
4. Analyze the results from the `search_licensing_rules` tool and determine if a design meets all requirements or violates any rules. 
For each evaluation, you must respond in a strict two-line format: 
First indicating 'Compliance Status: Compliant' or 'Compliance Status: Non-compliant', followed by 'Violation Reason:' with either 'None' for compliant designs or a brief explanation for non-compliant designs. 
Never elaborate beyond this format. Base your evaluation solely on actual violations present in the image, not hypothetical concerns.

GENERAL RULES FOR DETECTED GREEK ORGANIZATION:
General rejection reasons on Affinity
Rejected General Themes
    drinking games
    Sex/Nudity (provocative graphic images, phrases/text)
    Cigarette/Drugs (brands, graphic images, phrases/text)
    Violence (graphic images, phrases/text)
    Gambling  (graphic images, phrases/text)
    Profanity
    Any depiction in a demeaning way towards minorities, ethnicities, cultural segments, religious depictions or any images that objectify anyone or any organization.
    Official logos need clear space around them. They should not be obstructed/overlapped  with text or other design elements.
    Having the name of the group aligned vertically or Greek letters written upside down. Greek letters should be of the same size - One should not be bigger/longer than the other.
    Group names should not be split into multiple segments/lines.
    Official logos like Coat of Arms and seals of a particular group can not be altered and have to use the exact ones available on Affinity
    Designs near the butt/crotch area.
    Street, and house addresses, random numbers, or phone numbers on designs are not allowed.
    If using EST year, please ensure only the group's founding year is used. If the chapter's est year is used, the chapter name is mandatory along with it.
    When a design has custom names and numbers please submit the design after removing it, if we don't have the custom names and numbers already available.
    Please note slight variations in color etc. should use the "+ New Version" tool to keep the same designs together. If the design is new it needs to be submitted on its own.
    While working on revision requests, please check the verdict of the previous submission to make sure adequate changes have been made, in case the initial design was rejected.
    Reference to the movie "Wolf of Wall Street" is not allowed by any of the groups.
    If a design has names of more than one Affinity-affiliated Universities, make a separate submission for each one of them.
    Affinity had received a letter from the trademark owner that they claim ownership to the “Ducks Unlimited’ logo. As a result, designs bearing the logo are not approved by their clients. 
    Affinity has received a letter from the trademark owner that they claim ownership to the ‘Ron Jon Surf Shop’ logo.. As a result, designs bearing the logo are not approved by their clients.
    Affinity has received a letter from the trademark owner that they claim ownership to ‘Margaritaville’.. As a result, designs bearing the name are not approved by our clients.
Rejected brands for Affinity-affiliated groups:
    Patagonia
    Santa Cruz
    Dylan's Candy Bar
    Olympics
    Adidas
    Animal House
    Playboy
Brands we CAN’T DO AT ALL:
    OVO
    Life is Good

GENERAL RULES FOR DETECTED UNIVERSITY:
Standard Collegiate Rules
On any design using the listed verbiage and/or logos on the SPA, please note the following -
1. No direct or indirect references to alcohol - including altered alcohol brands/themes, images of bongs,
drinks, cups, or mugs (unless specifically marked as a non-alcoholic drink such as juice, milk, etc)
2. No direct or indirect references to drugs/smoking - includes quotes/phrases that hint at drug use,
slang, images of mushrooms, cigarettes, images of smoke, etc
3. No direct or indirect references to violence or profanity - swear words, images of fighting, dead
people, crossed-out eyes, dripping effect (referring to blood), guns, knives, machetes, or any other tools
depicted in a harmful manner. This applies even if it's a movie theme and the movie is about gore and
violence.
4. No demeaning representation of any race, culture, ethnicity, or religion.
5. No direct or indirect references to sex, nudity, sexual paraphernalia, or slang.
6. The design cannot depict affiliation or support to any political parties.
7. All the verbiage and logos must be used in tandem with ® and TMs as shown in the Helpjuice
articles.
8. All the logos must be used as is - no alterations/customizations are allowed - This includes modifying
certain aspects of the logo to match the rest of the theme, part-usage of a logo, attempts at creating own
logos, etc
9. No references to names, images, and likeness (NIL) of any current or former student-athletes and
coaches - design cannot have names, or photos of players, when using custom numbers on a sports
club/athletic design double check if the numbers belong to the current year's roster
10. No references to the NCAA. Cannot use any variation of these terms - National Collegiate Athletic
Association, PAC12, SEC, Big10, MAC, Champions, National Champs, Division I, Division II, championship
names, bowl names, images of NCAA stadiums, championship trophies/cups, etc.
"""

  
compliance_agent = Agent(
    name="Compliance verifier",
    # model= model,
    model="gpt-4o",
    tools= [search_licensing_rules],
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
