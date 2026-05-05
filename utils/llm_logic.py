import streamlit as st
from anthropic import Anthropic
from utils.seo_knowledge import get_combined_knowledge
from utils.rag_engine import search_knowledge
from utils.cannibalization import find_pillar_page
from utils.seo_tools import calculate_average_length


def generate_content_final(
    keyword: str,
    competitor_data: str,
    grammar_forms: list,
    raw_facts: str,
    google_sug: str,
    selected_lsi: list,
    manual_lsi: str,
    heading_keywords: str,
    brand_name: str = "",
    num_competitor_files: int = 1,
    internal_report_content=None,
    competitor_insights: dict | None = None,
) -> str:

    client = Anthropic(api_key=st.secrets["anthropic"]["api_key"])

    # --- Zaczytaj całą bazę wiedzy ---
    knowledge = get_combined_knowledge()

    # --- RAG: osobne zapytania dla różnych aspektów ---
    context_topic = search_knowledge(keyword)
    context_style = search_knowledge("zasady pisania styl naturalność copywriting")
    context_seo = search_knowledge("SEO nagłówki słowa kluczowe optymalizacja")
    context_eeat = search_knowledge(
        "E-E-A-T autorytet ekspert wiarygodność doświadczenie"
    )

    # Złącz konteksty, usuń duplikaty "brak dopasowań"
    def _clean(ctx):
        return ctx if "Brak" not in ctx and "zbyt krótkie" not in ctx else ""

    rag_context = "\n\n".join(
        filter(
            None,
            [
                _clean(context_topic),
                _clean(context_style),
                _clean(context_seo),
                _clean(context_eeat),
            ],
        )
    )

    pillar = find_pillar_page(keyword, internal_report_content)

    # Długość — z insights lub fallback
    if competitor_insights and competitor_insights.get("average_words"):
        avg_words = competitor_insights["average_words"]
    else:
        avg_words = calculate_average_length(
            competitor_data, num_files=num_competitor_files
        )

    # Dane z analizy konkurencji
    competitor_h2_str = ""
    competitor_q_str = ""
    if competitor_insights:
        if competitor_insights.get("top_headings"):
            competitor_h2_str = "\n".join(
                f"- {h}" for h in competitor_insights["top_headings"][:10]
            )
        if competitor_insights.get("questions"):
            competitor_q_str = "\n".join(
                f"- {q}" for q in competitor_insights["questions"][:10]
            )

    forms_str = ", ".join(grammar_forms) if grammar_forms else keyword

    # LSI
    lsi_combined = list(selected_lsi)
    if manual_lsi:
        lsi_combined += [w.strip() for w in manual_lsi.splitlines() if w.strip()]
    lsi_str = ", ".join(lsi_combined) if lsi_combined else "brak"

    # Pillar page
    pillar_block = ""
    if pillar:
        pillar_block = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PILLAR PAGE / LINK WEWNĘTRZNY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Wykryto artykuł nadrzędny: "{pillar['title']}" ({pillar['url']})
→ W leadzie OBOWIĄZKOWO umieść link wewnętrzny do: {pillar['url']} (anchor: Exact Match frazy głównej)
→ Skup się na szczegółach — ogólne tematy zostaw Pillar Page
"""

    # Marka
    brand_block = ""
    if brand_name:
        brand_block = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GŁOS MARKI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Firma/ekspert w artykule = wyłącznie: „{brand_name}"
ZAKAZ wymieniania jakichkolwiek innych firm, marek, serwisów, szkół.
Dane konkurencji = tylko wzorzec długości i struktury. NIGDY nie parafrazuj ich treści.
"""

    system_prompt = f"""Jesteś ekspertem SEO i copywriterem najwyższej klasy. Piszesz artykuły, które:
1. Zajmują TOP 3 w Google dzięki perfekcyjnemu dopasowaniu do intencji wyszukiwania
2. Spełniają standardy E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness)
3. Są w 100% oryginalne, pisane eksperckim głosem marki
4. Naturalnie zawierają frazy kluczowe bez upychania

{pillar_block}
{brand_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BAZA WIEDZY SEO (zasady stałe)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{knowledge}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WIEDZA EKSPERTA Z BAZY DANYCH (data/)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{rag_context if rag_context else "Brak dodatkowych materiałów w bazie — opieraj się na SEO_KNOWLEDGE i własnej wiedzy."}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INTENCJA WYSZUKIWANIA (OBOWIĄZKOWE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Przed napisaniem artykułu ZIDENTYFIKUJ intencję frazy „{keyword}":
- Informacyjna (chcę wiedzieć) → artykuł edukacyjny, dużo wyjaśnień, nagłówki pytające
- Nawigacyjna (szukam konkretnej strony) → nie dotyczy artykułu
- Transakcyjna (chcę kupić) → CTA, korzyści, ceny, trust signals
- Komercyjna (porównuję opcje) → porównania, tabele, pros/cons, recenzje

Dobierz TON, STRUKTURĘ i GŁĘBOKOŚĆ do zidentyfikowanej intencji.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ZASADY TECHNICZNE SEO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Długość: ~{avg_words} słów (±10%)
Format wyjściowy: CZYSTY MARKDOWN

H1 (jeden): zawiera frazę główną + korzyść lub kontekst
  Wzorzec: „{keyword} – [co czytelnik zyska/pozna]"

Odmiany frazy (używaj naprzemiennie, naturalnie):
  {forms_str}

LSI — OBOWIĄZKOWO każde słowo/frazę użyj min. 1x:
  {lsi_str}

Nagłówki H2/H3:
  - Oparte na pytaniach i longtailach z tematu
  - Każdy H2 = oddzielna myśl/sekcja
  - Min. 1 nagłówek z pytaniem (np. „Jak...", „Czy...", „Ile...")

Akapity:
  - Max 3-4 zdania każdy
  - Pierwsze zdanie = najważniejsza informacja (odwrócona piramida)
  - Jedno pogrubienie **STRONG** na akapit (kluczowy fakt lub fraza)

Lead (pierwsze 150 słów):
  - Fraza główna w pierwszym zdaniu
  - Lista 4-5 punktów „Z artykułu dowiesz się:"
  - BEZ „W dzisiejszych czasach" i podobnych ogólników

Zakończenie:
  - Konkretne CTA lub następny krok dla czytelnika
  - Podsumowanie w 3-4 zdaniach lub TL;DR

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MAKSYMALIZACJA SŁÓW KLUCZOWYCH (NATURALNIE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROZMIESZCZENIE FRAZY GŁÓWNEJ „{keyword}":
→ Pierwsze zdanie (exact match)
→ Jeden nagłówek H2 (exact match lub bliski wariant)
→ Co 300-400 słów w treści (odmieniona forma)
→ Ostatni akapit artykułu
→ NIGDY dwa razy w jednym akapicie

NAGŁÓWKI — maksymalne wykorzystanie LSI:
→ Min. 1 nagłówek zawiera frazę główną lub odmianę
→ Pozostałe nagłówki zawierają frazy LSI lub longtaile
→ Nagłówki muszą brzmieć naturalnie
→ Wzorzec: [fraza LSI lub pytanie] + [kontekst lub korzyść]

SŁOWA LSI — zasady wplatania:
→ Rzeczownik LSI → użyj jako podmiot lub dopełnienie zdania
→ Fraza pytająca LSI → użyj jako nagłówek H3 lub odpowiedz wprost w tekście
→ LSI z wysoką ważnością (⭐⭐⭐) → użyj w pierwszych 300 słowach

GĘSTOŚĆ:
→ Fraza główna: 1-2% całego tekstu
→ Każde LSI: min. 1x, max. 4x
→ Test naturalności: przeczytaj zdanie na głos — jeśli brzmi sztucznie, przepisz

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NATURALNOŚĆ I PŁYNNOŚĆ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
→ Każde zdanie logicznie wynika z poprzedniego
→ Zakaz zaczynania kolejnych akapitów od tego samego słowa
→ Zakaz wyliczanek tam gdzie pasuje tekst ciągły
→ Zakaz zdań: „To...", „Jest to...", „Są to..."
→ Przejścia między sekcjami — użyj zdania pomostowego
→ Nie powtarzaj tej samej informacji w różnych akapitach

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRUKTURY H2 KONKURENCJI (inspiracja — nie kopiuj)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{competitor_h2_str if competitor_h2_str else 'brak danych'}

PYTANIA Z TREŚCI KONKURENCJI (inspiracja H3/FAQ — nie kopiuj)
{competitor_q_str if competitor_q_str else 'brak danych'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ZAKAZ ABSOLUTNY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Zakaz wymieniania firm/marek/serwisów konkurencji
- Zakaz parafrazowania cudzych treści
- Zakaz ogólników: „W dzisiejszym świecie", „Coraz więcej firm", „Warto wiedzieć że"
- Zakaz fraz AI: „Zanurzmy się", „Przyjrzyjmy się", „Bez wątpienia", „Należy podkreślić"
- Zakaz superlatywów bez uzasadnienia: „najlepszy", „rewolucyjny", „wyjątkowy"
- Zakaz zdań: „To...", „Jest to...", „Są to..."
- Zakaz powtarzania tej samej myśli w różnych akapitach
"""

    user_prompt = f"""FRAZA GŁÓWNA: {keyword}

SUGESTIE GOOGLE / PAA (użyj jako bazy nagłówków H2/H3 i odpowiedzi w tekście):
{google_sug if google_sug else 'brak — bazuj na wiedzy o temacie i typowych pytaniach użytkowników'}

UNIKALNE FAKTY I DANE (OBOWIĄZKOWO uwzględnij — budują E-E-A-T):
{raw_facts if raw_facts else 'brak — opieraj się na bazie wiedzy i RAG'}

DODATKOWE WYTYCZNE DO NAGŁÓWKÓW:
{heading_keywords if heading_keywords else 'brak — dobierz samodzielnie na podstawie intencji'}

Napisz kompletny, oryginalny artykuł spełniający WSZYSTKIE powyższe wytyczne.
Pisz jak ekspert z {brand_name or 'tej branży'} który tłumaczy temat znajomemu — merytorycznie,
bez lania wody, z konkretnymi przykładami z praktyki.
Czytelnik ma po lekturze czuć że dostał realną wiedzę eksperta, a nie artykuł generowany pod SEO.

SELF-CHECK przed oddaniem artykułu:
✓ Czy fraza główna „{keyword}" jest w pierwszym zdaniu?
✓ Czy każde słowo z listy LSI użyte min. 1x?
✓ Czy żaden nagłówek nie brzmi sztucznie?
✓ Czy każdy akapit logicznie wynika z poprzedniego?
✓ Czy żaden akapit nie zaczyna się tak samo jak poprzedni?
✓ Czy zasady z bazy wiedzy (SEO_KNOWLEDGE + data/) zostały zastosowane?
Jeśli nie — popraw zanim zwrócisz wynik."""

    message = client.messages.create(
        model="claude-sonnet-4-5",
        system=system_prompt,
        max_tokens=8192,
        temperature=0.7,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text
