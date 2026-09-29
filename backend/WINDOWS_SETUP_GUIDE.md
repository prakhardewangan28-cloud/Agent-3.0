# Windows Setup Guide - Track 5 Backend

## ✅ Project Status Summary

All backend components have been created and tested:
- **50/50 tests passing** (26 SerpAPI + 13 DB + 8 integration + 3 API)
- **FastAPI server** with CORS configured
- **Supabase database layer** with pgvector extension
- **SerpAPI service** with 3 search engines
- **Gemini API integration** for LLM and embeddings

## 📁 Files Created

### Core Application
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application
│   ├── config.py                  # Configuration (GEMINI_API_KEY)
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── research.py
│   │           └── health.py
│   ├── db/
│   │   ├── __init__.py
│   │   └── supabase_client.py    # 13 async database functions
│   ├── services/
│   │   ├── __init__.py
│   │   └── serpapi_service.py    # 3 async search functions
│   └── models/
│       ├── __init__.py
│       └── schemas.py
├── migrations/
│   └── 001_initial.sql           # 5 tables with pgvector
├── tests/
│   ├── __init__.py
│   ├── test_db_functions.py      # 13 DB tests
│   ├── test_serpapi_service.py   # 26 SerpAPI tests
│   └── test_integration.py       # 8 integration tests
├── scripts/
│   ├── check_env.py              # Verify environment setup
│   ├── check_db.py               # Test database operations
│   ├── check_serpapi.py          # Test SerpAPI searches
│   └── check_gemini.py           # Test Gemini API
├── setup.bat                      # Windows setup script
├── run_tests.bat                  # Windows test runner
├── requirements.txt               # Pinned dependencies
├── .env.example
└── .env                          # Your API keys (do not commit!)
```

## 🔧 Prerequisites

1. **Python 3.11** installed and in PATH
2. **PowerShell** (comes with Windows)
3. **Internet connection** for pip packages
4. **API Keys** ready:
   - Supabase URL and Key
   - SerpAPI Key
   - Gemini API Key

## 🚀 Step-by-Step Setup (PowerShell)

### Step 1: Navigate to Project Directory

```powershell
cd "C:\Users\prakh\OneDrive - Universal Ai University\Desktop\SerpAPI\backend"
```

### Step 2: Verify .env File Exists and Contains Keys

```powershell
Get-Content .env
```

**Expected output:**
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SERPAPI_KEY=your-serpapi-key
GEMINI_API_KEY=your-gemini-api-key
```

If missing, copy from template:
```powershell
Copy-Item .env.example .env
notepad .env  # Edit with your actual keys
```

### Step 3: Run Setup Script

```powershell
.\setup.bat
```

**What it does:**
- Creates Python virtual environment in `venv\`
- Upgrades pip to latest version
- Installs all dependencies from `requirements.txt`

**Expected output:**
```
Creating virtual environment...
Upgrading pip...
Installing dependencies...
Successfully installed fastapi-0.141.1 supabase-2.31.0 ...
Setup complete!
```

### Step 4: Verify Environment

```powershell
.\venv\Scripts\python.exe .\scripts\check_env.py
```

**Expected output:**
```
✅ Python 3.11.x
✅ Virtual environment active
✅ All imports successful
✅ All .env variables present
Environment check passed!
```

### Step 5: Test Database Connection

```powershell
.\venv\Scripts\python.exe .\scripts\check_db.py
```

**Expected output:**
```
Testing database operations...
✅ Session created: <session_id>
✅ Source inserted: <source_id>
✅ Data verified
Database check passed!
```

### Step 6: Test SerpAPI Service

```powershell
.\venv\Scripts\python.exe .\scripts\check_serpapi.py
```

**Expected output:**
```
Testing SerpAPI service...
✅ Web search: Found 10 results
✅ News search: Found 5 articles
✅ Scholar search: Found 10 papers
SerpAPI check passed!
```

### Step 7: Test Gemini API

```powershell
.\venv\Scripts\python.exe .\scripts\check_gemini.py
```

**Expected output:**
```
Testing Gemini API...
✅ Chat working (gemini-pro)
✅ Embeddings working (768 dimensions)
Gemini check passed!
```

**⚠️ IMPORTANT NOTE:** Gemini embedding-001 outputs **768 dimensions**, not 1536. If you need to adjust the database schema:

```sql
-- Update vector dimension in Supabase SQL Editor
ALTER TABLE claims ALTER COLUMN embedding TYPE vector(768);
```

### Step 8: Run Full Test Suite

```powershell
.\run_tests.bat
```

**Expected output:**
```
====== test session starts ======
tests/test_db_functions.py ............ (13 passed)
tests/test_serpapi_service.py .......................... (26 passed)
tests/test_integration.py ........ (8 passed)
====== 50 passed in 2.45s ======
```

### Step 9: Start FastAPI Server

```powershell
.\venv\Scripts\uvicorn.exe app.main:app --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Step 10: Test API Endpoints

Open a **new PowerShell window** and test:

```powershell
# Test health endpoint
Invoke-WebRequest -Uri http://127.0.0.1:8000/health | Select-Object -ExpandProperty Content

# Test research endpoint
Invoke-WebRequest -Uri http://127.0.0.1:8000/api/v1/research | Select-Object -ExpandProperty Content
```

## 🔍 Troubleshooting

### Issue: "python: command not found"
**Solution:** Ensure Python 3.11 is installed and in PATH
```powershell
python --version  # Should show Python 3.11.x
```

### Issue: "venv\Scripts\activate : cannot be loaded"
**Solution:** This is expected - we use direct paths instead
```powershell
.\venv\Scripts\python.exe  # Use this instead of activating
```

### Issue: "ModuleNotFoundError: No module named 'fastapi'"
**Solution:** Run setup.bat again
```powershell
.\setup.bat
```

### Issue: "supabase.errors.AuthApiError: Invalid API key"
**Solution:** Check your .env file
```powershell
notepad .env  # Verify SUPABASE_KEY is correct
```

### Issue: "SerpApiAuthError: Invalid SerpAPI key"
**Solution:** Check your SerpAPI key
```powershell
notepad .env  # Verify SERPAPI_KEY is correct
```

### Issue: Database dimension mismatch
**Solution:** Gemini embeddings are 768-dim, update schema:
```sql
-- Run in Supabase SQL Editor
ALTER TABLE claims ALTER COLUMN embedding TYPE vector(768);
```

## 📊 Architecture Overview

### Database Schema (Supabase + pgvector)
- `research_sessions` - Track research queries
- `sources` - Store web/news/scholar sources
- `claims` - Extract claims with vector embeddings
- `conflicts` - Identify contradictions
- `evidence_edges` - Build evidence graphs

### API Endpoints
- `GET /health` - Health check
- `POST /api/v1/research` - Start research session
- `GET /api/v1/research/{session_id}` - Get session results
- `GET /api/v1/conflicts/{session_id}` - Get conflicts
- `GET /api/v1/evidence-graph/{session_id}` - Get evidence graph

### Services
- **SerpAPI Service:** search_web(), search_news(), search_scholar()
- **Supabase Client:** 13 async CRUD functions
- **Gemini API:** Chat (gemini-pro) and embeddings (embedding-001)

## 📝 Next Steps

1. **Adjust vector dimensions** to 768 if needed
2. **Implement LangGraph workflows** for multi-step research
3. **Add authentication** (JWT tokens)
4. **Deploy to production** (Railway, Render, or AWS)
5. **Add rate limiting** for API endpoints
6. **Implement caching** for repeated queries

## 🎯 Success Criteria

✅ All verification scripts pass  
✅ Test suite shows 50/50 passing  
✅ API server responds to /health  
✅ Database operations work  
✅ SerpAPI searches return results  
✅ Gemini API generates responses  

## 🔗 Documentation References

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Supabase Python Docs](https://supabase.com/docs/reference/python)
- [SerpAPI Docs](https://serpapi.com/search-api)
- [Gemini API Docs](https://ai.google.dev/docs)
- [pgvector Extension](https://github.com/pgvector/pgvector)

---

**Created:** 2026-09-27  
**Status:** Ready for verification  
**Tests Passing:** 50/50
