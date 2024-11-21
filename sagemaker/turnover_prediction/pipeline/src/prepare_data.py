######################################################## Import required modules ###############################################################
import sys
import subprocess
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'sagemaker==2.35.0'])

import functools
import multiprocessing
import pandas as pd
import argparse
import os
import pickle
import json
import glob
from pathlib import Path
import boto3
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder,OneHotEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
import sagemaker
import sklearn
print('sklearn version2:',sklearn.__version__)
subprocess.check_call([sys.executable, '-m', 'pip', 'list'])

###################################################### Setup environmental variables ###########################################################

region = os.environ['AWS_DEFAULT_REGION']
sm = boto3.Session(region_name=region).client(service_name='sagemaker', region_name=region)
bucket = sagemaker.Session().default_bucket()
sagemaker_session = sagemaker.Session(boto_session=boto3.Session(region_name=region), sagemaker_client=sm)

###################################################### Parse input arguments ###################################################################


def list_arg(raw_value):
    """argparse type for a list of strings"""
    return str(raw_value).split(',')

def parse_args():
    resconfig = {}
    try:
        with open('/opt/ml/config/resourceconfig.json', 'r') as cfgfile:
            resconfig = json.load(cfgfile)
    except FileNotFoundError:
        print('/opt/ml/config/resourceconfig.json not found. current_host is unknown.')
        pass # Ignore

    # Local testing with CLI args
    parser = argparse.ArgumentParser(description='Process')
    parser.add_argument('--hosts', type=list_arg, default=resconfig.get('hosts', ['unknown']),help='Comma-separated list of host names running the job' )
    parser.add_argument('--current-host', type=str,default=resconfig.get('current_host', 'unknown'),help='Name of this host running the job')
    parser.add_argument('--input-data', type=str,default='/opt/ml/processing/input/data')
    parser.add_argument('--output-data', type=str,default='/opt/ml/processing/output' )
    parser.add_argument('--train-split-percentage', type=float, default=0.90)
    parser.add_argument('--validation-split-percentage', type=float, default=0.05)    
    parser.add_argument('--test-split-percentage', type=float, default=0.05)
    parser.add_argument('--balance-dataset', type=eval, default=False )    
    
    return parser.parse_args()

####################################################### Processing functions ###################################################################

    
def _preprocess_file(file, balance_dataset):
    
    print('file {}'.format(file))
    print('balance_dataset {}'.format(balance_dataset))

 
    filename_without_extension = Path(Path(file).stem).stem

    df = pd.read_csv(file ,parse_dates=['item_sold_date','item_created_date'])

    print("COLUMNS, TYPES::",list(zip(df.columns,df.dtypes)))
    
    # Removing internally transfered items
    if 'Is internal' in df.columns:
        df = df[df['Is internal']==0].reset_index(drop=True)
        
    features = ['item_sold_date','item_created_date','price','description', 'CategoryFromDescription', 'Brand1','Turnover']
    df = df[features]
    
    print("Before Droping NA and Duplicates:",df.shape)
    df = df.drop_duplicates()
    df = df.dropna()
    df = df.reset_index(drop=True)
    print("After Droping NA and Duplicates:",df.shape)
    
    df = df.rename({'Turnover':'turnover','CategoryFromDescription':'category','Brand1':'brand1'},axis=1)

    df['category'] = df['category'].fillna('unknown').str.strip().str.lower()
    df['brand1'] = df['brand1'].str.strip().str.lower()
    df['description'] = df['description'].str.strip().str.lower()

    df['created_month'] = df.item_created_date.dt.month_name().str.lower()
    df['created_day'] = df.item_created_date.dt.day_name().str.lower()
    df['desc_len'] = df.description.str.len()
    df['cate_len'] = df.category.str.len()
    df['brand1_len'] = df.brand1.str.len()
    
    def get_price_bucket(price):
        bins = [ 0, 49, 99, 199, 249, 499, 999, np.inf]
        labels = ['25_50', '50_100', '100_200', '200_250', '250_500', '500_1000', '1000+']
        return pd.cut(price, bins=bins, labels=labels, right=True).astype(str)
    df['price_bucket'] = get_price_bucket(df.price)

    df['target']= (df.turnover<=30)
    
    print("info1::")
    df.info()
   
    # # Balancing data
    # if balance_dataset:  
    #     df_groupby = df.groupby('target')
    #     df= df_groupby.apply(lambda x: x.sample(df_groupby.size().min()).reset_index(drop=True)).droplevel(1).reset_index(drop=True)
    
    training_features = ['target','price','price_bucket','created_day', 'created_month','description','desc_len', 'category', 'cate_len','brand1_len','brand1']
    df = df[training_features]
    print("DF1::",df)
    df.drop_duplicates(inplace=True)
    df.dropna(inplace=True)
    df =df.reset_index(drop=True)
    print("info3::")
    df.info()
    features_to_encode = ['price_bucket','created_day','created_month','category']
    # Initialize the encoder
    onehot_encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
    onehot_encoder = onehot_encoder.fit(df[features_to_encode])
    brand_le = LabelEncoder()
    brand_le = brand_le.fit(df.brand1)
    tfidf_vectorizer = TfidfVectorizer(ngram_range=(1,1), max_features=100,stop_words='english')
    tfidf_vectorizer = tfidf_vectorizer.fit(df['description'])
    print(df)
    encoded_data = onehot_encoder.transform(df[features_to_encode])
    encoded_feature_names = onehot_encoder.get_feature_names_out(features_to_encode)
    df.loc[:,encoded_feature_names] = encoded_data.astype(int)
    df = df.drop(features_to_encode,axis=1)

    df['brand1']  = brand_le.transform(df.brand1).astype(int)
    print(df)
    
    ngram_features = tfidf_vectorizer.transform(df['description'])
    ngram_df = pd.DataFrame(ngram_features.toarray(), columns=tfidf_vectorizer.get_feature_names_out())
    df = pd.concat([df, ngram_df], axis=1).drop('description',axis=1)
    print(df)

    print("data transformed...")
    holdout_percentage = 1.00 - args.train_split_percentage
    print('holdout percentage {}'.format(holdout_percentage))
    df_train, df_holdout = train_test_split(df, test_size=holdout_percentage, stratify=df['target'])

    test_holdout_percentage = args.test_split_percentage / holdout_percentage
    print('test holdout percentage {}'.format(test_holdout_percentage))
    df_validation, df_test = train_test_split(df_holdout,test_size=test_holdout_percentage, stratify=df_holdout['target'])
    
    df_train = df_train.reset_index(drop=True)
    df_validation = df_validation.reset_index(drop=True)
    df_test = df_test.reset_index(drop=True)

    print('Shape of train dataframe {}'.format(df_train.shape))
    print('Shape of validation dataframe {}'.format(df_validation.shape))
    print('Shape of test dataframe {}'.format(df_test.shape))

    train_data = '{}/turnover/train'.format(args.output_data)
    validation_data = '{}/turnover/validation'.format(args.output_data)
    test_data = '{}/turnover/test'.format(args.output_data)
    
    df_train.to_csv('{}/part-{}-{}.csv'.format(train_data, args.current_host, filename_without_extension),index=False)
    df_validation.to_csv('{}/part-{}-{}.csv'.format(validation_data, args.current_host, filename_without_extension),index=False)
    df_test.to_csv('{}/part-{}-{}.csv'.format(test_data, args.current_host, filename_without_extension),index=False)

    encoders = {
        "tfidf_vectorizer":tfidf_vectorizer,
        "onehot_encoder":onehot_encoder,
        "brand_le":brand_le
    }

    encoders_data = '{}/turnover/encoders'.format(args.output_data)
    encoders_path = os.path.join(encoders_data, 'encoders.pkl')
    with open(encoders_path, 'wb') as f:
        pickle.dump(encoders, f)

def process(args):
    print('Current host: {}'.format(args.current_host))
 
    preprocessed_data = '{}/turnover'.format(args.output_data)
    train_data = '{}/turnover/train'.format(args.output_data)
    validation_data = '{}/turnover/validation'.format(args.output_data)
    test_data = '{}/turnover/test'.format(args.output_data)
    
    # partial functions allow to derive a function with some parameters to a function with fewer parameters 
    # and fixed values set for the more limited function
    # here 'preprocess_file' will be more limited function than '_preprocess_file' with fixed values for some parameters
    preprocess_file = functools.partial(_preprocess_file,balance_dataset=args.balance_dataset)
    
    input_files = glob.glob('{}/*.csv'.format(args.input_data))

    num_cpus = multiprocessing.cpu_count()
    print('num_cpus {}'.format(num_cpus))

    p = multiprocessing.Pool(num_cpus)
    p.map(preprocess_file, input_files)

    print('Listing contents of {}'.format(preprocessed_data))
    dirs_output = os.listdir(preprocessed_data)
    for file in dirs_output:
        print(file)

    print('Listing contents of {}'.format(train_data))
    dirs_output = os.listdir(train_data)
    for file in dirs_output:
        print(file)

    print('Listing contents of {}'.format(validation_data))
    dirs_output = os.listdir(validation_data)
    for file in dirs_output:
        print(file)

    print('Listing contents of {}'.format(test_data))
    dirs_output = os.listdir(test_data)
    for file in dirs_output:
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