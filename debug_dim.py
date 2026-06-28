import os
import cohere
from dotenv import load_dotenv

load_dotenv()
co = cohere.Client(os.getenv("COHERE_API_KEY"))

text = "Ini adalah dokumen test"
res = co.embed(texts=[text], model='embed-multilingual-v3.0', input_type='search_document')

print("Dimension:", len(res.embeddings[0]))
