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
    evaluation: str = Field(desc= "Write a one line explaination to compare Ai voilation reason and actual voilation reason.")
    score: float = Field(desc= "Score the difference as follows:\n0 if the violation reasons don’t match at all,\n0.5 for partial matches, and\n1 for full matches.")


def compliance_evaluation(actual_reason:str, actual_compliance_status:str, ai_reason:str, ai_compliance_status:str):

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
    df = pd.read_csv(csv_path).head(20)
    
    # Create a new DataFrame with the specified output structure
    output_data = []
    
    # Iterate over each row and call the API
    for idx, row in df.iterrows():
        image_url = row['Image Link']
        print(f"Processing row {idx}")
        
        try:
            # Download the image
            img_response = requests.get(image_url)
            img_response.raise_for_status()

            # Call the compliance API
            files = {'images': ('image.jpg', BytesIO(img_response.content), 'image/jpeg')}
            response = requests.post(api_url, files=files)
            response.raise_for_status()

            data = response.json()

            # Evaluate the ai response
            output = compliance_evaluation(row['Actual violation'], row['Actual status'], 
                                           data.get('violation_reason'), data.get('compliance_status'))

            
            row_data = {
                'image_url': image_url,
                'actual_violation': row['Actual violation'], 
                'violation_reason': data.get('violation_reason'),
                'actual_status': row['Actual status'],
                'compliance_status': data.get('compliance_status'),
                'ai_evaluation': output['evaluation'],
                'evaluation_score': output['score'],
                'org_mark_detected': data.get('org_mark_detected'),
                'organization': data.get('organizations'),
                'org_confidence_score': data.get('org_score'),
                'org_analysis': data.get('org_analysis'),
                'school_mark_detected': data.get('school_mark_detected'),
                'school': data.get('schools'),
                'school_confidence_score': data.get('school_score'),
                'school_analysis': data.get('school_analysis')
            }


            pprint(row_data, sort_dicts=False)
            print("\n\n")
            output_data.append(row_data)

        except Exception as e:
            print(f"Error processing row {idx} (URL: {image_url}): {e}")

        
        # Add the row data to output list

    # Create new DataFrame with the specified structure
    output_df = pd.DataFrame(output_data)
    
    # Save the new DataFrame
    output_df.to_csv(output_path, index=False)
    
    return output_df

if __name__ == '__main__':
    # Example usage
    CSV_PATH = 'test/test.csv'
    OUTPUT_PATH = 'test/test_updated.csv'
    API_URL = 'http://127.0.0.1:8000/compliance'
    
    result_df = test_compliance_api(CSV_PATH, OUTPUT_PATH, API_URL)
    print(f"Updated CSV saved to {OUTPUT_PATH}")
    print(f"New DataFrame shape: {result_df.shape}")
    print(f"Columns: {list(result_df.columns)}")
