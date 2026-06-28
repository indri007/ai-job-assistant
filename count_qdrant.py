import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()
client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)
count = client.count(collection_name="job_embeddings")
print("Total points:", count.count)
