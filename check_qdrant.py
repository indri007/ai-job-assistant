import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()
client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)

try:
    res = client.scroll(collection_name="job_embeddings", limit=1)
    if res[0]:
        print("PAYLOAD IN QDRANT:")
        print(res[0][0].payload)
    else:
        print("No documents found in Qdrant.")
except Exception as e:
    print("Error:", e)
