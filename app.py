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
        
        
        # Mengecek format output N8N (biasanya di properti 'output' atau 'text')
        if response.status_code == 200:
            result = response.json()
            # Debug log to terminal
            print("RAW N8N RESPONSE:", result)
            
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("output", result[0].get("text", str(result[0])))
            elif isinstance(result, dict):
                return result.get("output", result.get("text", str(result)))
            else:
                return str(result)
        else:
            return f"Error: Gagal terhubung ke N8N Webhook (Status Code: {response.status_code})"
            
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
                    # Tambahkan ke UI
                    prompt = "Tolong analisis CV saya ini dan carikan lowongan pekerjaan yang paling cocok dari database Anda."
                    st.session_state.messages.append({"role": "user", "content": "*(Mengunggah CV untuk dianalisis)*\n\n" + prompt})
                    
                    full_query = f"""Tolong analisis CV saya ini dan temukan lowongan pekerjaan yang paling cocok dari database Anda.

ATURAN WAJIB (SANGAT KETAT):
1. PENTING: ANDA DILARANG KERAS menjawab berdasarkan pengetahuan Anda sendiri. Anda WAJIB memanggil Tool Qdrant untuk mencari kecocokan CV ini dengan database lowongan kerja.
2. CARA MENGGUNAKAN TOOL: Saat memanggil Tool Qdrant, JANGAN memasukkan kata seperti 'Internship', 'Bogor', atau lokasi. Cukup masukkan DAFTAR SKILL TEKNIS saja sebagai kata kunci pencarian (contoh: 'JavaScript, HTML, CSS, PHP, MySQL').
3. PENTING: JIKA Tool Qdrant mengembalikan data lowongan (sekalipun lokasinya atau jabatannya tidak sama persis dengan CV pengguna), Anda WAJIB menyajikannya kepada pengguna sebagai "Rekomendasi Berdasarkan Skill"! JANGAN membuang/menolak data tersebut hanya karena perbedaan lokasi atau tingkat jabatan.
4. Anda WAJIB memberikan rekomendasi spesifik yang mencantumkan nama perusahaan dan jabatan secara lengkap.
5. HANYA JIKA Tool benar-benar merespons dengan hasil kosong, jawab persis seperti ini: "Maaf, belum ada lowongan yang cocok dengan CV Anda di database."
6. PENTING: Untuk menghemat token, Anda HANYA BOLEH memanggil Tool Qdrant SATU KALI SAJA. 
7. PENTING: Di baris PALING BAWAH dari jawaban Anda, tambahkan teks persis seperti ini: "*(Sumber: Agent RAG)*".

Isi CV Saya:
{cv_text[:2000]}"""
                    
                    answer = send_to_n8n(full_query, "Rekomendasi CV", cv_text)
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
        
        # Sesuaikan prompt berdasarkan mode yang dipilih
        if chat_mode == "Konsultasi Karir":
            strict_prompt = f"""Tolong berikan konsultasi karir terkait pertanyaan ini: '{prompt}'.
Anda adalah seorang konsultan karir profesional. Berikan saran terkait pengembangan karir, perbaikan CV, tren industri, atau transisi karir.
Gunakan pengetahuan umum Anda, dan jika relevan, cari data lowongan menggunakan Tool Qdrant.
PENTING: Di baris PALING BAWAH dari jawaban Anda, tambahkan teks persis seperti ini: "*(Sumber: Agent Utama)*".
Pertanyaan pengguna: {prompt}"""
        elif chat_mode == "Simulasi Wawancara":
            strict_prompt = f"""Tolong lakukan simulasi wawancara untuk pertanyaan ini: '{prompt}'.
Anda adalah seorang HRD atau User Interviewer yang tegas namun suportif. Tugas Anda adalah mewawancarai pengguna.
Ajukan 1 pertanyaan wawancara saja dan tunggu jawaban dari pengguna. Jika pengguna menjawab, evaluasi jawabannya secara singkat, lalu berikan 1 pertanyaan berikutnya.
Gunakan pengetahuan umum Anda.
PENTING: Di baris PALING BAWAH dari jawaban Anda, tambahkan teks persis seperti ini: "*(Sumber: Agent Utama)*".
Pertanyaan/jawaban pengguna: {prompt}"""
        else:
            # Mode Pencarian Umum (Chat)
            strict_prompt = f"""Tolong carikan data terkait ini: '{prompt}'.

ATURAN WAJIB:
1. PENTING: ANDA DILARANG KERAS menjawab berdasarkan pengetahuan Anda sendiri. Anda WAJIB memanggil salah satu Tool (Qdrant atau MySQL) untuk mencari data.
2. Jika pertanyaan HANYA meminta hitungan angka (contoh: "ada berapa total lowongan", "berapa rata-rata gaji") atau filter gaji eksak, Anda WAJIB menggunakan tool SQL/Database.
3. Jika pengguna mencari lowongan berdasarkan NAMA PEKERJAAN (contoh: "cari lowongan sales", "lowongan data analyst"), KEAHLIAN (skill), LOKASI, atau KUALIFIKASI, Anda WAJIB menggunakan tool Qdrant.
4. WAJIB menampilkan DAFTAR/LIST (bullet points) NAMA PEKERJAAN beserta NAMA PERUSAHAAN, LOKASI, dan GAJI (jika ada).
5. JIKA tool mengembalikan hasil kosong, JANGAN MENGARANG. Jawab jujur bahwa tidak ada data di database.
6. JANGAN MENGARANG nama perusahaan atau gaji jika tidak ada di database.
7. INFO SCHEMA DATABASE: Nama tabel di database MySQL adalah `jobs`. Kolom: `job_title`, `company_name`, `location`, `work_type`, `salary` (berupa TEKS, misal 'Rp 10.000.000 per month' atau 'None'), `job_description`.
8. PENTING: Karena `salary` adalah TEKS, JANGAN gunakan operator matematika (`>`, `<`, `=`) untuk filter gaji. Jika diminta "gaji di atas 5 juta", cukup ambil semua data yang `salary != 'None'` lalu Anda filter sendiri secara manual saat menyusun jawaban akhir.
9. JAWABAN AKHIR ANDA WAJIB DALAM BENTUK TEKS BIASA (BUKAN FORMAT JSON).
10. PENTING: Di baris PALING BAWAH dari jawaban Anda, tambahkan teks persis seperti ini: "*(Sumber: Agent SQL)*" jika Anda memakai SQL, atau "*(Sumber: Agent RAG)*" jika Anda memakai Qdrant.

Pertanyaan pengguna: {prompt}"""
        
        # Panggil fungsi Webhook N8N
        answer = send_to_n8n(strict_prompt, chat_mode, "")
        
        # Tampilkan balasan sesungguhnya
        message_placeholder.markdown(answer)

    # Simpan balasan ke history
    st.session_state.messages.append({"role": "assistant", "content": answer})
