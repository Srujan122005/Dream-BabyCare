# ✅ Supabase Migration Checklist

## Phase 1: Create Supabase Project (5 min)
- [ ] Go to https://supabase.com
- [ ] Sign up or login
- [ ] Click "New Project"
- [ ] Fill in:
  - [ ] Project name: "Dream Baby Care"
  - [ ] Create strong database password
  - [ ] Select closest region
- [ ] Wait for project to initialize (2-3 min)

## Phase 2: Create Database Tables (5 min)
- [ ] Go to Supabase dashboard
- [ ] Click "SQL Editor" (left sidebar)
- [ ] Click "New Query"
- [ ] Open file: `schema.sql` (in your project)
- [ ] Copy ALL the SQL code
- [ ] Paste into Supabase SQL Editor
- [ ] Click "Run"
- [ ] Verify all tables created (no errors)

## Phase 3: Get Your Credentials (2 min)
- [ ] Go to Settings → API (left sidebar)
- [ ] Copy "Project URL"
  - [ ] Format: `https://xxxxx.supabase.co`
  - [ ] Save it somewhere safe
- [ ] Copy "Anon Key" (under Project API keys)
  - [ ] Format: `eyJ...` (long string)
  - [ ] Save it somewhere safe

## Phase 4: Local Testing Setup (5 min)
- [ ] Create file `.env` in your project root
- [ ] Add these lines:
  ```
  SUPABASE_URL=your_project_url_here
  SUPABASE_KEY=your_anon_key_here
  ```
- [ ] Replace with YOUR actual values
- [ ] Save the file

## Phase 5: Install Dependencies (2 min)
```bash
pip install -r requirements.txt
```
- [ ] Command runs without errors
- [ ] Packages installed: supabase, python-dotenv

## Phase 6: Test Locally (5 min)
```bash
python app_supabase.py
```
- [ ] App starts without errors
- [ ] Visit http://localhost:5000
- [ ] See "Dream Baby Care" landing page
- [ ] Can click through to register
- [ ] Database not throwing errors (check terminal)

## Phase 7: Verify Database Connection (3 min)
- [ ] Register a test user locally
  - [ ] Email: `test@example.com`
  - [ ] Password: `testpass123`
  - [ ] Complete registration
- [ ] Go to Supabase dashboard
- [ ] Click "Table Editor"
- [ ] Click "users" table
- [ ] Look for your test user row
- [ ] If you see it: ✅ Connection works!

## Phase 8: Prepare for Deployment (2 min)
- [ ] Check `vercel.json` exists
- [ ] Check it has:
  ```
  "buildCommand": "pip install -r requirements.txt"
  ```
- [ ] Check main file setting is correct

## Phase 9: Vercel Deployment (5 min)
- [ ] Go to https://vercel.com
- [ ] Go to your project
- [ ] Click "Settings" → "Environment Variables"
- [ ] Add two variables:
  1. [ ] Key: `SUPABASE_URL` | Value: Your URL
  2. [ ] Key: `SUPABASE_KEY` | Value: Your key
- [ ] Click "Save"
- [ ] Go to "Deployments"
- [ ] Click "Redeploy" on latest deployment
- [ ] Wait for deployment to complete (2-3 min)

## Phase 10: Verify Production (5 min)
- [ ] Go to your Vercel deployment URL
- [ ] You should see landing page
- [ ] Try to register new user
- [ ] Check Supabase dashboard
- [ ] Look in "users" table
- [ ] Should see your new user
- [ ] If yes: ✅ Everything works!

---

## 🎯 Total Time
**~40 minutes** with everything working

---

## ❌ If Something Goes Wrong

### Symptom: "ModuleNotFoundError: No module named 'supabase'"
**Solution:**
```bash
pip install supabase python-dotenv
```

### Symptom: "SUPABASE_URL and SUPABASE_KEY environment variables are required"
**Solution:**
1. Check `.env` file exists locally
2. Check file has correct format:
   ```
   SUPABASE_URL=https://xxxxx.supabase.co
   SUPABASE_KEY=eyJ...
   ```
3. Restart the app: `python app_supabase.py`
4. For Vercel: Check Settings → Environment Variables

### Symptom: Can register locally but not on Vercel
**Solution:**
1. Check Vercel environment variables are set
2. Redeploy the project
3. Check Supabase project is active (not paused)

### Symptom: Tables not found error
**Solution:**
1. Go to Supabase → SQL Editor
2. Run `schema.sql` again
3. Verify all 9 tables exist in Table Editor

### Symptom: User data not appearing in Supabase
**Solution:**
1. Check table columns match code
2. Verify user registration completed
3. Check Supabase error logs: Settings → Logs

---

## 📞 Helpful Links

- Supabase: https://supabase.com
- Vercel: https://vercel.com
- Documentation: See SUPABASE_SETUP.md

---

## 🎉 Success Indicators

When complete, you should have:
- ✅ Supabase project created
- ✅ All 9 tables in database
- ✅ Local app working
- ✅ Test user in Supabase
- ✅ Vercel app deployed
- ✅ Production app working
- ✅ Data persisting between deployments

---

**Print this page and check off as you go!** 📋
