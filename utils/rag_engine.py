import os
import re
from collections import defaultdict

# ---------------------------------------------------------------------------
# CHUNKING
# ---------------------------------------------------------------------------

def _chunk_text(text: str, chunk_size: int = 400, overlap: int = 80) -> list[str]:
    """Dzieli tekst na nakładające się chunki."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks = []
    current = []
    current_len = 0

    for sent in sentences:
        words = sent.split()
        if current_len + len(words) > chunk_size and current:
            chunks.append(' '.join(current))
            # overlap: zostaw ostatnie N słów
            overlap_words = current[-overlap:] if len(current) > overlap else current
            current = overlap_words[:]
            current_len = len(current)
        current.extend(words)
        current_len += len(words)

    if current:
        chunks.append(' '.join(current))

    return chunks


# ---------------------------------------------------------------------------
# SCORING – dopasowanie słów kluczowych
# ---------------------------------------------------------------------------

def _score_chunk(chunk: str, query_tokens: list[str]) -> float:
    """
    Ocenia chunk na podstawie liczby dopasowanych tokenów z zapytania.
    Premiuje dokładne frazy i wielokrotne trafienia.
    """
    chunk_lower = chunk.lower()
    score = 0.0

    # Bonus za pełną frazę
    full_query = ' '.join(query_tokens)
    if full_query in chunk_lower:
        score += 10.0

    # Punkty za każdy token
    for token in query_tokens:
        if len(token) < 3:
            continue
        count = chunk_lower.count(token)
        if count > 0:
            score += count * (1.0 + len(token) * 0.05)  # dłuższe słowa = wyższy score

    return score


# ---------------------------------------------------------------------------
# TOKENIZACJA ZAPYTANIA
# ---------------------------------------------------------------------------

_PL_STOPWORDS = {
    'jak','czy','co','sie','jest','dla','nie','tak','ale','lub','oraz',
    'przez','przy','jako','tego','tej','które','który','będzie','mają',
    'więc','tylko','już','jeszcze','każdy','wiele','tutaj','teraz',
}

def _tokenize_query(query: str) -> list[str]:
    tokens = re.findall(r'\b[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]{3,}\b', query.lower())
    return [t for t in tokens if t not in _PL_STOPWORDS]


# ---------------------------------------------------------------------------
# GŁÓWNA FUNKCJA
# ---------------------------------------------------------------------------

def search_knowledge(
    query: str,
    data_folder: str = "data",
    top_k: int = 4,
    min_score: float = 0.5,
) -> str:
    """
    Przeszukuje pliki .txt w folderze 'data' metodą chunk-based keyword scoring.
    Zwraca top_k najlepiej dopasowanych fragmentów jako kontekst dla LLM.
    """
    if not os.path.exists(data_folder):
        return "Brak folderu z bazą wiedzy (data/)."

    query_tokens = _tokenize_query(query)
    if not query_tokens:
        return "Zapytanie zbyt krótkie do przeszukania bazy wiedzy."

    all_scored = []  # (score, filename, chunk)

    for filename in os.listdir(data_folder):
        if not filename.endswith('.txt'):
            continue
        file_path = os.path.join(data_folder, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            continue

        chunks = _chunk_text(content)
        for chunk in chunks:
            score = _score_chunk(chunk, query_tokens)
            if score >= min_score:
                all_scored.append((score, filename, chunk))

    if not all_scored:
        return "Brak dopasowań w bazie wiedzy dla tej frazy."

    # Sortuj malejąco, deduplikuj po pliku (max 2 chunki z jednego pliku)
    all_scored.sort(key=lambda x: x[0], reverse=True)
    file_counts = defaultdict(int)
    top_results = []
    for score, fname, chunk in all_scored:
        if file_counts[fname] < 2:
            top_results.append((score, fname, chunk))
            file_counts[fname] += 1
        if len(top_results) >= top_k:
            break

    # Formatuj wynik
    parts = []
    for score, fname, chunk in top_results:
        parts.append(
            f"[Źródło: {fname} | trafność: {score:.1f}]\n{chunk.strip()}"
        )

    return "\n\n---\n\n".join(parts)
