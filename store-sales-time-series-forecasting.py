# -*- coding: utf-8 -*-
"""Untitled20.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1ztac536-bnwe3tnKiKEz0Vqy_mYYW-Mf
"""

import os
import sys
from tempfile import NamedTemporaryFile
from urllib.request import urlopen
from urllib.parse import unquote, urlparse
from urllib.error import HTTPError
from zipfile import ZipFile
import tarfile
import shutil

CHUNK_SIZE = 40960
SOURCE_MAPPING = 'store-sales-time-series-forecasting:https%3A%2F%2Fstorage.googleapis.com%2Fkaggle-competitions-data%2Fkaggle-v2%2F29781%2F2887556%2Fbundle%2Farchive.zip%3FX-Goog-Algorithm%3DGOOG4-RSA-SHA256%26X-Goog-Credential%3Dgcp-kaggle-com%2540kaggle-161607.iam.gserviceaccount.com%252F20241003%252Fauto%252Fstorage%252Fgoog4_request%26X-Goog-Date%3D20241003T093405Z%26X-Goog-Expires%3D259200%26X-Goog-SignedHeaders%3Dhost%26X-Goog-Signature%3D2e0affe0ef700b87c4d7ff232330959776a92caebab553f8b07d9e5108e9d98407c78512057cf4eba66371069610c36550015367fcaa761b1241c34a4748c88804f6ba81a0af846dbc68a16390fca11a0ade9c2b828625d6e00cd579100db9eec72b7411200612fba31feaa314a5a239ee85f86e5ad9d6423eee2ee30dfb272022cf819afabfb96e66c798b1afa9fdaac354d47875e7d9cbdb0303ee15af7d60aa48421235a07dd5cb6715245941ce1ad0401c9231dd1bcbe11f5be74b6817557e13139fd91b36adbad2497716ca55e18c94c4a2932db0b567e6e93dd8cf45c3c42d7d3e81dee4f605fe1737f2d20f16edf76b2b91b69f3bf96812dcf714794f'

INPUT_PATH = '/kaggle/input'
WORKING_PATH = '/kaggle/working'

!umount /kaggle/input/ 2> /dev/null
shutil.rmtree(INPUT_PATH, ignore_errors=True)
os.makedirs(INPUT_PATH, 0o777, exist_ok=True)
os.makedirs(WORKING_PATH, 0o777, exist_ok=True)

try:
    os.symlink(INPUT_PATH, os.path.join("..", 'input'), target_is_directory=True)
except FileExistsError:
    pass
try:
    os.symlink(WORKING_PATH, os.path.join("..", 'working'), target_is_directory=True)
except FileExistsError:
    pass

for mapping in SOURCE_MAPPING.split(','):
    dir_name, url_encoded = mapping.split(':')
    download_url = unquote(url_encoded)
    filename = urlparse(download_url).path
    dest_path = os.path.join(INPUT_PATH, dir_name)
    try:
        with urlopen(download_url) as response, NamedTemporaryFile() as temp_file:
            total_length = response.headers['content-length']
            print(f'Downloading {dir_name}, {total_length} bytes compressed')
            downloaded = 0
            data_chunk = response.read(CHUNK_SIZE)
            while len(data_chunk) > 0:
                downloaded += len(data_chunk)
                temp_file.write(data_chunk)
                progress = int(50 * downloaded / int(total_length))
                sys.stdout.write(f"\r[{'=' * progress}{' ' * (50-progress)}] {downloaded} bytes downloaded")
                sys.stdout.flush()
                data_chunk = response.read(CHUNK_SIZE)
            if filename.endswith('.zip'):
                with ZipFile(temp_file) as zip_file:
                    zip_file.extractall(dest_path)
            else:
                with tarfile.open(temp_file.name) as tar_file:
                    tar_file.extractall(dest_path)
            print(f'\nDownloaded and uncompressed: {dir_name}')
    except HTTPError:
        print(f'Failed to load (likely expired) {download_url} to path {dest_path}')
        continue
    except OSError:
        print(f'Failed to load {download_url} to path {dest_path}')
        continue

print('Data source import complete.')

import numpy as np
import pandas as pd

import os
for path, _, files in os.walk('/kaggle/input'):
    for file in files:
        print(os.path.join(path, file))

use_data_since_2017 = True

!pip install catboost
from catboost import CatBoostRegressor, Pool
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

train_df = pd.read_csv('/kaggle/input/store-sales-time-series-forecasting/train.csv')
test_df = pd.read_csv('/kaggle/input/store-sales-time-series-forecasting/test.csv')
stores_df = pd.read_csv('/kaggle/input/store-sales-time-series-forecasting/stores.csv')
oil_df = pd.read_csv('/kaggle/input/store-sales-time-series-forecasting/oil.csv')
holidays_df = pd.read_csv('/kaggle/input/store-sales-time-series-forecasting/holidays_events.csv')
transactions_df = pd.read_csv('/kaggle/input/store-sales-time-series-forecasting/transactions.csv')
sample_submission_df = pd.read_csv('/kaggle/input/store-sales-time-series-forecasting/sample_submission.csv')

train_df['date'] = pd.to_datetime(train_df['date'])
test_df['date'] = pd.to_datetime(test_df['date'])

if use_data_since_2017:
    train_df = train_df[train_df['date'] >= '2017-01-01']
    test_df = test_df[test_df['date'] >= '2017-01-01']

train_df['holiday'] = train_df['date'].isin(holidays_df['date'])
test_df['holiday'] = test_df['date'] == pd.to_datetime('2017-08-24')

for df in [train_df, test_df]:
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df['day'] = df['date'].dt.day
    df['weekday'] = df['date'].dt.weekday

train_df.drop(columns=['date'], inplace=True)
test_df.drop(columns=['date'], inplace=True)

cat_cols = train_df.select_dtypes(include=['object']).columns
train_df = pd.get_dummies(train_df, columns=cat_cols, drop_first=True)
test_df = pd.get_dummies(test_df, columns=cat_cols, drop_first=True)

train_df, test_df = train_df.align(test_df, join='left', axis=1, fill_value=0)

print(train_df.head())
print(test_df.head())

X = train_df.drop(columns=['sales'])
y = train_df['sales']

y_log = np.log1p(y)

X_train, X_val, y_train, y_val = train_test_split(X, y_log, test_size=0.2, random_state=42)

X_train.columns = X_train.columns.str.replace('[^A-Za-z0-9_]+', '_', regex=True)
X_val.columns = X_val.columns.str.replace('[^A-Za-z0-9_]+', '_', regex=True)
test_df.columns = test_df.columns.str.replace('[^A-Za-z0-9_]+', '_', regex=True)

X_train, test_df = X_train.align(test_df, join='left', axis=1, fill_value=0)
X_val, test_df = X_val.align(test_df, join='left', axis=1, fill_value=0)

train_pool = Pool(X_train, y_train)
val_pool = Pool(X_val, y_val)

iterations = 100
learning_rate = 0.1
train_loop_count = 100
retrain_loop_count = 10

catboost_model = CatBoostRegressor(
    iterations=iterations,
    learning_rate=learning_rate,
    depth=8,
    random_seed=42,
    loss_function='RMSE',
    verbose=100
)

catboost_model.fit(
    train_pool,
    eval_set=val_pool,
    early_stopping_rounds=50,
    verbose=50,
    use_best_model=True,
    init_model=None
)

for _ in range(min(train_loop_count, 10)):
    catboost_model.fit(
        train_pool,
        eval_set=val_pool,
        early_stopping_rounds=50,
        verbose=50,
        use_best_model=True,
        init_model=catboost_model
    )

from catboost import Pool

august_pool = Pool(data=X_train, label=y_train)

for _ in range(retrain_loop_count):
    catboost_model.fit(
        august_pool,
        verbose=50,
        init_model=catboost_model
    )

from sklearn.metrics import mean_squared_error

# Generate predictions on the validation set
y_val_pred = catboost_model.predict(X_val)

# Calculate the RMSE
rmse = np.sqrt(mean_squared_error(y_val, y_val_pred))
print(f'RMSE: {rmse}')

test_predictions_log = catboost_model.predict(test_df)

test_df['sales'] = np.expm1(test_predictions_log)

test_df['sales'] = np.where(test_df['sales'] < 0, 0, test_df['sales'])

submission = test_df[['id', 'sales']]

submission.to_csv('submission.csv', index=False)

print(submission)

from google.colab import files
files.download('submission.csv')