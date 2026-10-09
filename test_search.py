
import os
from dotenv import load_dotenv
from serpapi_search_tools import web_search

load_dotenv()

if not os.getenv("SERPAPI_API_KEY"):
    raise ValueError(
        "SERPAPI_API_KEY is missing. Check your .env file."
    )

search = web_search(provider="function")

results = search(
    query="official Python 3.13 documentation",
    engine="google_light",
)

print("SerpApi search completed!")
print(results)
