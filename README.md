## 📊 How It Works

1. **Sign up / Log in** — JWT-based auth, tracks age/gender/history per user
2. **Start or continue a chat** — session-aware, with automatic 24-hour expiry handling
3. **Guardrail check** — every message is checked for medical relevance and emergency signals before anything else runs
4. **Intake** — a conversational agent asks 1-2 open-ended questions at a time to build a full symptom picture
5. **Retrieval** — semantic search over a curated disease knowledge base returns the top candidate conditions
6. **Differential diagnosis** — a reasoning agent asks targeted, discriminating questions, grounded strictly in the retrieved medical data, to narrow candidates down to the 3 most likely
7. **Explanation** — the top 3 are explained in plain English (overview, symptoms, causes — deliberately excluding risk factors/complications to avoid unnecessary alarm)
8. **Doctor routing** — on request, finds nearby specialists matching the diagnosed conditions
9. **Summarization** — updates the user's long-term medical timeline and generates a downloadable PDF report

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph (stateful multi-agent workflow) |
| Backend | FastAPI |
| Database | PostgreSQL (NeonDB) via SQLAlchemy |
| Vector search | ChromaDB + `all-MiniLM-L6-v2` embeddings |
| LLMs (dev) | Ollama (local, e.g. Qwen2.5) |
| LLMs (prod) | Gemini 2.5 Flash (light/moderate tier), Groq Llama 3.3 70B (heavy/diagnostic tier) |
| Auth | Custom JWT + bcrypt |
| Doctor search | Google Places API |
| Report generation | FPDF |
| Observability | LangSmith tracing |

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- A PostgreSQL database (e.g. a free [NeonDB](https://neon.tech) instance)
- (Optional, for local dev) [Ollama](https://ollama.com) installed with a model pulled

### Setup

1. **Clone the repository**
```bash
   git clone https://github.com/parvgupta09/MedAssist-New-Modern-RAG-Using-LANGCHAIN-and-LANGGRAPH.git
   cd MedAssist-New-Modern-RAG-Using-LANGCHAIN-and-LANGGRAPH
```

2. **Install dependencies**
```bash
   pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
   cp .env.example .env
   # Fill in your database URL, API keys, and JWT secret
   # Take the reference of the .env.example
```

4. **Web Scarape the data of all the required diseases from the Mayo Clinic Website**
```bash
   python -m src.data.webscrape.py
```

5. **Merge all the json data of the web scraped diseases**
```bash
   python -m src.data.merge_diseases.py
```

. **Build the medical knowledge base**
```bash
   python -m src.data.ingest_knowledge
```

5. **Run the server**
```bash
   uvicorn main:app --reload
```

6. **Explore the API**
   - Docs: http://127.0.0.1:8000/docs

## 🔧 Environment Variables

```env
APP_ENV=development                 # or "production"

NEON_DATABASE_URL=...
SECRET_KEY=...

GOOGLE_API_KEY=...                  # Gemini (Google AI Studio)
GOOGLE_PLACES_API_KEY=...           # Google Places (Cloud Console, needs billing)
GROQ_API_KEY=...

LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=...
LANGCHAIN_PROJECT=MedAssist-New-Modern-RAG-Using-LANGCHAIN-and-LANGGRAPH
```

## 📡 Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/signup` | Create an account |
| POST | `/auth/login` | Get a JWT token |
| GET | `/auth/me` | Get logged-in user's profile |
| POST | `/chat/init` | Start a new triage session |
| GET | `/chat/sessions/{user_id}` | List a user's past sessions |
| GET | `/chat/history/{session_id}` | Get a session's full transcript |
| POST | `/chat/message` | Send a message, get the AI's response |
| GET | `/chat/reports/{report_id}` | Download a generated PDF report |

## 🎯 Design Highlights

- **Manual state persistence over LangGraph checkpointer** — since the API is stateless per-request, key routing state (retrieved diseases, final diagnoses, next action) is deliberately persisted as explicit database columns rather than relying on LangGraph's built-in checkpointer, trading some automatic replay/debugging capability for full transparency and control over what's stored and why.
- **RAG-grounded diagnostic reasoning** — both the narrowing and explanation stages are explicitly instructed to reason only from retrieved reference data, reducing hallucinated or generic textbook answers disconnected from the actual curated knowledge base.
- **Defense-in-depth guardrails** — the topic/emergency check re-runs on every message (not just the first), using recent conversational context rather than isolated messages, to prevent both false positives on legitimate follow-up answers and attempts to pivot off-topic mid-conversation.

## ⚠️ Known Limitations

- No real-time streaming (responses arrive as complete blocks)
- Location is currently provided manually, not auto-detected
- No automated test suite yet
- Age/gender collection is currently conversational only (asked per session), not yet persisted to the user profile

## 📞 Contact

- Issues: open a GitHub issue
- Email: parvguptajpr@gmail.com

---

**Disclaimer**: MedAssist is an AI-assisted informational tool, not a substitute for professional medical advice, diagnosis, or treatment. Always consult a qualified healthcare provider for medical concerns.