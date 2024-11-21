import json
import boto3
import os

sm = boto3.client('sagemaker') 
s3 = boto3.client('s3')


def lambda_handler(event, context):
    retail_name = event['retail_name']
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

    processing_job_name = None
    # Iterate through the steps and find the evaluation step
    for step in response['PipelineExecutionSteps']:
        if step['StepName'] == 'EvaluateModelStep':    
            step_execution_arn = step['Metadata']['ProcessingJob']['Arn']
            processing_job_name=step_execution_arn.split('/')[-1]
    
    if not processing_job_name:
         return {
            "statusCode": 404,
            "body":f"{retail_name} currently don't have evaluation metrics.(hint: check the pipeline training status)"
             
            }

    describe_evaluation_processing_job_response = sm.describe_processing_job(ProcessingJobName=processing_job_name)
    evaluation_metrics_s3_uri = describe_evaluation_processing_job_response['ProcessingOutputConfig']['Outputs'][0]['S3Output']['S3Uri']
    
    bucket_name, prefix = evaluation_metrics_s3_uri.replace("s3://",'').split('/',1)
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

    # Prepare the dictionary to store the data
    data_dict = {}
    
    for obj in response.get('Contents', []):
        key = obj['Key']
        file_name = os.path.basename(key)
        
        # Download the object
        file_obj = s3.get_object(Bucket=bucket_name, Key=key)
        file_content = file_obj['Body'].read()
    
        # Check the file type and process accordingly
        if file_name.endswith('.json'):
            json_data = json.loads(file_content.decode('utf-8'))
            data_dict['metrics'] =  {k:round(v['value'],4) for k,v in json_data['metrics'].items()}
        elif file_name.endswith(('.png')):
            s3_url = f's3://{bucket_name}/{prefix}/{file_name}'
            file_name=file_name.replace('.png','')
            data_dict[file_name] = s3_url
    
    return {
            "statusCode": 200,
            "body": data_dict
        }