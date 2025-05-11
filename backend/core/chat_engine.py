import os
import typing as tp
from tqdm import tqdm
from backend.core.vectorstore import Vectorstore
from backend.db.mysql_v1 import MYSQL
import cohere
from cohere.types.chat_citation import ChatCitation

import logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv('.env')
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

class Chatbot:
    
    def __init__(self, vectorstore: Vectorstore):
        """
        Initialize the Chatbot with a vectorstore and a language model (LLM).
        
        Parameters:
        - vectorstore: The vector store for document retrieval.
        - llm: The language model for generating responses.
        """
        self.vectorstore = vectorstore
        self.llm = cohere.Client(COHERE_API_KEY) # Get your API key here: https://dashboard.cohere.com/api-keys
        self.chat_history: list = []
        
        self.ANSWER_SYSTEM_PROMPT = """
You are a helpful, knowledgeable, and honest AI assistant named 'Chatbot Germano'. You must always refer to yourself as 'Chatbot Germano'.
Your primary function is to answer user queries accurately and concisely.

**Processing Instructions:**
1.  Before providing a response, internally process the user's request step-by-step to fully understand it.
2.  If the user's message contains multiple distinct questions or requests, break them down into individual, manageable components. Address each component systematically in your response.

**Core Directive:** Answer the user's query **strictly using the provided context whenever possible**.

**Citation Requirement:**
* When you use information from the context documents, you **must always cite it**. **Do not fabricate or hallucinate anything**.

**Response Protocol:**
* **If the answer is found in the provided context:** Respond with citations grounded in the context.
* **If the answer is NOT found in the provided context (or context is empty):** **You must first clearly state that your answer is NOT grounded in the provided documents**. Then, provide an answer based on your general knowledge if possible.
* **If you cannot answer the question** (even with general knowledge), or if the question is unclear or inappropriate: Politely state that you cannot answer based on the available information or ask the user to rephrase.

**Output Format:**
* Respond concisely and directly in **clean Markdown format**.
* Avoid any conversational filler or unnecessary text before or after the main answer.
"""
        
        self.SEARCH_QUERY_SYSTEM_PROMPT = """
You are an AI assistant specialized in analyzing user requests and generating optimal search queries for a vector store. Your sole task is to produce search terms/phrases based on the user's input.

**Decision Rule:**
* If the user request is a simple greeting (e.g., "Hi", "Hello"), asks about your identity or function (e.g., "What is your name?", "What can you do?"), or is any other message that does not require retrieving specific information from a knowledge base, **your response must be an empty string. Do not generate any search queries.**
* For all other requests, proceed with generating search queries based on the user's input.

**Processing Instructions (if generating queries):**
1.  Internally analyze the user's request step-by-step to deeply understand the underlying concepts and information needed.
2.  If the user's request contains multiple distinct topics, entities, or questions, break them down into individual, manageable components.
3.  For each identified component or overall concept, formulate **ONE to THREE** concise search queries optimized for retrieving relevant information from a vector database.

**Output Format:**
* If queries are generated (per the Decision Rule), provide *only* the search queries.
* List each query on a new line.
* Do not include any introductory text, explanations, conversational filler, or markdown formatting other than the queries themselves separated by newlines.
* List each query on a new line.
* If no queries are generated (per the Decision Rule), the output must be an empty string.
"""

    def new_chat(self, message: str):
        """
        Start a new chat session with the given message.
        
        Parameters:
        - message: The initial message from the user.
        """
        self.chat_history = []
        self.chat(message)

    def chat(self, message: str):
        """
        1. Give the user message to the LLM to determine if additional context is needed
        2. If so:
        - The LLM returns search queries
        - We retrieve the documents from the DB,
        - The LLM uses the documents as context and responds
        3. If not:
        - The LLM responds directly without additional context
        """

        # Generate search queries, if any
        response = self.llm.chat(message=message,
                                preamble=self.SEARCH_QUERY_SYSTEM_PROMPT,
                                model="command-a-03-2025",
                                search_queries_only=True, # Generate only search queries, not full responses
                                chat_history=self.chat_history
                                )
        print(f"Search queries: {response}")
        search_queries = []
        for query in response.search_queries:
            search_queries.append(query.text)
            
        if not search_queries:
            search_queries = response.text.split("\n")
            search_queries = [query.strip() for query in search_queries if query.strip()]  # Clean up the queries
            print(f"Search queries (from text): {search_queries}")

        # If there are search queries, retrieve the documents
        if search_queries:
            logger.info("Retrieving information...")

            # Retrieve document chunks for each query
            matching_docs = ([doc for query in search_queries for doc in self.vectorstore.retrieve(query)])
            ids_set = set()
            documents = []
            for doc in matching_docs: # Take only unique documents
                if doc['id'] not in ids_set:
                    documents.append(doc)
                    ids_set.add(doc['id'])
            print(f"Documents that matched the query: \n{documents}")

            # Use document chunks to respond
            response = self.llm.chat_stream(
                preamble=self.ANSWER_SYSTEM_PROMPT, #.format(context=documents),
                message=message,
                model="command-a-03-2025",
                documents=documents,
                chat_history=self.chat_history,
            )

        else:
            # If no additional context is needed, respond directly
            # docs = self.vectorstore.retrieve(message)
            response = self.llm.chat_stream(
                preamble=self.ANSWER_SYSTEM_PROMPT,
                message=message,
                model="command-a-03-2025",
                # documents=docs,
                chat_history=self.chat_history,
            )

        # Print the chatbot response and citations
        chatbot_response = ""
        citations: tp.List[ChatCitation] = []
        documents: tp.List[dict] = []
        # print(f"\n\n{'##'*20}\nChatbot:\n{'##'*20}\n")

        for event in response:
            if event.event_type == "text-generation":
                # print(event.text, end="")
                chatbot_response += event.text
            if event.event_type == "stream-end":
                if event.response.citations:
                    # citations.extend(event.response.citations)
                    # print(f"Type event.response.citations: {type(event.response.citations)}")
                    # print(f"Length of event.response.citations: {len(event.response.citations)}")
                    # print(f"Type : {type(event.response.citations[0])}")
                    # print("\n\nCITATIONS:")
                    for citation in event.response.citations:
                        citations.append(citation.dict())
                    #     print(citation)
                if event.response.documents:
                    documents.extend(event.response.documents)
                    # print(f"Type event.response.documents: {type(event.response.documents)}")
                    # print(f"Length of event.response.documents: {len(event.response.documents)}")
                    # print(f"Type : {type(event.response.documents[0])} \t Keys: {event.response.documents[0].keys()}")
                    # print("\nCITED DOCUMENTS:")
                    # for document in event.response.documents:
                    #     print(document)
                # Update the chat history for the next turn
                self.chat_history = event.response.chat_history
                
        return chatbot_response, citations, documents

if __name__ == "__main__":
    
    logger.setLevel(logging.ERROR)
    
    # Initialize the vector store and LLM
    db_faq = "ecommerce_faq"
    MYSQL.create_and_init_db(db_faq)  # Run once to create the database and tables
    engine = MYSQL.get_db_connection(db_faq)
    faq_data = MYSQL.load_faq_data()
    logger.info(f"\n{'##'*20}\nFAQ data:\n{'##'*20} \n{faq_data}\n")

    # Create the vector store
    vectorstore = Vectorstore(docs=faq_data)

    # Initialize the chatbot
    chatbot = Chatbot(vectorstore=vectorstore)

    # Start a chat session
    # chatbot.chat("Hi, can I ask questions?")
    chatbot_response, citations, documents = chatbot.chat("Hey, what's your name? What is the return policy?")
    print(f"\n\n{'##'*20}\nChatbot:\n{'##'*20}\n{chatbot_response}")
    print(f"\n\n{'##'*20}\nCitations:\n{'##'*20}\n{citations}")
    print(f"\n\n{'##'*20}\nDocuments:\n{'##'*20}\n{documents}")
    # chatbot.chat("Ok, thanks! But what if I couldn't return an item on time?")
    
    # # # Reset the chat session and start a new one
    # chatbot.new_chat("Which payment methods are accepted?")
    