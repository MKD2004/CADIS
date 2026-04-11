import pandas as pd
from datasets import load_dataset
import random

def build_evaluation_dataset(output_file="test_dataset.csv", num_squad=45, num_cnn=55):
    print("Downloading SQuAD (QA) dataset...")
    squad = load_dataset("squad_v2", split="validation")
    
    print("Downloading CNN/DailyMail (Summarization) dataset...")
    cnn_dm = load_dataset("cnn_dailymail", "3.0.0", split="validation")
    
    # === SQuAD: 45 rows ===
    print(f"Extracting {num_squad} SQuAD QA rows...")
    squad_rows = []
    
    # Keep sampling until we get 45 valid SQuAD rows (with non-empty answers)
    while len(squad_rows) < num_squad:
        idx = random.randint(0, len(squad) - 1)
        sq_item = squad[idx]
        # Skip unanswerable questions (empty answers list)
        if not sq_item['answers']['text']:
            continue
        row = {
            "document_text": sq_item['context'],
            "question": sq_item['question'],
            "true_answer": sq_item['answers']['text'][0],
            "true_summary": pd.NA  # Explicit NaN for QA rows
        }
        squad_rows.append(row)
    
    # === CNN/DailyMail: 55 rows ===
    print(f"Extracting {num_cnn} CNN summarization rows...")
    cnn_rows = []
    cnn_indices = random.sample(range(len(cnn_dm)), num_cnn)
    
    for idx in cnn_indices:
        cnn_item = cnn_dm[idx]
        row = {
            "document_text": cnn_item['article'],
            "question": pd.NA,  # Explicit NaN for summarization rows
            "true_answer": pd.NA,  # Explicit NaN for summarization rows
            "true_summary": cnn_item['highlights']
        }
        cnn_rows.append(row)
    
    # === Combine DataFrames ===
    print("Building combined DataFrame...")
    df_squad = pd.DataFrame(squad_rows)
    df_cnn = pd.DataFrame(cnn_rows)
    
    df = pd.concat([df_squad, df_cnn], ignore_index=True)
    
    # === Shuffle the DataFrame ===
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    # === Export to CSV ===
    df.to_csv(output_file, index=False)
    print(f"Successfully saved {num_squad + num_cnn} benchmark rows to {output_file}!")
    print(f"  - SQuAD QA rows: {num_squad}")
    print(f"  - CNN summarization rows: {num_cnn}")

if __name__ == "__main__":
    build_evaluation_dataset()