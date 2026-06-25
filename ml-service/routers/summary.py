from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from services.summarizer import SummarizerService

router = APIRouter()


def get_summarizer() -> SummarizerService:
    svc = SummarizerService.get_instance()
    if not svc.is_ready:
        raise HTTPException(status_code=503, detail="Summarizer is not ready.")
    return svc


class SummaryRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50_000)

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Text must not be empty after trimming whitespace.")
        return v


@router.post("/generate")
def generate_summary(
    request: SummaryRequest,
    summarizer: SummarizerService = Depends(get_summarizer),
):
    try:
        text = request.text.strip()

        if len(text) < 100:
            return {"executive_summary": text, "inference_ms": 0}

        result = summarizer.summarize(text)
        return {
            "executive_summary": result["text"],
            "inference_ms": result["inference_ms"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
