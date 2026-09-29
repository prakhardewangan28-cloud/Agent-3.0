# 🎯 Track 5 Hackathon Backend

A FastAPI-based backend for the Track 5 hackathon featuring:
- 🔍 **SerpAPI Integration** - Google, Bing, Yahoo search
- 🤖 **Gemini AI** - Text generation and embeddings  
- 💾 **Supabase** - PostgreSQL with pgvector for semantic search
- ⚡ **FastAPI** - High-performance async API

## 🚀 Quick Start

### First Time Setup

**Windows:**
```bash
# Run the automatic setup script
quick_setup.bat
```

**Mac/Linux:**
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
```

See **[SETUP.md](SETUP.md)** for detailed setup instructions.

## 🔑 Required API Keys

You need to obtain these API keys:

1. **Supabase** - [Get here](https://supabase.com/dashboard)
2. **SerpAPI** - [Get here](https://serpapi.com/manage-api-key)
3. **Gemini AI** - [Get here](https://aistudio.google.com/apikey)

Add them to your `.env` file (copy from `.env.example`).

## ✅ Verify Setup

```bash
# Activate virtual environment first
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Run verification tests
python scripts/check_env.py       # Check environment variables
python scripts/check_gemini.py    # Test Gemini AI
python scripts/check_db.py        # Test Supabase
python scripts/check_serpapi.py   # Test SerpAPI
```

All should show ✅ PASSED.

## 🏃 Run the Server

```bash
# Make sure venv is activated
uvicorn app.main:app --reload --port 8000
```

API will be at: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🧪 Run Tests

```bash
pytest                          # Run all tests
pytest --cov=app tests/         # With coverage
pytest tests/test_serpapi.py -v # Specific test
```

## 📁 Project Structure

```
backend/
├── app/
│   ├── api/          # API endpoints (routes)
│   ├── db/           # Database operations
│   ├── services/     # External services (Gemini, SerpAPI)
│   ├── models/       # Pydantic models
│   └── main.py       # FastAPI application
├── migrations/       # Database migrations
├── scripts/          # Utility scripts
├── tests/            # Test files
├── .env.example      # Environment template
├── requirements.txt  # Dependencies
└── SETUP.md          # Detailed setup guide
```

## 🤝 Sharing This Project

### With GitHub (Recommended)

**Setup once:**
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-repo-url>
git push -u origin main
```

**Your friend clones:**
```bash
git clone <your-repo-url>
cd backend
quick_setup.bat  # Windows, or follow SETUP.md
```

### With USB/Cloud Drive

1. Copy the entire `backend` folder
2. **Delete your `.env` file first** (keep keys private!)
3. Share the folder
4. Friend runs `quick_setup.bat` or follows SETUP.md

## 🔒 Security

### ⚠️ NEVER commit these files:
- `.env` - Your private API keys
- `venv/` - Virtual environment
- `__pycache__/` - Cache files

✅ These are already in `.gitignore`

### ✅ Safe to share:
- `.env.example` - Template (no real keys)
- All `.py` files
- `requirements.txt`
- Documentation

## 📚 API Endpoints

### Search
- `POST /api/search/google` - Google search
- `POST /api/search/bing` - Bing search
- `POST /api/search/yahoo` - Yahoo search

### AI
- `POST /api/ai/generate` - Generate text with Gemini
- `POST /api/ai/embed` - Generate embeddings

### Database
- `POST /api/queries` - Store search query
- `GET /api/queries` - Get all queries
- `GET /api/queries/{id}` - Get specific query
- `POST /api/results` - Store search result
- `POST /api/search/semantic` - Semantic search

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| Module not found | Activate venv and run `pip install -r requirements.txt` |
| Invalid API key | Check `.env` file, regenerate keys if needed |
| Database connection failed | Verify Supabase credentials |
| Port already in use | Change port: `uvicorn app.main:app --port 8001` |

See [SETUP.md](SETUP.md) for more troubleshooting tips.

## 🛠️ Tech Stack

- **FastAPI** - Modern Python web framework
- **Supabase** - PostgreSQL with pgvector extension
- **Google Gemini** - AI text generation & embeddings
- **SerpAPI** - Multi-engine search API
- **Pydantic** - Data validation
- **pytest** - Testing framework

## 📊 Current Status

✅ **Working:**
- FastAPI application structure
- SerpAPI integration (all 3 engines)
- Database layer with pgvector
- Test suite (50+ tests)

⚠️ **Needs Configuration:**
- Valid API keys in `.env`
- Database migrations run
- Environment verification

## 📞 Getting Help

1. Check error messages in terminal
2. Run verification scripts (`scripts/check_*.py`)
3. Read [SETUP.md](SETUP.md)
4. Check API documentation at `/docs`

## 📝 License

[Your License Here]

## 👥 Contributors

- Your Name
- Your Friend's Name

---

**Ready to start?** Run `quick_setup.bat` (Windows) or follow [SETUP.md](SETUP.md)!
