"""Request/response models for the HTTP API."""

from pydantic import BaseModel


class ProcessRequest(BaseModel):
    text: str


class AskRequest(BaseModel):
    text: str
    question: str
