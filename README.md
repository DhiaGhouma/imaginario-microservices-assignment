# Fullstack Developer Internship Assignment

This folder contains a **working monolith application** for the fullstack developer internship position at Imaginario.

## Contents

- **`ASSIGNMENT.md`** - Main assignment instructions (break monolith into microservices + create dashboard)
- **`starter-backend/`** - Working Flask backend (monolith)
- **`starter-frontend/`** - Working Next.js frontend
- **`test_monolith.sh`** - Test script to verify the monolith works

## Quick Start

### 1. Test the Monolith (Verify It Works)

**Backend:**
```bash
cd starter-backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Backend runs on `http://localhost:5000`

**Frontend:**
```bash
cd starter-frontend
npm install
# Create .env.local:
echo "NEXT_PUBLIC_API_URL=http://localhost:5000" > .env.local
npm run dev
```

Frontend runs on `http://localhost:3000`

**Test the Backend:**
```bash
# In another terminal (with jq installed for JSON formatting)
./test_monolith.sh
```

### 2. Read the Assignment

Read `ASSIGNMENT.md` for complete instructions on:
- Breaking the monolith into microservices
- Creating a developer dashboard
- Submission requirements

## What's Working

### Backend (`starter-backend/`)
- ✅ User authentication (register, login)
- ✅ JWT token generation
- ✅ API key management (create, list, delete)
- ✅ Video CRUD operations
- ✅ Search functionality (text-based search in titles/descriptions)
- ✅ All endpoints functional

### Frontend (`starter-frontend/`)
- ✅ Login/Register pages
- ✅ Video library dashboard
- ✅ Create/Edit/Delete videos
- ✅ Search functionality
- ✅ API key management
- ✅ Redux state management
- ✅ All features working

## Your Task

1. **Break down the monolith**:
   - Extract search into Search Microservice
   - Convert backend to API Gateway
   - Maintain same API interface

2. **Create Developer Dashboard**:
   - Build a dashboard for API users (developers using API keys)
   - Track API usage statistics and analytics
   - Monitor search jobs in real-time
   - View usage per API key
   - Professional developer-focused UI

See `ASSIGNMENT.md` for detailed requirements.

## Project Structure

```
internship/
├── ASSIGNMENT.md              # Main assignment instructions
├── starter-backend/           # Working Flask monolith
│   ├── app.py                # Main application
│   ├── requirements.txt      # Dependencies
│   └── README.md             # Setup instructions
├── starter-frontend/          # Working Next.js frontend
│   ├── pages/                # Next.js pages
│   ├── lib/                  # API client, Redux slices
│   ├── package.json          # Dependencies
│   └── README.md             # Setup instructions
└── test_monolith.sh          # Test script
```

## Notes

- The monolith is **fully functional** - all features work
- Your task is to **refactor** it into microservices
- Maintain **backward compatibility** (same API interface)
- Create a **developer dashboard** for API users to:
  - Track their API usage and analytics
  - Monitor their search jobs
  - View usage per API key
  - Get insights into their API consumption

Good luck! 🚀
