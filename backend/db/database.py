# database.py
from html import escape
import os
import re
from sqlalchemy import create_engine, Column, String, Text, TIMESTAMP, Integer, ForeignKey, MetaData, Table
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
import datetime
import uuid

# from chatbot import Chatbot
# from vector_store import Vectorstore

# --- Configuration ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test2.db")
# Use connect_args for SQLite only to disable same-thread check needed for FastAPI background tasks/dependencies
engine_args = {"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, **engine_args)

# SessionLocal class: each instance is a database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy models (declarative approach)
Base = declarative_base()

# --- SQLAlchemy Models (Define Table Structure) ---

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("chat_sessions.id"), nullable=False, index=True)

    role = Column(String(9), nullable=False) # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now())
    ai_model = Column(String(10), nullable=True)
    link = Column(String(255), nullable=True)

class Citation(Base):
    __tablename__ = "citations"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    msg_id = Column(Integer, ForeignKey("messages.id"), nullable=False, index=True)
    # List of document IDs associated with this citation
    doc_ids = Column(Text, nullable=False) # Store as comma-separated String(255)
    start = Column(Integer, nullable=True) # Start index of the citation in the document text
    end = Column(Integer, nullable=True) # End index of the citation in the document text
    text = Column(Text, nullable=False)

# --- Database Initialization ---

def create_db_and_tables():
    """Creates database tables if they don't exist."""
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables checked/created successfully.")
    except Exception as e:
        print(f"Error creating database tables: {e}")

def get_db():
    """FastAPI dependency to get a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Initial Data Loading (Optional: For Citations) ---

# Sample documents from the original Streamlit code
sample_docs = [
    {'id': '0', 'text': 'Emperor penguins are the tallest.', 'title': 'Tall penguins'},
    {'id': '3', 'text': 'Yusuf is an AI student', 'title': 'AI student'},
    {'id': '4', 'text': 'Yusuf studies at La Sapienza University', 'title': 'AI student home University name'},
    {'id': '5', 'text': 'He is currently doing an Erasmus Programme in Trento University', 'title': 'AI student host University location'},
    {'id': '6', 'text': 'La Sapienza is a university located in Rome in the Lazio region of Italy. Trento university, instead, is located in Trento in Italy', 'title': 'Location of Home University and Host University'}
]
sample_text = "I'm doing well, thanks for asking."\
              "\nThe tallest living penguins are [citation:0]{Emperor penguins}."\
              "\nYusuf is an [citation:3]{AI student} who studies at [citation:4]{La Sapienza University}."\
              "\nHis host university, [citation:5]{Trento University}, is located in [citation:6]{Trento, Italy}."

def get_mock_llm_response(user_message):
    """Simulates an LLM response, sometimes includes a link."""

    # vectorstore = Vectorstore(docs=faq_data)
    # chatbot = Chatbot(vectorstore=vectorstore)
    
    if "penguin" in user_message.lower():
        return sample_docs[0]['text']
    elif "ai" in user_message.lower():
        return sample_docs[1]['text']
    elif "home" in user_message.lower() or "sapienza" in user_message.lower():
        return sample_docs[2]['text']
    elif "host" in user_message.lower() or "trento" in user_message.lower():
        return sample_docs[3]['text']
    elif "location" in user_message.lower():
        return sample_docs[4]['text']
    elif "sample" in user_message.lower():
        return sample_text 
    elif "help" in user_message.lower():
        return f"Write another of the words: [penguin, ai, home, host, sapienza, trento, location]"
    else:
        return ""
    
def extract_citations(text):
    """Extracts citations in the format [citation:id]{content} from text."""
    pattern = r'\[citation:([^\]]+)\]\{([^}]+)\}'
    matches = re.findall(pattern, text)
    citations = {citation_id: content for citation_id, content in matches}
    return citations

def format_text_with_citations(text, citations=None):
    """Replaces citation tags with HTML spans that can be clicked to trigger citation display."""
    def citation_replacement(match):
        citation_id = match.group(1)
        cited_text = match.group(2)
        unique_key = f"citation-{citation_id}-{uuid.uuid4().hex[:8]}"
        
        # Create a span with styling for the citation
        return f'''
                <span 
                class="citation" 
                id="{unique_key}" 
                data-key="{unique_key}"
                data-citation-id="{citation_id}" 
                style="background-color: #ADD8E6; color: black; padding: 2px 4px; border-radius: 3px; border-bottom: 2px dashed #007bff; cursor: pointer;"
                onclick="document.getElementById('trigger-button-{citation_id}').click();">
                {escape(cited_text)}[{citation_id}]
            </span>
            
            <script language="javascript">
            document.querySelector("span").style.color = "red";
            </script>
            '''
    
    # Replace all citation tags with styled spans
    pattern = r'\[citation:([^\]]+)\]\{([^}]+)\}'
    formatted_text = re.sub(pattern, citation_replacement, text)
    
    return formatted_text

def populate_initial_citations():
    """Adds sample citations to the DB if they don't exist."""
    if True: 
        return None
    db = SessionLocal()
    try:
        existing_ids = {c.id for c in db.query(Citation.id).all()}
        citations_to_add = []
        for doc in sample_docs:
            if doc['id'] not in existing_ids:
                citations_to_add.append(Citation(**doc))

        if citations_to_add:
            db.add_all(citations_to_add)
            db.commit()
            print(f"Added {len(citations_to_add)} initial citations.")
        else:
            print("Initial citations already exist.")
    except Exception as e:
        db.rollback()
        print(f"Error populating initial citations: {e}")
    finally:
        db.close()
