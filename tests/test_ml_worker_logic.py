# tests/test_ml_worker_logic.py

import pandas as pd
from retraining_pipeline.preprocess import preprocess_data

def test_preprocess_data_cleaning():
    """
    Tests if the preprocessing function correctly cleans text.
    It should remove URLs, HTML tags, numbers, and stopwords.
    """
    # Arrange: Create a sample DataFrame with messy data
    raw_data = {
        'subject': ['Test Subject 1'],
        'description': ['<p>Hello team,</p> please check http://example.com. My number is 123-456-7890. This is a test.'],
    }
    df = pd.DataFrame(raw_data)
    
    # Act: Run the function we want to test
    processed_df = preprocess_data(df)
    
    # Assert: Check if the output is what we expect
    actual_text = processed_df['processed_text'].iloc[0]
    
    # Note: The expected text may vary slightly based on NLTK/spaCy versions.
    # The key is that URLs, HTML, numbers, and stopwords are gone.
    assert "http" not in actual_text
    assert "<p>" not in actual_text
    assert "123" not in actual_text
    assert "is" not in actual_text # 'is' is a stopword
    assert "test" in actual_text
    assert "subject" in actual_text