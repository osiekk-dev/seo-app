"""
dataforseo_research.py
Moduł do pobierania danych SEO z DataForSEO API:
- PAA (People Also Ask)
- People Also Search
- Related Searches
- Featured Snippet
- Top 10 organicznych tytułów
"""

import logging
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

DFS_ENDPOINT = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"


def _call_api(login: str, password: str, payload: list) -> dict | None:
    try:
        resp = requests.post(
            DFS_ENDPOINT,
            auth=HTTPBasicAuth(login, password),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status_code") != 20000:
            logger.error(f"DataForSEO błąd: {data.get('status_message')}")
            return None
        tasks = data.get("tasks", [])
        if not tasks or tasks[0].get("status_code") != 20000:
            logger.error(
                f"Task błąd: {tasks[0].get('status_message') if tasks else 'brak taskow'}"
            )
            return None
        results = tasks[0].get("result", [])
        if not results:
            return None
        return results[0]
    except requests.exceptions.RequestException as e:
        logger.error(f"Błąd połączenia DataForSEO: {e}")
        return None
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd: {e}")
        return None


def _extract_paa(items: list) -> list[str]:
    """Wyciąga pytania People Also Ask."""
    questions = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "people_also_ask":
            continue
        for el in item.get("items") or []:
            if isinstance(el, dict):
                q = (el.get("title") or "").strip()
                if q and q not in questions:
                    questions.append(q)
    return questions


def _extract_people_also_search(items: list) -> list[str]:
    """Wyciąga frazy People Also Search (osobny moduł od Related Searches)."""
    results = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "people_also_search":
            continue
        for sub in item.get("items") or []:
            if isinstance(sub, dict):
                phrase = (sub.get("title") or sub.get("query") or "").strip()
            elif isinstance(sub, str):
                phrase = sub.strip()
            else:
                continue
            if phrase and phrase not in results:
                results.append(phrase)
    return results


def _extract_related_searches(items: list) -> list[str]:
    """Wyciąga Related Searches (tylko typ related_searches)."""
    related = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "related_searches":
            continue
        for sub in item.get("items") or []:
            if isinstance(sub, dict):
                phrase = (sub.get("title") or sub.get("query") or "").strip()
            elif isinstance(sub, str):
                phrase = sub.strip()
            else:
                continue
            if phrase and phrase not in related:
                related.append(phrase)
    return related


def _extract_featured_snippet(items: list) -> str:
    """Wyciąga tekst Featured Snippet."""
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "featured_snippet":
            desc = (item.get("description") or item.get("text") or "").strip()
            if desc:
                return desc
    return ""


def _extract_top_organic(items: list, limit: int = 10) -> list[str]:
    """Wyciąga tytuły top organicznych wyników."""
    titles = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "organic":
            title = (item.get("title") or "").strip()
            if title:
                titles.append(title)
            if len(titles) >= limit:
                break
    return titles


def fetch_serp_research(
    keyword: str,
    login: str,
    password: str,
    location_code: int = 2616,
    language_code: str = "pl",
    device: str = "mobile",
    depth: int = 30,
) -> dict:
    """
    Główna funkcja — pobiera dane SERP dla frazy i zwraca słownik:
    {
        'paa': [...],               # People Also Ask
        'people_also_search': [...], # People Also Search
        'related': [...],            # Related Searches
        'featured_snippet': '',      # Featured Snippet
        'top_titles': [...],         # Top 10 organicznych
        'keyword': '...',
        'error': None lub str
    }
    """
    payload = [
        {
            "keyword": keyword,
            "location_code": location_code,
            "language_code": language_code,
            "device": device,
            "depth": depth,
            "calculate_rectangles": False,
        }
    ]

    result = _call_api(login, password, payload)

    if result is None:
        return {
            "paa": [],
            "people_also_search": [],
            "related": [],
            "featured_snippet": "",
            "top_titles": [],
            "keyword": keyword,
            "error": "Nie udało się pobrać danych z DataForSEO. Sprawdź kredencjale i połączenie.",
        }

    items = result.get("items") or []

    return {
        "paa": _extract_paa(items),
        "people_also_search": _extract_people_also_search(items),
        "related": _extract_related_searches(items),
        "featured_snippet": _extract_featured_snippet(items),
        "top_titles": _extract_top_organic(items),
        "keyword": keyword,
        "error": None,
    }
