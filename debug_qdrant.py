import os
import cohere
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

load_dotenv()
co = cohere.Client(os.getenv("COHERE_API_KEY"))
client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))

text = "Ini adalah dokumen test"
res = co.embed(texts=[text], model='embed-multilingual-v3.0', input_type='search_document')

client.upsert(
    collection_name="job_embeddings",
    points=[
        PointStruct(id=999, vector=res.embeddings[0], payload={"text": text})
    ]
)
print("Count after upsert:", client.count(collection_name="job_embeddings").count)
