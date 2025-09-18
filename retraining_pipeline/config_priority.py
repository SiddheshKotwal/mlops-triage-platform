from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from lightgbm import LGBMClassifier

# 1. Define Vectorizers to test (Priority might benefit from just TF-IDF)
VECTORIZERS = {
    'Tfidf': TfidfVectorizer()
}

# 2. Define Classifiers to test
CLASSIFIERS = {
    # 'ExtraTrees': ExtraTreesClassifier(class_weight='balanced', random_state=42),
    # 'LightGBM': LGBMClassifier(class_weight='balanced', random_state=42),
    'CalibratedSVC': CalibratedClassifierCV(LinearSVC(dual=False, max_iter=10000, class_weight='balanced'))
}

# 3. Define Parameter Grids
PARAM_GRIDS = {
    # 'Tfidf': {
    #     'vect__ngram_range': [(1, 1), (1, 2)],
    #     'vect__max_df': [0.75, 1.0]
    # },
    # 'ExtraTrees': {
    #     'clf__n_estimators': [100, 200]
    # },
    # 'LightGBM': {
    #     'clf__n_estimators': [100, 200],
    #     'clf__learning_rate': [0.1, 0.2]
    # },
    'CalibratedSVC': {
        'clf__estimator__C': [0.1, 1, 10]
    }
}