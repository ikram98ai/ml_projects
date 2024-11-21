######################################################## Import required modules ###############################################################
import subprocess
import sys
subprocess.check_call([sys.executable, '-m','pip', 'install','xgboost==1.7.1', 'matplotlib==3.2.1'])
subprocess.check_call([sys.executable, '-m','pip', 'install','--upgrade', 'pandas>=1.0.0'])

import pandas as pd
import os
import argparse
import json
import pickle
import glob
import tarfile
from sklearn.metrics import confusion_matrix,ConfusionMatrixDisplay
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score, f1_score, recall_score, precision_score
from xgboost import plot_importance
import xgboost as xgb
import sklearn

print('sklearn version2:',sklearn.__version__)
print(xgb.__version__)

###################################################### Parse input arguments ###################################################################
def list_arg(raw_value):
    """argparse type for a list of strings"""
    return str(raw_value).split(',')

def parse_args():
    # Unlike SageMaker training jobs (which have `SM_HOSTS` and `SM_CURRENT_HOST` env vars), processing jobs to need to parse the resource config file directly
    resconfig = {}
    try:
        with open('/opt/ml/config/resourceconfig.json', 'r') as cfgfile:
            resconfig = json.load(cfgfile)
    except FileNotFoundError:
        print('/opt/ml/config/resourceconfig.json not found.  current_host is unknown.')
        pass # Ignore

    # Local testing with CLI args
    parser = argparse.ArgumentParser(description='Process')

    parser.add_argument('--hosts', type=list_arg,default=resconfig.get('hosts', ['unknown']),help='Comma-separated list of host names running the job')
    
    parser.add_argument('--current-host', type=str,default=resconfig.get('current_host', 'unknown'),help='Name of this host running the job')
    
    parser.add_argument('--input-data', type=str,default='/opt/ml/processing/input/data')
    
    parser.add_argument('--input-model', type=str,default='/opt/ml/processing/input/model')
    
    parser.add_argument('--output-data', type=str,default='/opt/ml/processing/output')

    
    return parser.parse_args()

####################################################### Processing function ####################################################################

def get_data(path): 
    print("Getting data")
    input_file = glob.glob('{}/*.csv'.format(path))[0]
    print("INPUT FILES:::",input_file)
    df = pd.read_csv(input_file)   
    return df
    
def process(args):
    print('Current host: {}'.format(args.current_host))
    

    print('Extracting model.tar.gz')
    model_tar_path = '{}/model.tar.gz'.format(args.input_model)                
    model_tar = tarfile.open(model_tar_path)
    model_tar.extractall(args.input_model)
    model_tar.close()    
    
    input_model_files = glob.glob('{}/*.*'.format(args.input_model))
    print('input_model_files: {}'.format(input_model_files))
    
    model_path = '{}/model.pkl'.format(args.input_model) 
    with open(model_path,'rb') as f:
        model = pickle.load(f)
        

    print('Listing contents of input data dir: {}'.format(args.input_data))
    df_test = get_data(args.input_data)
    
    y_test = df_test['target']
    X_test = df_test.drop('target',axis=1)
    dm = xgb.DMatrix(X_test,feature_names=X_test.columns.tolist())
    probs = model.predict(dm)
    preds = (probs > 0.5).astype(int)
    print("PREDICTION:::",preds[:5],' | PROBABILITY:::',probs[:5])

    # Model Output         
    metrics_path = os.path.join(args.output_data, 'metrics/')
    os.makedirs(metrics_path, exist_ok=True)

    plt.figure()
    cm = confusion_matrix(y_true=y_test, y_pred=preds)
    ConfusionMatrixDisplay(cm).plot()
    plt.savefig('{}/confusion_matrix.png'.format(metrics_path))

    plot_importance(model,max_num_features=20)
    plt.savefig('{}/feature_importance.png'.format(metrics_path))


    accuracy = accuracy_score(y_true=y_test, y_pred=preds)        
    recall = recall_score(y_true=y_test, y_pred=preds)        
    precision = precision_score(y_true=y_test, y_pred=preds)        
    f1 = f1_score(y_true=y_test, y_pred=preds)        
    print(f'Test scores:  {accuracy=}, {recall=}, {precision=}, {f1=}')

    report_dict = {
        "metrics": {
            "accuracy": {
                "value": accuracy,
            },
            "recall": {
                "value": recall,
            },
            "precision": {
                "value": precision,
            },
            "f1_score": {
                "value": f1,
            },
        },
    }

    evaluation_path = "{}/evaluation.json".format(metrics_path)
    with open(evaluation_path, "w") as f:
        f.write(json.dumps(report_dict))
        
    print('Listing contents of output dir: {}'.format(args.output_data))
    output_files = os.listdir(args.output_data)
    for file in output_files:
        print(file)

    print('Listing contents of output/metrics dir: {}'.format(metrics_path))
    output_files = os.listdir('{}'.format(metrics_path))
    for file in output_files:
        print(file)

    print('Complete')
    
#################################################################### Main ######################################################################
    
if __name__ == "__main__":
    args = parse_args()
    print('Loaded arguments:')
    print(args)
    
    print('Environment variables:')
    print(os.environ)

    process(args)    