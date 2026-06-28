import os
import json
import pandas as pd
import mysql.connector
import cohere
import time
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Load environment variables
load_dotenv()

# Konfigurasi
DATASET_PATH = 'dataset/jobs.jsonl'
QDRANT_COLLECTION = "job_embeddings"

def init_mysql():
    """Inisialisasi koneksi ke Aiven MySQL"""
    try:
        print("Menghubungkan ke MySQL...")
        conn = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),
            port=os.getenv("MYSQL_PORT"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE")
        )
        print("Berhasil terhubung ke MySQL!")
        return conn
    except Exception as e:
        print(f"Error koneksi MySQL: {e}")
        return None

def init_qdrant():
    """Inisialisasi koneksi ke Qdrant Cloud"""
    try:
        print("Menghubungkan ke Qdrant Cloud...")
        client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
            timeout=60
        )
        print("Berhasil terhubung ke Qdrant!")
        return client
    except Exception as e:
        print(f"Error koneksi Qdrant: {e}")
        return None

def process_and_ingest_data(mysql_conn, qdrant_client):
    if not os.path.exists(DATASET_PATH):
        print(f"File {DATASET_PATH} tidak ditemukan.")
        return

    print("Membaca dataset JSONL...")
    df = pd.read_json(DATASET_PATH, lines=True)
    
    # Batasi jumlah data untuk uji coba (100 data)
    df = df.head(100)
    print(f"Memproses {len(df)} data pertama dari dataset...")

    # 1. Ingestion ke Qdrant (dengan Cohere Embeddings)
    print("Inisialisasi Cohere Client...")
    co = cohere.Client(os.getenv("COHERE_API_KEY"))
    
    # Reset collection lama yang menggunakan FastEmbed
    print("Menghapus collection lama dan membuat ulang untuk vektor Cohere...")
    qdrant_client.recreate_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
    )
    
    print("Mempersiapkan data dan menghasilkan embeddings menggunakan Cohere API...")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=0,
        separators=["\n\n", "\n", " ", ""]
    )
    
    docs = []
    metadata = []
    ids = []
    
    current_id = 1
    for index, row in df.iterrows():
        combined_text = f"Title: {row.get('job_title', '')}. Company: {row.get('company_name', '')}. Description: {row.get('job_description', '')}"
        
        chunks = text_splitter.split_text(combined_text)
        for chunk in chunks:
            docs.append(chunk)
            metadata.append({
                "pageContent": chunk,  # Wajib sama persis case-nya untuk N8N
                "metadata": {
                    "job_title": str(row.get('job_title', '')),
                    "company_name": str(row.get('company_name', '')),
                    "location": str(row.get('location', '')),
                    "work_type": str(row.get('work_type', ''))
                }
            })
            ids.append(current_id)
            current_id += 1

    # Batch embedding (Cohere limits 96 docs per batch for optimal performance, but can handle more)
    # We will do it in chunks of 50 to be safe with rate limits on trial keys
    batch_size = 50
    points = []
    
    for i in range(0, len(docs), batch_size):
        batch_docs = docs[i:i+batch_size]
        batch_meta = metadata[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        
        print(f"Mengubah batch {i+1} ke {i+len(batch_docs)} menjadi vektor...")
        response = co.embed(
            texts=batch_docs,
            model='embed-multilingual-v3.0',
            input_type='search_document'
        )
        embeddings = response.embeddings
        
        for j in range(len(embeddings)):
            points.append(
                PointStruct(
                    id=batch_ids[j],
                    vector=embeddings[j],
                    payload=batch_meta[j]
                )
            )
        time.sleep(1) # Delay untuk mencegah rate limit

    print(f"Mengirim {len(points)} vektor ke Qdrant Cloud dalam beberapa bagian...")
    chunk_size = 25
    for i in range(0, len(points), chunk_size):
        chunk = points[i:i+chunk_size]
        qdrant_client.upsert(
            collection_name=QDRANT_COLLECTION,
            points=chunk
        )
        time.sleep(0.5)
    
    print("Berhasil menyimpan embeddings Cohere ke Qdrant!")

if __name__ == "__main__":
    print("=== Memulai proses Ingestion Data (Cohere Version) ===")
    
    mysql_conn = init_mysql() # MySQL tidak diulang insert karena datanya sudah ada
    qdrant_client = init_qdrant()
    
    if mysql_conn and qdrant_client:
        process_and_ingest_data(mysql_conn, qdrant_client)
        mysql_conn.close()
        
    print("=== Proses selesai ===")
