# ✅ Sharing Checklist - Before Sending to Friend

## 🔒 SECURITY FIRST - Remove Private Keys

Before you share this project, follow this checklist:

### Step 1: Backup Your `.env` File
```bash
# Make a backup copy in a SAFE location (NOT in the project!)
# Windows:
Copy-Item .env C:\Users\YourName\Documents\backend_env_backup.txt

# Mac/Linux:
cp .env ~/Desktop/backend_env_backup.txt
```

### Step 2: Delete `.env` from Project
```bash
# Windows PowerShell:
Remove-Item .env

# Mac/Linux:
rm .env
```

✅ **Verify**: `.env` file should NOT exist in the backend folder

### Step 3: Check `.gitignore` Includes `.env`
Open `.gitignore` and verify this line exists:
```
.env
```

✅ **Verified**: `.env` is in `.gitignore`

### Step 4: Clean Up Other Private Files

Remove these if they exist:
- `venv/` folder (too large, friend will recreate)
- `__pycache__/` folders
- `.pytest_cache/` folder
- Any test database files

```bash
# Windows:
Remove-Item -Recurse -Force venv, __pycache__, .pytest_cache

# Mac/Linux:
rm -rf venv __pycache__ .pytest_cache
```

## ✅ Verify These Files EXIST

Make sure these are in the project:

- [x] `.env.example` - Template file
- [x] `README.md` - Project overview
- [x] `SETUP.md` - Setup instructions
- [x] `quick_setup.bat` - Windows setup script
- [x] `requirements.txt` - Dependencies
- [x] `.gitignore` - Git ignore rules
- [x] All Python code files (`app/`, `scripts/`, `tests/`)

## 📦 Choose Your Sharing Method

### Option A: GitHub (Recommended)

**Advantages:**
- ✅ Easy updates (just push/pull)
- ✅ Version control
- ✅ Can work on different parts simultaneously
- ✅ Free backup

**Steps:**
1. Make sure `.env` is deleted (Step 2 above)
2. Initialize git:
   ```bash
   git init
   git add .
   git commit -m "Initial commit - backend setup"
   ```
3. Create a GitHub repository (public or private)
4. Push code:
   ```bash
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```
5. Share the GitHub URL with your friend

**Your friend will:**
```bash
git clone <your-github-repo-url>
cd backend
quick_setup.bat  # Windows
# Then follow prompts to add their own API keys
```

### Option B: USB Drive / Cloud (OneDrive, Google Drive)

**Advantages:**
- ✅ Works offline
- ✅ No GitHub account needed
- ✅ Simple copy-paste

**Steps:**
1. Make sure `.env` is deleted (Step 2 above)
2. Make sure `venv/` is deleted (too large)
3. Zip the entire `backend` folder
4. Copy to USB or upload to cloud drive
5. Share with friend

**Your friend will:**
1. Extract the zip
2. Run `quick_setup.bat` (Windows) or follow SETUP.md
3. Add their own API keys to `.env`

## 🔑 What Your Friend Needs

Tell your friend they need to get these API keys:

1. **Supabase** 
   - Can use YOUR Supabase project (share the URL)
   - Or create their own project
   - URL: https://supabase.com/dashboard

2. **SerpAPI**
   - Must get their own key (free tier available)
   - URL: https://serpapi.com/

3. **Gemini AI**
   - Must get their own key (free tier available)
   - URL: https://aistudio.google.com/apikey

## 📋 Send This Message to Your Friend

```
Hey! I'm sending you our Track 5 hackathon backend project.

📁 Setup Instructions:
1. [Extract/Clone] the project
2. Run quick_setup.bat (Windows) or follow SETUP.md
3. Get your API keys:
   - Supabase: https://supabase.com/dashboard
   - SerpAPI: https://serpapi.com/manage-api-key
   - Gemini: https://aistudio.google.com/apikey
4. Add keys to .env file
5. Run verification: python scripts/check_env.py

Need help? Read SETUP.md or README.md

Let me know if you get stuck!
```

## 🔄 After Sharing - Restore Your Environment

After you share, restore your `.env` on your computer:

```bash
# Windows:
Copy-Item C:\Users\YourName\Documents\backend_env_backup.txt .env

# Mac/Linux:
cp ~/Desktop/backend_env_backup.txt .env
```

Then recreate your virtual environment:
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## 🎯 Final Checks

Before sending, verify:

- [ ] `.env` file deleted from project
- [ ] `venv/` folder deleted (optional but recommended)
- [ ] `.env.example` exists with template
- [ ] README.md and SETUP.md exist
- [ ] All code files are present
- [ ] No personal information in code comments

## ✅ You're Ready to Share!

Once all checks pass, you can safely share the project!

---

**Remember:** 
- Never commit `.env` to git
- Each person needs their own API keys
- Keep backups of your `.env` file somewhere safe (NOT in the project)
