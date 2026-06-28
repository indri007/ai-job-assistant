import os
import cohere
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()
co = cohere.Client(os.getenv("COHERE_API_KEY"))
client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))

query = "lowongan Marketing & Sales"
res = co.embed(texts=[query], model='embed-multilingual-v3.0', input_type='search_query')

results = client.search(
    collection_name="job_embeddings",
    query_vector=res.embeddings[0],
    limit=3
)

print("SEARCH RESULTS:")
for hit in results:
    print(hit.score, hit.payload.get("metadata", {}).get("company_name", "UNKNOWN"), hit.payload.get("pageContent", "NO_TEXT")[:50])
