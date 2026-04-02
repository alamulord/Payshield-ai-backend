# PayShield AI — Deployment Guide

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Local Development Setup](#local-development-setup)  
3. [Backend Deployment (Render / Railway)](#backend-deployment)
4. [Frontend Deployment (Vercel)](#frontend-deployment)
5. [Docker Deployment](#docker-deployment)
6. [Production PostgreSQL Migration](#production-postgresql-migration)
7. [Environment Variables Reference](#environment-variables-reference)
8. [API Endpoints Reference](#api-endpoints-reference)
9. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────────┐     ┌────────────┐
│   React/Vite    │────▶│   FastAPI Backend     │────▶│  SQLite /  │
│   Frontend      │     │   (Port 8000)         │     │ PostgreSQL │
│   (Port 5173)   │◀────│                       │     └────────────┘
│                 │     │  ┌─────────────────┐  │
│  - Overview     │  WS │  │ Scoring Engine  │  │
│  - Transactions │◀───▶│  │ Alert Service   │  │
│  - Alerts       │     │  │ Analytics       │  │
│  - Analytics    │     │  │ WebSocket Mgr   │  │
│  - Models       │     │  └─────────────────┘  │
│  - Investigations│    └──────────────────────┘
└─────────────────┘
```

### Tech Stack
- **Frontend**: React 18 + Vite + TypeScript + TailwindCSS
- **Backend**: Python 3.11+ / FastAPI / SQLAlchemy (async)
- **Database**: SQLite (dev) → PostgreSQL (production)
- **Auth**: JWT with RBAC (analyst/admin roles)
- **Real-time**: WebSocket for live alerts/transactions

---

## Local Development Setup

### Prerequisites
- Python 3.11+ (`python --version`)
- Node.js 18+ (`node --version`)
- Git

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd paysheild-architect
```

### 2. Backend Setup
```bash
# Navigate to backend
cd backend/payshield-backend

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the backend (auto-seeds database on first run)
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

> **Note**: On first startup, the database will be automatically created and seeded with 200 transactions, 50 alerts, 15 investigations, 5 ML models, and 6 rules.

**Default Login Credentials:**
| Role    | Email                  | Password    |
|---------|------------------------|-------------|
| Admin   | admin@payshield.ai     | admin123    |
| Analyst | analyst@payshield.ai   | analyst123  |

### 3. Frontend Setup
```bash
# In a new terminal
cd payshield-frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

### 4. Access the Application
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc
- **WebSocket**: ws://localhost:8000/ws

---

## Backend Deployment

### Option A: Render (Recommended — Free Tier)

1. **Push backend to GitHub**
```bash
cd backend/payshield-backend
git init
git add .
git commit -m "PayShield backend"
git remote add origin https://github.com/<user>/payshield-backend.git
git push -u origin main
```

2. **Create Render Web Service**
   - Go to [render.com](https://render.com) → New → Web Service
   - Connect your GitHub repository
   - Configure:
     - **Name**: `payshield-api`
     - **Runtime**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
     - **Instance Type**: Free

3. **Set Environment Variables** (in Render dashboard):
```
DATABASE_URL=sqlite+aiosqlite:///./payshield.db
JWT_SECRET=<generate-a-strong-secret>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440
CORS_ORIGINS=https://your-frontend.vercel.app,http://localhost:5173
DEBUG=false
```

4. **For PostgreSQL on Render** (recommended for production):
   - Create a Render PostgreSQL database
   - Use the Internal Database URL:
```
DATABASE_URL=postgresql+asyncpg://<user>:<pass>@<host>/<dbname>
```
   - Add `asyncpg==0.30.0` to `requirements.txt`

### Option B: Railway

1. **Install Railway CLI**
```bash
npm install -g @railway/cli
railway login
```

2. **Deploy**
```bash
cd backend/payshield-backend
railway init
railway up
```

3. **Set environment variables** via Railway dashboard (same as Render).

### Option C: DigitalOcean App Platform

1. Push to GitHub
2. Create App → Select repository
3. Configure:
   - **Run command**: `uvicorn main:app --host 0.0.0.0 --port 8080`
   - Add environment variables

---

## Frontend Deployment

### Vercel (Recommended)

1. **Update environment for production**

Create/update `payshield-frontend/.env.production`:
```env
VITE_API_URL=https://payshield-api.onrender.com/api/v1
VITE_API_BASE_URL=https://payshield-api.onrender.com/api/v1
VITE_WS_URL=wss://payshield-api.onrender.com/ws
```

2. **Push frontend to GitHub**
```bash
cd payshield-frontend
git add .
git commit -m "Production config"
git push
```

3. **Deploy on Vercel**
   - Go to [vercel.com](https://vercel.com) → Import Project
   - Connect GitHub repo → Select `payshield-frontend/`
   - **Framework**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - Set environment variables:
```
VITE_API_BASE_URL=https://payshield-api.onrender.com/api/v1
VITE_WS_URL=wss://payshield-api.onrender.com/ws
VITE_FIREBASE_API_KEY=<your-key>
VITE_FIREBASE_AUTH_DOMAIN=<your-domain>
VITE_FIREBASE_PROJECT_ID=<your-project>
```

4. **Update Backend CORS**

Add your Vercel domain to the backend's `CORS_ORIGINS` environment variable:
```
CORS_ORIGINS=https://payshield-ai.vercel.app,http://localhost:5173
```

### Netlify (Alternative)
```bash
cd payshield-frontend
npm run build
# Deploy dist/ folder to Netlify
npx netlify-cli deploy --prod --dir=dist
```

---

## Docker Deployment

### Docker Setup

Create `backend/payshield-backend/Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create `backend/payshield-backend/.dockerignore`:
```
__pycache__
*.pyc
*.pyo
.env
*.db
venv/
.git/
```

### Docker Compose (Full Stack)

Create `docker-compose.yml` in the project root:
```yaml
version: '3.8'

services:
  backend:
    build: ./backend/payshield-backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://payshield:payshield@db:5432/payshield
      - JWT_SECRET=your-production-secret-here
      - CORS_ORIGINS=http://localhost:5173,http://localhost:3000
      - DEBUG=false
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  frontend:
    build: ./payshield-frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=payshield
      - POSTGRES_USER=payshield
      - POSTGRES_PASSWORD=payshield
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U payshield"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

### Build & Run
```bash
docker compose up --build -d

# Check logs
docker compose logs -f backend

# Stop
docker compose down
```

---

## Production PostgreSQL Migration

When moving from SQLite to PostgreSQL:

### 1. Install PostgreSQL driver
```bash
pip install asyncpg
```

Add to `requirements.txt`:
```
asyncpg==0.30.0
```

### 2. Update DATABASE_URL
```env
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/payshield
```

### 3. Remove SQLite-specific config
In `app/db/database.py`, the `check_same_thread` arg is automatically skipped for non-SQLite databases (already handled in the code).

### 4. Re-seed the database
```bash
# Delete old SQLite file (if present)
del payshield.db

# Restart — auto-seeds fresh PostgreSQL
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Environment Variables Reference

### Backend (`backend/payshield-backend/.env`)

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | Database connection string | `sqlite+aiosqlite:///./payshield.db` | Yes |
| `JWT_SECRET` | Secret key for JWT signing | — | **Yes (change in prod!)** |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` | No |
| `JWT_EXPIRATION_MINUTES` | Token expiry in minutes | `1440` (24h) | No |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:5173` | Yes |
| `HOST` | Server host | `0.0.0.0` | No |
| `PORT` | Server port | `8000` | No |
| `DEBUG` | Enable debug mode | `true` | No |
| `RATE_LIMIT_PER_MINUTE` | API rate limit | `120` | No |

### Frontend (`payshield-frontend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | API base URL | `/api/v1` |
| `VITE_API_BASE_URL` | API base URL (used by apiClient) | `/api/v1` |
| `VITE_WS_URL` | WebSocket URL | `ws://localhost:8000/ws` |
| `VITE_FIREBASE_API_KEY` | Firebase API key | — |
| `VITE_FIREBASE_AUTH_DOMAIN` | Firebase auth domain | — |
| `VITE_FIREBASE_PROJECT_ID` | Firebase project ID | — |

---

## API Endpoints Reference

### Authentication
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/login` | Login with email/password |
| POST | `/api/v1/auth/register` | Register new user |
| GET | `/api/v1/auth/me` | Get current user profile |

### Transactions
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/transactions` | List transactions (paginated) |
| GET | `/api/v1/transactions/{id}` | Get transaction detail |
| POST | `/api/v1/transactions` | Create transaction (triggers scoring) |

### Alerts
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/alerts` | List alerts (paginated) |
| GET | `/api/v1/alerts/stats` | Alert queue statistics |
| GET | `/api/v1/alerts/{id}` | Get alert detail |
| PUT | `/api/v1/alerts/{id}/status` | Update alert status |
| POST | `/api/v1/alerts/{id}/assign` | Assign alert to analyst |

### Analytics
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/analytics/overview` | Dashboard KPIs |
| GET | `/api/v1/analytics/velocity` | Transaction velocity chart data |
| GET | `/api/v1/analytics/fraud-by-type` | Fraud type distribution |
| GET | `/api/v1/analytics/trends` | Monthly fraud trends |
| GET | `/api/v1/analytics/live-activity` | Live activity feed |
| GET | `/api/v1/analytics/full` | Full analytics overview |
| GET | `/api/v1/analytics/system-health` | System health metrics |

### Investigations
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/investigations` | List investigations |
| GET | `/api/v1/investigations/{id}` | Get investigation detail |
| POST | `/api/v1/investigations` | Create investigation |
| PUT | `/api/v1/investigations/{id}/verdict` | Submit verdict |

### Models
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/models` | List ML models |
| GET | `/api/v1/models/{id}` | Get model detail |
| GET | `/api/v1/models/{id}/performance` | Model performance metrics |
| POST | `/api/v1/models/train-new` | Trigger model training |

### Scoring & Health
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/score` | Score a transaction |
| GET | `/api/v1/health` | Full health check |
| GET | `/api/v1/health/ping` | Simple ping |

### WebSocket
| URL | Description |
|-----|-------------|
| `ws://host:8000/ws` | Real-time alerts & transaction feed |

---

## Troubleshooting

### Backend won't start
```bash
# Check Python version (need 3.11+)
python --version

# Reinstall dependencies
pip install -r requirements.txt

# Check if port is in use
netstat -ano | findstr :8000
# Kill process using port:
taskkill /PID <pid> /F
```

### Database errors
```bash
# Reset database (delete and re-seed)
del payshield.db
python -m uvicorn main:app --host 127.0.0.1 --port 8000
# Database auto-seeds on startup when empty
```

### CORS errors in browser
- Ensure backend `CORS_ORIGINS` includes your frontend URL
- For local dev: `CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`
- For production: `CORS_ORIGINS=https://your-frontend.vercel.app`

### Frontend can't reach backend
- Check Vite proxy in `vite.config.ts` points to correct backend port
- Ensure backend is running: `curl http://127.0.0.1:8000/api/v1/health/ping`
- Check browser DevTools Network tab for failed requests

### WebSocket disconnects
- WebSocket auto-reconnects with exponential backoff (5 attempts)
- Check firewall isn't blocking WebSocket connections
- For production, ensure your hosting supports WebSocket upgrades

### greenlet / bcrypt errors
```bash
pip install greenlet bcrypt==4.2.0
```

---

## Security Checklist for Production

- [ ] Change `JWT_SECRET` to a strong random value (`openssl rand -hex 32`)
- [ ] Set `DEBUG=false`
- [ ] Use PostgreSQL instead of SQLite
- [ ] Enable HTTPS on your hosting provider
- [ ] Set `CORS_ORIGINS` to only your production frontend domain
- [ ] Set up rate limiting appropriately
- [ ] Use environment variables for all secrets (never commit `.env`)
- [ ] Enable Render/Railway auto-deploy on push
- [ ] Set up monitoring/logging (e.g. Sentry, DataDog)
