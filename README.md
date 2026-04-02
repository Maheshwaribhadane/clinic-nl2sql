# Clinic NL2SQL System

An AI-powered Natural Language to SQL chatbot built with Vanna AI 2.0 and FastAPI.

## Tech Stack
- Python 3.13
- Vanna AI 2.0
- FastAPI + Uvicorn
- SQLite (clinic.db)
- Google Gemini 2.5 Flash (LLM)

## Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/clinic-nl2sql.git
cd clinic-nl2sql
```

### 2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
Create a `.env` file:
```
GOOGLE_API_KEY=your_gemini_api_key_here
```
Get free key at: https://aistudio.google.com/apikey

### 5. Create database
```bash
python setup_database.py
```

### 6. Seed agent memory
```bash
python seed_memory.py
```

### 7. Start the server
```bash
uvicorn main:app --reload --port 8000
```

## API Documentation

### POST /chat
Ask a question in plain English.

**Request:**
```json
{"question": "How many patients do we have?"}
```

**Response:**
```json
{
  "message": "I can help with that...",
  "sql_query": "SELECT count(*) FROM patients",
  "columns": ["count(*)"],
  "rows": [[200]],
  "row_count": 1
}
```

### GET /health
```json
{"status": "ok", "database": "connected", "agent_memory_items": 15}
```

## Architecture
```
User Question → FastAPI → Vanna 2.0 Agent (Gemini LLM)
→ SQL Validation → SQLite Execution → Results
```

## LLM Provider
Google Gemini 2.5 Flash (free tier via Google AI Studio)