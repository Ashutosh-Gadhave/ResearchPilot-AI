import os
import streamlit as st
from dotenv import load_dotenv
from src.search_engine import execute_search
from src.llm_analyzer import generate_decision_report

load_dotenv()

# Page Configuration
st.set_page_config(
    page_title="ResearchPilot AI | Evidence-Based Decision Agent",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for rich aesthetics
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #1e1e2f 0%, #0f172a 100%);
        padding: 2.2rem 2.5rem;
        border-radius: 16px;
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 10px 30px rgba(0,0,0,0.25);
        margin-bottom: 2rem;
    }
    
    .badge-tag {
        background: linear-gradient(90deg, #3b82f6 0%, #8b5cf6 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        display: inline-block;
        margin-bottom: 0.8rem;
    }

    .recommendation-card {
        background: linear-gradient(135deg, #064e3b 0%, #022c22 100%);
        border: 1px solid #059669;
        border-radius: 14px;
        padding: 1.5rem;
        color: #ecfdf5;
        margin-bottom: 1.5rem;
    }
    
    .metric-box {
        background: #1e293b;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        border: 1px solid #334155;
        text-align: center;
    }
    
    .source-card {
        background-color: #1e293b;
        border-left: 4px solid #3b82f6;
        padding: 1rem 1.2rem;
        border-radius: 8px;
        margin-bottom: 0.8rem;
    }
    
    .source-title {
        font-weight: 600;
        font-size: 1.05rem;
        color: #60a5fa;
        text-decoration: none;
    }
    
    .source-title:hover {
        text-decoration: underline;
    }
    
    .stButton>button {
        background: linear-gradient(90deg, #2563eb 0%, #7c3aed 100%);
        color: white;
        font-weight: 700;
        font-size: 1.05rem;
        padding: 0.6rem 2rem;
        border-radius: 10px;
        border: none;
        transition: all 0.3s ease;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.4);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(124, 58, 237, 0.6);
    }
</style>
""", unsafe_allow_html=True)

# Application Header
st.markdown("""
<div class="main-header">
    <div class="badge-tag">SERPAPI INDIA HACKATHON 2026</div>
    <h1 style="margin: 0; font-weight: 800; font-size: 2.4rem; color: #f8fafc;">
        🚀 ResearchPilot AI
    </h1>
    <p style="margin-top: 0.5rem; margin-bottom: 0; font-size: 1.1rem; color: #94a3b8;">
        Evidence-based decision agent powered by <b>SerpApi Live Web Search</b> & <b>Gemini Intelligence</b>
    </p>
</div>
""", unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Configuration & Status")
    
    # API Key Verification
    serpapi_key_env = os.getenv("SERPAPI_API_KEY", "")
    gemini_key_env = os.getenv("GEMINI_API_KEY", "")
    
    st.subheader("🔑 API Keys")
    if serpapi_key_env:
        st.success("✓ SerpApi Key Loaded (.env)", icon="✅")
    else:
        st.warning("⚠️ SerpApi Key Missing", icon="⚠️")
        
    if gemini_key_env:
        st.success("✓ Gemini Key Loaded (.env)", icon="✅")
    else:
        st.warning("⚠️ Gemini Key Missing", icon="⚠️")
        
    # Optional Manual Key Overrides
    with st.expander("Override API Keys"):
        custom_serpapi_key = st.text_input("Custom SerpApi Key", value="", type="password")
        custom_gemini_key = st.text_input("Custom Gemini Key", value="", type="password")
        
    active_serpapi_key = custom_serpapi_key if custom_serpapi_key else serpapi_key_env
    active_gemini_key = custom_gemini_key if custom_gemini_key else gemini_key_env

    st.divider()
    
    # Engine & Model Settings
    st.subheader("🔍 Engine Settings")
    search_engine = st.selectbox(
        "SerpApi Search Engine",
        options=["google_light", "google", "google_scholar", "bing", "duckduckgo"],
        index=0,
        help="Google Light provides fast, compact live search results via SerpApi."
    )
    
    num_results = st.slider("Max Search Results", min_value=5, max_value=20, value=10, step=1)
    
    st.subheader("🤖 LLM Model")
    llm_model = st.selectbox(
        "Gemini Model",
        options=["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"],
        index=0
    )
    
    st.divider()
    st.caption("Built with Streamlit, SerpApi Search Tools, and Google GenAI SDK.")

# Preset Examples Handler
def set_example(question: str, priorities: str):
    st.session_state["research_question"] = question
    st.session_state["decision_priorities"] = priorities

# Quick Presets
st.markdown("##### 💡 Preset Decision Scenarios")
col_p1, col_p2, col_p3 = st.columns(3)

with col_p1:
    if st.button("⚡ Postgres vs DuckDB (Local Analytics)", use_container_width=True):
        set_example(
            "Should I use PostgreSQL or DuckDB for a local analytics workload?",
            "Query execution speed, low memory overhead, zero configuration, SQL support"
        )
with col_p2:
    if st.button("🌐 Next.js vs Remix (Enterprise Web App)", use_container_width=True):
        set_example(
            "Which web framework is better for an enterprise e-commerce platform: Next.js or Remix?",
            "SEO performance, server-side rendering, developer ecosystem, deployment simplicity"
        )
with col_p3:
    if st.button("🤖 LangChain vs LlamaIndex vs DSPy", use_container_width=True):
        set_example(
            "Compare LangChain, LlamaIndex, and DSPy for building AI agent workflows in Python.",
            "Ease of debugging, production reliability, RAG integration, minimal abstraction bloat"
        )

st.markdown("<br>", unsafe_allow_html=True)

# Main Form Inputs
with st.form("research_form"):
    default_q = st.session_state.get("research_question", "Should I use PostgreSQL or DuckDB for local data analytics?")
    default_p = st.session_state.get("decision_priorities", "Query speed, low memory consumption, ease of setup, embedded execution")
    
    question_input = st.text_area(
        "🎯 Research Question / Decision Prompt",
        value=default_q,
        height=100,
        placeholder="e.g. Compare Option A vs Option B for my specific use case..."
    )
    
    priorities_input = st.text_input(
        "⚙️ Key Priorities & Decision Criteria",
        value=default_p,
        placeholder="e.g. Speed, Cost, Memory, Security, Ease of maintenance"
    )
    
    submit_button = st.form_submit_button("🚀 Run Research & Decision Analysis", use_container_width=True)

# Processing & Results Output
if submit_button:
    # Input Validation
    if not question_input.strip():
        st.error("Please enter a research question or decision prompt to analyze.")
    elif not active_serpapi_key:
        st.error("SerpApi API Key is missing. Please add SERPAPI_API_KEY to your .env file.")
    elif not active_gemini_key:
        st.error("Gemini API Key is missing. Please add GEMINI_API_KEY to your .env file.")
    else:
        with st.status("🔍 Researching and Analyzing...", expanded=True) as status:
            # Step 1: Live SerpApi Search
            st.write(f"📡 Querying SerpApi (`{search_engine}`)...")
            search_response = execute_search(
                query=question_input,
                engine=search_engine,
                num_results=num_results,
                api_key=active_serpapi_key
            )
            
            if not search_response["success"]:
                status.update(label="❌ Search Failed", state="error", expanded=True)
                st.error(search_response["error"])
            else:
                organic_results = search_response["organic_results"]
                st.write(f"✓ Retrieved **{len(organic_results)}** live search results.")
                
                # Step 2: Gemini LLM Grounded Analysis
                st.write(f"🧠 Synthesizing evidence with Gemini (`{llm_model}`)...")
                report_response = generate_decision_report(
                    question=question_input,
                    priorities=priorities_input,
                    organic_results=organic_results,
                    model_name=llm_model,
                    api_key=active_gemini_key
                )
                
                if not report_response["success"]:
                    status.update(label="❌ LLM Analysis Failed", state="error", expanded=True)
                    st.error(report_response["error"])
                else:
                    status.update(label="✅ Decision Report Complete!", state="complete", expanded=False)
                    
                    # Store in Session State
                    st.session_state["last_report"] = report_response["report"]
                    st.session_state["last_sources"] = organic_results
                    st.session_state["last_model"] = report_response.get("model_used", llm_model)
                    st.session_state["last_query"] = question_input

# Display Results if Available
if "last_report" in st.session_state:
    report_text = st.session_state["last_report"]
    sources = st.session_state.get("last_sources", [])
    used_model = st.session_state.get("last_model", llm_model)
    
    st.markdown("---")
    
    # Top Metrics Bar
    mcol1, mcol2, mcol3 = st.columns(3)
    with mcol1:
        st.markdown(f"""
        <div class="metric-box">
            <span style="font-size:0.85rem; color:#94a3b8;">SERPAPI SEARCH RESULTS</span>
            <h3 style="margin:0; color:#38bdf8;">{len(sources)} Sources Analyzed</h3>
        </div>
        """, unsafe_allow_html=True)
    with mcol2:
        st.markdown(f"""
        <div class="metric-box">
            <span style="font-size:0.85rem; color:#94a3b8;">GEMINI AI ENGINE</span>
            <h3 style="margin:0; color:#a78bfa;">{used_model}</h3>
        </div>
        """, unsafe_allow_html=True)
    with mcol3:
        st.markdown(f"""
        <div class="metric-box">
            <span style="font-size:0.85rem; color:#94a3b8;">DECISION STATUS</span>
            <h3 style="margin:0; color:#34d399;">Grounded Evidence</h3>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Structured Tabs View
    tab_report, tab_sources, tab_export = st.tabs([
        "📄 Decision Report", 
        "🔗 Verified Evidence & Sources", 
        "📥 Raw Markdown & Export"
    ])
    
    with tab_report:
        st.markdown(report_text, unsafe_allow_html=True)
        
    with tab_sources:
        st.markdown("### 📚 Grounded Search Evidence (SerpApi)")
        st.info("The decision report above was constructed strictly from the following real-time web search results:")
        
        for idx, src in enumerate(sources, start=1):
            st.markdown(f"""
            <div class="source-card">
                <span style="color:#94a3b8; font-weight:600; font-size:0.85rem;">SOURCE [{idx}] &bull; {src.get('source', '')}</span><br>
                <a href="{src.get('link')}" target="_blank" class="source-title">{src.get('title')}</a>
                <p style="margin-top:0.4rem; margin-bottom:0; color:#cbd5e1; font-size:0.92rem;">{src.get('snippet')}</p>
            </div>
            """, unsafe_allow_html=True)
            
    with tab_export:
        st.markdown("### 📥 Export Decision Report")
        st.text_area("Markdown Output", value=report_text, height=400)
        
        st.download_button(
            label="💾 Download Report as Markdown (.md)",
            data=report_text,
            file_name="ResearchPilot_Decision_Report.md",
            mime="text/markdown"
        )
