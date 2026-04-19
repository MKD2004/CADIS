# 🧠 CADIS: Context-Aware Document Intelligence System

![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![Node.js](https://img.shields.io/badge/Node.js-43853D?style=for-the-badge&logo=node.js&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python&logoColor=white)
![HuggingFace](https://img.shields.io/badge/HuggingFace-Transformers-orange?style=for-the-badge&logo=huggingface&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-FF69B4?style=for-the-badge)

---

## 🚀 Overview

CADIS is an enterprise-grade **Multimodal Retrieval-Augmented Generation (RAG)** platform and academic research tool. It combines:

- Extractive Question Answering  
- Zero-shot Entity Extraction  
- Abstractive Summarization  

Along with a **novel semantic ambiguity resolution system** for interpreting complex text.

The system is built as a **fully decoupled microservice architecture**:

- ⚡ React Dashboard  
- 🔗 Node.js API Gateway  
- 🧠 FastAPI ML Backend  

---

## 🛠️ Tech Stack

### 🎨 Frontend
- React & Vite  
- Tailwind CSS & Framer Motion  
- Axios & Lucide React  

### 🔗 Middleware
- Node.js & Express.js  

### 🧠 Backend
- Python & FastAPI  
- ChromaDB  
- Uvicorn  

### 🤖 Models
- sentence-transformers/all-MiniLM-L6-v2  
- urchade/gliner_base  
- deepset/roberta-base-squad2  
- sshleifer/distilbart-cnn-12-6  

---

## 🏗️ Architecture Pipeline

1. **Ingestion & Vectorization**  
2. **NER & Extraction**  
3. **Ambiguity Resolution**  
4. **Summarization**  
5. **RAG QA Engine**  

---

## ⚙️ Installation

### Prerequisites

- Node.js (v18+)  
- Python (3.9–3.12)  
- Git  

---

### Clone Repo

```bash
git clone https://github.com/MKD2004/CADIS.git
cd CADIS
```

---

## ⚡ Quick Start

Run **3 terminals simultaneously**.

---

### 🧠 Terminal 1 — Backend

```bash
cd ml-service

python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt

uvicorn main:app --reload --port 8000
```

---

### 🔗 Terminal 2 — Middleware

```bash
cd server

npm install

node server.js
```

---

### 🎨 Terminal 3 — Frontend

```bash
cd client

npm install

npm run dev
```

---

## 🌐 Access

- Frontend → http://localhost:5173  
- Backend → http://localhost:8000  

---

## 💡 Notes

- Run all 3 services together  
- Start backend first  
- Check ports if errors occur  

---

## 🚀 Future Work

- Multi-document reasoning  
- Streaming responses  
- Model fine-tuning  
- Docker + Kubernetes deployment  

---
