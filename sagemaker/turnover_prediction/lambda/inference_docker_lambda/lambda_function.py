import json
import boto3
import os
import io
import tarfile
import pickle
import pandas as pd
from scipy.optimize import minimize
import xgboost as xgb
import numpy as np
sm = boto3.client('sagemaker') 
s3 = boto3.client('s3')



def lambda_handler(event, context):
    retail_name = event['retail_name']
    input_data = event['data']

    pipeline_name = 'xgb-turnover-pipeline'
    execution_name =  'LambdaTriggeredExecution-' + str.upper(retail_name)
    
    list_executions_response = sm.list_pipeline_executions( PipelineName=pipeline_name )
    pipeline_execution_arn = None
    # Look for the specific execution by name
    for execution_summary in list_executions_response['PipelineExecutionSummaries']:
        if execution_summary['PipelineExecutionDisplayName'] == execution_name:
            pipeline_execution_arn = execution_summary['PipelineExecutionArn']
            break
    if not pipeline_execution_arn:
        return {
            "statusCode": 404,
            "body": f"No execution found with retail name {retail_name} for pipeline {pipeline_name}."
            }

    # List pipeline execution steps
    response = sm.list_pipeline_execution_steps( PipelineExecutionArn=pipeline_execution_arn )
    training_job_name = None
    # Iterate through the steps and find the evaluation step
    for step in response['PipelineExecutionSteps']:
        if step['StepName'] == 'TrainingStep':    
            step_execution_arn = step['Metadata']['TrainingJob']['Arn']
            training_job_name=step_execution_arn.split('/')[-1]
    
    if not training_job_name:
         return {
            "statusCode": 404,
            "body":f"{retail_name} currently don't have training step.(please check the pipeline training status)"
             
            }
    describe_training_job_response = sm.describe_training_job(TrainingJobName=training_job_name)
    model_s3_uri = describe_training_job_response['ModelArtifacts']['S3ModelArtifacts']
    if not os.path.isfile('/tmp/model.pkl'):
        download_model_from_s3(model_s3_uri)
    df = transform_data(input_data)
    pred,prob,optimal_price = predict_fn(df)

    return {
        'statusCode': 200,
        'body': {
            "prediction":pred,
            "probability":prob,
            'optimal_price':optimal_price
        }
    }


def transform_data(input_data):
    print("TRANSFORMING DATA...")
    encoders_path = '/tmp/encoders/encoders.pkl'  
    with open(encoders_path, 'rb') as f:
        encoders = pickle.load(f)

    df = pd.DataFrame(input_data,index=[0])
    df['category'] = df['category'].str.strip().str.lower()
    df['brand1'] = df['brand1'].str.strip().str.lower()
    df['description'] =  df['description'].str.strip().str.lower()
    df['created_month'] =  df['created_month'].str.strip().str.lower()
    df['created_day'] =  df['created_day'].str.strip().str.lower()
    
    df['desc_len'] = df.description.str.len()
    df['cate_len'] = df.category.str.len()
    df['brand1_len'] = df.brand1.str.len()
    
    onehot_encoder = encoders['onehot_encoder']
    brand_le = encoders['brand_le']
    tfidf_vectorizer = encoders['tfidf_vectorizer']

    features = ['price','price_bucket','created_day', 'created_month','description','desc_len', 'category', 'cate_len','brand1_len','brand1']
    df = df[features]
    
    columns_to_encode = ['price_bucket','created_day','created_month','category']
    encoded_data = onehot_encoder.transform(df[columns_to_encode])
    encoded_feature_names = onehot_encoder.get_feature_names_out(columns_to_encode)
    df.loc[:,encoded_feature_names] = encoded_data.astype(int)
    df = df.drop(columns_to_encode,axis=1)

    na_label = '<unknown>'
    brands = df.brand1.map(lambda brand: na_label if brand not in brand_le.classes_ else brand)
    print(brands)
    if not set(brand_le.classes_ ).issuperset(brands):
        brand_le.classes_ = np.append(brand_le.classes_,na_label)
        print('unknown label apended to brand_le')
    df['brand1']  = brand_le.transform(brands).astype(int)

    ngram_features = tfidf_vectorizer.transform(df['description'])
    ngram_df = pd.DataFrame(ngram_features.toarray(), columns=tfidf_vectorizer.get_feature_names_out())
    df = pd.concat([df, ngram_df], axis=1).drop('description',axis=1)
    return df



 
def predict_fn(df):
    model_path = '/tmp/model.pkl'
    with open(model_path,'rb') as f:
        model = pickle.load(f)
    dm = xgb.DMatrix(df)
    print("DMATRIX:::",dm)
    print('dm predicting...')
    prob = model.predict(dm)
    pred = (prob>0.5).astype(int)
    optimal_price = get_optimal_price(df, model)
    return  pred.tolist()[0], round(prob.tolist()[0],4), optimal_price


def get_optimal_price(x,model):
    def objective(price):
        # Predict the probability of a product being sold within 30 days given a price
        x.loc[:, 'price'] = price
        dm = xgb.DMatrix(x)
        prob = model.predict(dm)

        # If model predicts that the product will be sold within 30 days, return negative price to maximize
        if prob[0] > 0.95 :
            return -price
        else:
            return float('inf')  # Discard prices that exceed the turnover target
        
    # Set bounds for the price optimization (e.g., min price=1, max price=1000)
    bounds = [(x.price-10, x.price+10)]  # Adjust these bounds according to your specific problem

    # Optimize the price for an example product with bounds
    result = minimize(objective, x0=x.price, method='L-BFGS-B', bounds=bounds)
    optimal_price = result.x[0]
    return optimal_price    


# Download the model file from S3
def download_model_from_s3(model_s3_uri):
    S3_BUCKET, S3_KEY = model_s3_uri.replace('s3://','').split('/',1)
    FILE_NAME = S3_KEY.split('/')[-1]
    TMP_FILE_PATH = os.path.join('/tmp', FILE_NAME)
 
    # Download the file into a memory buffer
    file_buffer = io.BytesIO()
    s3.download_fileobj(S3_BUCKET, S3_KEY, file_buffer)
    file_buffer.seek(0)  # Move the pointer back to the beginning of the file buffer

    # Save the file to the /tmp directory
    with open(TMP_FILE_PATH, 'wb') as f:
        f.write(file_buffer.read())
    
    # Extract the tar file in /tmp
    with tarfile.open(TMP_FILE_PATH, 'r:gz') as tar:
        tar.extractall(path='/tmp/')
        print("Model extracted to /tmp/")
    print(os.listdir('/tmp/'))




# # Input::
# {
#   "retail_name": "retail",
#   "data": {
#     "price": 250,
#     "price_bucket": "200_500",
#     "created_day": "Thursday",
#     "created_month": "March",
#     "description": "Blus Stockhlm brun 40 glansig vringad",
#     "category": "blus",
#     "brand1": "brun"
#   }
# }