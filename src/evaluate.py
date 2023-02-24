# -*- coding: utf-8 -*-
"""evaluate.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1ES52isGI-Tc-V5M_lt-2hA3yKd4TObIk
"""

#for evaluate

# Commented out IPython magic to ensure Python compatibility.
# cd [your src path]
# %cd /content/drive/MyDrive/bistelligence/BISTelligence/src

# Commented out IPython magic to ensure Python compatibility.
# %pip install pyod tensorflow shap

#from sklearn.utils.validation import check_is_fitted
#import scipy.stats as ss
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import pickle
import joblib
import shap
from tensorflow.keras.models import load_model
import pandas as pd
import os
import sys

#for backend [NSException]
matplotlib.use('agg')

import src.data.preprocessing as dp
import src.model.models as mm
import src.XAI.xai as xx

BIS_path =  os.path.abspath(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
path = BIS_path + '/' + 'BISTelligen_Project_Data.csv'
train_data, test_data = 0, 0
threshold = 0

trainer = mm.ModelTrain()

def SetData(scaled=True, key_num = -1):
  global train_data, test_data

  train_data, test_data = dp.GetPreprocessedData(path, scaled, key_num = key_num)

def GetModel(model_name='MCD', param_dict={}):
  '''
  input
  - model_name
  - param_dict
  model parameter
  [default value in 'ModelTrain' Class]
  param_dict = {'contamination': 0.01,
                           'nu': 0.01,
                           'novelty': True,
                           'random_state': 42,
                           'n_components': 1,
                           'covariance_type': 'full',
                           'momentum': 0.9,
                           'learning_rate': 0.03,
                           'epochs': 100,
                           'patience': 10,
                           'n_neighbors': 20,
                           'kernel': 'rbf',
                           'degree': 3,
                           'n_estimators': 100,
                           'support_fraction': None}
  ------------------------------------------------------
  return
  - model
  '''

  global trainer

  trainer.SetTrainer(train_data)
  trainer.SetParam(param_dict)
  model = trainer.GetTrainedModel(model_name)

  return model

def GetAnomalyScore(model=None):
  '''
  input
  - model
  ---------------------
  return
  - anomaly score
  '''

  
  model_name = type(model).__name__
  if model_name == 'GaussianMixture':
    model_name = 'GMM'


  if model_name in ['MCD','LOF']:
    anomaly_score = model.decision_function(test_data)

  elif model_name in ['OCSVM','IForest']:
    anomaly_score = model.decision_function(test_data) + np.abs(np.min(model.decision_function(test_data)))
  elif model_name == 'GMM':
    anomaly_score = np.sum(-model._estimate_weighted_log_prob(test_data), axis = 1)
  else:
    reconstruction = model.predict(test_data)
    anomaly_score = np.mean(np.power(test_data-reconstruction,2),axis=1)
    

  return anomaly_score

def ShowHealthIndex(model = None, anomaly_score = None, scaled = True, key_num = 123456):
  '''
  input
  - model

  - anomaly_score

  - scaled
  True = RobustScaling, False = No scaling

  - key_num
  select key in 0~6

  -----------------------
  return
  - visualize anomaly score by scatterplot
  '''

  model_name = type(model).__name__
  if model_name == 'Sequential':
    model_name = 'AutoEncoder'
  elif model_name == 'GaussianMixture':
    model_name = 'GMM'
  sns.scatterplot(range(len(anomaly_score)), anomaly_score)
  plt.title('{} health index in key {} '.format(model_name, key_num ,scaled), fontsize = 25)


def DoXAI(model=None, key_num=1, threshold=0, plot_type=0, sample_index=0):
  '''
  input
  - model

  - threshold

  - plot_type (0 or 1)
  0 = summary plot(bar type), 1 = force plot

  - sample_index
  sample index number
  --------------------------------------------
  return
  - XAI result visualizaion
  '''
  model_name = type(model).__name__
  if model_name == 'GaussianMixture':
    model_name = 'GMM'

  # AutoEncoder
  if model_name == 'Sequential':
    model_name = 'AutoEncoder'
    score = GetAnomalyScore(model)
    exp_model = xx.AutoEncoderSHAP(threshold_to_explain=threshold, reconstruction_error_percent=0.9,
                                   shap_values_selection='constant')
    shap_values_all = exp_model.explain_unsupervised_data(x_train=train_data,
                                                          x_explain=test_data,
                                                          autoencoder=model,
                                                          return_shap_values=True)

    print(shap_values_all)

    if plot_type == 0:
      col = shap_values_all.sum().sort_values().index[0]
      shap_values_all.drop([col], axis=1, inplace=True)
      shap.summary_plot(shap_values_all.values, shap_values_all.columns, plot_type="bar", show=False)
      plt.title('{} summary_plot about {} in key{}'.format(model_name, col, key_num), fontsize=20)


    elif plot_type == 1:
      shap_values = shap_values_all.iloc[sample_index]
      col = shap_values[shap_values == -1].index
      shap_values.drop(col, inplace=True)
      print(shap_values.index)
      reconstruction = pd.DataFrame(model.predict(train_data), columns=train_data.columns)

      # mse 가장 큰(shap value 정확하지 않은) 변수 제거 후 expected value 계산
      train_data.drop(col, axis=1, inplace=True)
      reconstruction.drop(col, axis=1, inplace=True)
      error = np.mean(np.power(train_data - reconstruction, 2), axis=1)
      expected_value = np.mean(error)

      shap.force_plot(expected_value, shap_values=shap_values.values, feature_names=shap_values.index, show=False,
                      matplotlib=True)
      plt.title('{} force_plot about {} in key{}'.format(model_name, col[0], key_num), fontsize=20)

    plt.gcf().subplots_adjust(bottom=0.2)
    plt.savefig(BIS_path+'/'+'src/XAI/plot/{}_key{}_type{}.png'.format(model_name, key_num, plot_type), bbox_inches='tight',
                pad_inches=0.1)
    plt.show()

  # Other Models
  else:
    score = GetAnomalyScore(model)
    shap_values_all, explainer = xx.OtherModelSHAP(model).novelty_contribution(train_data, test_data, score, threshold)
    if plot_type == 0:
      shap.summary_plot(shap_values_all.values, shap_values_all.columns, plot_type="bar", show=False)
      plt.title('{} summary_plot in key{}'.format(model_name, key_num), fontsize=20)
    elif plot_type == 1:
      shap.force_plot(explainer.expected_value, shap_values=shap_values_all.values[0],
                      feature_names=shap_values_all.columns, show=False, matplotlib=True)
      plt.title('{} force_plot in key{}'.format(model_name, key_num), fontsize=20)
    plt.gcf().subplots_adjust(bottom=0.2)
    plt.savefig(BIS_path+'/'+'src/XAI/plot/{}_key{}_type{}.png'.format(model_name, key_num, plot_type), bbox_inches='tight',
                pad_inches=0.1)
    plt.show()

save_path = BIS_path +'/' +'src/model/saved_model'
best_path = BIS_path +'/' +'src/model/best_model'

# model.saved_model 폴더에 모델 저장
def SaveModel(model, path ,key_num = 0):
  model_name = type(model).__name__
  if model_name == 'GaussianMixture':
    model_name = 'GMM'

  #AutoEncoder
  if model_name =='Sequential':
    file = 'AE_key' + str(key_num) + '.h5'
    filename = '/'.join([path, file])
    model.save(filename)
    print('model saved in PATH : {}'.format(filename))

  #Other Models
  else:
    file = model_name + '_key' +str(key_num)
    filename = '/'.join([path, file])
    #'_'.join(['best', type(model).__name__])
    joblib.dump(model, filename)
    print('model saved in PATH : {}'.format(filename))

# model.saved_model 폴더에서 모델 불러옴
def LoadModel(model_name, path ,key_num = 0):
  
  #AutoEncoder
  if model_name =='AE':
    file = 'AE_key' + str(key_num) + '.h5'
    filename = '/'.join([path, file])
    model = load_model(filename)
    print('model load from PATH : {}'.format(filename))

  #Other Models
  else:
    file = model_name + '_key' +str(key_num)
    filename ='/'.join([path, file])
    model = joblib.load(filename)
    print('model load from PATH : {}'.format(filename))
    
  return model

SetData()

"""# MCD """

# # scale o
# plt.rcParams["figure.figsize"] = (20, 20)
# for i in range(1, 7):
#     plt.subplot(3,2,i)
#     SetData(key_num = i)
#     model = GetModel(model_name = 'MCD')
#     model_name = type(model).__name__
#     SaveModel(model,path = save_path, key_num = i)
#     score = GetAnomalyScore(model)
#     ShowHealthIndex(model, score, key_num = i)
#     plt.xticks(fontsize=15)
#     plt.yticks(fontsize=15)

# # scale X
# plt.rcParams["figure.figsize"] = (20, 20)
# for i in range(1, 7):
#     plt.subplot(3,2,i)
#     SetData(scaled = False, key_num = i)
#     model = GetModel(model_name = 'MCD')
#     model_name = type(model).__name__
#     score = GetAnomalyScore(model)
#     ShowHealthIndex(model, score, key_num = i)
#     plt.xticks(fontsize=15)
#     plt.yticks(fontsize=15)

"""# LOF"""

# scale o
# plt.rcParams["figure.figsize"] = (20, 20)
# for i in range(1, 7):
#     plt.subplot(3,2,i)
#     SetData(key_num = i)
#     model = GetModel(model_name = 'LOF',param_dict = {'n_neighbors':400})
#     model_name = type(model).__name__
#     SaveModel(model,path = save_path, key_num = i)
#     score = GetAnomalyScore(model)
#     ShowHealthIndex(model, score, key_num = i)
#     plt.xticks(fontsize=15)
#     plt.yticks(fontsize=15)
#     plt.title('{} health index key = {}'.format(model_name, i),fontsize=30)
# print(model)
#
# # scale x
# plt.rcParams["figure.figsize"] = (20, 20)
# for i in range(1, 7):
#     plt.subplot(3,2,i)
#     SetData(scaled = False, key_num = i)
#     model = GetModel(model_name = 'LOF', param_dict = {'n_neighbors': 30})
#     model_name = type(model).__name__
#     score = GetAnomalyScore(model)
#     ShowHealthIndex(model, score, key_num = i)
#     plt.xticks(fontsize=15)
#     plt.yticks(fontsize=15)
#     plt.title('{} health index key = {}'.format(model_name, i),fontsize=30)
# print(model)

"""# OCSVM"""

# # scale o
# plt.rcParams["figure.figsize"] = (20, 20)
# for i in range(1, 7):
#     plt.subplot(3,2,i)
#     SetData(key_num = i)
#     model = GetModel(model_name = 'OCSVM')
#     model_name = type(model).__name__
#     SaveModel(model,path = save_path, key_num = i)
#     score = GetAnomalyScore(model)
#     ShowHealthIndex(model, score, key_num = i)
#     plt.xticks(fontsize=15)
#     plt.yticks(fontsize=15)
#     plt.title('{} health index key = {}'.format(model_name, i),fontsize=30)
# print(model)

# # scale x
# plt.rcParams["figure.figsize"] = (20, 20)
# for i in range(1, 7):
#     plt.subplot(3,2,i)
#     SetData(scaled = False, key_num = i)
#     model = GetModel(model_name = 'OCSVM')
#     model_name = type(model).__name__
#     score = GetAnomalyScore(model)
#     ShowHealthIndex(model, score, key_num = i)
#     plt.xticks(fontsize=15)
#     plt.yticks(fontsize=15)
#     plt.title('{} health index key = {}'.format(model_name, i),fontsize=30)
# print(model)

"""# GMM"""

# # scale o
# plt.rcParams["figure.figsize"] = (20, 20)
# for i in range(1, 7):
#     plt.subplot(3,2,i)
#     SetData(key_num = i)
#     model = GetModel(model_name = 'GMM', param_dict = {'n_components': 2, 'covariance_type': 'full'})
#     model_name = type(model).__name__
#     SaveModel(model,path = save_path, key_num = i)
#     score = GetAnomalyScore(model)
#     print(np.min(score))
#     ShowHealthIndex(model, score, key_num = i)
#     plt.xticks(fontsize=15)
#     plt.yticks(fontsize=15)
#     plt.title('{} health index key = {}'.format(model_name, i),fontsize=30)
# print(model)

# # scale x
# plt.rcParams["figure.figsize"] = (20, 20)
# for i in range(1, 7):
#     plt.subplot(3,2,i)
#     SetData(scaled = False, key_num = i)
#     model = GetModel(model_name = 'GMM', param_dict = {'n_components':2, 'covariance_type': 'full'})
#     model_name = type(model).__name__
#     score = GetAnomalyScore(model)
#     ShowHealthIndex(model, score, key_num = i)
#     plt.xticks(fontsize=15)
#     plt.yticks(fontsize=15)
#     plt.title('{} health index key = {}'.format(model_name, i),fontsize=30)
# print(model)

"""# Isolation Forest"""

# # scale o
# plt.rcParams["figure.figsize"] = (20, 20)
# for i in range(1, 7):
#     plt.subplot(3,2,i)
#     SetData(key_num = i)
#     model = GetModel(model_name = 'IForest', param_dict = {'n_estimators': 200})
#     model_name = type(model).__name__
#     SaveModel(model,path = save_path, key_num = i)
#     score = GetAnomalyScore(model)
#     ShowHealthIndex(model, score, key_num = i)
#     plt.xticks(fontsize=15)
#     plt.yticks(fontsize=15)
#     plt.title('{} health index key = {}'.format(model_name, i),fontsize=30)
# print(model)

# # scale x
# plt.rcParams["figure.figsize"] = (20, 20)
# for i in range(1, 7):
#     plt.subplot(3,2,i)
#     SetData(scaled = False, key_num = i)
#     model = GetModel(model_name = 'IForest', param_dict = {'n_estimators': 200})
#     model_name = type(model).__name__
#     score = GetAnomalyScore(model)
#     ShowHealthIndex(model, score, key_num = i)
#     plt.xticks(fontsize=15)
#     plt.yticks(fontsize=15)
#     plt.title('{} health index key = {}'.format(model_name, i),fontsize=30)
# print(model)

"""# AutoEncoder"""

# # scale o
# plt.rcParams["figure.figsize"] = (20, 20)
# for i in range(1, 7):
#     plt.subplot(3,2,i)
#     SetData(key_num = i)
#     model = GetModel(model_name = 'AE', param_dict = {'momentum':0.6, 'learning_rate':0.03, 'patience':50,'epochs':200})
#     SaveModel(model,path = save_path, key_num = i)
#     model_name = type(model).__name__
#     score = GetAnomalyScore(model)
#     ShowHealthIndex(model, score, key_num = i)
#     plt.xticks(fontsize=15)
#     plt.yticks(fontsize=15)
# print(model)

# # scale x
# plt.rcParams["figure.figsize"] = (20, 20)
# for i in range(1, 7):
#     plt.subplot(3,2,i)
#     SetData(scaled = False, key_num = i)
#     model = GetModel(model_name = 'AE', param_dict = {'momentum': 0.6, 'learning_rate': 0.03,'patience':20})
#     model_name = type(model).__name__
#     score = GetAnomalyScore(model)
#     ShowHealthIndex(model, score, key_num = i)
#     plt.xticks(fontsize=15)
#     plt.yticks(fontsize=15)
# print(model)

"""#Best Model XAI"""

# for i in range(1, 7):
#   SetData(key_num = i)
#   model = LoadModel('LOF',save_path, key_num = i)
#   SaveModel(model, best_path, key_num = i)
#   DoXAI(model=model, threshold = 1, plot_type = 0)
#
# for i in range(1, 7):
#   SetData(key_num = i)
#   model = LoadModel('LOF',save_path, key_num = i)
#   SaveModel(model, best_path, key_num = i)
#   DoXAI(model=model, threshold = 1, plot_type = 1)
