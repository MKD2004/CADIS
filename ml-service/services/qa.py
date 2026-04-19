from transformers import pipeline
import logging

logger = logging.getLogger(__name__)

class QAService:
    def __init__(self):
        self.qa_pipeline = None

    def load_model(self):
        logger.info("Loading RoBERTa QA model...")
        # RoBERTa is heavily optimized for extracting exact answers from context blocks
        self.qa_pipeline = pipeline("question-answering", model="deepset/roberta-base-squad2")
        logger.info("QA model loaded successfully.")

    def answer_question(self, question: str, context: str) -> str:
        if not self.qa_pipeline:
            self.load_model()
            
        if not context or not context.strip():
            return "No context provided to find the answer."
            
        try:
            # We feed RoBERTa the question and the ChromaDB chunk
            result = self.qa_pipeline(question=question, context=context[:2500]) # Safety limit
            return result['answer']
        except Exception as e:
            logger.error(f"QA extraction failed: {e}")
            return "I could not extract a definitive answer."

qa_service = QAService()