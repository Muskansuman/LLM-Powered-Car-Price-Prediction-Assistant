# 🚗 Conversational Car Price Prediction (FastAPI + LLM)

A hybrid **classical ML + LLM** system: a scikit-learn regressor predicts used-car prices, and a free-tier LLM (Groq, Gemini, or local Ollama) lets users interact with it in plain English.

```
User text → LLM extracts features → ML model predicts price → LLM explains it
```

---

## ✨ Features

- **Classical ML serving**: RandomForest pipeline with sklearn `ColumnTransformer`, served via FastAPI.
- **Conversational layer**: free-text chat that extracts structured car features, calls the model, and explains the prediction in natural language.
- **Multi-provider LLM abstraction**: swap between **Groq** (free, fast), **Google Gemini** (free), and **Ollama** (local, offline) via one env var.
- **Conversation memory**: Redis-backed multi-turn chat keyed by session id, with in-process fallback if Redis is down.
- **Resilient caching**: Redis prediction cache with safe `json` serialization (no `eval`!) and graceful degradation.
- **JWT auth + API key** for protected endpoints.
- **Observability**: Prometheus metrics + Grafana dashboards, structured request/response logging.
- **Streamlit chat UI** for instant demos.
- **Dockerized**: API + UI + Redis + Prometheus + Grafana via one `docker compose up`.

---

## 🏗️ Architecture

```
┌──────────────┐   text   ┌──────────────────┐   features  ┌────────────┐
│  Streamlit   │────────► │  FastAPI /chat   │────────────►│  ML model  │
│   chat UI    │          │  ┌────────────┐  │             │ (sklearn)  │
└──────────────┘          │  │ extractor  │  │             └────────────┘
                          │  │ explainer  │  │                  │
                          │  └────────────┘  │                  ▼
                          │        │         │             ┌────────────┐
                          │        ▼         │             │   Redis    │
                          │  LLM provider    │             │ (cache +   │
                          │  (Groq/Gemini/   │             │  history)  │
                          │   Ollama)        │             └────────────┘
                          └──────────────────┘
                                    │
                                    ▼
                       ┌──────────────────────────┐
                       │ Prometheus + Grafana     │
                       │  (latency, errors, RPS)  │
                       └──────────────────────────┘
```

---

## 🚀 Quickstart (with Docker)

1. **Get free LLM API keys** (no credit card needed):
   - Groq: https://console.groq.com → copy key
   - Gemini: https://aistudio.google.com → copy key

2. **Configure environment**:

   ```bash
   cp .env.example .env
   # edit .env and paste your GROQ_API_KEY (or GOOGLE_API_KEY)
   ```

3. **Start everything**:

   ```bash
   docker compose up --build
   ```

4. **Open**:
   - Chat UI: http://localhost:8501
   - Swagger docs: http://localhost:8000/docs
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000

---

## 🧪 Quickstart (local, without Docker)

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run Redis
docker run -d --name redis -p 6379:6379 redis:alpine

# Configure (.env auto-loaded)
cp .env.example .env  # edit and add your GROQ_API_KEY

# Backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# UI (separate terminal)
streamlit run frontend/chat_app.py
```

You **do not** need to type API URLs in the sidebar: the app builds the backend address from the hostname you used (e.g. phone on Wi‑Fi opens `http://192.168.x.x:8501` → API is assumed at `http://192.168.x.x:8000`). Run uvicorn on **`0.0.0.0`** so other devices can reach it. If your API uses another port (e.g. **8001**), start Streamlit with `API_PORT=8001 streamlit run frontend/chat_app.py`.

---

## 🌐 Public deploy (Render API + Streamlit Community Cloud)

Use this when you want a **shareable HTTPS link** (no same WiFi required).

### Prerequisites

1. Push this repo to **GitHub**. Ensure **`app/models/model.joblib`** is in the repo (train locally with `python -m training.train_model` and commit the file), or add a build step that trains before `uvicorn` starts.
2. Default Git branch should be **`main`** (or edit `branch:` in `render.yaml`).

### Part A — API on Render

1. Sign up at [render.com](https://render.com) and connect GitHub.
2. **New → Blueprint** → select this repo → Render reads `render.yaml`.
3. Apply the blueprint. It creates:
   - **Redis** (free Key Value instance)
   - **Web service** `fastapi-car-price-api` (Docker build)
4. After the first deploy, open the **web service → Environment** and set:
   - **`API_KEY`** — long random string (you will reuse this in Streamlit).
   - **`GROQ_API_KEY`** — from [console.groq.com](https://console.groq.com) (free).
5. Wait for deploy to go **Live**. Copy the public URL, e.g. `https://fastapi-car-price-api.onrender.com`.
6. Smoke test: open `https://YOUR-SERVICE.onrender.com/health` — expect `{"status":"ok"}`.

**Free tier note:** the service **spins down** after idle time; the first request after sleep can take **~30–60 seconds**.

### Part B — Chat UI on Streamlit Community Cloud

1. Sign up at [share.streamlit.io](https://share.streamlit.io) with GitHub.
2. **New app** → pick this repo.
3. **Main file path:** `frontend/chat_app.py`
4. **Python version:** 3.10 (or match your project).
5. **App secrets** (gear icon → Secrets) paste TOML like below (see `.streamlit/secrets.toml.example`):

   ```toml
   [api]
   base_url = "https://fastapi-car-price-api.onrender.com"
   api_key = "same API_KEY you set on Render"
   ```

6. Deploy. Share the **Streamlit** URL (e.g. `https://your-app.streamlit.app`) — that is the link you give to anyone.

### Security

- Never commit real API keys. Use Render env vars and Streamlit Secrets only.
- Rotate any key that was ever pasted into chat or a public issue.

### Semi-public demo (optional)

- **Streamlit password gate:** add a `[demo]` section with `password` in Streamlit Secrets (see `.streamlit/secrets.toml.example`), or set **`DEMO_PASSWORD`** when running Streamlit locally. You can share the **public Streamlit link** widely; only people who receive the **password** separately can use the chat. Sidebar includes **Lock demo** to require the password again on that browser.
- **API rate limits:** FastAPI applies per-IP limits on `/chat`, `DELETE /chat/{session_id}`, and `/predict` (defaults in `app/core/config.py`; override with **`RATE_LIMIT_CHAT`**, **`RATE_LIMIT_CHAT_DELETE`**, **`RATE_LIMIT_PREDICT`** on Render). Helps control abuse and LLM cost. Clients behind a proxy use **`X-Forwarded-For`** when present.

---

## 🔌 API endpoints

| Method | Path                    | Auth                | Purpose                                         |
|--------|-------------------------|---------------------|-------------------------------------------------|
| POST   | `/login`                | -                   | Get a JWT (creds: `admin` / `admin`)            |
| POST   | `/predict`              | `api-key` + `token` | Predict from a structured JSON payload          |
| POST   | `/chat`                 | `api-key`           | Chat in natural language                        |
| DELETE | `/chat/{session_id}`    | `api-key`           | Reset a chat session                            |
| GET    | `/health`               | -                   | Health check                                    |
| GET    | `/metrics`              | -                   | Prometheus metrics                              |
| GET    | `/docs`                 | -                   | Swagger UI                                      |

### Example: `/chat`

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "api-key: demo-key" \
  -d '{
    "message": "I have a 2015 Maruti Swift, ran about 70k km, petrol, second owner, manual."
  }'
```

Response:

```json
{
  "session_id": "abc123...",
  "reply": "Your 2015 Swift looks like roughly ₹3.5 lakh. The 70k km on the clock and second-owner status pull the price down a bit; a fresh service record could get you ₹15-20k more. Note: I assumed a 5-seater 1.2L petrol setup typical of that year.",
  "predicted_price": 352418.75,
  "formatted_price": "₹352,418.75",
  "extracted_features": { "...": "..." },
  "missing_fields": [],
  "assumptions": ["Assumed 1197 cc engine and 82 bhp typical for 2015 Swift VXI"],
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "latency_ms": 612.4
}
```

If fields are missing, the assistant asks a follow-up instead. Pass back the same `session_id` to continue the conversation.

---

## 🔧 Switching LLM providers

Just change one env var:

```bash
LLM_PROVIDER=groq      # default — fastest, free
LLM_PROVIDER=gemini    # also free, best function calling
LLM_PROVIDER=ollama    # fully local, offline (needs `ollama serve`)
```

Restart the API. No code changes.

---

## 🧠 Train the model

```bash
pip install -r requirements.txt
python training/train_model.py
# writes app/models/model.joblib
```

The training data lives at `data/car-details.csv`.

---

## 📦 Project layout

```
app/
├── api/              # /login, /predict, /chat routers
├── cache/            # Redis-backed prediction cache (graceful)
├── core/             # config, security, exception handlers
├── llm/
│   ├── base.py           # LLMProvider abstract interface
│   ├── factory.py        # provider selection from env
│   ├── prompts.py        # system prompts
│   ├── extractor.py      # text → CarFeatures (JSON-mode)
│   ├── explainer.py      # price → friendly explanation
│   └── providers/        # groq, gemini, ollama implementations
├── memory/           # Redis-backed conversation history
├── middleware/       # request/response logging
├── models/           # trained model artifact (commit for cloud deploy)
└── services/         # model loading + inference
frontend/
└── chat_app.py       # Streamlit chat UI
training/             # training pipeline
```

---

## 🛠️ Tech stack

| Layer            | Tool                                                |
|------------------|-----------------------------------------------------|
| API              | FastAPI, Uvicorn                                    |
| ML               | scikit-learn (RandomForest + ColumnTransformer)     |
| LLM              | Groq, Google Gemini, Ollama (pluggable)             |
| Cache & memory   | Redis                                               |
| Frontend         | Streamlit                                           |
| Monitoring       | Prometheus + Grafana                                |
| Packaging        | Docker + Docker Compose                             |

---

## 👨‍💻 Author

Made by Muskan Suman · [Email](muskan.suman2907@gmail.com) · [LinkedIn](https://www.linkedin.com/in/muskansuman29/)
