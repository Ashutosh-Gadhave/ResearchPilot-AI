import os
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()

logger = logging.getLogger(__name__)

def format_search_context(organic_results: List[Dict[str, Any]]) -> str:
    """Formats raw search results into structured text for Gemini grounding."""
    if not organic_results:
        return "No web search results available."
    
    formatted_sources = []
    for idx, item in enumerate(organic_results, start=1):
        formatted_sources.append(
            f"[Source {idx}]\n"
            f"Title: {item.get('title', 'N/A')}\n"
            f"URL: {item.get('link', 'N/A')}\n"
            f"Snippet: {item.get('snippet', 'N/A')}\n"
        )
    return "\n---\n".join(formatted_sources)

def generate_decision_report(
    question: str,
    priorities: str,
    organic_results: List[Dict[str, Any]],
    model_name: str = "gemini-2.5-flash",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyzes search evidence using Gemini LLM and generates a grounded decision report.
    Includes retry logic and model fallback for high availability.
    """
    import time
    
    if api_key is None:
        api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return {
            "success": False,
            "error": "GEMINI_API_KEY is missing. Please set it in your .env file or sidebar.",
            "report": ""
        }

    if not organic_results:
        return {
            "success": False,
            "error": "Cannot generate analysis without search results. Please run web search first.",
            "report": ""
        }

    search_context = format_search_context(organic_results)

    prompt = f"""You are **ResearchPilot AI**, an elite evidence-based decision agent created for SerpApi India Hackathon 2026.
Your role is to help users make high-stakes technical and strategic decisions based strictly on web search evidence.

### User Request
- **Research Question / Decision Prompt**: {question}
- **User Priorities & Evaluation Criteria**: {priorities if priorities.strip() else "Balanced performance, cost, durability, reliability, and ease of implementation"}

### Retrieved Web Search Evidence (SerpApi)
{search_context}

---

### Instructions & Grounding Guidelines
1. **Analyze Evidence**: Evaluate the options and options presented in the search results against the user's specific priorities.
2. **Grounded Source Citations**: Whenever you state facts, benchmark data, pricing, or claims, cite the exact source using markdown links, e.g., `[Source Title](URL)` or `[Source N](URL)`.
3. **Structured Response Required**: Produce your report in clean GitHub-Flavored Markdown with the following section headers:

# 🏆 Recommendation Summary
- State the recommended top choice clearly.
- Provide 2-3 sentence core rationale explaining why it best matches the user's stated priorities.

# 📊 Options Comparison Matrix
Create a markdown table comparing the main candidate options against key criteria (e.g. Performance, Cost, Ecosystem, Complexity, Priority Alignment).

| Option / Candidate | Pros | Cons | Priority Alignment | Grounded Evidence |
| :--- | :--- | :--- | :--- | :--- |
| ... | ... | ... | ... | [Source](URL) |

# 🔍 Detailed Analysis & Trade-Offs
- Deep dive into competing options.
- Discuss major trade-offs (e.g., speed vs cost, flexibility vs maintenance).
- Highlight key findings grounded in the search snippets.

# ⚠️ Uncertainties & Risks
- Highlight missing details, conflicting information, or potential risks in the available evidence.
- Note any assumptions that require verification before final decision.

# 📚 Cited Sources & Evidence
List the primary referenced sources with their titles and full clickable URLs.
"""

    candidate_models = [model_name]
    for fallback in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
        if fallback not in candidate_models:
            candidate_models.append(fallback)

    client = genai.Client(api_key=api_key)
    last_error = None

    for current_model in candidate_models:
        for attempt in range(2):  # Try twice per model
            try:
                logger.info(f"Generating decision report with {current_model} (attempt {attempt+1})")
                response = client.models.generate_content(
                    model=current_model,
                    contents=prompt
                )
                
                report_text = response.text if response.text else "No report generated."

                return {
                    "success": True,
                    "error": None,
                    "report": report_text,
                    "model_used": current_model
                }

            except errors.APIError as e:
                last_error = str(e)
                logger.warning(f"Gemini API Error on {current_model} (attempt {attempt+1}): {e}")
                time.sleep(1)  # Brief pause before retry or fallback
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Error on {current_model}: {e}")
                time.sleep(1)

    return {
        "success": False,
        "error": f"Gemini API call failed across models: {last_error}",
        "report": ""
    }

