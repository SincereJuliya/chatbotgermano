# routers/chat.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any, Dict, List

from backend.core.chat_engine import Chatbot
from backend.db import crud, models, database
from backend.db.mysql_v1 import MYSQL
from backend.core.vectorstore import Vectorstore

router = APIRouter(
    prefix="/sessions", # Base path for routes in this file
    tags=["Chat Sessions & Messages"], # Tag for Swagger UI documentation
)

# --- Chat Session Endpoints ---

@router.post("/", response_model=models.ChatSessionResponse, status_code=status.HTTP_201_CREATED)
def create_new_chat_session(
    session_create: models.ChatSessionCreate, db: Session = Depends(database.get_db)
):
    """
    Creates a new chat session.
    - Optionally accepts a `title` in the request body.
    - If no title is provided, a default title with timestamp is generated.
    - Returns the created chat session details including its unique ID.
    """
    return crud.create_chat_session(db=db, session_create=session_create)

@router.get("/", response_model=List[models.ChatSessionResponse])
def read_chat_sessions(
    skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)
):
    """
    Retrieves a list of all existing chat sessions, ordered by creation date (newest first).
    Supports pagination using `skip` and `limit` query parameters.
    """
    sessions = crud.get_chat_sessions(db, skip=skip, limit=limit)
    return sessions

@router.get("/{session_id}", response_model=models.ChatSessionResponse)
def read_chat_session(session_id: str, db: Session = Depends(database.get_db)):
    """
    Retrieves details for a specific chat session by its ID.
    Returns 404 Not Found if the session ID does not exist.
    """
    db_session = crud.get_chat_session(db, session_id=session_id)
    if db_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    return db_session

# --- Message Endpoints ---

#######################################
# Initialize the vector store and LLM
db_faq = "ecommerce_faq"
MYSQL.create_and_init_db(db_faq)  # Run once to create the database and tables
engine = MYSQL.get_db_connection(db_faq)
faq_data = MYSQL.load_faq_data()
# logger.info(f"\n{'##'*20}\nFAQ data:\n{'##'*20} \n{faq_data}\n")

# Create the vector store
vectorstore = Vectorstore(docs=faq_data)

# Initialize the chatbot
chatbot = Chatbot(vectorstore=vectorstore)
    
############################################

@router.post("/{session_id}/messages/", response_model=models.MessageResponse, status_code=status.HTTP_201_CREATED)
def create_new_message(
    session_id: str, message: models.MessageCreate, db: Session = Depends(database.get_db)
):
    """
    Adds a new message (user or assistant) to the specified chat session.
    - Requires `role` and `content` in the request body.
    - `ai_model` and `link` are optional.
    - Returns 404 Not Found if the `session_id` does not exist.
    - Returns the details of the created message.
    """
    # First, check if the session exists
    db_session = crud.get_chat_session(db, session_id=session_id)
    if db_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")

    # Validate role
    if message.role not in ["user", "assistant"]:
         raise HTTPException(
             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
             detail="Message role must be 'user' or 'assistant'"
         )

    # store user data and generate and store assistant data concurrently/simultaneously
    _ = crud.create_message(db=db, session_id=session_id, message=message)
    
    # assistant_response = database.get_mock_llm_response(message.content) 
    # citations = []
    # if not assistant_response:
    assistant_response, citations, _ = chatbot.chat(message.content)
    print(f"\ncreate_new_message -> Citations: {citations}\n")
    
    # print(f"\nCitations: {citations}\n")
    
    assistant_message = models.MessageCreate(
        role="assistant",
        content=assistant_response,
        ai_model="Gemma 3",
    )
    assistant_data = crud.create_message(db=db, session_id=session_id, message=assistant_message)
    if citations:
        citations = crud.create_citations(db=db, message_id=assistant_data.id, citations=citations)
        # print(f"Type Citation -> ID {type(citations[-1].id)}, doc IDs: {citations[-1].doc_ids}")
        
    response_msg = models.MessageResponse(
        id=assistant_data.id,
        session_id=session_id,
        role=assistant_data.role,
        content=assistant_data.content,
        ai_model=assistant_data.ai_model,
        link=assistant_data.link,
        timestamp=assistant_data.timestamp,
        citations=citations,
    )
    return response_msg

@router.get("/{session_id}/messages/", response_model=List[models.MessageResponse])
def read_messages_for_session(
    session_id: str, skip: int = 0, limit: int = 1000, db: Session = Depends(database.get_db)
):
    """
    Retrieves all messages associated with a specific chat session, ordered by timestamp (oldest first).
    - Returns 404 Not Found if the `session_id` does not exist.
    - Supports pagination (`skip`, `limit`), defaulting to retrieve up to 1000 messages.
    """
    # Check if session exists (optional, but good practice)
    db_session = crud.get_chat_session(db, session_id=session_id)
    if db_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")

    messages = crud.get_messages_for_session(db, session_id=session_id, skip=skip, limit=limit)
    
    response_msgs = []
    for message in messages:
        # Get citations for each message
        db_citations = crud.get_citations_by_msg_id(db, msg_id=message.id)
        response_msg = models.MessageResponse(
            id=message.id,
            session_id=session_id,
            role=message.role,
            content=message.content,
            ai_model=message.ai_model,
            link=message.link,
            timestamp=message.timestamp,
            citations=db_citations,  # Include citations in the response
        )
        response_msgs.append(response_msg)
    return response_msgs

# Get list of documents by their ids
@router.post("/documents/", response_model=List[Dict[str, Any]], status_code=status.HTTP_200_OK)
def get_docs(request: models.DocIdsRequest) -> List[Dict[str, Any]]:
    """
    Retrieves a list of documents by their IDs.
    - Accepts a list of document IDs as query parameters.
    - Returns the documents in JSON format.
    """    
    doc_ids = request.doc_ids
    if not doc_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No document IDs provided")
    # print(f"get_docs -> doc_ids: {doc_ids}")
    
    # docs = [faq_data[idx] for idx in doc_ids] # same as vectorstore.docs[idx]
    docs = [doc for doc in faq_data if str(doc['id']) in doc_ids]
    # print(f"get_docs -> docs: {docs}")
    return docs



