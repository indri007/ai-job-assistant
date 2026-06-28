import os
import cohere
from dotenv import load_dotenv

load_dotenv()
co = cohere.Client(os.getenv("COHERE_API_KEY"))

texts = ["Hello world", "Test string"]
response = co.embed(
    texts=texts,
    model='embed-multilingual-v3.0',
    input_type='search_document'
)

print("Type of embeddings:", type(response.embeddings))
print("Length of embeddings:", len(response.embeddings))
