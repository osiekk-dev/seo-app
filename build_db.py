"""
build_db.py — Jednorazowy skrypt budujący gramatyka.db z Morfeusz2
Uruchom RAZ przed pierwszym startem aplikacji:

    pip install morfeusz2
    python build_db.py

Skrypt buduje bazę SQLite z formami fleksyjnymi języka polskiego.
Czas działania: ~30-120 sekund zależnie od komputera.
"""

import sqlite3
import os
import sys


def check_morfeusz():
    try:
        import morfeusz2
        return morfeusz2
    except ImportError:
        print("❌ Morfeusz2 nie jest zainstalowany!")
        print("   Uruchom najpierw: pip install morfeusz2")
        sys.exit(1)


# ─────────────────────────────────────────────
# Lista lematów do wygenerowania form
# Zawiera słowa typowe dla treści SEO/marketingowych
# + ogólne polskie słownictwo
# ─────────────────────────────────────────────
LEMATY = [
    # Wirtualne spacery / fotografia 360
    "wirtualny","spacer","wycieczka","panorama","zdjęcie","fotografia","kamera",
    "obraz","widok","sferyczny","interaktywny","trójwymiarowy","cyfrowy","nowoczesny",
    "profesjonalny","wizualizacja","prezentacja","tour","matterport","google",

    # Branża / usługi
    "usługa","oferta","realizacja","projekt","wdrożenie","wykonanie","obsługa",
    "firma","przedsiębiorstwo","biznes","marka","produkt","rozwiązanie","technologia",
    "system","platforma","narzędzie","aplikacja","oprogramowanie","integracja",

    # Klient / sprzedaż
    "klient","użytkownik","nabywca","odbiorca","kontrahent","partner","zleceniodawca",
    "sprzedaż","zakup","zamówienie","transakcja","umowa","kontrakt","współpraca",
    "marketing","reklama","promocja","kampania","strategia","pozycjonowanie",

    # Nieruchomości / obiekty
    "nieruchomość","mieszkanie","dom","budynek","lokal","biuro","sklep","hotel",
    "restauracja","obiekt","wnętrze","przestrzeń","pokój","sala","hala","park",
    "galeria","muzeum","kościół","szkoła","szpital","centrum","kompleks","apartament",

    # Jakość / ocena
    "jakość","standard","poziom","wartość","efekt","wynik","rezultat","korzyść",
    "zaleta","wada","opinia","recenzja","ocena","certyfikat","nagroda","rekomendacja",
    "doświadczenie","ekspert","specjalista","profesjonalista","mistrz","autor",

    # Czasowniki kluczowe
    "tworzyć","realizować","wykonywać","fotografować","nagrywać","prezentować",
    "zwiedzać","oglądać","zobaczyć","sprawdzić","wybrać","kupić","zamówić",
    "zbudować","zaprojektować","wdrożyć","uruchomić","dostosować","zintegrować",
    "poprawić","zwiększyć","zmniejszyć","rozwijać","wspierać","pomagać","oferować",
    "dostarczać","zapewniać","gwarantować","posiadać","mieć","być","stać",

    # SEO / internet / treść
    "strona","witryna","portal","serwis","blog","artykuł","treść","tekst","opis",
    "nagłówek","słowo","fraza","pozycja","ranking","wynik","wyszukiwarka","link",
    "nawigacja","mapa","wizytówka","profil","konto","formularz","kontakt","email",

    # Czas / cena
    "czas","termin","data","rok","miesiąc","tydzień","dzień","godzina","minuta",
    "cena","koszt","opłata","budżet","inwestycja","zwrot","zysk","oszczędność",
    "rabat","zniżka","promocja","pakiet","abonament","subskrypcja","licencja",

    # Geolokalizacja
    "miasto","kraj","region","województwo","dzielnica","ulica","adres","lokalizacja",
    "polska","warszawa","kraków","wrocław","poznań","gdańsk","łódź","katowice",
    "śląsk","mazowsze","małopolska","wielkopolska","pomorze",

    # Przymiotniki ogólne
    "dobry","lepszy","najlepszy","szybki","łatwy","prosty","skuteczny","efektywny",
    "tani","drogi","bezpieczny","niezawodny","dokładny","precyzyjny","kompletny",
    "kompleksowy","indywidualny","unikalny","oryginalny","innowacyjny","kreatywny",
    "duży","mały","nowy","stary","pierwszy","ostatni","każdy","wszystko","wiele",

    # Ogólne rzeczowniki
    "informacja","wiedza","dane","raport","analiza","badanie","wyniki","statystyka",
    "przykład","przypadek","sytuacja","problem","rozwiązanie","odpowiedź","pytanie",
    "lista","zestaw","kolekcja","seria","grupa","kategoria","typ","rodzaj","forma",
    "możliwość","opcja","wybór","decyzja","plan","cel","zadanie","krok","etap","proces",
    "metoda","sposób","technika","podejście","standard","norma","zasada","reguła",
    "warunek","wymóg","potrzeba","oczekiwanie","wymaganie","specyfikacja","zakres",
]


def build_database(db_path: str = "gramatyka.db"):
    print("🔍 Sprawdzam Morfeusz2...")
    morfeusz2 = check_morfeusz()
    morf = morfeusz2.Morfeusz()
    print("✅ Morfeusz2 załadowany")

    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"🗑️  Usunięto starą bazę: {db_path}")

    print("🗄️  Tworzę nową bazę SQLite...")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""
        CREATE TABLE slowa (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            lemat TEXT NOT NULL,
            forma TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX idx_lemat ON slowa(lemat)")
    conn.execute("CREATE INDEX idx_forma ON slowa(forma)")
    conn.commit()

    print(f"📖 Generuję formy dla {len(LEMATY)} lematów...")
    batch = []
    batch_size = 5000
    total_forms = 0
    total_lemats = 0
    seen_pairs = set()

    for i, lemma in enumerate(LEMATY):
        try:
            forms = morf.generate(lemma.lower().strip())
            added = 0
            for form_tuple in forms:
                # form_tuple = (forma, lemat, tag, [], [])
                forma = form_tuple[0].lower().strip()
                lemat = form_tuple[1].lower().strip()
                lemat = lemat.split(':')[0]  # usuń :qub i podobne
                pair = (lemat, forma)
                if pair not in seen_pairs and forma and lemat and len(forma) >= 2:
                    seen_pairs.add(pair)
                    batch.append(pair)
                    added += 1
                    total_forms += 1

            if added > 0:
                total_lemats += 1

            if len(batch) >= batch_size:
                conn.executemany("INSERT INTO slowa (lemat, forma) VALUES (?, ?)", batch)
                conn.commit()
                batch = []

            if (i + 1) % 50 == 0:
                print(f"   [{i+1}/{len(LEMATY)}] {total_forms:,} form wygenerowanych...")

        except Exception as e:
            print(f"   ⚠️  Błąd dla '{lemma}': {e}")
            continue

    # Zapisz pozostałe
    if batch:
        conn.executemany("INSERT INTO slowa (lemat, forma) VALUES (?, ?)", batch)
        conn.commit()

    # Statystyki końcowe
    count = conn.execute("SELECT COUNT(*) FROM slowa").fetchone()[0]
    lemats_count = conn.execute("SELECT COUNT(DISTINCT lemat) FROM slowa").fetchone()[0]
    conn.close()

    size_kb = os.path.getsize(db_path) // 1024

    print(f"\n{'='*50}")
    print(f"✅ Baza gotowa: {db_path}")
    print(f"   Formy fleksyjne: {count:,}")
    print(f"   Unikalne lematy: {lemats_count:,}")
    print(f"   Rozmiar pliku:   {size_kb} KB")
    print(f"{'='*50}")
    print(f"\n🚀 Uruchom aplikację: streamlit run app.py")


if __name__ == "__main__":
    build_database()
