# 🚀 Track 5 Hackathon Backend - Setup Guide

This guide will help you set up the backend on any computer (yours or your friend's laptop).

## 📋 Prerequisites

- Python 3.11 or higher
- Git (optional, for sharing via GitHub)

## 🔧 Setup Steps

### Step 1: Clone/Copy the Project

**Option A: Via GitHub (Recommended)**
```bash
git clone <your-repo-url>
cd backend
```

**Option B: Via USB/Cloud Drive**
- Copy the entire `backend` folder to the new computer
- Open terminal in the `backend` folder

### Step 2: Create Virtual Environment

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

1. **Copy the template:**
   ```bash
   # Windows PowerShell
   Copy-Item .env.example .env
   
   # Mac/Linux
   cp .env.example .env
   ```

2. **Edit `.env` file** and add your actual API keys:

   ```env
   # Supabase Configuration
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_KEY=your_actual_supabase_anon_key
   
   # SerpAPI Configuration
   SERPAPI_KEY=your_actual_serpapi_key
   
   # Gemini Configuration
   GEMINI_API_KEY=your_actual_gemini_key
   ```

### Step 5: Get Your API Keys

#### 🔑 Supabase API Key
1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project (or create a new one)
3. Go to **Settings** → **API**
4. Copy **URL** and **anon public** key
5. Paste into `.env`

#### 🔑 SerpAPI Key
1. Go to [SerpAPI](https://serpapi.com/)
2. Sign up or log in
3. Go to **Dashboard** → **API Key**
4. Copy your API key
5. Paste into `.env`

#### 🔑 Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Click **Create API Key**
3. Copy the key (starts with `AQ.`)
4. Paste into `.env`

### Step 6: Verify Setup

Run the verification scripts to test all connections:

```bash
# Test environment variables
python scripts/check_env.py

# Test Gemini API
python scripts/check_gemini.py

# Test Supabase database
python scripts/check_db.py

# Test SerpAPI
python scripts/check_serpapi.py
```

All tests should show ✅ PASSED.

### Step 7: Initialize Database (First Time Only)

```bash
# Run database migrations
python scripts/run_migrations.py
```

## 🎯 Running the Server

```bash
# Start the development server
uvicorn app.main:app --reload --port 8000
```

The API will be available at: `http://localhost:8000`

## 📖 API Documentation

Once the server is running:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🧪 Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_serpapi.py -v
```

## 🔒 Security Notes

### ⚠️ IMPORTANT: Never Commit These Files to Git

- `.env` - Contains your private API keys
- `venv/` - Virtual environment (too large)
- `__pycache__/` - Python cache files

These are already in `.gitignore`, but double-check before pushing to GitHub!

### ✅ Safe to Commit

- `.env.example` - Template with no real keys
- All Python code files
- `requirements.txt`
- Documentation files
- Test files

## 🤝 Sharing with Friends

### Method 1: GitHub (Best for Multiple Collaborators)

**On your computer:**
```bash
# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit"

# Push to GitHub
git remote add origin <your-github-repo-url>
git push -u origin main
```

**On your friend's laptop:**
```bash
git clone <your-github-repo-url>
cd backend
# Follow Step 2-7 above
```

### Method 2: USB/Cloud Drive (Quick Share)

1. Copy entire `backend` folder
2. **Make sure to delete `.env` before copying** (keep your keys private!)
3. Give folder to friend
4. Friend follows Step 2-7 above with their own API keys

## 🐛 Troubleshooting

### Problem: "Module not found"
**Solution:** Make sure virtual environment is activated and dependencies are installed:
```bash
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Problem: "Invalid API key" errors
**Solution:** 
- Check `.env` file has correct keys
- No extra spaces or quotes around keys
- Keys are complete (not truncated)

### Problem: "Database connection failed"
**Solution:**
- Verify Supabase URL and key are correct
- Check internet connection
- Make sure Supabase project is active

### Problem: Tests fail
**Solution:**
- Run verification scripts one by one
- Check which API is failing
- Regenerate that API key

## 📦 Project Structure

```
backend/
├── app/
│   ├── api/              # API endpoints
│   ├── db/               # Database layer
│   ├── services/         # External services (Gemini, SerpAPI)
│   ├── models/           # Data models
│   ├── config.py         # Configuration
│   └── main.py           # FastAPI app
├── migrations/           # Database migrations
├── scripts/              # Utility scripts
├── tests/                # Test files
├── .env.example          # Environment template
├── .gitignore            # Git ignore rules
├── requirements.txt      # Python dependencies
└── SETUP.md             # This file
```

## 📞 Need Help?

If you get stuck:
1. Check error messages in terminal
2. Run verification scripts to isolate the problem
3. Make sure all API keys are valid
4. Check that virtual environment is activated

## 🎉 You're Ready!

Once all verification scripts pass ✅, your backend is fully configured and ready for development!
