import sqlite3
import os
import re
import math
import streamlit as st
from collections import Counter
from bs4 import BeautifulSoup

@st.cache_resource
def get_db_conn():
    if not os.path.exists('gramatyka.db'):
        return None
    return sqlite3.connect('gramatyka.db', check_same_thread=False)


def get_grammar_forms(word: str) -> list[str]:
    conn = get_db_conn()
    if conn is None:
        return [word]
    search = word.lower().strip()
    res = conn.execute("SELECT DISTINCT forma FROM slowa WHERE lemat=?", (search,)).fetchall()
    return [r[0] for r in res] if res else [search]


PL_STOPWORDS = {
    'jest','oraz','które','przez','tylko','tego','tej','tych','tym','się','nie','jak','jako','więc','ale','lecz','przy',
    'jego','jej','ich','być','można','będzie','zostać','mają','mieć','która','który','którzy','było','były','będą','sobie',
    'kiedy','gdzie','każdy','wiele','wszystko','jeden','dwa','trzy','cztery','pięć','bardzo','jeszcze','jednak','właśnie',
    'teraz','tutaj','żeby','aby','jeśli','chociaż','dlatego','ponieważ','więcej','mniej','span','style','color','font',
    'margin','weight','padding','width','height','background','border','class','href','html','body','head','nbsp','div',
    'table','tbody','thead','rgba','sans','serif','none','true','false','null','undefined','return','function','const',
    'else','display','block','inline','flex','grid','auto','solid','normal','menu','strona','stronie','kontakt','oferta',
    'oferty','czytaj','dalej','kliknij','tutaj','pobierz','zapisz','dodaj','koszyk','sklep','home','about','blog',
    'news','search','login','logout','register','cookie','polityka','prywatnosci','regulamin','rodo','zgoda','akceptuj',
    'nasz','nasze','naszej','naszych','nasza','twój','twoja','twoje','tamten','tamta','inne','inny','różne','różny',
    'każde','roku','lata','lecie','dniu','dnia','razie','celu','cenie','zakresie','ramach','skutek','przypadku',
    'będzie','można','należy','warto','trzeba','należy','więcej','mniej','każdy','między','przed','przez','ponad',
    'poniżej','podczas','dzięki','według','wobec','oprócz','spośród','zamiast',
}

NOISE_SELECTORS = ['script','style','header','footer','nav','aside','noscript','form','button','svg','iframe']
CONTENT_SELECTORS = [
    'article','main','[role="main"]','.content','.entry-content','.post-content',
    '.article-content','.article','.post','.single-post','.page-content','.wysiwyg','.text-content'
]


def _clean(text: str) -> str:
    return re.sub(r'\s+', ' ', text or '').strip()


def _looks_like_brand(word: str) -> bool:
    if '.' in word or '/' in word or 'www' in word.lower():
        return True
    if word.isupper() and len(word) > 4:
        return True
    return False


def _is_custom_report_format(soup: BeautifulSoup) -> bool:
    """Sprawdza czy plik to raport z tagami [H2], [P], [LI] itd."""
    div = soup.find('div', style=lambda s: s and 'pre-wrap' in s)
    if not div:
        return False
    sample = div.get_text()[:500]
    return bool(re.search(r'\[(H[123]|P|LI|IMG|STRONG)\]', sample))


def _parse_custom_format(soup: BeautifulSoup) -> dict:
    """Parser dla formatu raportów z tagami [H2], [P], [LI] itd."""
    title = ''
    meta_description = ''
    headings = {'h1': [], 'h2': [], 'h3': []}
    body_paragraphs = []
    list_items = []
    faq = []
    link_texts = []
    image_alts = []
    audit_labels = []

    # Title i meta z góry dokumentu
    if soup.title:
        raw_title = soup.title.get_text(strip=True)
        title = re.sub(r'^Raport\s*[—\-]\s*', '', raw_title).strip()

    for p in soup.find_all('p'):
        text = p.get_text(' ', strip=True)
        if re.search(r'^Description\s*[:\-]', text, re.I):
            meta_description = re.sub(r'^Description\s*[:\-]\s*', '', text, flags=re.I).strip()
        elif re.search(r'brakuj', text, re.I) or 'ALT' in text:
            audit_labels.append(text)

    # Główny div z treścią
    div = soup.find('div', style=lambda s: s and 'pre-wrap' in s)
    if not div:
        return None

    # Kluczowe: zamień <br> na \n zanim wywołamy get_text
    for br in div.find_all('br'):
        br.replace_with('\n')

    raw_lines = [l.strip() for l in div.get_text(separator='').split('\n') if l.strip()]

    for line in raw_lines:
        # Czyść URL-e z linii
        clean_line = re.sub(r'https?://[^\s\)\]]+', '', line).strip()
        clean_line = re.sub(r'\s+', ' ', clean_line).strip()

        if re.match(r'^\[H1\]', line):
            text = re.sub(r'^\[H1\]\s*', '', clean_line).strip()
            if text: headings['h1'].append(text)

        elif re.match(r'^\[H2\]', line):
            text = re.sub(r'^\[H2\]\s*', '', clean_line).strip()
            if text: headings['h2'].append(text)

        elif re.match(r'^\[H3\]', line):
            text = re.sub(r'^\[H3\]\s*', '', clean_line).strip()
            if text: headings['h3'].append(text)

        elif re.match(r'^\[P\]', line):
            text = re.sub(r'^\[P\]\s*', '', clean_line).strip()
            # Usuń osadzone [IMG] z akapitu
            text = re.sub(r'\[IMG\]\s*Alt:[^\[]*', '', text).strip()
            text = re.sub(r'\[link-[^\]]+\]\([^\)]*\)', '', text).strip()
            text = _clean(text)
            if len(text.split()) >= 5:
                if '?' in text:
                    faq.append(text)
                else:
                    body_paragraphs.append(text)

        elif re.match(r'^\[LI\]', line):
            text = re.sub(r'^\[LI\]\s*', '', clean_line).strip()
            text = re.sub(r'\[(?:link|button-link)-[^\]]+\]\([^\)]*\)', '', text).strip()
            text = re.sub(r'\[(?:link|button-link)-[^\]]+\]', '', text).strip()
            text = _clean(text)
            if len(text.split()) >= 3:
                list_items.append(text)

        elif re.match(r'^\[IMG\]', line):
            alt_match = re.search(r'Alt:\s*(.+?)(?:\s*\([^\)]*\))?$', clean_line)
            if alt_match:
                alt = alt_match.group(1).strip()
                if 'BRAK ALT' not in alt and '🚩' not in alt and len(alt.split()) >= 2:
                    image_alts.append(alt)

        elif re.match(r'^\[STRONG\]', line):
            text = re.sub(r'^\[STRONG\]\s*', '', clean_line).strip()
            if len(text.split()) >= 4:
                body_paragraphs.append(text)

        elif re.match(r'^\[(?:DT|DD)\]', line):
            text = re.sub(r'^\[(?:DT|DD)\]\s*', '', clean_line).strip()
            if len(text.split()) >= 3:
                faq.append(text)

        elif re.match(r'^\[link-', line):
            # Linki nawigacyjne — niski priorytet
            text = re.sub(r'^\[link-[^\]]+\]\([^\)]*\)\s*', '', clean_line).strip()
            if 2 <= len(text.split()) <= 12:
                link_texts.append(text)

    content_parts = (
        headings['h1'] * 5 +
        headings['h2'] * 3 +
        headings['h3'] * 2 +
        body_paragraphs +
        list_items +
        faq
    )
    content_text = ' '.join(content_parts)
    meta_text = ' '.join([title, meta_description])
    audit_text = ' '.join(audit_labels)

    return {
        'title': title,
        'meta_description': meta_description,
        'headings': headings,
        'body_paragraphs': body_paragraphs,
        'list_items': list_items,
        'faq': faq,
        'link_texts': link_texts,
        'image_alts': image_alts,
        'audit_labels': audit_labels,
        'audit_metrics': [],
        'content_text': content_text,
        'meta_text': meta_text,
        'audit_text': audit_text,
        'stats': {
            'h1': len(headings['h1']),
            'h2': len(headings['h2']),
            'h3': len(headings['h3']),
            'paragraphs': len(body_paragraphs),
            'lists': len(list_items),
            'faq': len(faq),
            'links': len(link_texts),
            'alts': len(image_alts),
            'audit_lines': len(audit_labels),
            'content_words': len(content_text.split()),
        }
    }


def _extract_meta_description(soup: BeautifulSoup) -> str:
    tag = soup.find('meta', attrs={'name': re.compile(r'^description$', re.I)})
    if tag and tag.get('content'):
        return _clean(tag.get('content'))
    return ''


def _is_audit_line(text: str) -> bool:
    AUDIT_PATTERNS = [
        r'^description\s*:', r'^title\s*:', r'^meta\s*:', r'^canonical\s*:', r'^robots\s*:',
        r'^brakujące\s+alt', r'^alt\s*:', r'^h1\s*:', r'^h2\s*:', r'^raport\b',
        r'^błąd\b', r'^ostrzeżenie\b', r'^liczba\b', r'^status\b',
    ]
    t = _clean(text).lower()
    if not t:
        return False
    for pattern in AUDIT_PATTERNS:
        if re.search(pattern, t):
            return True
    if re.match(r'^[a-ząćęłńóśźż\s]+:\s*\d+\s*$', t):
        return True
    return False


def _parse_standard_html(soup: BeautifulSoup) -> dict:
    """Parser dla standardowego HTML."""
    for s in soup.select(','.join(NOISE_SELECTORS)):
        s.decompose()

    title = _clean(soup.title.get_text()) if soup.title else ''
    meta_description = _extract_meta_description(soup)

    # Szukaj głównego contentu
    root = None
    for selector in CONTENT_SELECTORS:
        found = soup.select_one(selector)
        if found:
            root = found
            break
    if not root:
        root = soup.body or soup

    headings = {'h1': [], 'h2': [], 'h3': []}
    body_paragraphs = []
    list_items = []
    faq = []
    link_texts = []
    image_alts = []
    audit_labels = []

    for tag in root.find_all(['h1','h2','h3','p','li','a','img','dt','dd']):
        if tag.name == 'img':
            text = _clean(tag.get('alt', ''))
        else:
            text = _clean(tag.get_text(' ', strip=True))
        if not text:
            continue
        if _is_audit_line(text):
            audit_labels.append(text)
            continue
        if tag.name in ['h1','h2','h3']:
            headings[tag.name].append(text)
        elif tag.name == 'p' and len(text.split()) >= 6:
            if '?' in text:
                faq.append(text)
            else:
                body_paragraphs.append(text)
        elif tag.name == 'li' and len(text.split()) >= 3:
            list_items.append(text)
        elif tag.name in ['dt','dd'] and len(text.split()) >= 3:
            faq.append(text)
        elif tag.name == 'a' and 2 <= len(text.split()) <= 12:
            link_texts.append(text)
        elif tag.name == 'img' and len(text.split()) >= 2:
            image_alts.append(text)

    content_text = ' '.join(headings['h1']*5 + headings['h2']*3 + headings['h3']*2 + body_paragraphs + list_items + faq)
    return {
        'title': title, 'meta_description': meta_description,
        'headings': headings, 'body_paragraphs': body_paragraphs,
        'list_items': list_items, 'faq': faq, 'link_texts': link_texts,
        'image_alts': image_alts, 'audit_labels': audit_labels, 'audit_metrics': [],
        'content_text': content_text,
        'meta_text': ' '.join([title, meta_description]),
        'audit_text': ' '.join(audit_labels),
        'stats': {
            'h1': len(headings['h1']), 'h2': len(headings['h2']), 'h3': len(headings['h3']),
            'paragraphs': len(body_paragraphs), 'lists': len(list_items), 'faq': len(faq),
            'links': len(link_texts), 'alts': len(image_alts),
            'audit_lines': len(audit_labels), 'content_words': len(content_text.split()),
        }
    }


def normalize_competitor_report(html_content: str) -> dict:
    """Główna funkcja normalizacji — automatycznie wykrywa format i parsuje."""
    soup = BeautifulSoup(html_content, 'html.parser')
    if _is_custom_report_format(soup):
        result = _parse_custom_format(soup)
        if result:
            result['format'] = 'custom_report'
            return result
    result = _parse_standard_html(soup)
    result['format'] = 'standard_html'
    return result


def _tokenize(text: str) -> list[str]:
    return re.findall(r'\b[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]{3,}\b', (text or '').lower())


def _prepare_blacklist(brand_blacklist: list[str] | None) -> set[str]:
    result = set()
    if not brand_blacklist:
        return result
    for b in brand_blacklist:
        for token in _tokenize(b):
            result.add(token)
    return result


def _valid_token(t: str, blacklist: set[str]) -> bool:
    if t in PL_STOPWORDS or t in blacklist or t.isdigit() or _looks_like_brand(t):
        return False
    return True


def extract_lsi_keywords(html_content: str, top_n: int = 60, brand_blacklist: list[str] | None = None) -> list[dict]:
    normalized = normalize_competitor_report(html_content)
    blacklist = _prepare_blacklist(brand_blacklist)

    weighted_buckets = (
        normalized['headings']['h1'] * 5 +
        normalized['headings']['h2'] * 3 +
        normalized['headings']['h3'] * 2 +
        normalized['body_paragraphs'] +
        normalized['list_items'] +
        normalized['faq'] +
        ([normalized['meta_description']] if normalized['meta_description'] else []) +
        normalized['link_texts'][:10]
    )

    full_text = ' '.join(weighted_buckets)
    raw_tokens = _tokenize(full_text)
    tokens = [t for t in raw_tokens if _valid_token(t, blacklist)]

    bigrams = []
    for i in range(len(tokens) - 1):
        a, b = tokens[i], tokens[i+1]
        if _valid_token(a, blacklist) and _valid_token(b, blacklist):
            bigrams.append(f'{a} {b}')

    tf_counter = Counter(tokens)
    bg_counter = Counter(bigrams)
    total_tokens = len(tokens) + 1
    candidates = {}

    for word, count in tf_counter.items():
        tf = count / total_tokens
        idf = math.log(1 + total_tokens / (count + 1))
        candidates[word] = {'word': word, 'count': count, 'tfidf_score': round(tf * idf * 100, 3), 'type': 'unigram'}

    for bg, count in bg_counter.items():
        if count < 2:
            continue
        tf = count / total_tokens
        idf = math.log(1 + total_tokens / (count + 1))
        candidates[bg] = {'word': bg, 'count': count, 'tfidf_score': round(tf * idf * 100 * 1.35, 3), 'type': 'bigram'}

    sorted_candidates = sorted(candidates.values(), key=lambda x: (x['tfidf_score'], x['count']), reverse=True)
    result = []
    for i, item in enumerate(sorted_candidates[:top_n]):
        if i < top_n * 0.15:
            item['importance'] = '🔴 Krytyczne'
        elif i < top_n * 0.40:
            item['importance'] = '🟡 Ważne'
        else:
            item['importance'] = '⚪ Uzupełniające'
        result.append(item)
    return result


def extract_competitor_insights(html_documents: list[str], brand_blacklist: list[str] | None = None) -> dict:
    blacklist = _prepare_blacklist(brand_blacklist)
    normalized_docs = [normalize_competitor_report(doc) for doc in html_documents if doc]

    combined_content = ' '.join(doc['content_text'] for doc in normalized_docs)
    combined_meta = ' '.join(doc['meta_text'] for doc in normalized_docs)
    avg_words = max(1000, int(
        sum(doc['stats']['content_words'] for doc in normalized_docs) / max(len(normalized_docs), 1)
    ))

    heading_counter = Counter()
    questions = []
    for doc in normalized_docs:
        for level in ['h1','h2','h3']:
            heading_counter.update(doc['headings'][level])
        for p in doc['body_paragraphs'] + doc['faq']:
            if '?' in p:
                questions.append(p)

    lsi = extract_lsi_keywords(' '.join(html_documents), top_n=80, brand_blacklist=list(blacklist)) if html_documents else []

    return {
        'normalized_docs': normalized_docs,
        'combined_content': combined_content,
        'combined_meta': combined_meta,
        'average_words': avg_words,
        'top_headings': [h for h, _ in heading_counter.most_common(12)],
        'questions': questions[:20],
        'lsi': lsi,
        'diagnostics': {
            'documents': len(normalized_docs),
            'total_content_words': len(combined_content.split()),
            'total_meta_words': len(combined_meta.split()),
            'audit_lines_removed': sum(doc['stats']['audit_lines'] for doc in normalized_docs),
            'formats': [doc.get('format', 'unknown') for doc in normalized_docs],
        }
    }


def calculate_average_length(competitor_text: str, num_files: int = 1) -> int:
    if not competitor_text:
        return 1500
    words = re.findall(r'\b\w+\b', competitor_text)
    avg = len(words) // max(num_files, 1)
    return max(1000, avg)
