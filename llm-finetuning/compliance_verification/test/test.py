import pandas as pd
import requests
from io import BytesIO
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from openai import OpenAI
from pprint import pprint
load_dotenv()

client = OpenAI()

class EvaluationOutput(BaseModel):
    evaluation: list[str] = Field(desc= "Write a one line explaination to compare Ai voilation reason and actual voilation reason.")
    score: float = Field(desc= "Score the difference as follows:\n0 if the violation reasons don’t match at all,\n0.5 for partial matches, and\n1 for full matches.")


def compliance_evaluation(actual_reason:str, actual_compliance_status:str, ai_reason:str, ai_compliance_status:str):
    print("actual_compliance_status != ai_compliance_status: ",actual_compliance_status != ai_compliance_status, actual_compliance_status, ai_compliance_status)
    if actual_compliance_status.lower().strip() != ai_compliance_status.lower().strip():
        return {"evaluation":None, "score": -1 }
    
    evaluation_response =  client.responses.parse(
        model="gpt-4o-mini",
        input=[{
            "role": "user",
            "content": f"Actual voilation reason: {actual_reason}\n\nAI generated voilation reason: {ai_reason}"
        },
        {
            "role": "user",
            "content": "Compare the actual compliance voilation reason with ai generated voilation reason, explain the evaluation in one line and score the evaluation. "
        }],
        text_format=EvaluationOutput
    )

    output = evaluation_response.output_parsed
    return dict(output)

def test_compliance_api(csv_path, output_path, api_url):
    # Read the input CSV
    df = pd.read_csv(csv_path)

    # Prepare columns if they don't exist
    for col in ['AI Compliance', 'AI violation', 'Confidence Score', 'Trademark Detected', 
                'Organization', 'Organization Type', 'AI Evaluation', 'AI Score']:
        if col not in df.columns:
            df[col] = None

    # Iterate over each row and call the API
    for idx, row in df.iterrows():
        image_url = row['Image Link']
        # if idx > 4: break
        print(f"Processing row {idx} with image URL: {image_url}")
        try:
            # Download the image
            img_response = requests.get(image_url)
            img_response.raise_for_status()

            # Call the compliance API
            files = {'images': ('image.jpg', BytesIO(img_response.content), 'image/jpeg')}
            response = requests.post(api_url, files=files)
            response.raise_for_status()

            data = response.json()

            print("AI response: ")
            pprint(data, indent=4)

            # Evaluate the ai response
            output = compliance_evaluation(row['Actual violation'], row['Actual status'], 
                                           data.get('violation_reason'), data.get('compliance_status'))
            print("Evaluation output: ")
            pprint(output, indent=4)

            print("\n\n")

            # Update the dataframe
            df.at[idx, 'AI Compliance'] = data.get('compliance_status')
            df.at[idx, 'AI violation'] = data.get('violation_reason')
            df.at[idx, 'Confidence Score'] = data.get('confidence_score')

            df.at[idx, 'Trademark Detected'] = data.get('trademark_detected')
            df.at[idx, 'Organization'] = data.get('organization')
            df.at[idx, 'Organization Type'] = data.get('org_type')

            df.at[idx, 'AI Evaluation'] = output.get("evaluation")
            df.at[idx, 'AI Score'] = output.get('score')

        except Exception as e:
            print(f"Error processing row {idx} (URL: {image_url}): {e}")
            df.at[idx, 'AI Compliance'] = 'Error'
            df.at[idx, 'AI violation'] = str(e)
            df.at[idx, 'Confidence Score'] = None

            df.at[idx, 'Trademark Detected'] = None
            df.at[idx, 'Organization'] = None
            df.at[idx, 'Organization Type'] = None

            df.at[idx, 'AI Evaluation'] = None
            df.at[idx, 'AI Score'] = None


    # Save the updated CSV
    df.to_csv(output_path, index=False)

if __name__ == '__main__':
    # Example usage
    CSV_PATH = 'test/test.csv'
    OUTPUT_PATH = 'test_updated.csv'
    API_URL = 'http://127.0.0.1:8000/compliance-detect'
    test_compliance_api(CSV_PATH, OUTPUT_PATH, API_URL)
    print(f"Updated CSV saved to {OUTPUT_PATH}")
