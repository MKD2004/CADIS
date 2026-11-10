"""/collections — create and list collections, upload and list documents."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from cadis.api.deps import Principal, get_allowed_collections, get_db, get_principal
from cadis.api.documents import document_out
from cadis.api.schemas import CollectionCreate, CollectionOut, DocumentOut, UploadOut
from cadis.config import get_settings
from cadis.ingest import service
from cadis.storage import repositories

router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("", response_model=CollectionOut, status_code=201)
def create_collection(body: CollectionCreate, db: Session = Depends(get_db),
                      principal: Principal = Depends(get_principal)):
    repositories.ensure_tenant(db, principal.tenant_id)
    col = repositories.create_collection(db, principal.tenant_id, body.name.strip())
    db.commit()
    return CollectionOut(id=col.id, name=col.name, created_at=col.created_at, document_count=0)


@router.get("", response_model=list[CollectionOut])
def list_collections(db: Session = Depends(get_db),
                     allowed: list[str] = Depends(get_allowed_collections)):
    return [CollectionOut(id=c.id, name=c.name, created_at=c.created_at, document_count=n)
            for c, n in repositories.list_collections(db, allowed)]


def _collection_or_404(db, collection_id, allowed):
    col = repositories.get_collection(db, collection_id, allowed)
    if col is None:
        raise HTTPException(404, "Collection not found")
    return col


@router.get("/{collection_id}", response_model=CollectionOut)
def get_collection(collection_id: str, db: Session = Depends(get_db),
                   allowed: list[str] = Depends(get_allowed_collections)):
    col = _collection_or_404(db, collection_id, allowed)
    n = len(repositories.list_documents(db, collection_id, allowed))
    return CollectionOut(id=col.id, name=col.name, created_at=col.created_at, document_count=n)


@router.get("/{collection_id}/documents", response_model=list[DocumentOut])
def list_documents(collection_id: str, db: Session = Depends(get_db),
                   allowed: list[str] = Depends(get_allowed_collections)):
    _collection_or_404(db, collection_id, allowed)
    return [document_out(db, d) for d in repositories.list_documents(db, collection_id, allowed)]


@router.post("/{collection_id}/documents", response_model=list[UploadOut], status_code=202)
def upload_documents(collection_id: str, files: list[UploadFile] = File(...),
                     db: Session = Depends(get_db),
                     allowed: list[str] = Depends(get_allowed_collections)):
    """Queue one ingest job per file and return at once (202). Follow progress
    with ``GET /jobs/{id}`` or ``GET /jobs/{id}/events``. All files are checked
    first; if any is rejected, nothing is stored."""
    _collection_or_404(db, collection_id, allowed)
    limit = get_settings().max_upload_mb * 1024 * 1024
    items = []
    for f in files:
        content = f.file.read(limit + 1)          # never read more than the limit allows
        try:
            service.validate_upload(f.filename or "", content)
        except service.UploadRejected as e:
            raise HTTPException(e.status_code, str(e))
        items.append((f.filename or "upload", content))
    results = [service.upload(db, collection_id, name, content) for name, content in items]
    db.commit()
    return [UploadOut(**r.__dict__) for r in results]
