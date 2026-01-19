# Sequential Narrative AI - Project Configuration

## Overview
AI-driven sequential narrative recommendation system for streaming media. Replaces grid-based browsing with conversational AI that presents 2-5 curated recommendations as an engaging reel with micro-pitches.

## Tech Stack

### Backend (FastAPI)
- **Location**: `backend/`
- **Entry**: `backend/app/main.py`
- **Port**: 8888
- **Key Services**:
  - `recommendation_engine.py` - DPP-based diversity optimization
  - `nlp_service.py` - Intent parsing, micro-pitch generation
  - `streaming_apis.py` - TMDb, YouTube, Paramount+ integrations
  - `multi_head_encoder.py` - Decision state encoding
  - `survival_model.py` - Hazard-of-commit predictions

### Frontend (React + TypeScript + Vite)
- **Location**: `src/`
- **Entry**: `src/main.tsx`
- **Port**: 3000
- **Key Components**:
  - `ConversationalInterface.tsx` - Main chat UI
  - `ReelViewer.tsx` - Recommendation carousel
  - `ReelCard.tsx` - Individual recommendation cards
  - `AnalyticsDashboard.tsx` - Decision metrics

## Quick Commands

```bash
# Start backend
cd backend && ./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8888 --reload

# Start frontend
npm run dev

# Test recommendations
curl -X POST http://localhost:8888/api/recommendations/generate \
  -H "Content-Type: application/json" \
  -d '{"query": "action movies", "user_profile": {...}}'
```

## API Conventions

### Request/Response Format
- Backend uses **snake_case** (Python/Pydantic)
- Frontend uses **camelCase** (TypeScript)
- Transform in `src/api/client.ts` when crossing boundary

### Key Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/recommendations/generate` | POST | Get AI recommendations |
| `/api/telemetry/batch` | POST | Send behavioral signals |
| `/ws/telemetry/{user_id}` | WS | Real-time telemetry |
| `/api/decision-state/{user_id}` | GET | Get decision state |

## Environment Variables

```bash
# backend/.env
OPENROUTER_API_KEY=...
TMDB_API_KEY=...
YOUTUBE_API_KEY=...
GROQ_API_KEY=...      # Fallback
CEREBRAS_API_KEY=...  # Fallback
```

## Architecture Patterns

### Recommendation Flow
```
User Query → NLP Intent Parsing → Content Fetching (APIs) 
→ Scoring & Ranking → DPP Diversity Selection 
→ Micro-Pitch Generation → Audio Synthesis → Reel Display
```

### Decision State Encoding
- Tracks: scroll velocity, dwell time, focus changes, micro-pauses
- Computes: stress level, hesitation score, commit probability
- Adapts: recommendation count (2-5) based on user state

### Audio
- Uses browser Web Speech API (SpeechSynthesis)
- Prefers premium voices: Samantha, Ava, Google US English
- Rate: 0.95x, Pitch: 1.05x for natural sound

## Code Style

### TypeScript
- Functional components with hooks
- Types in `src/types/index.ts`
- API calls through `src/api/client.ts`

### Python
- Pydantic models in `backend/app/models.py`
- Services are singletons (instantiated at module level)
- Async handlers throughout

## Testing Endpoints

```bash
# Health check
curl http://localhost:8888/health

# Test specific query
curl -X POST http://localhost:8888/api/recommendations/generate \
  -H "Content-Type: application/json" \
  -d '{"query": "something relaxing", "user_profile": {"id": "test", ...}}'
```

## Common Issues

| Issue | Solution |
|-------|----------|
| WebSocket fails | Check backend is on port 8888 |
| 422 errors | Ensure snake_case in API requests |
| No audio | Check browser speech synthesis support |
| Same recommendations | Clear user session, vary query |
