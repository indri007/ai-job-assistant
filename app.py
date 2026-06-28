import streamlit as st
import requests
import os
import PyPDF2
import pdfplumber
import docx
import pytesseract
from pdf2image import convert_from_bytes
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Konfigurasi N8N Webhook (Pastikan path-nya sesuai dengan yang ada di n8n)
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/job-assistant")

st.set_page_config(page_title="AI Job Assistant", page_icon="💼", layout="wide")

# Styling (Glassmorphism & Modern UI)
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        color: #fafafa;
    }
    .stChatFloatingInputContainer {
        padding-bottom: 20px;
    }
    .css-1d391kg {
        background-color: #1e1e2e;
        border-radius: 10px;
        padding: 20px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("💼 AI Job Assistant (Indonesia)")
st.markdown("Asisten cerdas berbasis **N8N Multi-Agent** untuk mencari pekerjaan, konsultasi karir, dan rekomendasi CV.")

# Inisialisasi Session State untuk Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

def extract_text_from_pdf(pdf_file):
    text = ""
    try:
        # Coba baca teks digital dengan pdfplumber terlebih dahulu
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                    
        # Jika teks kosong, kemungkinan ini PDF hasil scan. Lakukan OCR!
        if not text.strip():
            pdf_file.seek(0)
            images = convert_from_bytes(pdf_file.read())
            for img in images:
                text += pytesseract.image_to_string(img) + "\n"
                
        return text
    except Exception as e:
        st.error(f"Gagal membaca PDF: {e}")
        return ""

def extract_text_from_docx(docx_file):
    try:
        doc = docx.Document(docx_file)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        st.error(f"Gagal membaca DOCX: {e}")
        return ""

def send_to_n8n(query, mode, cv_text=""):
    payload = {
        "query": query,
        "mode": mode,
        "cv_text": cv_text
    }
    try:
        # Menambahkan timeout agar tidak hanging
        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=60)
        response.raise_for_status()
        
        # N8N Agent (Langchain) biasanya mengembalikan response dalam struktur tertentu
        result = response.json()
        
        # Mengecek format output N8N (biasanya di properti 'output' atau 'text')
        if isinstance(result, list) and len(result) > 0:
            return result[0].get("output", result[0].get("text", str(result[0])))
        elif isinstance(result, dict):
            return result.get("output", result.get("text", str(result)))
        else:
            return str(result)
            
    except requests.exceptions.ConnectionError:
        return "❌ Error: Tidak dapat terhubung ke N8N. Pastikan N8N sedang berjalan dan URL Webhook sudah benar."
    except Exception as e:
        return f"❌ Error dari N8N: {str(e)}"

# Sidebar untuk Advanced Features
with st.sidebar:
    st.header("✨ Fitur Lanjutan")
    
    st.subheader("📄 Rekomendasi dari CV")
    st.markdown("Unggah CV Anda untuk mendapatkan rekomendasi lowongan yang paling cocok dari database kami.")
    uploaded_file = st.file_uploader("Unggah CV (PDF, DOCX)", type=["pdf", "doc", "docx"])
    
    if uploaded_file is not None:
        st.success("CV siap dianalisis!")
        if st.button("Analisis & Cari Pekerjaan"):
            with st.spinner("Membaca CV dan menghubungi N8N..."):
                cv_text = ""
                if uploaded_file.name.lower().endswith(".pdf"):
                    cv_text = extract_text_from_pdf(uploaded_file)
                else:
                    cv_text = extract_text_from_docx(uploaded_file)
                    
                if cv_text:
                    prompt = "Tolong analisis CV saya ini dan carikan lowongan pekerjaan yang paling cocok dari database Anda."
                    
                    # Tambahkan ke UI
                    st.session_state.messages.append({"role": "user", "content": "*(Mengunggah CV untuk dianalisis)*\n\n" + prompt})
                    
                    # Kirim ke N8N dengan instruksi qdrant_tool
                    strict_prompt = f"""Gunakan tool Qdrant (qdrant_tool) untuk mencari data terkait ini: '{prompt}'.

ATURAN WAJIB:
1. WAJIB sebutkan nama perusahaan HANYA jika ada di hasil pencarian Qdrant.
2. JANGAN MENGARANG nama perusahaan (seperti PT Indofood, Unilever, dll) jika tidak ada di database.
3. JANGAN gunakan web search atau pengetahuan umum untuk mengisi informasi yang tidak ditemukan.
4. Jika hasil pencarian Qdrant kosong atau tidak relevan dengan pertanyaan, jawab dengan jujur: "Maaf, saya tidak menemukan data lowongan yang sesuai di database kami saat ini."
5. Jangan menambahkan asumsi, perkiraan, atau informasi di luar hasil tool Qdrant.

Pertanyaan pengguna: {prompt}"""
                    
                    answer = send_to_n8n(strict_prompt, "Rekomendasi CV", cv_text)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    st.rerun()
            
    st.divider()
    st.subheader("🎯 Mode Percakapan")
    chat_mode = st.radio("Pilih Mode Agen AI:", [
        "Pencarian Umum (Chat)", 
        "Konsultasi Karir", 
        "Simulasi Wawancara"
    ])

# Tampilkan chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input Chat Utama
if prompt := st.chat_input("Contoh: Cari lowongan Data Analyst di Jakarta..."):
    # Tampilkan pesan user di UI
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Kirim ke N8N Webhook
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("*(Agen N8N sedang berpikir...)*")
        
        # Kirim ke N8N Webhook dengan instruksi paksaan agar tidak halusinasi
        strict_prompt = f"""Gunakan tool Qdrant (qdrant_tool) untuk mencari data terkait ini: '{prompt}'.

ATURAN WAJIB:
1. WAJIB sebutkan nama perusahaan HANYA jika ada di hasil pencarian Qdrant.
2. JANGAN MENGARANG nama perusahaan (seperti PT Indofood, Unilever, dll) jika tidak ada di database.
3. JANGAN gunakan web search atau pengetahuan umum untuk mengisi informasi yang tidak ditemukan.
4. Jika hasil pencarian Qdrant kosong atau tidak relevan dengan pertanyaan, jawab dengan jujur: "Maaf, saya tidak menemukan data lowongan yang sesuai di database kami saat ini."
5. Jangan menambahkan asumsi, perkiraan, atau informasi di luar hasil tool Qdrant.

Pertanyaan pengguna: {prompt}"""
        
        # Panggil fungsi Webhook N8N
        answer = send_to_n8n(strict_prompt, chat_mode)
        
        # Tampilkan balasan sesungguhnya
        message_placeholder.markdown(answer)

    # Simpan balasan ke history
    st.session_state.messages.append({"role": "assistant", "content": answer})
