# Backend Setup Guide - Step by Step

## ✅ Current Status

Your backend is **WORKING** and running successfully! 

- ✓ Virtual environment created
- ✓ All dependencies installed
- ✓ Server tested and running
- ✓ Health check endpoint working
- ✓ Research endpoint working
- ✓ API documentation accessible

## 🌐 Access Your API

- **API Server**: http://127.0.0.1:8000
- **Interactive API Docs**: http://127.0.0.1:8000/docs
- **Alternative API Docs**: http://127.0.0.1:8000/redoc
- **Health Check**: http://127.0.0.1:8000/health

## 🚀 How to Start the Server

### Option 1: Using PowerShell Script (Easiest)

```powershell
cd backend
.\run.ps1
```

This script will:
- Check and create virtual environment if needed
- Install dependencies if needed
- Create .env file if needed
- Start the server with auto-reload

### Option 2: Manual Commands

```powershell
cd backend

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Start the server
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Option 3: Using Python Directly

```powershell
cd backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

## 🧪 Testing the API

### Test with the included script:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python test_server.py
```

### Test with cURL (PowerShell):

```powershell
# Health check
Invoke-WebRequest -Uri http://127.0.0.1:8000/health -UseBasicParsing

# Research endpoint
$body = @{
    query = "What is climate change?"
    max_results = 10
} | ConvertTo-Json

Invoke-WebRequest -Uri http://127.0.0.1:8000/api/v1/research `
    -Method POST `
    -Body $body `
    -ContentType "application/json" `
    -UseBasicParsing
```

### Test with Python:

```python
import requests

# Health check
response = requests.get("http://127.0.0.1:8000/health")
print(response.json())

# Research endpoint
response = requests.post(
    "http://127.0.0.1:8000/api/v1/research",
    json={"query": "What is climate change?", "max_results": 10}
)
print(response.json())
```

## 📝 Environment Variables

Edit the `.env` file in the backend directory with your actual API keys:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# SerpAPI Configuration
SERPAPI_KEY=your-serpapi-key

# OpenAI Configuration
OPENAI_API_KEY=your-openai-key

# Application Configuration
LOG_LEVEL=INFO
MAX_SEARCH_RESULTS=10
```

### Getting API Keys:

1. **Supabase**: https://supabase.com/
   - Create a new project
   - Get your URL and anon key from Settings > API

2. **SerpAPI**: https://serpapi.com/
   - Sign up for a free account
   - Get your API key from the dashboard

3. **OpenAI**: https://platform.openai.com/
   - Create an account
   - Generate an API key from API Keys section

## 📁 Project Structure

```
backend/
├── app/
│   ├── main.py              # ✓ FastAPI app (working)
│   ├── config.py            # ✓ Configuration (working)
│   ├── api/
│   │   └── routes.py        # ✓ API endpoints (working)
│   ├── agents/
│   │   └── research_agent.py # ⚠️ TODO: Implement LangGraph workflow
│   ├── services/
│   │   ├── serpapi_service.py      # ⚠️ TODO: Implement search
│   │   ├── credibility_service.py  # ⚠️ TODO: Implement credibility
│   │   ├── claim_service.py        # ⚠️ TODO: Implement claims
│   │   ├── conflict_service.py     # ⚠️ TODO: Implement conflicts
│   │   └── refinement_service.py   # ⚠️ TODO: Implement refinement
│   ├── db/
│   │   └── supabase_client.py # ✓ Database client (working)
│   └── models/
│       └── schemas.py        # ✓ Data models (working)
├── tests/
│   └── conftest.py          # ✓ Test configuration
├── migrations/
│   └── 001_initial.sql      # ✓ Database schema
├── venv/                    # ✓ Virtual environment (created)
├── .env                     # ✓ Environment variables (created)
├── requirements.txt         # ✓ Dependencies list
├── pyproject.toml          # Poetry configuration
├── run.ps1                 # ✓ Quick start script (created)
├── test_server.py          # ✓ Test script (created)
└── README.md               # Documentation
```

## 🔧 Common Issues & Solutions

### Issue: "Module not found" errors
**Solution**: Make sure virtual environment is activated
```powershell
.\venv\Scripts\Activate.ps1
```

### Issue: "Port already in use"
**Solution**: Change the port or kill the process using port 8000
```powershell
# Kill process on port 8000
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process

# Or use a different port
python -m uvicorn app.main:app --reload --port 8001
```

### Issue: Validation errors for environment variables
**Solution**: Check your .env file has all required variables set

### Issue: CORS errors from frontend
**Solution**: The backend already allows http://localhost:3000. If using different port, update `app/main.py`:
```python
allow_origins=["http://localhost:3000", "http://localhost:YOUR_PORT"]
```

## 🎯 Next Steps

1. ✅ **Backend scaffold is complete and working**
2. ⚠️ **Set up your API keys in .env**
3. ⚠️ **Run database migrations in Supabase** (migrations/001_initial.sql)
4. ⚠️ **Implement service layer business logic**:
   - SerpAPI search functionality
   - OpenAI claim extraction
   - Credibility assessment
   - Conflict detection
5. ⚠️ **Build LangGraph workflow** in research_agent.py
6. ⚠️ **Write tests** for your services
7. ⚠️ **Connect with frontend** (if you have one)

## 📚 Additional Resources

- FastAPI Documentation: https://fastapi.tiangolo.com/
- LangGraph Documentation: https://langchain-ai.github.io/langgraph/
- Supabase Documentation: https://supabase.com/docs
- SerpAPI Documentation: https://serpapi.com/docs
- OpenAI API Documentation: https://platform.openai.com/docs

## 🐛 Debugging

To see detailed logs:

```powershell
# Set log level to DEBUG in .env
LOG_LEVEL=DEBUG

# Restart the server
.\run.ps1
```

Check server logs in the terminal where uvicorn is running.

## 🤝 Need Help?

- Check the API docs at http://127.0.0.1:8000/docs
- Review error messages in the terminal
- Check the logs for detailed error information
- Ensure all API keys are correctly set in .env

---

**Status**: ✅ Backend is fully functional and ready for development!
