# from seperate_ver.Transformers import *
# from seperate_ver.KNN_F1score import *

from sklearn.base import BaseEstimator, TransformerMixin
import pandas as pd
import numpy as np
import subprocess
import sys
import sklearn
from sklearn.linear_model import LogisticRegressionCV
sklearn.set_config(transform_output="pandas")  # says pass pandas tables through pipeline instead of numpy matrices
from sklearn.pipeline import Pipeline
from sklearn.impute import KNNImputer
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier  # the KNN model
from sklearn.metrics import f1_score, roc_auc_score  # typical metric used to measure goodness of a model
from sklearn.metrics import precision_score, recall_score, accuracy_score

subprocess.call([sys.executable, '-m', 'pip', 'install', 'category_encoders'])  # replaces !pip install
import category_encoders as ce

# ----------------------------------------------------------------------------
# Transformers
# ----------------------------------------------------------------------------
'''Fitted Transformer'''
# fitted_pipeline = titanic_transformer.fit(X_train, y_train)  # notice just fit method called
# import joblib
# joblib.dump(fitted_pipeline, 'fitted_pipeline.pkl')

class CustomMappingTransformer(BaseEstimator, TransformerMixin):
    """Given a mapping of values to integers, this class converts values in a given column to corresponding integers."""

    def __init__(self, mapping_column, mapping_dict: dict):
        assert isinstance(mapping_dict,
                          dict), f'{self.__class__.__name__} constructor expected dictionary but got {type(mapping_dict)} instead.'
        self.mapping_dict = mapping_dict
        self.mapping_column = mapping_column  # column to focus on

    def fit(self, X, y=None):
        print(f"\nWarning: {self.__class__.__name__}.fit does nothing.\n")
        return self

    def transform(self, X):
        """Given a dataframe, transform it to ... using a dictionary of mappings"""
        assert isinstance(X,
                          pd.core.frame.DataFrame), f'{self.__class__.__name__}.transform expected Dataframe but got {type(X)} instead.'
        assert self.mapping_column in X.columns.to_list(), f'{self.__class__.__name__}.transform unknown column "{self.mapping_column}"'  # column legit?

        # Set up for producing warnings. First have to rework nan values to allow set operations to work.
        # In particular, the conversion of a column to a Series, e.g., X[self.mapping_column], transforms nan values in strange ways that screw up set differencing.
        # Strategy is to convert empty values to a string then the string back to np.nan
        placeholder = "NaN"
        column_values = X[self.mapping_column].fillna(
            placeholder).tolist()  # convert all nan values to the string "NaN" in new list
        column_values = [np.nan if v == placeholder else v for v in column_values]  # now convert back to np.nan
        keys_values = self.mapping_dict.keys()

        column_set = set(
            column_values)  # without the conversion above, the set will fail to have np.nan values where they should be.
        keys_set = set(keys_values)  # this will have np.nan values where they should be so no conversion necessary.

        # now check to see if all keys are contained in column.
        keys_not_found = keys_set - column_set
        if keys_not_found:
            print(
                f"\nWarning: {self.__class__.__name__}[{self.mapping_column}] these mapping keys do not appear in the column: {keys_not_found}\n")

        # now check to see if some keys are absent
        keys_absent = column_set - keys_set
        if keys_absent:
            print(
                f"\nWarning: {self.__class__.__name__}[{self.mapping_column}] these values in the column do not contain corresponding mapping keys: {keys_absent}\n")

        # do actual mapping
        X_ = X.copy()
        X_[self.mapping_column].replace(self.mapping_dict, inplace=True)
        return X_

    def fit_transform(self, X, y=None):
        # self.fit(X,y)
        result = self.transform(X)
        return result


class CustomRenamingTransformer(BaseEstimator, TransformerMixin):
    """This class will rename one or more columns."""

    def __init__(self, renaming_dict: dict):
        assert isinstance(renaming_dict,
                          dict), f'{self.__class__.__name__} constructor expected dictionary but got {type(renaming_dict)} instead.'
        self.renaming_dict = renaming_dict

        # define fit to do nothing but give warning

    def fit(self, X, y=None):
        print(f"\nWarning: {self.__class__.__name__}.fit does nothing.\n")
        return self

        # write the transform method with asserts. Again, maybe copy and paste from MappingTransformer and fix up.

    def transform(self, X):
        assert isinstance(X,
                          pd.core.frame.DataFrame), f'{self.__class__.__name__}.transform expected Dataframe but got {type(X)} instead.'

        keys_values = self.renaming_dict.keys()
        column_set = set(X.columns)
        keys_set = set(keys_values)  # this will have np.nan values where they should be so no conversion necessary.

        # now check to see if all keys are contained in column.
        keys_not_found = keys_set - column_set
        assert not keys_not_found, f"{self.__class__.__name__}[{self.renaming_dict}] these renaming keys do not appear in the column: {keys_not_found}\n"

        # do actual renaming
        X_ = X.copy()
        X_.rename(columns=self.renaming_dict, inplace=True)
        return X_

        # write fit_transform that skips fit

    def fit_transform(self, X, y=None):
        # self.fit(X,y)
        result = self.transform(X)
        return result


class CustomOHETransformer(BaseEstimator, TransformerMixin):
    """This class applies One Hot Encoding to a given column"""

    def __init__(self, target_column, dummy_na=False, drop_first=False):
        self.target_column = target_column
        self.dummy_na = dummy_na
        self.drop_first = drop_first

        # fill in the rest below

    def fit(self, X, y=None):
        print(f"\nWarning: {self.__class__.__name__}.fit does nothing.\n")
        return self

    def transform(self, X):
        assert isinstance(X,
                          pd.core.frame.DataFrame), f'{self.__class__.__name__}.transform expected Dataframe but got {type(X)} instead.'
        assert self.target_column in X.columns.to_list(), f'{self.__class__.__name__}.transform unknown column "{self.target_column}"'  # column legit?

        # do actual OHE
        X_ = pd.get_dummies(X,
                            prefix=self.target_column,
                            prefix_sep='_',
                            columns=[self.target_column],
                            dummy_na=self.dummy_na,
                            drop_first=self.drop_first)
        return X_

    def fit_transform(self, X, y=None):
        # self.fit(X,y)
        result = self.transform(X)
        return result


class CustomSigma3Transformer(BaseEstimator, TransformerMixin):
    """
    Clip outliers using 3 Sigma method through standard deviation and mean
    """

    def __init__(self, target_column):
        self.target_column = target_column
        self.minb = None
        self.maxb = None

    def fit(self, X, y=None):
        """Calculate mean and standard deviation"""
        assert isinstance(X,
                          pd.core.frame.DataFrame), f'{self.__class__.__name__}.transform expected Dataframe but got {type(X)} instead.'
        assert self.target_column in X.columns.to_list(), f'{self.__class__.__name__}.transform unknown column "{self.target_column}"'  # column legit?
        assert all([isinstance(v, (int, float)) for v in X[self.target_column].to_list()])

        std = X[self.target_column].std()
        mean = X[self.target_column].mean()
        self.minb = mean - 3 * std
        self.maxb = mean + 3 * std
        return self

    def transform(self, X):
        """Move the outliers to the boundary"""
        assert isinstance(X,
                          pd.core.frame.DataFrame), f'{self.__class__.__name__}.transform expected Dataframe but got {type(X)} instead.'
        assert self.minb is not None and self.maxb is not None, f'NotFittedError: This {self.__class__.__name__} instance is not fitted yet. Call "fit" with appropriate arguments before using this estimator.'

        X_ = X.copy()
        X_[self.target_column] = X_[self.target_column].clip(lower=self.minb, upper=self.maxb)
        return X_.reset_index(drop=True)

    def fit_transform(self, X, y=None):
        self.fit(X)
        result = self.transform(X)
        return result


class CustomTukeyTransformer(BaseEstimator, TransformerMixin):
    """
    Clip outliers using Tukey method through quartiles and median
    """

    def __init__(self, target_column, fence='outer'):
        assert fence in ['inner', 'outer']
        self.fence = fence
        self.target_column = target_column
        self.minb, self.maxb = None, None

    def fit(self, X, y=None):
        """Calculate boundary values based on fence"""
        assert isinstance(X,
                          pd.core.frame.DataFrame), f'{self.__class__.__name__}.transform expected Dataframe but got {type(X)} instead.'
        assert self.target_column in X.columns.to_list(), f'{self.__class__.__name__}.transform unknown column "{self.target_column}"'  # column legit?
        assert all([isinstance(v, (int, float)) for v in X[self.target_column].to_list()])

        q1 = X[self.target_column].quantile(0.25)
        q3 = X[self.target_column].quantile(0.75)
        iqr = q3 - q1
        match self.fence:
            case 'inner':
                self.minb, self.maxb = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            case 'outer':
                self.minb, self.maxb = q1 - 3 * iqr, q3 + 3 * iqr
        return self

    def transform(self, X):
        """Move the outliers to the boundary"""
        assert isinstance(X,
                          pd.core.frame.DataFrame), f'{self.__class__.__name__}.transform expected Dataframe but got {type(X)} instead.'
        assert self.minb is not None and self.maxb is not None, f'NotFittedError: This {self.__class__.__name__} instance is not fitted yet. Call "fit" with appropriate arguments before using this estimator.'

        X_ = X.copy()
        X_[self.target_column] = X_[self.target_column].clip(lower=self.minb, upper=self.maxb)
        return X_.reset_index(drop=True)

    def fit_transform(self, X, y=None):
        self.fit(X)
        result = self.transform(X)
        return result


class CustomRobustTransformer(BaseEstimator, TransformerMixin):
    """
    This class scales a given column values in [0,1] using Robust Scaler.
    Formula: value_new = (value – median) / iqr #iqr = q3-q1
    """

    def __init__(self, column):
        self.column = column
        self.iqr, self.med = None, None

    def fit(self, X, y=None):
        """Calculate iqr and median"""
        assert isinstance(X,
                          pd.core.frame.DataFrame), f'{self.__class__.__name__}.transform expected Dataframe but got {type(X)} instead.'
        assert self.column in X.columns.to_list(), f'{self.__class__.__name__}.transform unknown column "{self.target_column}"'  # column legit?
        assert all([isinstance(v, (int, float)) for v in X[self.column].to_list()])

        q1 = X[self.column].quantile(0.25)
        q3 = X[self.column].quantile(0.75)
        self.iqr = q3 - q1
        self.med = X[self.column].median()
        return self

    def transform(self, X):
        """Scale using Robust Scaler"""
        assert isinstance(X,
                          pd.core.frame.DataFrame), f'{self.__class__.__name__}.transform expected Dataframe but got {type(X)} instead.'
        assert self.iqr is not None and self.med is not None, f'NotFittedError: This {self.__class__.__name__} instance is not fitted yet. Call "fit" with appropriate arguments before using this estimator.'

        X_ = X.copy()
        X_[self.column] -= self.med
        X_[self.column] /= self.iqr
        # X_[self.column].fillna(0, inplace=True)
        return X_

    def fit_transform(self, X, y=None):
        self.fit(X)
        result = self.transform(X)
        return result

# ----------------------------------------------------------------------------
# DataSetup + Global Variables (Pipelines, rs)
# Ch2 - Cardinality, Correlation, Numeric/Categorical Data,
#       (Binary, Ordinal, Non-Binary(One Hot Encoding)), Pipeline
# Ch4 - Distribution, Clip Outlier(Kurtosis, Skew), 3Sigma Method(Mean+STD), Tukey Method(Median+Quantiles)
# Ch5 - Euclidean distance, Scaling(Min-Max Scaling, Standardization(Z-score Normalization),
#       Robust Scaler, Box Cox normalizer, Yeo Johnson)
# Ch6 - Impute for NaN
# ---------------------------------------------------------------------------
titanic_variance_based_split = 107  # random state that provides best average
customer_variance_based_split = 113  # random state that provides best average
titanic_transformer = Pipeline(steps=[
    ('map_gender', CustomMappingTransformer('Gender', {'Male': 0, 'Female': 1})),
    ('map_class', CustomMappingTransformer('Class', {'Crew': 0, 'C3': 1, 'C2': 2, 'C1': 3})),
    ('target_joined', ce.TargetEncoder(cols=['Joined'],
                                       handle_missing='return_nan',  # will use imputer later to fill in
                                       handle_unknown='return_nan'  # will use imputer later to fill in
                                       )),
    ('tukey_age', CustomTukeyTransformer(target_column='Age', fence='outer')),
    ('tukey_fare', CustomTukeyTransformer(target_column='Fare', fence='outer')),
    ('scale_age', CustomRobustTransformer('Age')),  # from chapter 5
    ('scale_fare', CustomRobustTransformer('Fare')),  # from chapter 5
    ('imputer', KNNImputer(n_neighbors=5, weights="uniform", add_indicator=False))  # from chapter 6
], verbose=True)
customer_transformer = Pipeline(steps=[
    ('map_os', CustomMappingTransformer('OS', {'Android': 0, 'iOS': 1})),
    ('target_isp', ce.TargetEncoder(cols=['ISP'],
                                    handle_missing='return_nan',  # will use imputer later to fill in
                                    handle_unknown='return_nan'  # will use imputer later to fill in
                                    )),
    ('map_level', CustomMappingTransformer('Experience Level', {'low': 0, 'medium': 1, 'high': 2})),
    ('map_gender', CustomMappingTransformer('Gender', {'Male': 0, 'Female': 1})),
    ('tukey_age', CustomTukeyTransformer('Age', 'inner')),  # from chapter 4
    ('tukey_time spent', CustomTukeyTransformer('Time Spent', 'inner')),  # from chapter 4
    ('scale_age', CustomRobustTransformer('Age')),  # from 5
    ('scale_time spent', CustomRobustTransformer('Time Spent')),  # from 5
    ('impute', KNNImputer(n_neighbors=5, weights="uniform", add_indicator=False)),
], verbose=True)

def dataset_setup(original_table, label_column_name: str, the_transformer, rs, ts=.2):
    labels = original_table[label_column_name].to_list()
    table_features = original_table.drop(columns=label_column_name)
    X_train, X_test, y_train, y_test = train_test_split(table_features, labels, test_size=ts, shuffle=True,
                                                        random_state=rs, stratify=labels)
    X_train_transformed = the_transformer.fit_transform(X_train, y_train)  # fit with train
    X_test_transformed = the_transformer.transform(X_test)  # only transform

    # Transform to numpy array
    X_train_numpy = X_train_transformed.to_numpy()
    X_test_numpy = X_test_transformed.to_numpy()
    y_train_numpy = np.array(y_train)
    y_test_numpy = np.array(y_test)
    return X_train_numpy, X_test_numpy, y_train_numpy, y_test_numpy


def titanic_setup(titanic_table, transformer=titanic_transformer, rs=titanic_variance_based_split, ts=.2):
    return dataset_setup(titanic_table, 'Survived', transformer, rs=rs, ts=ts)


def customer_setup(customer_table, transformer=customer_transformer, rs=customer_variance_based_split, ts=.2):
    return dataset_setup(customer_table, 'Rating', transformer, rs=rs, ts=ts)


# ----------------------------------------------------------------------------
# Train-Test Split, stratify split, random state split
# (Ch7)
# ----------------------------------------------------------------------------
def find_random_state(features_df, labels, n=200):
    """Takes a dataframe in and runs the variance code on it.
    It should return the value to use for the random state in the split method.
    """
    model = KNeighborsClassifier(n_neighbors=5)  # instantiate with k=5.
    var = []  # collect test_error/train_error where error based on F1 score

    for i in range(1, n):
        train_X, test_X, train_y, test_y = train_test_split(features_df, labels, test_size=0.2, shuffle=True,
                                                            random_state=i, stratify=labels)
        model.fit(train_X, train_y)  # train model
        train_pred = model.predict(train_X)  # predict against training set
        test_pred = model.predict(test_X)  # predict against test set
        train_f1 = f1_score(train_y, train_pred)  # F1 on training predictions
        test_f1 = f1_score(test_y, test_pred)  # F1 on test predictions
        f1_ratio = test_f1 / train_f1  # take the ratio
        var.append(f1_ratio)

    rs_value = sum(var) / len(var)  # get average ratio value
    idx = np.array(abs(var - rs_value)).argmin()  # find the index of the smallest value
    return idx

# ----------------------------------------------------------------------------
# Loss, (Stochastic) Gradient Descent, Learning Rate, Epoch, Batch, Sigmoid, KNN
# (Ch8)
# ----------------------------------------------------------------------------
def predict(X, w, b):
    yhat = [(x * w + b) for x in X]
    return yhat


def MSE(Y, Yhat):
    sdiffs = [(yhat - y) ** 2 for y, yhat in zip(Y, Yhat)]
    mse = sum(sdiffs) / len(sdiffs)
    return mse


def sgd(X, Y, w, b, lr=.001):
    # X is list of ages, Y is list of fare_labels, w is starting weight, b is stating bias, lr is learning rate
    for i in range(len(X)):
        # get values for rowi
        xi = X[i]  # e.g., age on rowi
        yi = Y[i]  # e.g., actual fare on rowi
        yhat = w * xi + b  # prediction
        # loss = (yhat - yi)**2 = ((w*xi+b) - yi)**2, i.e., f(g(x,w,b),yi)
        # dloss/dw = dl/dyhat * dyhat/dw by the chain rule
        # dloss/dyhat = 2*(yhat - yi) by the power rule (first part of chain)
        # dyhat/dw = d((w*xi+b) - yi)/dw = xi (second part of chain)
        gradient_w = 2 * (yhat - yi) * xi  # take the partial derivative wrt w to get slope
        # for b same first part of chain but then #dyhat/db = d((w*xi+b) - yi)/db = 1 for second part of chain
        gradient_b = 2 * (yhat - yi) * 1  # take the partial derivative wrt b to get slope
        w = w - lr * gradient_w  # if len(X) is 2000, will change 2000 times
        b = b - lr * gradient_b
        # return the last w and b of the loop
    return w, b


def full_batch(X, Y, w, b, lr=.001):
    gw = []
    gb = []
    for i in range(len(X)):
        xi = X[i]
        yi = Y[i]
        yhat = w * xi + b  # prediction
        gradient_w = 2 * (yhat - yi) * xi
        gradient_b = 2 * (yhat - yi) * 1
        gw.append(gradient_w)  # just collect change, don't make it
        gb.append(gradient_b)
    w = w - lr * sum(gw) / len(gw)  # Now average and make the change.
    b = b - lr * sum(gb) / len(gb)
    return w, b


def mini_batch(X, Y, w, b, batch=1, lr=.001):
    assert batch >= 1
    assert batch <= len(X)

    num = len(X) // batch if len(X) % batch == 0 else len(X) // batch + 1

    for batch_idx in range(num):
        start = batch_idx * batch
        batch_X = X[start:batch + start]
        batch_Y = Y[start:batch + start]
        gw = []
        gb = []
        for i in range(len(batch_X)):
            xi = batch_X[i]
            yi = batch_Y[i]
            yhat = w * xi + b  # prediction
            gradient_w = 2 * (yhat - yi) * xi
            gradient_b = 2 * (yhat - yi) * 1
            gw.append(gradient_w)
            gb.append(gradient_b)
        w = w - lr * sum(gw) / len(gw)
        b = b - lr * sum(gb) / len(gb)
    return w, b


# ----------------------------------------------------------------------------
# LogisticRegressionCV, C = 1/lambda (Regularization), Cross Validation,
# Stratified k-folds, sigmoid threshold, Lime Explainer
# (Ch9)
# ----------------------------------------------------------------------------
from sklearn.linear_model import LogisticRegressionCV

def Chapter9(csv_url='https://raw.githubusercontent.com/fickas/asynch_models/main/datasets/titanic_trimmed.csv',label='Survived'):
    titanic_trimmed = pd.read_csv(csv_url)
    labels = titanic_trimmed[label].to_list()
    features = titanic_trimmed.drop(columns=label)
    X_train, X_test, y_train, y_test = train_test_split(features, labels, test_size=0.2, shuffle=True,
                                                        random_state=titanic_variance_based_split, stratify=labels)
    X_train_transformed = titanic_transformer.fit_transform(X_train, y_train)
    X_test_transformed = titanic_transformer.transform(X_test)
    X_train_numpy = X_train_transformed.to_numpy()
    X_test_numpy = X_test_transformed.to_numpy()
    y_train_numpy = np.array(y_train)
    y_test_numpy = np.array(y_test)

    # define model
    model = LogisticRegressionCV(cv=5, random_state=1, max_iter=5000)
    model.fit(X_train_numpy, y_train_numpy)

    # selected model variables
    scores_df = pd.DataFrame(model.scores_[1], columns=range(1,11))  #accuracies across folds and Cs values
    model.Cs_  #the 10 alternatives that were tried
    model.C_  #final Cs chosen - #7
    list(zip(X_train_transformed.columns.to_list(), model.coef_[0])) # weights, yraw = w1*f1 + w2*f2 ... + w6*f6 + b
    model.score(X_train_numpy, y_train_numpy)  # train simple accuracy
    model.score(X_test_numpy, y_test_numpy)  # test simple accuracy

    # prediction scores
    yhat = model.predict(X_test_numpy)
    yprob = model.predict_proba(X_test_numpy)  #output from sigmoid as pair (perished, survived)
    yprob = yprob[:,1]  #grab the 2nd (1) column
    threshold = .5  #might want to explore different values - see below
    yhat2 = [0 if v<=threshold else 1 for v in yprob]
    all(yhat2==yhat)  #yhat is what we got from model.predict
    sum([a==b for a,b in zip(yhat2, y_test_numpy)])/len(yhat2)  #accuary on test set

    import lime
    from lime import lime_tabular
    # lime explainer
    feature_names  = X_train_transformed.columns.to_list()
    explainer = lime.lime_tabular.LimeTabularExplainer(X_train_numpy,
                        feature_names=feature_names,
                        training_labels=y_train_numpy,
                        class_names=[0,1], #Outcome values
                        verbose=True,
                        mode='classification')
    import dill as pickle
    with open('lime_explainer.pkl', 'wb') as file:
        pickle.dump(explainer, file)


# ----------------------------------------------------------------------------
# Confusion Matrix (Precision, Recall, F1, MCC), ROC AUC - score=area under curve
# (Ch10)
# ----------------------------------------------------------------------------
def threshold_results(thresh_list, actuals, predicted):
    '''

    Usage: result_df, fancy_df = threshold_results(np.round(np.arange(0.0,1.01,.05), 2), y_test, yraw)
    '''
    result_df = pd.DataFrame(columns=['threshold', 'precision', 'recall', 'f1', 'accuracy'])
    for t in thresh_list:
        yhat = [1 if v >= t else 0 for v in predicted]
        # note: where TP=0, the Precision and Recall both become 0. And I am saying return 0 in that case.
        precision = precision_score(actuals, yhat, zero_division=0)
        recall = recall_score(actuals, yhat, zero_division=0)
        f1 = f1_score(actuals, yhat)
        accuracy = accuracy_score(actuals, yhat)
        result_df.loc[len(result_df)] = {'threshold': t, 'precision': precision, 'recall': recall, 'f1': f1,
                                         'accuracy': accuracy}

    result_df = result_df.round(2)

    # Next bit fancies up table for printing. See https://betterdatascience.com/style-pandas-dataframes/
    # Note that fancy_df is not really a dataframe. More like a printable object.
    headers = {
        "selector": "th:not(.index_name)",
        "props": "background-color: #800000; color: white; text-align: center"
    }
    properties = {"border": "1px solid black", "width": "65px", "text-align": "center"}

    fancy_df = result_df.style.format(precision=2).set_properties(**properties).set_table_styles([headers])
    return (result_df, fancy_df)

def calculate_roc_auc_solvers(X_train, y_train, X_test, y_test):
    # record AUC score using each solver separately
    roc_auc_scores = []
    solvers = ['newton-cg', 'lbfgs', 'liblinear', 'sag', 'saga']
    for sol in solvers:
        model = LogisticRegressionCV(cv=5, random_state=1, solver=sol, max_iter=500)
        model.fit(X_train, y_train)
        yraw = model.predict_proba(X_test)[:, 1]
        roc_auc_scores.append((sol, roc_auc_score(y_test, yraw)))
    # sort on AUC score
    roc_auc_scores.sort(key=lambda x: x[1])
    return roc_auc_scores

# ----------------------------------------------------------------------------
# Tuning, Configuration Space, Parameter Grid, Halving Search, SVM
# (Ch11)
# ----------------------------------------------------------------------------
from sklearn.experimental import enable_halving_search_cv
from sklearn.model_selection import HalvingGridSearchCV
from sklearn.model_selection import ParameterGrid

def Chapter11():
    titanic_trimmed = pd.read_csv('https://raw.githubusercontent.com/fickas/asynch_models/main/datasets/titanic_trimmed.csv')
    x_train, x_test, y_train, y_test = titanic_setup(titanic_trimmed)
    # configuration space
    knn_grid = dict(n_neighbors=range(5,100,10),
                    weights=('uniform', 'distance'),
                    algorithm=('auto', 'ball_tree', 'kd_tree', 'brute'),
                    p=(1,2)  #When p=1, manhattan_distance, when p=2 euclidean_distance.
    )
    # Parameter Grid
    param_grid = ParameterGrid(knn_grid)  #a list of dictionaries, one for each combo
    len(param_grid)  #160

    knn_model = KNeighborsClassifier() # basic model
    #do the grid search
    halving_cv = HalvingGridSearchCV(
        knn_model, knn_grid,  #our model and the parameter combos we want to try
        scoring="roc_auc",  #from chapter 10
        n_jobs=-1,  #use all available cpus
        min_resources=30,  #"exhaust" sets this to 20, which is non-optimal. Possible bug in algorithm.
        factor=2,  #double samples and take top half of combos on each iteration
        cv=5, random_state=1234,
        refit=True,  #remembers the best combo and gives us back that model already trained and ready for testing
    )

    # selected model
    grid_result = halving_cv.fit(x_train, y_train)
    grid_result.best_params_  #{'algorithm': 'auto', 'n_neighbors': 15, 'p': 1, 'weights': 'uniform'}
    pd.set_option('display.max_colwidth', None)  #don't limit/elide text values in a cell
    df = pd.DataFrame(grid_result.cv_results_)
    df[['iter', 'n_resources', 'params', 'mean_test_score']][0:]
    best_knn_model = grid_result.best_estimator_
    best_knn_model.score(x_test,y_test)  #0.7490494296577946

    # threshold table
    yraw = best_knn_model.predict_proba(x_test)[:,1]
    result_df, fancy_df = threshold_results(np.round(np.arange(0.0,1.01,.05), 2), y_test, yraw)

    # save result
    result_df.to_csv('knn_thresholds.csv', index=False)
    from joblib import dump
    dump(best_knn_model, 'knn_model.joblib')

    # load result
    from joblib import load
    knn_model2 = load('knn_model.joblib')
    knn_model2.predict_proba(x_test)[:,1][:5]  #array([0.6       , 1.        , 1.        , 0.13333333, 0.06666667])
    best_knn_model.predict_proba(x_test)[:,1][:5]  #array([0.6       , 1.        , 1.        , 0.13333333, 0.06666667])

    # Challenge 2: SVM
    from sklearn.svm import SVC
    svc_model = SVC(probability=True, random_state=1)  # needs to be True to get probabilities out
    svc_model.fit(x_train, y_train)
    yraw = svc_model.predict_proba(x_test)[:, 1]
    result_df, fancy_df = threshold_results(np.round(np.arange(0.0,1.01,.05), 2), y_test, yraw)

    # Grid
    # For C, try the values 1,2,3.
    # For gamma try both its values; exclude float.
    # For shrinking, try all its values.
    # For kernel, try everything except 'precomputed' and callable.
    # For max_iter, try 5000, 10000, -1.
    svc_grid = dict(C=(1, 2, 3),
                    # Regularization parameter. The strength of the regularization is inversely proportional to C. Must be strictly positive. The penalty is a squared l2 penalty.
                    gamma=('auto', 'scale'),
                    # Kernel coefficient for ‘rbf’, ‘poly’ and ‘sigmoid’.'scale' uses 1 / (n_features * X.var()), ‘auto’uses 1 / n_features
                    shrinking=(True, False),  # Whether to use the shrinking heuristic.
                    kernel=('sigmoid', 'linear', 'poly', 'rbf'),
                    max_iter=(5000, 10000, -1))
    param_grid = ParameterGrid(svc_grid)
    len(param_grid)  # 144
    len(x_train)  # 1050
    svc_model = SVC(probability=True, random_state=1)  # base model
    # do the grid search
    halving_cv = HalvingGridSearchCV(
        svc_model, svc_grid,  # our model and the parameter combos we want to try
        scoring="roc_auc",  # from chapter 10
        n_jobs=-1,  # use all available cpus
        min_resources=30,  # "exhaust" sets this to 20, which is non-optimal. Possible bug in algorithm.
        factor=2,  # double samples and take top half of combos on each iteration
        cv=5, random_state=1234,
        refit=True,  # remembers the best combo and gives us back that model already trained and ready for testing
    )

    grid_result = halving_cv.fit(x_train, y_train)
    df = pd.DataFrame(grid_result.cv_results_)
    df[['iter', 'n_resources', 'params', 'mean_test_score']][0:]
    grid_result.best_params_
    best_svc_model = grid_result.best_estimator_  # get best model because we have refit=True
    best_svc_model.get_params()

'''
Example Usage:
# define grid ...
grid_result = halving_search(dt_model, dt_grid, x_train, y_train)
best_model = grid_result.best_estimator_
grid_result.best_params_
'''
def halving_search(model, grid, x_train, y_train, factor=2, min_resources="exhaust", scoring='roc_auc'):

  halving_cv = HalvingGridSearchCV(
    model, grid,  #our model and the parameter combos we want to try
    scoring=scoring,  #from chapter 10
    n_jobs=-1,  #use all available cpus
    min_resources=min_resources,  #"exhaust" sets this to 20, which is non-optimal. Possible bug in algorithm.
    factor=factor,  #double samples and take top half of combos on each iteration
    cv=5, random_state=1234,
    refit=True,  #remembers the best combo and gives us back that model already trained and ready for testing
  )
  grid_result = halving_cv.fit(x_train, y_train)
  return grid_result


# ----------------------------------------------------------------------------
# DecisionTreeClassifier,
# (Ch12)
# ----------------------------------------------------------------------------


# ----------------------------------------------------------------------------
#
# (Ch13)
# ----------------------------------------------------------------------------


# ----------------------------------------------------------------------------
#
# (Midterm2)
# ----------------------------------------------------------------------------