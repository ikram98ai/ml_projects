######################################################## Import required modules ###############################################################
import subprocess
import sys
subprocess.check_call([sys.executable, '-m','pip', 'install','scikit-optimize'])
subprocess.check_call([sys.executable, '-m','pip', 'install','--upgrade', 'scikit-learn==1.2.0'])


import argparse
import pprint
import json
import os
import glob
import pickle
import pandas as pd
from sklearn.model_selection import train_test_split, PredefinedSplit
from xgboost import XGBClassifier
from skopt import BayesSearchCV
import xgboost
import sklearn
from skopt.space import Integer, Real

print('sklearn version3:',sklearn.__version__)
print(xgboost.__version__)


###################################################### Parse input arguments ###################################################################

def parse_args():

    parser = argparse.ArgumentParser()
    
    # CLI args
    
    
    parser.add_argument('--seed',  type=int, default=42)
    

    # Container environment  
    
    parser.add_argument('--hosts', type=list, default=json.loads(os.environ['SM_HOSTS']))
    
    parser.add_argument('--current_host', type=str, default=os.environ['SM_CURRENT_HOST'])
    
    parser.add_argument('--model_dir', type=str, default=os.environ['SM_MODEL_DIR'])

    parser.add_argument('--train_data', type=str, default=os.environ['SM_CHANNEL_TRAIN'])
    
    parser.add_argument('--validation_data', type=str, default=os.environ['SM_CHANNEL_VALIDATION'])
    
    parser.add_argument('--encoders', type=str, default=os.environ['SM_CHANNEL_ENCODERS'])
        
    parser.add_argument('--output_dir', type=str, default=os.environ['SM_OUTPUT_DIR'])
   

    return parser.parse_args()

########################################################### Tools and variables ################################################################
MODEL_NAME = 'model.pkl'

def save_encoders(encoders, model_dir):
    path = '{}/encoders'.format(model_dir)
    os.makedirs(path, exist_ok=True)                              
    print('Saving encoders to {}'.format(path))
    save_path = os.path.join(path,'encoders.pkl')
    with open(save_path, 'wb') as f:
        pickle.dump(encoders, f)

def save_xgboost_model(model, model_dir):
    os.makedirs(model_dir, exist_ok=True) 
    print('Saving XGBoost model to {}'.format(model_dir))
    save_path = os.path.join(model_dir, MODEL_NAME)
    with open(save_path, 'wb') as f:
        pickle.dump(model.get_booster(), f)

def get_data(path): 
    print("Getting data")
    input_file = glob.glob('{}/*.csv'.format(path))[0]
    print("INPUT FILES:::",input_file)
    df = pd.read_csv(input_file)   
    print(df)
    return df
 

    

################################################################ Train model ###################################################################

def train(df_train,df_test):
    df = pd.concat([df_train,df_test], axis=0).reset_index(drop=True)
    X = df.drop('target',axis=1)
    y = df['target']
    print("DATA SHAPE:::", df.shape, X.shape)
    X_tr, X_val, y_tr, y_val = train_test_split( X, y,stratify=y, test_size=0.3,random_state=42)
    split_index = [0 if x in X_val.index else -1 for x in X.index ]
    custom_split= PredefinedSplit(split_index)

    print('Training...')   
    xgb = XGBClassifier(random_state=42)
    params = { 
                'learning_rate': Real(0.01,0.3,prior='log-uniform'),
                'max_depth': Integer(2,10,prior='uniform'),
                'min_child_weight': Integer(2,10,prior='uniform'),
                'n_estimators': Integer(50,1000,prior='uniform'),
                'reg_alpha':Real(0.0001,2,prior='log-uniform'),
                'reg_lambda': Real(0.0001,2,prior='log-uniform')
            }
    xgb_cv =BayesSearchCV(xgb,params,cv=custom_split,n_iter=5,random_state=42,n_jobs=-1,refit='precision')
    xgb_cv.fit(X,y)
    model = xgb_cv.best_estimator_
       
    return model                   
       


#################################################################### Main ######################################################################

if __name__ == '__main__':
    
    # Parse args
    
    args = parse_args()
    print('Loaded arguments:')
    print(args)

    # Get environment variables
    
    env_var = os.environ 
    print('Environment variables:')
    pprint.pprint(dict(env_var), width = 1) 


    encoders_path = args.encoders+'/encoders.pkl'
    with open(encoders_path,'rb') as f:
        encoders = pickle.load(f)
        
    df_train = get_data(args.train_data)
    df_test = get_data(args.validation_data)
    
    model = train(df_train,df_test)
    save_xgboost_model(model,args.model_dir)
    save_encoders(encoders,args.model_dir)

    # Prepare for inference which will be used in deployment
    inference_path = os.path.join(args.model_dir, "code/")
    os.makedirs(inference_path, exist_ok=True)
    print('Training Job Completed')