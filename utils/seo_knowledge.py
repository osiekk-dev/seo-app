SEO_KNOWLEDGE = {
    "frazy_kluczowe": """
- KLASTRYZACJA: Twórz silosy tematyczne (Artykuł główny/Pillar Page + Artykuły wspierające).
- ZASADA 1 ARTYKUŁU: Łącz frazy o identycznej intencji w jeden materiał.
- KANIBALIZACJA: Unikaj tworzenia wielu artykułów na tę samą frazę.
- SELEKCJA: Dopasowuj frazy do etapu lejka (Brandowe, Zasięgowe, Informacyjne, Produktowe).
""",
    "linki_wewnetrzne": """
- HIERARCHIA: Strona główna/kategorie (dużo linków), Artykuły (mało linków).
- ANCHORY: Używaj Exact Match (EMA) dla klastrów. Unikaj "kliknij tutaj".
- ZASADA 3 KLIKNIĘĆ: Każdy artykuł dostępny w max 3 kliknięciach od strony głównej.
- LINKOWANIE W TREŚCI: Artykuły wspierające muszą prowadzić do Pillar Page.
""",
    "tworzenie_tresci": """
- STRUKTURA: H1 (fraza główna + korzyść), H2/H3 (pytania longtail).
- LEAD: Pierwsze zdanie zawiera frazę główną + lista punktowana (podsumowanie).
- SEMANTYKA: Używaj fraz LSI i synonimów (matematyka, nie emocje).
- OPTYMALIZACJA: Krótkie akapity, listy punktowane, pogrubienia STRONG (max 1 na akapit).
"""
}

def get_combined_knowledge() -> str:
    return "\n".join([f"MODUŁ {k.upper()}:\n{v}" for k, v in SEO_KNOWLEDGE.items()])
