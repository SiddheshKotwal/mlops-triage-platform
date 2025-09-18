from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from lightgbm import LGBMClassifier

# 1. Define Vectorizers to test
VECTORIZERS = {
    # 'Tfidf': TfidfVectorizer(),
    'Count': CountVectorizer()
}

# 2. Define Classifiers to test
CLASSIFIERS = {
    # 'RandomForest': RandomForestClassifier(class_weight='balanced', random_state=42),
    # 'LightGBM': LGBMClassifier(class_weight='balanced', random_state=42),
    'LogisticRegression': LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)
}

# 3. Define Parameter Grids for each component
PARAM_GRIDS = {
    # 'Count': {
    #     'vect__ngram_range': [(1, 1), (1, 2)],
    #     'vect__max_df': [0.85, 1.0],
    # },
    # 'Tfidf': {
    #     'vect__ngram_range': [(1, 1), (1, 2)],
    #     'vect__max_df': [0.85, 1.0],
    # },
    # 'RandomForest': {
    #     'clf__n_estimators': [100, 200],
    #     'clf__max_depth': [None, 20],
    # },
    # 'LightGBM': {
    #     'clf__n_estimators': [100, 200],
    #     'clf__learning_rate': [0.05, 0.1],
    # },
    'LogisticRegression': {
        'clf__C': [0.1, 1, 10],
    }
}