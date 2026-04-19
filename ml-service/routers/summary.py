from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
# Notice we are importing the direct Model and Tokenizer classes now instead of pipeline
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Global variables to hold our model and tokenizer in memory
tokenizer = None
model = None

def load_summarizer():
    global tokenizer, model
    if model is None:
        logger.info("Loading DistilBART summarizer natively (this may take a minute on first run)...")
        model_id = "sshleifer/distilbart-cnn-12-6"
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_id)
        logger.info("Summarization model loaded successfully.")

class SummaryRequest(BaseModel):
    text: str

@router.post("/generate")
def generate_summary(request: SummaryRequest):
    try:
        text = request.text.strip()
        
        if not text or len(text) < 100:
            return {"executive_summary": text}

        load_summarizer()
        
        # 1. Grab both the input_ids AND the attention_mask
        inputs = tokenizer(text, return_tensors="pt", max_length=1024, truncation=True)
        
        # 2. Pass the mask to the model so it knows what to focus on
        outputs = model.generate(
            input_ids=inputs.input_ids,
            attention_mask=inputs.attention_mask, # <-- The missing link!
            max_length=100,
            min_length=20,
            num_beams=4,          # Activates Beam Search for high-quality summaries
            length_penalty=2.0,   # Forces the AI to compress the text
            do_sample=False
        )
        
        summary_text = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
        
        return {"executive_summary": summary_text}
        
    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))