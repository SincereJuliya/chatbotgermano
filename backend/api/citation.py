# routers/citation.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.db import crud, models, database

router = APIRouter(
    prefix="/citations",
    tags=["Citations"],
)

@router.get("/", response_model=List[models.CitationResponse])
def read_all_citations(
    skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)
):
    """
    Retrieves a list of all available citations (documents).
    Supports pagination using `skip` and `limit`.
    """
    citations = crud.get_citations(db, skip=skip, limit=limit)
    return citations

@router.get("/{citation_id}", response_model=models.CitationResponse)
def read_citation_details(citation_id: str, db: Session = Depends(database.get_db)):
    """
    Retrieves the details (title, text) for a specific citation ID.
    Returns 404 Not Found if the citation ID does not exist in the database.
    """
    db_citation = crud.get_citation(db, citation_id=citation_id)
    if db_citation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Citation not found")
    return db_citation

