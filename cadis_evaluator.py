"""
CADIS Evaluator — Benchmark Script
Measures QA F1 and Summarization ROUGE scores against test_dataset.csv
"""

import re
import csv
import sys
from typing import Optional, Tuple

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    def tqdm(iterable, *args, **kwargs):
        return iterable

from modules.utils import load_qa_pipeline, load_summarizer


def clean_text(text: str) -> str:
    """Clean raw text using standard regex substitutions."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def calculate_f1(predicted: str, true: str) -> float:
    """Calculate F1 score between predicted and true answer strings."""
    pred_tokens = set(clean_text(predicted).lower().split())
    true_tokens = set(clean_text(true).lower().split())
    
    if not pred_tokens or not true_tokens:
        return 0.0
    
    intersection = pred_tokens & true_tokens
    if not intersection:
        return 0.0
    
    precision = len(intersection) / len(pred_tokens)
    recall = len(intersection) / len(true_tokens)
    
    if precision + recall == 0:
        return 0.0
    
    f1 = 2 * (precision * recall) / (precision + recall)
    return f1


def calculate_rouge(predicted: str, true: str) -> Tuple[float, float]:
    """Calculate ROUGE-1 and ROUGE-L scores."""
    try:
        from rouge_score import rouge_scorer
    except ImportError:
        try:
            from rouge import Rouge
        except ImportError:
            print("ERROR: Please install rouge-score or rouge library: pip install rouge-score")
            sys.exit(1)
        
        rouge = Rouge()
        scores = rouge.get_scores(predicted, true)
        return scores[0]['rouge-1']['f'], scores[0]['rouge-l']['f']
    
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rougeL'], use_stemmer=True)
    scores = scorer.score(true, predicted)
    return scores['rouge1'].fmeasure, scores['rougeL'].fmeasure


def truncate_for_summarizer(text: str, max_words: int = 400) -> str:
    """Dynamic length checking to prevent pipeline crashes on short text."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return ' '.join(words[:max_words])


def run_qa(qa_pipeline, document: str, question: str) -> str:
    """Run QA pipeline and extract answer."""
    try:
        result = qa_pipeline(question=question, context=document)
        return result['answer']
    except Exception as e:
        return f"[QA Error: {e}]"


def run_summarization(summarizer_pipeline, document: str) -> str:
    """Run summarization with length safety checks."""
    truncated = truncate_for_summarizer(document)
    
    if len(truncated.split()) < 10:
        return truncated
    
    try:
        result = summarizer_pipeline(
            truncated,
            max_length=90,
            min_length=25,
            do_sample=False
        )
        return result[0]['summary_text']
    except Exception as e:
        return f"[Summarization Error: {e}]"


def load_test_dataset(path: str) -> list:
    """Load test dataset from CSV file."""
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('document_text') and (row.get('true_answer') or row.get('true_summary')):
                rows.append(row)
    return rows


def print_dashboard(qa_results: list, summ_results: list):
    """Print professional formatted terminal dashboard."""
    qa_f1_scores = [r['f1'] for r in qa_results if isinstance(r['f1'], (int, float))]
    rouge1_scores = [r['rouge1'] for r in summ_results if isinstance(r['rouge1'], (int, float))]
    rougel_scores = [r['rougel'] for r in summ_results if isinstance(r['rougel'], (int, float))]
    
    avg_qa_f1 = sum(qa_f1_scores) / len(qa_f1_scores) if qa_f1_scores else 0.0
    avg_rouge1 = sum(rouge1_scores) / len(rouge1_scores) if rouge1_scores else 0.0
    avg_rougel = sum(rougel_scores) / len(rougel_scores) if rougel_scores else 0.0
    
    total_samples = len(qa_results) + len(summ_results)
    qa_passed = sum(1 for s in qa_f1_scores if s >= 0.5)
    summ_passed = sum(1 for s in rouge1_scores if s >= 0.3)
    
    print("\n" + "=" * 70)
    print("              CADIS BENCHMARK RESULTS".center(70))
    print("=" * 70)
    
    print("\n┌───────────────────── QA ENGINE PERFORMANCE ─────────────────────┐")
    print(f"│  Samples Evaluated:     {len(qa_results):>5}                              │")
    print(f"│  Avg F1 Score:           {avg_qa_f1:>5.1%}                              │")
    print(f"│  Samples (F1 ≥ 0.5):     {qa_passed:>5} ({qa_passed/len(qa_results)*100:.1f}%)                     │")
    print("└──────────────────────────────────────────────────────────────────┘")
    
    print("\n┌────────────────── SUMMARIZATION PERFORMANCE ──────────────────┐")
    print(f"│  Samples Evaluated:     {len(summ_results):>5}                              │")
    print(f"│  Avg ROUGE-1:            {avg_rouge1:>5.1%}                              │")
    print(f"│  Avg ROUGE-L:            {avg_rougel:>5.1%}                              │")
    print(f"│  Samples (R1 ≥ 0.3):     {summ_passed:>5} ({summ_passed/len(summ_results)*100:.1f}%)                     │")
    print("└────────────────────────────────────────────────────────────────┘")
    
    print("\n┌────────────────────── OVERALL METRICS ───────────────────────┐")
    overall_score = (avg_qa_f1 + avg_rouge1 + avg_rougel) / 3
    print(f"│  Combined Score:        {overall_score:>5.1%}                              │")
    print(f"│  Total Samples:         {total_samples:>5}                              │")
    print("└──────────────────────────────────────────────────────────────────┘")
    
    print("\n" + "─" * 70)
    print("Legend: QA F1 ≥ 0.5 = Acceptable | ROUGE ≥ 0.3 = Acceptable")
    print("=" * 70 + "\n")


def main():
    print("\n[INFO] Loading CADIS pipelines...")
    qa_pipeline = load_qa_pipeline()
    summarizer = load_summarizer()
    
    dataset_path = "test_dataset.csv"
    print(f"[INFO] Loading test dataset from {dataset_path}...")
    
    dataset = load_test_dataset(dataset_path)
    print(f"[INFO] Loaded {len(dataset)} test samples\n")
    
    qa_results = []
    summ_results = []
    
    print("[BENCHMARK] Running QA evaluations...")
    qa_samples = [d for d in dataset if d.get('question') and d.get('true_answer')]
    
    for row in tqdm(qa_samples, desc="QA Progress", unit="doc"):
        doc = clean_text(row['document_text'])
        question = clean_text(row['question'])
        true_answer = clean_text(row['true_answer'])
        
        pred_answer = run_qa(qa_pipeline, doc, question)
        f1 = calculate_f1(pred_answer, true_answer)
        
        qa_results.append({
            'question': question,
            'predicted': pred_answer,
            'true': true_answer,
            'f1': f1
        })
    
    print("\n[BENCHMARK] Running Summarization evaluations...")
    summ_samples = [d for d in dataset if d.get('true_summary')]
    
    for row in tqdm(summ_samples, desc="Summarization Progress", unit="doc"):
        doc = clean_text(row['document_text'])
        true_summary = clean_text(row['true_summary'])
        
        pred_summary = run_summarization(summarizer, doc)
        rouge1, rougel = calculate_rouge(pred_summary, true_summary)
        
        summ_results.append({
            'predicted': pred_summary,
            'true': true_summary,
            'rouge1': rouge1,
            'rougel': rougel
        })
    
    print_dashboard(qa_results, summ_results)


if __name__ == "__main__":
    main()
