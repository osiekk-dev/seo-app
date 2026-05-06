from bs4 import BeautifulSoup

def find_pillar_page(keyword: str, html_content) -> dict | None:
    if not html_content:
        return None
    try:
        if isinstance(html_content, bytes):
            raw = html_content.decode('utf-8', errors='replace')
        else:
            raw = html_content
        soup = BeautifulSoup(raw, 'html.parser')
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 3:
                url = cells[0].text.strip()
                title = cells[2].text.strip()
                if keyword.lower() in title.lower():
                    return {"url": url, "title": title}
    except Exception:
        pass
    return None
