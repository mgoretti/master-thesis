import sys
sys.path.insert(0, '../classes')

from Model import Model as Model

import pickle
import numpy as np
import pandas as pd

import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from importlib import reload

def print_full(x):
    pd.set_option('display.max_rows', len(x))
    print(x)
    pd.reset_option('display.max_rows')

params = {
 'grid.color': '.9',
 'axes.edgecolor': '.5',
 'text.color': '.3',
 'xtick.color': '.5',
 'xtick.direction': 'out',
 'xtick.major.size': 6.0,
 'xtick.minor.size': 3.0,
 'ytick.color': '.5',
 'ytick.direction': 'out',
 'ytick.major.size': 6.0,
 'ytick.minor.size': 3.0
}
sns.set_style("whitegrid", params)

"""
 FEDFUNDS     : Effective Fed Funds Rate, percent.
 GDP          : Real GDP, 3 decimals, billions of Chained 2000 Dollars.
 INDPRO       : Industrial Production Index
 CPIAUCSL     : Consumer Price Index for All Urban Consumers: All Items
 UNRATE       : Civilian Unemployment Rate
 PAYEMS       : All Employees: Total Nonfarm Payrolls
"""

data = pd.read_csv('quarterly.csv', index_col = 'DATE')


import scipy.io as sio

factors_data = sio.loadmat('factors.mat')

# process the factors: raw

factors_q = pd.DataFrame(factors_data['quarterly'])

# drop the last period (as done with the data)
factors_q = factors_q[:-1]

# drop every col that has missings after the beginning
factors_q = factors_q.ix[:, factors_q[5:].isnull().sum(axis=0)==0]



df_raw = data.reset_index(drop = True)
df_raw.columns = ['GDP', 'CPI', 'FF', 'IP', 'emp', 'unemp']

# put the interest variable, GDP, in the format we want to predict: the percentage growth from last period
df = df_raw.copy()
df['GDP'] = df_raw[['GDP']].pct_change()
df = df.iloc[1:]

def splitTimeData(df, ratio):
    rows = len(df.index)
    trainRows = int(rows * (1 - ratio))
    testRows = rows - trainRows

    train = df.ix[0:trainRows-1]
    test = df #df.ix[trainRows:rows+1]
    start = trainRows

    return train, test, start

df_train, df_test, start = splitTimeData(df, 0.18)

'''
standard transformations
'''
from Transform import Transform as Transform

cols = ['IP', 'GDP', 'emp', 'CPI', 'FF']

# not FF, GDP or unemp
t1 = Transform('log', ['IP', 'emp', 'CPI'])

o = {
    'diffs': {
        'IP': 1,
        'GDP': 0,
        'emp': 1,
        'CPI': 2,
        'FF': 1
    }
}


t2 = Transform('diff', cols, o)
t3 = Transform('standardize', cols)
# t3 = Transform('normalize', cols)

transfs =  [t1, t2, t3]

'''
standard scorefuns
'''

def RMSE(y_hat, y):
    start = y_hat.first_valid_index()
    errors = y.loc[start:] - y_hat
    RMSE = np.sqrt(np.mean(np.square(errors)))[0]
    return RMSE

def MAE(y_hat, y):
    start = y_hat.first_valid_index()
    errors = y.loc[start:] - y_hat
    MAE = np.mean(np.absolute(errors))[0]
    return MAE

TRAIN_OFFSET = 160
TEST_OFFSET = df_train.last_valid_index() + 1

import MLP
reload(MLP)
MLP = 1
from MLP import MLP

import Model
reload(Model)
Model = 1
from Model import Model

from var_model import VAR as VAR


from FAVAR import FAVAR

results = {}

favar = FAVAR(factors_q)


cols = ['GDP']
y_col = ['GDP']

X_train, y_train = df_train[cols], df_train[y_col]
X_test, y_test = df_test[cols], df_test[y_col]

lags = 9


def gen_x(X, start):
    X = VAR.gen_X(X, lags, start)
#     X = X[:, 1:] # remove constant
    return X

def gen_y(y, start):
    y = VAR.gen_y(y, lags, start)
    return y

model = MLP((4,), training_epochs = 2000, beta=1e-5, debug = False)

m = Model(model, transfs, gen_x, gen_y, RMSE)

window = [1, 4, 12]
ret_MLPAR = m.expanding_window(X_test, y_test, TEST_OFFSET, window, 'dynamic')
results['MLPAR'] = ret_MLPAR
print([ret_MLPAR[h][0] for h in window])

pickle.dump(ret_MLPAR, open( "MLPAR.p", "wb" ) )
