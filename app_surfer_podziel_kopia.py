import streamlit as st
import markdown
import pandas as pd
from utils.seo_tools import (
    get_grammar_forms,
    extract_lsi_keywords,
    extract_competitor_insights,
    calculate_average_length,
)
from utils.llm_logic import generate_content_final
from utils.ui_helpers import apply_footer
from utils.dataforseo_research import fetch_serp_research


# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="DD Serwis - Content Engine", layout="wide")
apply_footer()


# --- INICJALIZACJA SESJI ---
defaults = {
    "generated_article": "",
    "competitor_context": "",
    "internal_report_content": None,
    "selected_lsi": [],
    "manual_lsi": "",
    "competitor_insights": None,
    "research_paa": "",
    "research_facts": "",
    "research_extra_lsi": "",
    "research_done": False,
    "_pending_research_paa": None,
    "_pending_research_facts": None,
    "_pending_research_extra_lsi": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Przenieś wyniki researchu do pól widgetów przed ich utworzeniem
if st.session_state.get("_pending_research_paa") is not None:
    st.session_state["research_paa"] = st.session_state["_pending_research_paa"]
    st.session_state["_pending_research_paa"] = None
if st.session_state.get("_pending_research_facts") is not None:
    st.session_state["research_facts"] = st.session_state["_pending_research_facts"]
    st.session_state["_pending_research_facts"] = None
if st.session_state.get("_pending_research_extra_lsi") is not None:
    st.session_state["research_extra_lsi"] = st.session_state[
        "_pending_research_extra_lsi"
    ]
    st.session_state["_pending_research_extra_lsi"] = None


# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ DD Serwis Engine")
    st.divider()

    # Raporty konkurencji
    st.subheader("📂 Raporty konkurencji")
    uploaded_files = st.file_uploader(
        "Wgraj raporty (HTML)",
        type=["html", "md", "txt"],
        accept_multiple_files=True,
    )
    if uploaded_files:
        html_docs = []
        for f in uploaded_files:
            try:
                html_docs.append(f.read().decode("utf-8", errors="replace"))
            except Exception:
                st.warning(f"Nie udało się wczytać: {f.name}")

        if html_docs:
            all_text = " ".join(html_docs)
            st.session_state["competitor_context"] = all_text

            brand_blacklist_raw = st.text_area(
                "Marki do wykluczenia z LSI (nowa linia):",
                height=80,
                placeholder="np.\n3dtrip\nMatterport\n3Dvista",
            )
            brand_list = [
                b.strip() for b in brand_blacklist_raw.splitlines() if b.strip()
            ]

            insights = extract_competitor_insights(
                html_docs, brand_blacklist=brand_list
            )
            st.session_state["competitor_insights"] = insights

            st.success(f"✅ Wczytano {len(html_docs)} raport(y)")
            diag = insights["diagnostics"]
            st.caption(
                f"Słów contentu: {diag['total_content_words']:,} | "
                f"Usuniętych linii audytu: {diag['audit_lines_removed']} | "
                f"Formaty: {', '.join(set(diag['formats']))}"
            )

    st.divider()

    # Raport Internal
    st.subheader("📄 Raport Internal (opcjonalnie)")
    internal_file = st.file_uploader("Wgraj raport Internal (HTML)", type=["html"])
    if internal_file:
        st.session_state["internal_report_content"] = internal_file.getvalue()
        st.success("✅ Raport Internal wczytany!")

    st.divider()

    # Nazwa marki
    st.subheader("🏷️ Marka")
    brand_name = st.text_input("Nazwa firmy/eksperta:", placeholder="np. DD Serwis")


# --- GŁÓWNE OKNO ---
st.title("🛡️ SEO Content Engine v7.2")


tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Analiza LSI", "📝 Konfiguracja SEO", "🔍 Research Google", "✨ Generator"]
)


# ══════════════════════════════════════════
# TAB 1 — ANALIZA LSI
# ══════════════════════════════════════════
with tab1:
    if st.session_state["competitor_context"]:
        insights = st.session_state.get("competitor_insights")
        lsi_list = insights["lsi"] if insights else []

        if lsi_list:
            col_l1, col_l2 = st.columns([2, 1])

            with col_l1:
                st.subheader("🔑 Słowa kluczowe LSI z analizy konkurencji")

                options_display = [
                    f"{item['importance']} {item['word']} (×{item['count']})"
                    for item in lsi_list
                ]
                selected_display = st.multiselect(
                    "Zaznacz słowa do artykułu:",
                    options=options_display,
                    default=options_display[:15],
                )
                selected_lsi = []
                for d in selected_display:
                    for item in lsi_list:
                        label = (
                            f"{item['importance']} {item['word']} (×{item['count']})"
                        )
                        if label == d:
                            selected_lsi.append(item["word"])
                            break
                st.session_state["selected_lsi"] = selected_lsi
                st.caption(f"Wybrano: {len(selected_lsi)} fraz")

            with col_l2:
                st.subheader("✏️ Własne LSI")
                manual_lsi = st.text_area(
                    "Dodaj własne frazy (nowa linia):",
                    value=st.session_state.get("manual_lsi", ""),
                    height=300,
                    placeholder="spacer wirtualny\nfotografia 360\ngoogle street view",
                )
                st.session_state["manual_lsi"] = manual_lsi

        # Diagnostyka
        if insights:
            st.divider()
            st.subheader("🔬 Diagnostyka parsowania")
            docs = insights.get("normalized_docs", [])
            if docs:
                rows = []
                for i, doc in enumerate(docs):
                    s = doc["stats"]
                    rows.append(
                        {
                            "index": i + 1,
                            "Title": doc.get("title", f"Plik {i+1}"),
                            "Meta description": doc.get("meta_description", ""),
                            "H1": s["h1"],
                            "H2": s["h2"],
                            "H3": s["h3"],
                            "Akapity": s["paragraphs"],
                            "Listy": s["lists"],
                            "FAQ": s["faq"],
                            "Linie audytu": s["audit_lines"],
                        }
                    )
                df = pd.DataFrame(rows)
                st.dataframe(
                    df,
                    width="content",
                    column_config={
                        "Title": st.column_config.TextColumn("Title", width="large"),
                        "Meta description": st.column_config.TextColumn(
                            "Meta description", width="large"
                        ),
                    },
                )

                # Eksport CSV
                csv_bytes = df.to_csv(index=False).encode("utf-8-sig")

                # Eksport HTML
                html_table = df.to_html(index=False, border=1, classes="diag-table")
                html_export = f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<title>Diagnostyka parsowania</title>
<style>
  body {{ font-family: Arial, sans-serif; padding: 20px; color: #222; }}
  h2 {{ color: #333; }}
  .diag-table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  .diag-table th {{ background: #2c6e6f; color: white; padding: 8px 12px; text-align: left; }}
  .diag-table td {{ padding: 7px 12px; border-bottom: 1px solid #ddd; vertical-align: top; }}
  .diag-table tr:nth-child(even) {{ background: #f5f5f5; }}
  .section {{ margin-top: 32px; }}
  .section h3 {{ color: #2c6e6f; }}
  ul {{ margin: 0; padding-left: 20px; }}
  li {{ margin-bottom: 4px; }}
</style>
</head>
<body>
<h2>🔬 Diagnostyka parsowania</h2>
{html_table}
"""
                # Dodaj nagłówki jeśli są
                top_headings = insights.get("top_headings", [])
                if top_headings:
                    items_html = "".join(f"<li>{h}</li>" for h in top_headings)
                    html_export += f'<div class="section"><h3>📌 Najczęstsze nagłówki</h3><ul>{items_html}</ul></div>'

                # Dodaj pytania jeśli są
                questions = insights.get("questions", [])
                if questions:
                    items_html = "".join(f"<li>{q}</li>" for q in questions)
                    html_export += f'<div class="section"><h3>❓ Pytania znalezione w treści</h3><ul>{items_html}</ul></div>'

                html_export += "\n</body>\n</html>"

                col_exp1, col_exp2 = st.columns(2)
                with col_exp1:
                    st.download_button(
                        "📥 Pobierz CSV",
                        data=csv_bytes,
                        file_name="diagnostyka_raportu.csv",
                        mime="text/csv",
                        width="content",
                    )
                with col_exp2:
                    st.download_button(
                        "📥 Pobierz HTML",
                        data=html_export.encode("utf-8"),
                        file_name="diagnostyka_raportu.html",
                        mime="text/html",
                        width="content",
                    )
    else:
        st.info(
            "⬅️ Wgraj raporty konkurencji w panelu bocznym, aby zobaczyć analizę LSI."
        )


# ══════════════════════════════════════════
# TAB 2 — KONFIGURACJA SEO
# ══════════════════════════════════════════
with tab2:
    st.subheader("⚙️ Parametry artykułu")

    col_kw, col_loc = st.columns([3, 1])
    with col_kw:
        main_word = st.text_input(
            "🎯 Główne słowo kluczowe (lemat):",
            placeholder="np. wirtualny spacer",
        )
    with col_loc:
        heading_keywords = st.text_input(
            "📌 Słowa kluczowe do H2/H3:",
            placeholder="opcjonalnie",
        )

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        google_sug = st.text_area(
            "🔍 Sugestie Google / PAA:",
            height=200,
            key="research_paa",
            placeholder="Wpisz ręcznie lub użyj zakładki 🔍 Research Google",
        )

    with col_b:
        user_facts = st.text_area(
            "💡 Unikalne fakty i dane:",
            height=200,
            key="research_facts",
            placeholder="Lata doświadczenia, certyfikaty, liczby, case studies...",
        )

    st.divider()
    st.text_area(
        "🔎 People Also Search / Related searches:",
        height=140,
        key="research_extra_lsi",
        placeholder="Uzupełni się po researchu w zakładce 🔍 Research Google (możesz edytować).",
    )

    selected_lsi = st.session_state.get("selected_lsi", [])
    extra_lsi_raw = st.session_state.get("research_extra_lsi", "")
    extra_lsi = [w.strip() for w in extra_lsi_raw.splitlines() if w.strip()]
    all_lsi = selected_lsi + extra_lsi

    if all_lsi:
        st.caption(
            f"📎 LSI w artykule ({len(all_lsi)} fraz): {', '.join(all_lsi[:20])}{'...' if len(all_lsi) > 20 else ''}"
        )


# ══════════════════════════════════════════
# TAB 3 — RESEARCH GOOGLE (DataForSEO)
# ══════════════════════════════════════════
with tab3:
    st.subheader("🔍 Research Google via DataForSEO")
    st.caption("Pobiera PAA, Related Searches i Featured Snippet jednym kliknięciem.")

    if not main_word:
        st.warning("⬅️ Najpierw wpisz frazę główną w zakładce **📝 Konfiguracja SEO**.")
    else:
        st.info(f"Fraza: **{main_word}**")

        LOKALIZACJE = {
            "Polska (Cały kraj)": 2616,
            "Warszawa": 1011419,
            "Kraków": 1011362,
            "Wrocław": 1011508,
            "Poznań": 1011404,
            "Gdańsk": 1011308,
            "Katowice": 1011356,
            "Łódź": 1011375,
        }
        wybrana_lok = st.selectbox("Lokalizacja:", list(LOKALIZACJE.keys()))
        kod_lok = LOKALIZACJE[wybrana_lok]

        if st.button("🚀 Pobierz dane z Google", type="primary"):
            try:
                api_login = st.secrets["dataforseo"]["login"]
                api_password = st.secrets["dataforseo"]["password"]
            except KeyError:
                st.error(
                    "❌ Brak kredencjali w secrets.toml! Dodaj sekcję [dataforseo] z login i password."
                )
                st.stop()

            with st.spinner("Pobieram dane z DataForSEO..."):
                data = fetch_serp_research(
                    keyword=main_word,
                    login=api_login,
                    password=api_password,
                    location_code=kod_lok,
                )

            if data["error"]:
                st.error(f"❌ {data['error']}")
            else:
                st.success("✅ Dane pobrane!")
                st.session_state["research_done"] = True

                paa_text = "\n".join(data["paa"]) if data["paa"] else ""
                st.session_state["_pending_research_paa"] = paa_text
                st.session_state["_pending_research_facts"] = data["featured_snippet"]
                pas = data.get("people_also_search") or []
                rel = data.get("related") or []
                combined = []
                for x in list(pas) + list(rel):
                    if x and x not in combined:
                        combined.append(x)
                related_text = "\n".join(combined) if combined else ""
                st.session_state["_pending_research_extra_lsi"] = related_text
                st.rerun()

                col_r1, col_r2 = st.columns(2)

                with col_r1:
                    st.markdown("#### ❓ People Also Ask")
                    if data["paa"]:
                        for q in data["paa"]:
                            st.markdown(f"- {q}")
                    else:
                        st.caption("Brak PAA dla tej frazy.")

                    st.markdown("#### 🔗 Related Searches")
                    if data["related"]:
                        for r in data["related"]:
                            st.markdown(f"- {r}")
                    else:
                        st.caption("Brak related searches.")

                with col_r2:
                    st.markdown("#### ⭐ Featured Snippet")
                    if data["featured_snippet"]:
                        st.info(data["featured_snippet"])
                    else:
                        st.caption("Brak featured snippet dla tej frazy.")

                    st.markdown("#### 📋 Top 10 organicznych — tytuły")
                    if data["top_titles"]:
                        for i, t in enumerate(data["top_titles"], 1):
                            st.markdown(f"{i}. {t}")
                    else:
                        st.caption("Brak wyników organicznych.")

                st.success(
                    "✅ Dane auto-uzupełnione w zakładce **📝 Konfiguracja SEO** — możesz je edytować przed generowaniem!"
                )

        elif st.session_state.get("research_done"):
            st.success(
                "✅ Dane z poprzedniego researchu są już wczytane w zakładce Konfiguracja SEO."
            )


# ══════════════════════════════════════════
# TAB 4 — GENERATOR
# ══════════════════════════════════════════
with tab4:
    st.subheader("✨ Generator artykułu")

    insights = st.session_state.get("competitor_insights")
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        st.metric("Fraza główna", main_word or "—")
    with col_s2:
        st.metric("LSI fraz", len(st.session_state.get("selected_lsi", [])))
    with col_s3:
        avg_w = insights["average_words"] if insights else "—"
        st.metric("Cel. długość (słów)", avg_w)
    with col_s4:
        st.metric(
            "Research Google", "✅" if st.session_state.get("research_done") else "❌"
        )

    st.divider()

    if st.button("🚀 GENERUJ ARTYKUŁ", type="primary", width="content"):
        if not main_word:
            st.error("❌ Wpisz frazę główną w zakładce Konfiguracja SEO!")
        elif not st.session_state.get("competitor_context"):
            st.warning(
                "⚠️ Brak raportów konkurencji — artykuł zostanie wygenerowany bez analizy konkurencji."
            )
            odmiany = get_grammar_forms(main_word)
            with st.spinner("Claude buduje artykuł... (~30-60 sek.)"):
                try:
                    st.session_state["generated_article"] = generate_content_final(
                        keyword=main_word,
                        competitor_data="",
                        grammar_forms=odmiany,
                        raw_facts=user_facts,
                        google_sug=google_sug,
                        selected_lsi=st.session_state.get("selected_lsi", []),
                        manual_lsi=st.session_state.get("manual_lsi", ""),
                        heading_keywords=heading_keywords,
                        brand_name=brand_name,
                        competitor_insights=None,
                    )
                except Exception as e:
                    st.error(f"❌ Błąd generowania: {e}")
        else:
            odmiany = get_grammar_forms(main_word)
            with st.spinner("Claude buduje artykuł... (~30-60 sek.)"):
                try:
                    st.session_state["generated_article"] = generate_content_final(
                        keyword=main_word,
                        competitor_data=st.session_state["competitor_context"],
                        grammar_forms=odmiany,
                        raw_facts=user_facts,
                        google_sug=google_sug,
                        selected_lsi=st.session_state.get("selected_lsi", []),
                        manual_lsi=st.session_state.get("manual_lsi", ""),
                        heading_keywords=heading_keywords,
                        brand_name=brand_name,
                        num_competitor_files=(
                            len(uploaded_files) if uploaded_files else 1
                        ),
                        competitor_insights=insights,
                    )
                except Exception as e:
                    st.error(f"❌ Błąd generowania: {e}")

    if st.session_state["generated_article"]:
        st.divider()
        st.markdown("### 📄 Wygenerowany artykuł")

        col_view, col_raw = st.columns([3, 1])
        with col_view:
            st.markdown(st.session_state["generated_article"])
        with col_raw:
            st.text_area(
                "Raw Markdown:",
                value=st.session_state["generated_article"],
                height=400,
            )
            safe_filename = (main_word or "artykul").replace(" ", "_").strip()
            html_export = f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{main_word}</title>
<style>
  body {{ font-family: Georgia, serif; max-width: 860px; margin: 40px auto; padding: 0 20px; line-height: 1.7; color: #222; }}
  h1 {{ font-size: 2em; }} h2 {{ font-size: 1.5em; margin-top: 2em; }} h3 {{ font-size: 1.2em; }}
  p {{ margin-bottom: 1em; }} ul, ol {{ margin-bottom: 1em; }} li {{ margin-bottom: 0.4em; }}
  strong {{ color: #111; }}
</style>
</head>
<body>
{markdown.markdown(st.session_state['generated_article'])}
</body>
</html>"""
            st.download_button(
                "📥 Pobierz HTML",
                data=html_export.encode("utf-8"),
                file_name=f"{safe_filename}.html",
                mime="text/html",
            )
            st.download_button(
                "📥 Pobierz Markdown",
                data=st.session_state["generated_article"].encode("utf-8"),
                file_name=f"{safe_filename}.md",
                mime="text/markdown",
            )
