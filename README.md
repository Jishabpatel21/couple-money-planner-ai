# Couple's Money Planner - Streamlit Project

India-specific, AI-powered joint financial planning app for couples.

## 🚀 Live Demo

➡️ **[Try the app here](https://couple-money-planner-ai.streamlit.app/)**

## Features

- Partner A and Partner B input form
- HRA calculator with metro/non-metro logic
- Old vs New tax regime comparison
- SIP split suggestion by income ratio
- NPS optimization (extra Rs 50,000 deduction)
- Insurance recommendations (term + health)
- Net worth and savings dashboard with Plotly charts
- Goal tracking using SQLite
- AI financial suggestions via OpenAI (with fallback)
- Savings Score (0-100)
- Before vs After optimization chart

## Key Documents

| Architecture | Impact Model |
|---|---|
| [Couple's Money Planner: Architecture Document](ARCHITECTURE_DOCUMENT.md) | [Couple's Money Planner: Impact Model](IMPACT_MODEL.md) |
| Covers agent roles, communication flow, tool integrations, and error-handling logic. | Covers quantified estimates for time saved, cost reduced, and revenue recovered with assumptions. |

## Project Structure

```text
main.py
utils/
	hra.py
	tax.py
	investment.py
	ai.py
	storage.py
data/
	database.db
requirements.txt
```

## Important Functions

- `calculate_hra()` in `utils/hra.py`
- `compare_tax_regime()` in `utils/tax.py`
- `suggest_sip_split()` in `utils/investment.py`
- `calculate_net_worth()` in `utils/investment.py`
- `generate_ai_recommendations()` in `utils/ai.py`

## Run Locally

1. Create virtual environment

```bash
# Windows
python -m venv backend\venv

# Mac/Linux
python3 -m venv backend/venv
```

2. Install dependencies

```bash
# Windows
backend\venv\Scripts\python.exe -m pip install -r requirements.txt

# Mac/Linux
./backend/venv/bin/python -m pip install -r requirements.txt
```

3. Start app

```bash
# Windows
backend\venv\Scripts\python.exe -m streamlit run main.py --server.port 8501

# Mac/Linux
./backend/venv/bin/python -m streamlit run main.py --server.port 8501
```

Alternative launch scripts:

```bash
# Windows (PowerShell or CMD)
.\start_streamlit.bat

# Mac/Linux
bash start_streamlit.sh
```

Important: run only one command for your OS at each step.

4. Open in browser

```text
http://localhost:8501
```

## AI Model Setup (Optional)

This app supports pretrained models via OpenAI or Hugging Face Inference API.

Set environment variables before launching app:

```bash
AI_PROVIDER=auto

# Option 1: OpenAI
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o

# Option 2: Hugging Face pretrained model
HF_API_TOKEN=your_hf_token_here
HF_MODEL=mistralai/Mistral-7B-Instruct-v0.2
```

Provider options:

- `auto` (default): tries Hugging Face first, then OpenAI, then fallback rules
- `huggingface`: uses Hugging Face only, then fallback rules if unavailable
- `openai`: uses OpenAI only, then fallback rules if unavailable
- `fallback`: deterministic rule-based suggestions only

## Theme (Default Color)

This project uses a Streamlit theme file at `.streamlit/config.toml`.

- Primary color: `#2F80ED`
- Base mode: `light`

You can change `primaryColor` in `.streamlit/config.toml` to set your preferred default app color.

## Streamlit Cloud Deployment

**Live app**: https://couple-money-planner-ai.streamlit.app/

### Setup Steps:

1. Push this project to GitHub.
2. Open Streamlit Community Cloud: https://streamlit.io/cloud
3. Create a new app.
4. Select repository and branch.
5. Main file path: `main.py`
6. Dependency file: `requirements.txt`
7. Add secret in Streamlit settings (optional):

```toml
AI_PROVIDER="auto"
OPENAI_API_KEY="your-key"
OPENAI_MODEL="gpt-4o"
HF_API_TOKEN="your-hf-token"
HF_MODEL="mistralai/Mistral-7B-Instruct-v0.2"
```

