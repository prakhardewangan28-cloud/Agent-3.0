# 🚀 Quick Start Guide

## Start the Server (3 steps)

```powershell
cd backend
.\run.ps1
```

That's it! Server will be running at **http://127.0.0.1:8000**

---

## Alternative Manual Start

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## Test the API

```powershell
# Activate environment
.\venv\Scripts\Activate.ps1

# Run test script
python test_server.py
```

---

## Access Points

| What | URL |
|------|-----|
| 🌐 API Server | http://127.0.0.1:8000 |
| 💚 Health Check | http://127.0.0.1:8000/health |
| 📚 Interactive Docs | http://127.0.0.1:8000/docs |
| 📖 Alternative Docs | http://127.0.0.1:8000/redoc |

---

## API Examples

### Health Check
```powershell
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
```

### Research Query
```powershell
$body = @{query = "What is AI?"; max_results = 10} | ConvertTo-Json
Invoke-WebRequest -Uri http://127.0.0.1:8000/api/v1/research -Method POST -Body $body -ContentType "application/json" -UseBasicParsing
```

---

## File Structure

```
backend/
├── run.ps1              ← Start here!
├── test_server.py       ← Test here!
├── .env                 ← Add your API keys
├── app/
│   ├── main.py          ← FastAPI app
│   ├── config.py        ← Configuration
│   ├── api/routes.py    ← Endpoints
│   ├── agents/          ← LangGraph agents (TODO)
│   ├── services/        ← Business logic (TODO)
│   ├── db/              ← Database
│   └── models/          ← Data schemas
└── migrations/          ← SQL scripts
```

---

## Next Steps

1. ✅ Server is running
2. ⚠️ Add your API keys to `.env`
3. ⚠️ Run database migrations in Supabase
4. ⚠️ Implement service layer logic
5. ⚠️ Build LangGraph workflow

---

## Need Help?

- 📄 Read `SETUP_GUIDE.md` for detailed instructions
- 📋 Check `VERIFICATION_REPORT.md` for what's working
- 📖 Read `README.md` for full documentation
- 🌐 Visit http://127.0.0.1:8000/docs for API reference

---

**Status**: ✅ Everything is working!
