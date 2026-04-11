import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import sys
import warnings

warnings.filterwarnings('ignore')


def load_data(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    required_cols = {'sentence', 'trigger_preposition', 'candidate_1', 'candidate_2', 'true_head'}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return df


def embed_texts(model, sentences: list) -> np.ndarray:
    return model.encode(sentences, convert_to_numpy=True)


def evaluate_pp_attachment(df: pd.DataFrame, model_name: str = 'all-MiniLM-L6-v2') -> dict:
    print(f"Loading model: {model_name}...")
    model = SentenceTransformer(model_name)
    
    results = {
        'total': len(df),
        'correct': 0,
        'failed': 0,
        'details': []
    }
    
    print("Processing rows...")
    
    for idx, row in df.iterrows():
        sentence = str(row['sentence'])
        candidate_1 = str(row['candidate_1'])
        candidate_2 = str(row['candidate_2'])
        true_head = str(row['true_head']).strip().lower()
        
        sentence_emb = embed_texts(model, [sentence])
        cand_emb = embed_texts(model, [candidate_1, candidate_2])
        
        similarities = cosine_similarity(sentence_emb, cand_emb)[0]
        
        sim_1, sim_2 = similarities[0], similarities[1]
        
        if sim_1 > sim_2:
            predicted_head = 'verb'
        else:
            predicted_head = 'noun1'
        
        is_correct = (predicted_head == true_head)
        
        if is_correct:
            results['correct'] += 1
        else:
            results['failed'] += 1
        
        results['details'].append({
            'index': idx,
            'sentence': sentence[:80] + '...' if len(sentence) > 80 else sentence,
            'candidate_1': candidate_1,
            'candidate_2': candidate_2,
            'true_head': true_head,
            'predicted_head': predicted_head,
            'sim_candidate_1': round(sim_1, 4),
            'sim_candidate_2': round(sim_2, 4),
            'correct': is_correct
        })
    
    results['accuracy'] = round((results['correct'] / results['total']) * 100, 2)
    
    return results


def print_report(results: dict) -> None:
    print("\n" + "=" * 60)
    print("       PP ATTACHMENT RESOLUTION - EVALUATION REPORT")
    print("=" * 60)
    print(f"\n  Model Used: all-MiniLM-L6-v2")
    print(f"\n  {'-' * 50}")
    print(f"  | METRICS")
    print(f"  {'-' * 50}")
    print(f"  | Total Processed    : {results['total']:>6}")
    print(f"  | Correct Predictions: {results['correct']:>6}")
    print(f"  | Failed Predictions : {results['failed']:>6}")
    print(f"  | Overall Accuracy   : {results['accuracy']:>6.2f}%")
    print(f"  {'-' * 50}")
    print("\n")


def main():
    filepath = "data/ambiguity_dataset.csv"
    
    try:
        print("Loading dataset...")
        df = load_data(filepath)
        print(f"Loaded {len(df)} rows.\n")
        
        results = evaluate_pp_attachment(df)
        print_report(results)
        
    except FileNotFoundError:
        print(f"ERROR: File not found - {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()