import os, sys
import json
import cohere
# import uuid
import hnswlib
from typing import List, Dict
#from unstructured.partition.html import partition_html
#from unstructured.chunking.title import chunk_by_title
from tqdm import tqdm

import logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv('.env')

COHERE_API_KEY = os.getenv("COHERE_API_KEY")
co = cohere.Client(COHERE_API_KEY) # Get your API key here: https://dashboard.cohere.com/api-keys

class Vectorstore:
    """The Vectorstore class handles the ingestion of documents into embeddings (or vectors)
    and the retrieval of relevant documents given a query.
    """
    def __init__(self, docs: List[Dict[str, str]]):
        self.docs = docs
        self.docs_embs = [] # embeddings of the chunked documents
        self.retrieve_top_k = 10
        self.rerank_top_k = 3
        self.embed()
        self.index()

    def embed(self) -> None:
        """
        Embeds the document chunks using the Cohere API.

        With the Embed v3 model, we need to define an input_type, of which there are four options depending
        on the type of task. Using these input types ensures the highest possible quality for the respective tasks.
        Since our document chunks will be used for retrieval, we use search_document as the input_type
        """
        
        # Since the endpoint has a limit of 96 documents per call, we send them in batches.
        batch_size = 90
        self.docs_len = len(self.docs)
        for i in tqdm( range(0, self.docs_len, batch_size), desc="Embedding documents"):
            batch = self.docs[i : min(i + batch_size, self.docs_len)]
            texts = [item["text"] for item in batch]
            docs_embs_batch = co.embed(
                texts=texts, model="embed-english-v3.0", input_type="search_document"
            ).embeddings
            self.docs_embs.extend(docs_embs_batch)
            
        logger.info(f"Embedded {len(self.docs_embs)} documents successfully.")

    def index(self) -> None:
        """
        Indexes the documents for efficient retrieval.

        For production environments, typically a vector database (like Weaviate or MongoDB) is
        required to handle the continuous process of indexing documents and maintaining the index.

        Here, however, we’ll keep it simple and use a vector library instead.
        We can choose from many open-source projects, such as Faiss, Annoy, ScaNN,
        or Hnswlib, which is the one we’ll use.
        These libraries store embeddings in in-memory indexes and implement
        approximate nearest neighbor (ANN) algorithms to make similarity search efficient.
        """
        logger.info("Indexing documents...")

        # ip = inner product for the similarity metric to be used
        self.idx = hnswlib.Index(space="ip", dim=1024)

        # ef_construction=512: Controls the quality and speed of index construction.
        # Higher values lead to better recall at the cost of slower indexing.
        # M=64: Determines the number of bi-directional links created for each element in the HNSW graph.
        # Larger values increase accuracy but also increase memory usage.
        self.idx.init_index(max_elements=self.docs_len, ef_construction=512, M=64)
        
        # Add the embeddings to the index with their corresponding IDs from (0 to len(docs_embs))
        self.idx.add_items(self.docs_embs, list(range(len(self.docs_embs))))

        logger.info(f"Indexing complete with {self.idx.get_current_count()} documents.")

    def retrieve(self, query: str) -> List[Dict[str, str]]:
        """Retrieves document chunks based on the given query using Semantic Search.
        It has 2 steps: Dense retrieval and Reranking.

        While our dense retrieval component is already highly capable of retrieving relevant sources,
        Cohere Rerank provides an additional boost to the quality of the search results,
        especially for complex and domain-specific queries. It takes the search results and
        sorts them according to their relevance to the query.

        Parameters:
        query (str): The query to retrieve document chunks for.

        Returns:
        List[Dict[str, str]]: A list of dictionaries representing the retrieved document chunks, with 'title', 'text', and 'url' keys.
        """

        # Dense retrieval with input_type=”search_query” for queries
        query_emb = co.embed(
            texts=[query], model="embed-english-v3.0", input_type="search_query"
        ).embeddings

        doc_ids = self.idx.knn_query(query_emb, k=self.retrieve_top_k)[0][0]
        logger.info(f"Retrieved document IDs: {doc_ids}")

        # Reranking for additional boost in relevance
        rank_fields = ["title", "text"] # We'll use the title and text fields for reranking

        docs_to_rerank = [self.docs[doc_id] for doc_id in doc_ids]

        rerank_results = co.rerank(
            query=query,
            documents=docs_to_rerank,
            top_n=self.rerank_top_k,
            model="rerank-english-v3.0",
            rank_fields=rank_fields
        )

        doc_ids_reranked = [doc_ids[result.index] for result in rerank_results.results]
        logger.info(f"Rerank results: {rerank_results.results}")

        docs_retrieved = []
        for i, doc_id in enumerate(doc_ids_reranked):
            docs_retrieved.append(
                {
                    "title": self.docs[doc_id]["title"],
                    "text": self.docs[doc_id]["text"],
                    "id": str(doc_id),
                    "relevance_score": str(rerank_results.results[i].relevance_score),
                }
            )

        return docs_retrieved



if __name__ == "__main__":
    
    from mysql_v1 import MYSQL
    
    docs = MYSQL.load_faq_data()
    vectorstore = Vectorstore(docs=docs)
    answer = vectorstore.retrieve("What is the return policy?")
    print(answer)
    print(f"\ndocs[0]: {docs[0]}")
    
    

    