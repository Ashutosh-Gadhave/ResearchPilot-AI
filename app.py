import os
import streamlit as st
from dotenv import load_dotenv
from src.search_engine import execute_search
from src.llm_analyzer import generate_decision_report
from src.scorer import parse_criteria, format_decision_matrix_markdown

load_dotenv()

# Page Configuration
st.set_page_config(
    page_title="ResearchPilot AI | Evidence-Based Decision Agent",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for SaaS Experience
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
        margin-bottom: 1.8rem;
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

# Main Inputs Form
with st.form("research_form"):
    default_q = st.session_state.get("research_question", "Should I use PostgreSQL or DuckDB for local data analytics?")
    default_p = st.session_state.get("decision_priorities", "Query execution speed, low memory consumption, ease of setup, embedded execution")
    
    question_input = st.text_area(
        "🎯 Research Question / Decision Prompt",
        value=default_q,
        height=90,
        placeholder="e.g. Compare Option A vs Option B for my specific use case..."
    )
    
    priorities_input = st.text_input(
        "⚙️ Key Evaluation Criteria (comma-separated)",
        value=default_p,
        placeholder="e.g. Speed, Cost, Memory, Security, Ease of maintenance"
    )
    
    # Dynamic Criteria Weight Configuration
    parsed_criteria_list = parse_criteria(priorities_input)
    st.markdown("##### 🧮 Criteria Weight Configuration (1 = Low, 5 = Critical)")
    
    weight_cols = st.columns(min(len(parsed_criteria_list), 4))
    user_weights = {}
    for idx, crit in enumerate(parsed_criteria_list):
        col_target = weight_cols[idx % len(weight_cols)]
        user_weights[crit] = col_target.slider(
            f"Weight: {crit[:18]}",
            min_value=1,
            max_value=5,
            value=4 if "speed" in crit.lower() or "performance" in crit.lower() else 3,
            key=f"w_slider_{idx}"
        )
    
    submit_button = st.form_submit_button("🚀 Run Evidence Research & Transparent Scoring", use_container_width=True)

# Processing Execution
if submit_button:
    if not question_input.strip():
        st.error("Please enter a research question or decision prompt to analyze.")
    elif not active_serpapi_key:
        st.error("SerpApi API Key is missing. Please set SERPAPI_API_KEY in .env or sidebar.")
    elif not active_gemini_key:
        st.error("Gemini API Key is missing. Please set GEMINI_API_KEY in .env or sidebar.")
    else:
        with st.status("🔍 Executing Evidence Research & Scoring...", expanded=True) as status:
            # Step 1: Execute Live SerpApi Web Search
            st.write(f"📡 Querying SerpApi live index (`{search_engine}`)...")
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
                st.write(f"✓ Retrieved **{len(organic_results)}** live search results from SerpApi.")
                
                # Step 2: Synthesize Evidence & Generate Report with Gemini
                st.write(f"🧠 Computing weighted decision matrix & report with Gemini (`{llm_model}`)...")
                report_response = generate_decision_report(
                    question=question_input,
                    priorities_input=priorities_input,
                    organic_results=organic_results,
                    criteria_weights=user_weights,
                    model_name=llm_model,
                    api_key=active_gemini_key
                )
                
                if not report_response["success"]:
                    status.update(label="❌ Decision Analysis Failed", state="error", expanded=True)
                    st.error(report_response["error"])
                else:
                    status.update(label="✅ Evidence Analysis & Scoring Complete!", state="complete", expanded=False)
                    
                    st.session_state["last_report"] = report_response["report"]
                    st.session_state["last_matrix"] = report_response.get("matrix_md", "")
                    st.session_state["last_sources"] = organic_results
                    st.session_state["last_model"] = report_response.get("model_used", llm_model)
                    st.session_state["last_evaluations"] = report_response.get("evaluations", {})
                    st.session_state["last_weights"] = user_weights

# Results Display
if "last_report" in st.session_state:
    report_text = st.session_state["last_report"]
    matrix_md = st.session_state.get("last_matrix", "")
    sources = st.session_state.get("last_sources", [])
    used_model = st.session_state.get("last_model", llm_model)
    evaluations = st.session_state.get("last_evaluations", {})
    weights = st.session_state.get("last_weights", {})
    
    st.markdown("---")
    
    # Top Metrics Bar
    mcol1, mcol2, mcol3 = st.columns(3)
    with mcol1:
        st.markdown(f"""
        <div class="metric-box">
            <span style="font-size:0.85rem; color:#94a3b8;">LIVE SEARCH SOURCES</span>
            <h3 style="margin:0; color:#38bdf8;">{len(sources)} Organic Results</h3>
        </div>
        """, unsafe_allow_html=True)
    with mcol2:
        st.markdown(f"""
        <div class="metric-box">
            <span style="font-size:0.85rem; color:#94a3b8;">SCORING ENGINE</span>
            <h3 style="margin:0; color:#a78bfa;">Weighted Matrix (1-5)</h3>
        </div>
        """, unsafe_allow_html=True)
    with mcol3:
        st.markdown(f"""
        <div class="metric-box">
            <span style="font-size:0.85rem; color:#94a3b8;">GEMINI AI MODEL</span>
            <h3 style="margin:0; color:#34d399;">{used_model}</h3>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Structured Tabs View
    tab_summary, tab_matrix, tab_sources, tab_export = st.tabs([
        "🏆 Executive Recommendation & Analysis", 
        "📊 Transparent Decision Matrix", 
        "🔗 Verified Sources & Evidence", 
        "📥 Report Export & Markdown"
    ])
    
    with tab_summary:
        st.markdown(report_text, unsafe_allow_html=True)
        
    with tab_matrix:
        st.markdown("### 🧮 Weighted Decision Matrix & Criterion Scores")
        if matrix_md:
            st.markdown(matrix_md, unsafe_allow_html=True)
        else:
            # Render fallback matrix from saved evaluations
            fallback_matrix = format_decision_matrix_markdown(evaluations, weights)
            st.markdown(fallback_matrix, unsafe_allow_html=True)
            
        st.info("💡 **Scoring Methodology**: Overall scores are normalized (1.0–5.0) by taking the weighted sum of criterion scores divided by total criteria weights. Criteria ratings reflect LLM-assisted evidence extraction from live SerpApi search snippets.")

    with tab_sources:
        st.markdown("### 📚 Grounded Search Evidence (SerpApi)")
        st.caption("All factual claims and recommendations above are grounded strictly in the following live organic web search results:")
        
        for idx, src in enumerate(sources, start=1):
            st.markdown(f"""
            <div class="source-card">
                <span style="color:#94a3b8; font-weight:600; font-size:0.85rem;">
                    [SOURCE {idx}] &bull; {src.get('source', '')} &bull; 
                    <span style="color:#34d399;">Snippet Evidence Scope</span>
                </span><br>
                <a href="{src.get('link')}" target="_blank" class="source-title">{src.get('title')}</a>
                <p style="margin-top:0.4rem; margin-bottom:0; color:#cbd5e1; font-size:0.92rem;">{src.get('snippet')}</p>
            </div>
            """, unsafe_allow_html=True)
            
    with tab_export:
        st.markdown("### 📥 Export Full Research Report")
        
        full_export_text = f"{report_text}\n\n---\n\n## 🧮 Weighted Decision Matrix\n\n{matrix_md}\n"
        st.text_area("Markdown Report Content", value=full_export_text, height=350)
        
        st.download_button(
            label="💾 Download Decision Report (.md)",
            data=full_export_text,
            file_name="ResearchPilot_Decision_Report.md",
            mime="text/markdown"
        )
