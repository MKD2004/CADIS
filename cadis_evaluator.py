import pandas as pd
from tqdm import tqdm
import string
import re
from collections import Counter
from rouge_score import rouge_scorer
import warnings

# IMPORT YOUR ACTUAL CADIS MODULES
from modules import preprocessing, ambiguity, qa_engine, summarizer

# Suppress technical warnings for a clean research report
warnings.filterwarnings("ignore")

# ==========================================
# 1. TEXT NORMALIZATION & MATH LOGIC
# ==========================================
def normalize_text(text):
    if not isinstance(text, str): return ""
    text = text.lower()
    text = "".join(ch for ch in text if ch not in set(string.punctuation))
    text = re.sub(r'\b(a|an|the)\b', ' ', text)
    return " ".join(text.split())

def calculate_qa_metrics(prediction, ground_truth):
    """Calculates Exact Match and F1 Score for a single QA pair."""
    norm_pred = normalize_text(prediction)
    norm_truth = normalize_text(ground_truth)
    
    # Exact Match
    em = int(norm_pred == norm_truth)
    
    # F1 Score (Token Overlap)
    pred_tokens = norm_pred.split()
    truth_tokens = norm_truth.split()
    common = Counter(pred_tokens) & Counter(truth_tokens)
    num_same = sum(common.values())
    
    if len(pred_tokens) == 0 or len(truth_tokens) == 0:
        f1 = int(pred_tokens == truth_tokens)
    elif num_same == 0:
        f1 = 0.0
    else:
        precision = 1.0 * num_same / len(pred_tokens)
        recall = 1.0 * num_same / len(truth_tokens)
        f1 = (2 * precision * recall) / (precision + recall)
    
    return em, f1

def calculate_rouge(prediction, ground_truth):
    """Calculates ROUGE-1, ROUGE-2, and ROUGE-L using official rouge-score package."""
    # Bulletproof: ensure both inputs are strings and stripped
    if not isinstance(prediction, str):
        prediction = str(prediction) if prediction is not None else ""
    if not isinstance(ground_truth, str):
        ground_truth = str(ground_truth) if ground_truth is not None else ""
    
    prediction = prediction.strip()
    ground_truth = ground_truth.strip()
    
    if not prediction or not ground_truth:
        return {"r1": 0.0, "r2": 0.0, "rL": 0.0}
    
    # Use official rouge_scorer from rouge-score package
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    scores = scorer.score(ground_truth, prediction)
    return {
        "r1": scores['rouge1'].fmeasure,
        "r2": scores['rouge2'].fmeasure,
        "rL": scores['rougeL'].fmeasure
    }

# ==========================================
# 2. FULL PIPELINE EVALUATION ENGINE
# ==========================================
def evaluate_cadis_pipeline(csv_file="test_dataset.csv"):
    print(f"--- CADIS SYSTEM VALIDATION ---\nSource: {csv_file}")
    
    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        print(f"Error: Could not read {csv_file}. Run fetch_benchmarks.py first.")
        return

    # Print exact column names for debugging
    print("CSV COLUMNS:", df.columns.tolist())
    
    # Metrics Accumulators
    metrics = {
        "qa_em": [], "qa_f1": [],
        "rouge1": [], "rouge2": [], "rougeL": [],
        "empty_generations": 0,  # Count of empty/failed generations
        "debug_count": 0  # For visibility debugger (first 3 rows)
    }

    print("\nRunning CADIS Pipeline over benchmark data...")
    
    # tqdm creates the professional progress bar
    for index, row in tqdm(df.iterrows(), total=len(df), desc="Analyzing Documents"):
        # === CONSTRAINT 1: ISOLATE LOOP VARIABLES ===
        # Explicitly reset text variables at start of each iteration
        text_to_summarize = None
        raw_text = None
        cleaned_context = None
        text_for_summarizer = None
        
        # === CONSTRAINT 2: EXACT COLUMN MAPPING ===
        # Input Text: document_text for BOTH QA and Summarization
        raw_text = str(row['document_text'])
        
        # --- PHASE 1: CADIS CONTEXT PREPARATION ---
        # We pass the text through your specific preprocessing logic
        cleaned_context = preprocessing.clean_text(raw_text)
        
        # --- PHASE 2: QA EVALUATION ===
        # QA ONLY IF: pd.notna(row['question'])
        if pd.notna(row['question']) and pd.notna(row['true_answer']):
            # CALLING YOUR ACTUAL QA MODULE
            # QA Target: true_answer
            pred_ans = qa_engine.get_answer(cleaned_context, str(row['question']))
            em, f1 = calculate_qa_metrics(pred_ans, str(row['true_answer']))
            metrics["qa_em"].append(em)
            metrics["qa_f1"].append(f1)

        # --- PHASE 3: SUMMARIZATION EVALUATION ===
        # Summarization ONLY IF: pd.notna(row['true_summary']) and string is not empty
        true_summary = row.get('true_summary')
        is_summarization_row = (
            pd.notna(true_summary) and
            isinstance(true_summary, str) and
            len(true_summary.strip()) > 15
        )
        
        if is_summarization_row:
            row_index = row.name
            # Summarization Target: true_summary
            reference = str(true_summary)
            
            # Input Text: document_text (exact mapping)
            text_to_summarize = raw_text
            
            # Preprocess for summarization
            text_for_summarizer = preprocessing.clean_text(text_to_summarize)
            
            try:
                pred_sum = summarizer.get_summary(text_for_summarizer)
                if not pred_sum or not isinstance(pred_sum, str) or not pred_sum.strip():
                    tqdm.write(f"[WARN] Empty prediction for row {row_index}, penalizing with 0.0")
                    metrics["rouge1"].append(0.0)
                    metrics["rouge2"].append(0.0)
                    metrics["rougeL"].append(0.0)
                    metrics["empty_generations"] += 1
                else:
                    r_scores = calculate_rouge(pred_sum, reference)
                    metrics["rouge1"].append(r_scores['r1'])
                    metrics["rouge2"].append(r_scores['r2'])
                    metrics["rougeL"].append(r_scores['rL'])
                    
                    # Visibility Debugger: first 3 summarization rows
                    if metrics["debug_count"] < 3:
                        idx = metrics["debug_count"] + 1
                        tqdm.write(f"\n--- DEBUG ROW [{idx}] ---")
                        tqdm.write(f"INPUT TEXT: {text_to_summarize[:100]}...")
                        tqdm.write(f"REFERENCE SUMMARY: {reference[:150]}...")
                        tqdm.write(f"GENERATED SUMMARY: {pred_sum[:150]}...")
                        tqdm.write(f"ROUGE-1 SCORE: {r_scores['r1']*100:.2f}%")
                        metrics["debug_count"] += 1
            except Exception as e:
                tqdm.write(f"[WARN] get_summary() failed on row {row_index}: {e}, penalizing with 0.0")
                metrics["rouge1"].append(0.0)
                metrics["rouge2"].append(0.0)
                metrics["rougeL"].append(0.0)
                metrics["empty_generations"] += 1

    # ==========================================
    # 3. FINAL STATISTICAL REPORT
    # ==========================================
    print("\n" + "="*45)
    print(" CADIS RESEARCH VALIDATION COMPLETE")
    print("="*45)
    
    if metrics["qa_f1"]:
        print(f"QA PERFORMANCE (N={len(metrics['qa_f1'])}):")
        print(f"  Avg Exact Match (EM): {sum(metrics['qa_em'])/len(metrics['qa_em'])*100:.2f}%")
        print(f"  Avg F1-Score:         {sum(metrics['qa_f1'])/len(metrics['qa_f1'])*100:.2f}%")
    
    print("-" * 45)
    
    if metrics["rouge1"]:
        print(f"SUMMARIZATION PERFORMANCE (N={len(metrics['rouge1'])}):")
        print(f"  Avg ROUGE-1: {sum(metrics['rouge1'])/len(metrics['rouge1'])*100:.2f}%")
        print(f"  Avg ROUGE-2: {sum(metrics['rouge2'])/len(metrics['rouge2'])*100:.2f}%")
        print(f"  Avg ROUGE-L: {sum(metrics['rougeL'])/len(metrics['rougeL'])*100:.2f}%")
        print(f"  Empty/Failed Generations: {metrics['empty_generations']}")
    print("="*45)

if __name__ == "__main__":
    evaluate_cadis_pipeline()