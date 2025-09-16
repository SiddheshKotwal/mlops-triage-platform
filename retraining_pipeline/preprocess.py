# src/preprocess.py

import pandas as pd
import nltk
import re
from nltk.corpus import stopwords, wordnet
from nltk.stem import WordNetLemmatizer
import os
import sys

LEMMATIZER = WordNetLemmatizer()

# Define a custom set of stop words
stop_words_base = set(stopwords.words('english'))
negations = {'no', 'not', 'nor', 'neither', "don't", "isn't", "wasn't", "shouldn't", "wouldn't", "couldn't"}
useless_words = {'dear', 'customer', 'support', 'team', 'hello', 'hi', 'regards'}
STOP_WORDS = (stop_words_base | useless_words) - negations


def _get_wordnet_pos(treebank_tag):
    """
    Internal helper function to map NLTK's POS tags to WordNet POS tags.
    This is required for POS-aware lemmatization.
    """
    if treebank_tag.startswith('J'):
        return wordnet.ADJ
    elif treebank_tag.startswith('V'):
        return wordnet.VERB
    elif treebank_tag.startswith('N'):
        return wordnet.NOUN
    elif treebank_tag.startswith('R'):
        return wordnet.ADV
    else:
        # Default to noun if no specific tag is found
        return wordnet.NOUN


def _clean_and_lemmatize_text(text: str) -> str:
    """
    Internal helper function to perform all cleaning and processing on a single text string.
    """
    if not isinstance(text, str):
        return ""

    # 1. Convert to lowercase
    text = text.lower()

    # 2. Remove URLs, emails, and file paths
    text = re.sub(r'(https?|ftp)://[^\s/$.?#].[^\s]*|www\.\S+|(\S+@\S+)|([a-z]:\\[^\s:]+)', ' ', text)
    
    # 3. Remove HTML tags
    text = re.sub(r'<.*?>', ' ', text)
    
    # 4. Remove long numbers (e.g., phone numbers, tracking IDs)
    text = re.sub(r'\b(?:\d[ -]?){6,12}\d\b', ' ', text)
    
    # 5. Remove long alphanumeric strings (e.g., transaction IDs, tokens)
    text = re.sub(r'\b[a-z0-9]{20,}\b', ' ', text)

    # 6. Remove all non-alphabetic characters
    text = re.sub(r'[^a-z\s]', ' ', text)

    # 7. Tokenize, POS-tag, and Lemmatize
    tokens = nltk.word_tokenize(text)
    pos_tags = nltk.pos_tag(tokens)
    lemmatized_tokens = [LEMMATIZER.lemmatize(word, _get_wordnet_pos(pos)) for word, pos in pos_tags]

    # 8. Filter out stop words and short tokens
    processed_tokens = [
        word for word in lemmatized_tokens if word not in STOP_WORDS and len(word) > 2
    ]

    return " ".join(processed_tokens).strip()


def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    The main function to preprocess the ticket data.
    It takes a DataFrame with 'subject' and 'description' columns and returns
    a DataFrame with an added 'processed_text' column.

    Args:
        df (pd.DataFrame): The input DataFrame.

    Returns:
        pd.DataFrame: The processed DataFrame.
    """
    print("Starting data preprocessing...")

    # Combine subject and description for a complete text representation
    # Note: Using 'description' to align with our database schema, not 'body'
    df['full_text'] = df['subject'] + ' ' + df['description']
    
    # Apply the cleaning and lemmatization function
    df['processed_text'] = df['full_text'].apply(_clean_and_lemmatize_text)

    print("Preprocessing complete.")
    
    return df