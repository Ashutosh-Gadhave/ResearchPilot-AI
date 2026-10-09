# 🚀 ResearchPilot AI

**SerpApi India Hackathon 2026 Submission**

ResearchPilot AI is an evidence-based decision agent. It empowers technical leads, researchers, and decision-makers to answer complex comparison and evaluation questions by performing live web searches via **SerpApi**, synthesizing real-world evidence using **Gemini LLM**, and presenting grounded recommendations with source citations, trade-offs, and uncertainties.

---

## 🌟 Key Features

- **Live Web Search Grounding**: Retrieves real-time organic web search results using `serpapi-search-tools` (`WebSearch` engine).
- **Gemini Intelligence**: Uses the official `google-genai` SDK (`gemini-2.5-flash` with automatic fallback to `gemini-2.0-flash`) for multi-perspective synthesis.
- **Evidence Citation**: Cites specific retrieved source URLs for facts, benchmarks, and claims.
- **Structured Comparison Matrix**: Auto-generates markdown comparison tables contrasting options against user priorities.
- **Trade-Offs & Uncertainty Analysis**: Identifies risks, missing information, and key assumptions before decision execution.
- **Interactive Streamlit Interface**: Sleek SaaS design with preset decision scenarios, custom engine selection, expandable source viewer, and markdown export.

---

## 🛠️ Architecture

```
ResearchPilot-AI/
├── app.py                  # Streamlit application UI & state management
├── test_search.py          # Standalone verification script for SerpApi
├── requirements.txt        # Project dependencies
├── .env.example            # Environment template for API keys
├── src/
│   ├── __init__.py
│   ├── search_engine.py    # SerpApi web_search wrapper & JSON output parser
│   └── llm_analyzer.py     # Gemini client integration & prompt synthesizer
└── tests/
    ├── test_search_engine.py # Unit tests for search engine logic
    └── test_llm_analyzer.py  # Unit tests for LLM grounding logic
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.13+
- SerpApi API Key ([Get SerpApi Key](https://serpapi.com))
- Gemini API Key ([Get Gemini Key](https://aistudio.google.com))

### 2. Environment Setup

Clone the repository and set up your virtual environment:

```bash
git clone <repository-url>
cd ResearchPilot-AI

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure API Keys

Copy `.env.example` to `.env` and fill in your API keys:

```env
SERPAPI_API_KEY=your_serpapi_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## 🧪 Running Tests

Execute the unit test suite:

```bash
python -m unittest discover tests
```

To test raw search execution:

```bash
python test_search.py
```

---

## 🖥️ Launching the Application

Start the Streamlit dashboard:

```bash
streamlit run app.py
```

Open your browser to `http://localhost:8501`.

---

## 📜 License & Acknowledgments

Built for the **SerpApi India Hackathon 2026** using `serpapi-search-tools`, `google-genai`, and `streamlit`.
