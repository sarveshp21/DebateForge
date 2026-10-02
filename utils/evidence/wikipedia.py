import json
import ssl
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi


WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"


def fetch_topic_evidence(topic, limit=3):
    query = urlencode({
        "action": "query",
        "generator": "search",
        "gsrsearch": topic,
        "gsrnamespace": 0,
        "gsrlimit": limit,
        "prop": "extracts|info",
        "exintro": 1,
        "explaintext": 1,
        "exsentences": 4,
        "inprop": "url",
        "format": "json",
        "formatversion": 2,
    })
    request = Request(
        f"{WIKIPEDIA_API}?{query}",
        headers={"User-Agent": "AIMultiAgentDebateSystem/1.0 (evidence retrieval)"},
    )

    try:
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        with urlopen(request, timeout=10, context=ssl_context) as response:
            payload = json.load(response)
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Could not retrieve topic evidence from Wikipedia: {error}") from error

    pages = payload.get("query", {}).get("pages", [])
    evidence = []
    for page in pages:
        excerpt = page.get("extract", "").strip()
        url = page.get("fullurl", "").strip()
        if not excerpt or not url:
            continue
        evidence.append({
            "id": f"S{len(evidence) + 1}",
            "title": page.get("title", "Wikipedia article"),
            "url": url,
            "excerpt": excerpt,
        })

    if not evidence:
        raise RuntimeError("No relevant Wikipedia evidence was found for this topic.")
    return evidence