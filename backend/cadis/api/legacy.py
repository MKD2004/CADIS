"""V1 endpoints, kept working during the migration (DECISIONS ADR-023).

Remove each endpoint once no frontend page calls it.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile

from cadis.analysis.pipeline import process_text
from cadis.answer.extractive import answer_question
from cadis.api.schemas import AskRequest, ProcessRequest
from cadis.ingest.parsers import MissingParser, UnsupportedFileType, extract_text
from cadis.models import registry

router = APIRouter(prefix="/api", tags=["legacy-v1"])


@router.post("/extract")
async def extract(file: UploadFile = File(...)):
    """Extract plain text from .txt, .pdf, or .docx uploads."""
    content = await file.read()
    try:
        text = extract_text(file.filename, content)
    except UnsupportedFileType as e:
        raise HTTPException(status_code=400, detail=str(e))
    except MissingParser as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction error: {e}")

    if not text:
        raise HTTPException(status_code=422, detail="No text could be extracted from the file.")
    return {"text": text, "chars": len(text), "words": len(text.split())}


@router.post("/qa-ask")
def qa_ask(req: AskRequest):
    """Answer a single custom question against the provided document."""
    tokenizer, model = registry.get_qa_pipe()
    try:
        return answer_question(req.question, req.text, tokenizer, model, registry.get_embedder())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process")
def process(req: ProcessRequest):
    """Run all six modules over the text in one request."""
    text = req.text.strip()
    if not text:
        return {"error": "Empty document"}
    return process_text(text)
