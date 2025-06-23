import pandas as pd
import requests
from io import BytesIO

def test_compliance_api(csv_path, output_path, api_url):
    # Read the input CSV
    df = pd.read_csv(csv_path)

    # Prepare columns if they don't exist
    for col in ['AI Compliance', 'AI violation', 'Confidence Score', 'Joint Confidence Score']:
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
            # Update the dataframe
            df.at[idx, 'AI Compliance'] = data.get('compliance_status')
            df.at[idx, 'AI violation'] = data.get('violation_reason')
            df.at[idx, 'Confidence Score'] = data.get('confidence_score')
            # df.at[idx, 'Joint Confidence Score'] = data.get('joint_confidence')

        except Exception as e:
            print(f"Error processing row {idx} (URL: {image_url}): {e}")
            df.at[idx, 'AI Compliance'] = 'Error'
            df.at[idx, 'AI violation'] = str(e)
            df.at[idx, 'Confidence Score'] = None
            # df.at[idx, 'Joint Confidence Score'] = None


    # Save the updated CSV
    df.to_csv(output_path, index=False)

if __name__ == '__main__':
    # Example usage
    CSV_PATH = 'test.csv'
    OUTPUT_PATH = 'test_updated.csv'
    API_URL = 'http://127.0.0.1:8000/compliance_flow'
    test_compliance_api(CSV_PATH, OUTPUT_PATH, API_URL)
    print(f"Updated CSV saved to {OUTPUT_PATH}")
