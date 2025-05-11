import os
# import uuid
import typing as tp
#from unstructured.partition.html import partition_html
#from unstructured.chunking.title import chunk_by_title
from sqlalchemy import create_engine, text
import sqlparse
import mysql
from mysql.connector import errorcode # Or handle pymysql errors

from tqdm import tqdm

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv('.env')

PASSWORD = os.getenv("MYSQL_PASSWORD")
USER = os.getenv("MYSQL_USER")
HOST = os.getenv("MYSQL_HOST")
PORT = os.getenv("MYSQL_PORT")
WORKING_DIR = os.getcwd()

class MYSQL:
    
    @staticmethod
    def get_db_connection(database_name: str = "ecommerce_faq"):
        """Create a connection to the MySQL database using SQLAlchemy."""
        
        db_url = f"mysql+mysqlconnector://{USER}:{PASSWORD}@{HOST}:{PORT}/{database_name}"
        engine = create_engine(db_url)
        logger.info(f"Connected successfully to database:\n {database_name}: {engine}")
        return engine
    
    @staticmethod
    def create_and_init_db(database_name: str = "ecommerce_faq"):
        """Create a (new) database and initialize it."""
        
        if database_name == "ecommerce_faq":
            sql_file_path = os.path.join(WORKING_DIR, "ecommerce-faq-database_mysql.sql")
        elif database_name == "ecommerce_ticketing":
            sql_file_path = os.path.join(WORKING_DIR, "ecommerce-ticket-database-sql_mysql.sql")
        else:
            raise ValueError(f"Unknown database name: {database_name}. Use 'ecommerce_faq' or 'ecommerce_ticketing'.")
        
        logger.info(f"Reading SQL file: {sql_file_path}")
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
            
        # Use sqlparse to split into individual sql statements
        statements = sqlparse.split(sql_script)
        logger.info(f"Executing {len(statements)} SQL statements...")
        executed_count = 0
        
        # Connect to the server instance *without* specifying the database initially
        server_url = f"mysql+mysqlconnector://{USER}:{PASSWORD}@{HOST}:{PORT}/"
        engine = create_engine(server_url)
        
        with engine.connect() as connection:
            # Drop databse if exixts
            connection.execute(text(f"DROP DATABASE IF EXISTS {database_name}"))
            # connection.execute(text(f"CREATE DATABASE IF NOT EXISTS {database_name}"))
            # connection.execute(text(f"USE {database_name}"))
            
            for statement in tqdm(statements, desc="Executing SQL statements"):
                # Clean up the statement (remove whitespace, trailing semicolons)
                clean_statement = sqlparse.format(statement, strip_comments=True).strip()
                if not clean_statement: # Skip empty statements
                    continue
                try:
                    connection.execute(text(clean_statement))
                    executed_count += 1
                except (mysql.connector.Error, Exception) as cmd_err:
                    logger.error(f"\n{'--'*20}Executing statement: {clean_statement} \nError: {cmd_err}\n{'--'*20}", exc_info=True)
                    raise cmd_err # Stop on first error

            connection.commit() # Commit only if all statements execute successfully
            logger.info(f"Successfully executed {executed_count} SQL statements.")
    
    @staticmethod
    def load_faq_data():
        """Load Ecommerce FAQ data from the MySQL database
        
        Returns:
            List[Dict[str, str]]: A list of dictionaries containing FAQ data.
        Each dictionary contains the question and answer.
        """
        
        engine = MYSQL.get_db_connection("ecommerce_faq")
        query = "SELECT category_id, question, answer FROM faq_items"
        
        with engine.connect() as connection:
            result = connection.execute(text(query))
            rows = result.fetchall()
        
        documents = []
        for i, row in tqdm(enumerate(rows), desc="Loading FAQ data", total=len(rows)):
            documents.append({
                "title": "Ecommerce FAQ",
                "text": f"Question: {row[1]}\nAnswer: {row[2]}",
                "category_id": row[0],
                "id": i 
                })
            
        logger.info(f"Loaded {len(documents)} Ecommerce FAQ documents")
            
        return documents
        
    def load_ticketing_data():
        """Load Ecommerce Ticketing data from the MySQL database
        
        Returns:
            List[Dict[str, str]]: A list of dictionaries containing ticketing data.
        Each dictionary contains the ticket ID, customer query, and resolution.
        """
        
        engine = MYSQL.get_db_connection("ecommerce_ticketing")
        query = "SELECT ticket_id, customer_query, resolution FROM tickets WHERE status = 'resolved'"
        
        with engine.connect() as connection:
            result = connection.execute(text(query))
            rows = result.fetchall()
        
        documents = []
        for i, row in tqdm(enumerate(rows), desc="Loading Ticketing data", total=len(rows)):
            documents.append({
                "title": "Ecommerce Ticketing",
                "text": f"Query: {row[1]}\nResolution: {row[2]}",
                "ticket_id": row[0],
                "id": i
                })
            
        logger.info(f"Loaded {len(documents)} Ecommerce Ticketing documents")
        
        return documents
    
    @staticmethod
    def record_interaction(session_id, user_message, bot_response):
        engine = MYSQL.get_db_connection("ecommerce_ticketing")
        
        # Insert conversation into a tracking table for future model improvement
        query = text("""
        INSERT INTO conversation_history (session_id, user_message, bot_response, timestamp)
        VALUES (:session_id, :user_message, :bot_response, GETDATE())
        """)
        
        with engine.connect() as connection:
            connection.execute(query, {
                "session_id": session_id,
                "user_message": user_message,
                "bot_response": bot_response
            })
            connection.commit()
            
        logger.info(f"Recorded interaction for session {session_id}")


if __name__ == "__main__":
    # logger.setLevel(logging.DEBUG)
    
    # FAQ data
    db_faq = "ecommerce_faq"
    MYSQL.create_and_init_db(db_faq) # Run once to create the database and tables
    engine = MYSQL.get_db_connection(db_faq)
    faq_data = MYSQL.load_faq_data()
    logger.info(f"\n{'##'*20}\nFAQ data:\n{'##'*20} \n{faq_data}\n")
    
    # Ticketing data
    # db_ticketing = "ecommerce_ticketing"
    # MYSQL.create_and_init_db(db_ticketing) # Run once to create the database and tables
    # engine = MYSQL.get_db_connection(db_ticketing)
    # ticketing_data = MYSQL.load_ticketing_data()
    # logger.info(f"\n{'##'*20}\nTicketing data:\n{'##'*20} \n{ticketing_data}")