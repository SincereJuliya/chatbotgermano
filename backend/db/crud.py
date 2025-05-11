# crud.py
from sqlalchemy.orm import Session
from backend.db import models, database
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

# --- Chat Session CRUD ---

def create_chat_session(db: Session, session_create: models.ChatSessionCreate) -> database.ChatSession:
    """Creates a new chat session in the database."""
    session_id = str(uuid.uuid4())
    # Use provided title or generate a default one
    title = session_create.title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    db_session = database.ChatSession(id=session_id, title=title)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def get_chat_session(db: Session, session_id: str) -> Optional[database.ChatSession]:
    """Retrieves a single chat session by its ID."""
    return db.query(database.ChatSession).filter(database.ChatSession.id == session_id).first()

def get_chat_sessions(db: Session, skip: int = 0, limit: int = 100) -> List[database.ChatSession]:
    """Retrieves a list of chat sessions with pagination."""
    return db.query(database.ChatSession).order_by(database.ChatSession.created_at.desc()).offset(skip).limit(limit).all()

# --- Message CRUD ---

def create_message(db: Session, session_id: str, message: models.MessageCreate) -> database.Message:
    """Creates a new message within a specific chat session."""
    db_message = database.Message(
        session_id=session_id,
        role=message.role,
        content=message.content,
        ai_model=message.ai_model,
        link=message.link
        # timestamp is handled by server_default
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def get_messages_for_session(db: Session, session_id: str, skip: int = 0, limit: int = 1000) -> List[database.Message]:
    """Retrieves all messages for a given chat session, oldest first."""
    # Limit 1000 to avoid overwhelming requests, adjust as needed
    return db.query(database.Message)\
             .filter(database.Message.session_id == session_id)\
             .order_by(database.Message.timestamp.asc())\
             .offset(skip)\
             .limit(limit)\
             .all()

# --- Citation CRUD ---

def create_citations(db: Session, message_id: str, citations: List[Dict[str, Any]]) -> List[database.Citation]:
    """Creates new citations for a specific message."""
    citations_list = []
    returned_citation_list = []
    # Citations: [{'start': 0, 'end': 41, 'text': '', 'document_ids': ['4'], 'type': 'TEXT_CONTENT'}]
    for citation in citations:
        db_citation = database.Citation(
            # id=citation['id'],
            msg_id=message_id,
            doc_ids=",".join([idx for idx in citation['document_ids']]),
            text=citation['text'],
            start=citation['start'],
            end=citation['end']
        )
        citations_list.append(db_citation)
    db.add_all(citations_list)
    db.commit()
    db.refresh(db_citation)
    
    for citation in citations_list:
        citation.doc_ids = [idx for idx in citation.doc_ids.split(",")]
        returned_citation_list.append(citation)
    return returned_citation_list

def get_citation(db: Session, citation_id: str) -> Optional[database.Citation]:
    """Retrieves citation details by ID."""
    citation = db.query(database.Citation).filter(database.Citation.id == citation_id).first()
    citation.doc_ids = [idx for idx in citation.doc_ids.split(",")]
    return citation

def get_citations_by_msg_id(db: Session, msg_id: int) -> List[database.Citation]:
    """Retrieves all citations associated with a specific message ID."""
    temp_citations = db.query(database.Citation).filter(database.Citation.msg_id == msg_id).all()
    citations = []
    for citation in temp_citations:
        citation.doc_ids = [idx for idx in citation.doc_ids.split(",")]
        citations.append(citation)
    return citations

def get_citations(db: Session, skip: int = 0, limit: int = 100) -> List[database.Citation]:
    """Retrieves a list of all citations."""
    temp_citations = db.query(database.Citation).order_by(database.Citation.id).offset(skip).limit(limit).all()
    citations = []
    for citation in temp_citations:
        citation.doc_ids = [idx for idx in citation.doc_ids.split(",")]
        citations.append(citation)
    return citations

