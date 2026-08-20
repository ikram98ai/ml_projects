import json
import boto3
import pandas as pd
from io import StringIO

def lambda_handler(event, context):
    # Initialize boto3 SageMaker client
    sagemaker_client = boto3.client('sagemaker')

    # Get the input data path and pipeline name from the event
    input_data_path = event.get('input_data_path',None)
    retail_name = event['retail_name']
    
    if input_data_path:
        error_msg = data_validation(input_data_path)
        if error_msg:
            return { 'statusCode':400,   "body":json.dumps(error_msg) }

    
    pipeline_name = 'xgb-turnover-pipeline'
    pipeline_execution_name = 'LambdaTriggeredExecution-' + str.upper(retail_name)
    print("RETAIL::",retail_name)
    try:
        # Check for any currently running pipeline executions
        executions = sagemaker_client.list_pipeline_executions(
            PipelineName=pipeline_name,
            SortBy='CreationTime',
            SortOrder='Descending',
        )
        
        for execution_summary in executions['PipelineExecutionSummaries']:
            print("execution::",execution_summary)
            if execution_summary['PipelineExecutionDisplayName'] == pipeline_execution_name:
                # Extract the execution details
                execution_arn = execution_summary['PipelineExecutionArn']
                execution_status = execution_summary['PipelineExecutionStatus']
                if input_data_path is None or execution_status in ['Executing', 'Stopping']:
                    return {
                        'statusCode': 200,
                         

                        'body': json.dumps({
                            'PipelineExecutionStatus': execution_status,
                            'PipelineExecutionArn': execution_arn,
                            })
                        } 

        # execute only if there is no retail execution or no running retail execution
                
        # Pipeline execution parameters
        pipeline_parameters = [
            {'Name': 'InputData', 'Value': input_data_path},
            {'Name': 'TrainInstanceType', 'Value': 'ml.m5.large'},
        ]
        # If no running execution is found, start a new one
        response = sagemaker_client.start_pipeline_execution(
            PipelineName=pipeline_name,
            PipelineExecutionDisplayName=pipeline_execution_name,
            PipelineParameters=pipeline_parameters
        )
        # Extract the pipeline execution ARN from the response
        pipeline_execution_arn = response['PipelineExecutionArn']

        return {
            'statusCode': 200,
             
            'body':json.dumps({
                'message': f"Pipeline execution started successfully for {retail_name}",
                'PipelineExecutionArn': pipeline_execution_arn,
            })
        }

    except Exception as e:
        # Handle any errors that occur
        return {
            'statusCode': 500,
            'error': str(e)

        }

# Input:
# {
#   "input_data_path": "s3://turnover-data-123/input/data.csv",
#   "retail_name": "retail"
# }


def data_validation(input_data_path):
    error_msg = None
    try:
        s3 = boto3.client('s3')
        bucket_name, key_name = input_data_path.replace("s3://", "").split("/", 1)
        
        # Download CSV file from S3
        response = s3.get_object(Bucket=bucket_name, Key=key_name)
        
        # Read CSV content into Pandas DataFrame
        csv_content = response['Body'].read().decode('utf-8')
        df = pd.read_csv(StringIO(csv_content))
    except Exception as e:
        print(str(e))
        error_msg = str(e)
        return error_msg
           
    print(df.head())
    columns_to_check = ['item_sold_date','item_created_date','price','PriceBucket','CreatedDay', 'CreatedMonth','description', 'CategoryFromDescription', 'Brand1','Turnover']
    missing_fields = [col for col in columns_to_check if col not in df.columns]
    if missing_fields:
       error_msg = f"Invalid data, missing columns in training data: {missing_fields}" if missing_fields else f"{response}", 
    
           
    
    return error_msg