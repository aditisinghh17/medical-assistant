# 🏥 Medical Assistant App

A full-stack AI-powered medical assistant web application that helps users get health-related support and suggestions. Built with **FastAPI** (backend) and **React** (frontend), powered by **Groq API** for fast, low-latency inference using meta-llama/llama-4-scout-17b-16e-instruct.

---

## 📦 Features

- 🧠 AI-driven medical insight system via Groq API
- 🔒 Secure communication between frontend and backend
- ⚡ Real-time suggestions
- 📱 Responsive UI

---

## 🧰 Tech Stack

| Layer     | Tech Used                    |
|-----------|------------------------------|
| Frontend  | React, JavaScript            |
| Backend   | FastAPI, Uvicorn             |
| AI Model  | Groq API (meta-llama/llama-4-scout-17b-16e-instruct)     |
| Styling   | CSS / Tailwind / Chakra UI (as applicable) |

---

## 🚀 Getting Started

### ✅ Prerequisites

- Python 3.8+
- Node.js & npm

---
# How to use 
### 🧠 Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

cd frontend
npm install
npm run dev
 

