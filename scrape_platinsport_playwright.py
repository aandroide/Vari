#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script automatico per scraping eventi live da Platinsport.com
Usa Playwright per bypassare CloudFlare e estrarre link Acestream
Compatibile con GitHub Actions
"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re
import base64
import time

# Mappatura nazioni per bandiere (compatibile MandraKodi)
LEAGUE_TO_COUNTRY = {
    'Africa': 'AFRICA',
    'Scotland': 'SCOTLAND',
    'England': 'UNITED KINGDOM',
    'Spain': 'SPAIN',
    'Italy': 'ITALY',
    'France': 'FRANCE',
    'Portugal': 'PORTUGAL',
    'Saudi Arabia': 'SAUDI ARABIA',
    'Australia': 'AUSTRALIA',
    'Germany': 'GERMANY',
    'Netherlands': 'NETHERLANDS',
    'Belgium': 'BELGIUM',
    'Turkey': 'TURKEY',
    'USA': 'USA',
    'NBA': 'USA',
    'NFL': 'USA',
    'Brazil': 'BRASIL',
    'Argentina': 'ARGENTINA'
}

def extract_country_from_league(league_text):
    """Estrae la nazione dal testo della lega"""
    for key, country in LEAGUE_TO_COUNTRY.items():
        if key.lower() in league_text.lower():
            return country
    return 'INTERNATIONAL'

def generate_stream_link():
    """Genera il link con chiave base64 per source-list.php"""
    date_str = datetime.utcnow().strftime('%Y-%m-%d')
    key_string = date_str + "PLATINSPORT"
    key_base64 = base64.b64encode(key_string.encode()).decode()
    url = f"https://www.platinsport.com/link/source-list.php?key={key_base64}"
    return url

def extract_acestream_links(page):
    """
    Estrae link Acestream dalla pagina source-list.php
    Cerca in HTML, attributi data-, onclick, e testo
    """
    print("[INFO] Estrazione link Acestream...")
    acestream_links = []
    
    try:
        # Aspetta che la pagina sia caricata
        page.wait_for_load_state('networkidle', timeout=10000)
        
        # Prendi l'HTML
        content = page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Pattern 1: Link <a href="acestream://...">
        for link in soup.find_all('a', href=True):
            href = link['href']
            if 'acestream://' in href:
                acestream_links.append({
                    'url': href.strip(),
                    'text': link.get_text(strip=True) or 'Stream Link',
                    'quality': extract_quality(link.get_text(strip=True))
                })
        
        # Pattern 2: Attributi data-*
        for elem in soup.find_all(attrs={'data-stream': True}):
            stream = elem['data-stream']
            if 'acestream://' in stream:
                acestream_links.append({
                    'url': stream.strip(),
                    'text': elem.get_text(strip=True) or 'Stream Link',
                    'quality': extract_quality(elem.get_text(strip=True))
                })
        
        # Pattern 3: Cerca nel testo con regex
        acestream_pattern = r'acestream://[a-f0-9]{40}'
        matches = re.findall(acestream_pattern, content, re.IGNORECASE)
        for match in matches:
            # Evita duplicati
            if not any(link['url'] == match for link in acestream_links):
                acestream_links.append({
                    'url': match.strip(),
                    'text': 'Extracted from page',
                    'quality': 'Unknown'
                })
        
        # Pattern 4: Cerca in onclick events
        for elem in soup.find_all(onclick=True):
            onclick = elem['onclick']
            matches = re.findall(acestream_pattern, onclick, re.IGNORECASE)
            for match in matches:
                if not any(link['url'] == match for link in acestream_links):
                    acestream_links.append({
                        'url': match.strip(),
                        'text': elem.get_text(strip=True) or 'From onclick',
                        'quality': extract_quality(elem.get_text(strip=True))
                    })
        
        # Rimuovi duplicati
        seen = set()
        unique_links = []
        for link in acestream_links:
            if link['url'] not in seen:
                seen.add(link['url'])
                unique_links.append(link)
        
        print(f"[OK] Trovati {len(unique_links)} link Acestream unici")
        return unique_links
        
    except Exception as e:
        print(f"[WARN] Errore estrazione Acestream: {e}")
        return []

def extract_quality(text):
    """Estrae qualità video dal testo (HD, FHD, SD, etc.)"""
    text_upper = text.upper()
    if 'FHD' in text_upper or '1080' in text_upper:
        return 'FHD'
    elif 'HD' in text_upper or '720' in text_upper:
        return 'HD'
    elif 'SD' in text_upper or '480' in text_upper:
        return 'SD'
    return 'Unknown'

def scrape_source_list(browser):
    """
    Naviga a source-list.php e estrae link Acestream
    """
    stream_url = generate_stream_link()
    print(f"[INFO] Navigazione a: {stream_url}")
    
    try:
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        # Naviga alla pagina stream
        page.goto(stream_url, wait_until='domcontentloaded', timeout=30000)
        
        # Aspetta un po' per il caricamento completo
        time.sleep(3)
        
        # Estrai link Acestream
        acestream_links = extract_acestream_links(page)
        
        context.close()
        return acestream_links
        
    except PlaywrightTimeoutError:
        print(f"[WARN] Timeout navigazione a source-list.php")
        return []
    except Exception as e:
        print(f"[WARN] Errore scraping source-list.php: {e}")
        return []

def find_pagination(soup, base_url):
    """Cerca link di paginazione"""
    pagination_urls = []
    
    patterns = [
        (r'/page/(\d+)', 'href'),
        (r'\?page=(\d+)', 'href'),
        (r'page-(\d+)', 'href')
    ]
    
    for link in soup.find_all('a', href=True):
        href = link['href']
        text = link.get_text(strip=True).lower()
        
        # Check pattern numerici
        for pattern, _ in patterns:
            if re.search(pattern, href):
                full_url = base_url + href if href.startswith('/') else href
                if full_url not in pagination_urls:
                    pagination_urls.append(full_url)
        
        # Check testo
        if any(word in text for word in ['next', 'successivo', '»', '>']):
            if href and href not in ['#', 'javascript:void(0)']:
                full_url = base_url + href if href.startswith('/') else href
                if full_url not in pagination_urls and full_url != base_url:
                    pagination_urls.append(full_url)
    
    return pagination_urls

def scrape_events_page(page, url):
    """Estrae eventi da una singola pagina"""
    print(f"[INFO] Scraping: {url}")
    
    try:
        # Naviga alla pagina e aspetta caricamento completo
        print(f"[DEBUG] Navigazione in corso...")
        page.goto(url, wait_until='networkidle', timeout=60000)
        
        # Aspetta un po' per il rendering JavaScript
        print(f"[DEBUG] Attendo rendering JavaScript...")
        time.sleep(5)
        
        # Salva screenshot per debug
        screenshot_path = 'debug_screenshot.png'
        page.screenshot(path=screenshot_path)
        print(f"[DEBUG] Screenshot salvato: {screenshot_path}")
        
        # Aspetta che la tabella sia visibile (prova più selettori)
        table_found = False
        selettori = ['table', 'table.events', '#events-table', '.post-listing table']
        
        for selettore in selettori:
            try:
                print(f"[DEBUG] Cerco tabella con selettore: {selettore}")
                page.wait_for_selector(selettore, timeout=5000)
                print(f"[OK] Tabella trovata con selettore: {selettore}")
                table_found = True
                break
            except:
                continue
        
        if not table_found:
            print(f"[WARN] Tabella non trovata con nessun selettore")
            # Salva HTML per analisi
            html_path = 'debug_page.html'
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(page.content())
            print(f"[DEBUG] HTML salvato: {html_path}")
            return [], None, []
        
        # Prendi HTML
        content = page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Estrai data
        date_div = soup.find('div', class_='div-1')
        event_date = date_div.get_text(strip=True) if date_div else None
        
        # Cerca paginazione
        pagination = find_pagination(soup, url.rsplit('/', 1)[0] if '/' in url else url)
        
        # Estrai eventi
        eventi = []
        current_league = ""
        current_country = ""
        
        table = soup.find('table')
        if not table:
            return eventi, event_date, pagination
        
        for row in table.find_all('tr'):
            # Intestazione lega
            league_header = row.find('td', class_='stil')
            if league_header:
                current_league = league_header.get_text(strip=True)
                current_country = extract_country_from_league(current_league)
                print(f"  [LEGA] {current_league} -> {current_country}")
                continue
            
            # Riga evento
            cells = row.find_all('td')
            if len(cells) == 3:
                time_elem = cells[0].find('time')
                if time_elem and time_elem.get('datetime'):
                    match_text = cells[1].get_text(strip=True)
                    datetime_utc = time_elem['datetime']
                    
                    event_id = f"platin_{datetime_utc}_{match_text}".replace(' ', '_').replace(':', '').replace('/', '_')
                    
                    evento = {
                        'id': event_id,
                        'title': match_text,
                        'league': current_league,
                        'country': current_country,
                        'datetime': datetime_utc,
                        'source': 'platinsport',
                        'url': url
                    }
                    eventi.append(evento)
        
        print(f"  [OK] Estratti {len(eventi)} eventi")
        return eventi, event_date, pagination
        
    except PlaywrightTimeoutError:
        print(f"[ERRORE] Timeout caricamento {url}")
        return [], None, []
    except Exception as e:
        print(f"[ERRORE] Eccezione scraping {url}: {e}")
        import traceback
        traceback.print_exc()
        return [], None, []

def scrape_platinsport():
    """
    Funzione principale - Scraping con Playwright
    """
    print("=" * 60)
    print("PLATINSPORT SCRAPER - PLAYWRIGHT")
    print("=" * 60)
    
    url = "https://platinsport.com/"
    all_events = []
    event_date = None
    visited_urls = set()
    
    with sync_playwright() as p:
        # Lancia browser headless con flag anti-detection
        print("[INFO] Avvio browser Chromium...")
        browser = p.chromium.launch(
            headless=True,  # Cambia a False per debug visivo
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',  # Nasconde che è automazione
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        # Crea context con user agent realistico e stealth options
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='Europe/Rome',
            # Simula comportamento umano
            geolocation={'longitude': 12.4964, 'latitude': 41.9028},  # Roma
            permissions=['geolocation'],
            # Headers realistici
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9,it;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1'
            }
        )
        
        page = context.new_page()
        
        # Nasconde che il browser è controllato da Playwright
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override chrome object
            window.chrome = {
                runtime: {}
            };
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        # Scrape homepage
        events, date, pagination = scrape_events_page(page, url)
        all_events.extend(events)
        event_date = date or event_date
        visited_urls.add(url)
        
        # Scrape pagine aggiuntive (max 3)
        for page_url in pagination[:3]:
            if page_url not in visited_urls:
                visited_urls.add(page_url)
                events, _, _ = scrape_events_page(page, page_url)
                all_events.extend(events)
        
        print(f"\n[INFO] Totale eventi raccolti: {len(all_events)}")
        
        # Scrape link Acestream
        print("\n[INFO] Tentativo estrazione link Acestream...")
        acestream_links = scrape_source_list(browser)
        
        # Genera link stream
        stream_link = generate_stream_link()
        
        # Aggiungi link a tutti gli eventi
        for event in all_events:
            event['stream_link'] = stream_link
            event['acestream_links'] = acestream_links
            event['thumbnail'] = 'https://www.platinsport.com/resim/Logo.webp'
        
        # Chiudi browser
        browser.close()
    
    print("\n" + "=" * 60)
    print("RISULTATI:")
    print(f"  - Eventi totali: {len(all_events)}")
    print(f"  - Pagine visitate: {len(visited_urls)}")
    print(f"  - Link Acestream trovati: {len(acestream_links)}")
    print(f"  - Link stream: {stream_link}")
    print("=" * 60)
    
    return {
        'date': event_date,
        'events': all_events,
        'pagination_links': list(visited_urls),
        'stream_link': stream_link,
        'acestream_links': acestream_links,
        'acestream_found': len(acestream_links),
        'last_update': datetime.utcnow().isoformat() + 'Z',
        'source': 'platinsport.com'
    }

def organize_by_country(data):
    """Organizza eventi per nazione (formato MandraKodi cartelle)"""
    if not data or not data.get('events'):
        return {}
    
    countries = {}
    for event in data['events']:
        country = event['country']
        if country not in countries:
            countries[country] = []
        countries[country].append(event)
    
    return countries

def save_json(data, filename):
    """Salva dati in formato JSON"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[OK] File salvato: {filename}")
        return True
    except Exception as e:
        print(f"[ERRORE] Impossibile salvare {filename}: {e}")
        return False

def main():
    """Funzione principale"""
    print("\n" + "=" * 60)
    print("PLATINSPORT SCRAPER - PLAYWRIGHT + GITHUB ACTIONS")
    print("=" * 60 + "\n")
    
    # Scrape dati
    data = scrape_platinsport()
    
    if not data or not data.get('events'):
        print("\n[ERRORE] Nessun evento estratto!")
        return 1
    
    # Salva JSON principale
    save_json(data, 'platinsport_events.json')
    
    # Organizza per nazione
    countries = organize_by_country(data)
    
    # Salva JSON per nazione
    for country, events in countries.items():
        country_safe = country.replace(' ', '_').upper()
        country_data = {
            'country': country,
            'events': events,
            'count': len(events),
            'stream_link': data['stream_link'],
            'acestream_links': data['acestream_links'],
            'last_update': data['last_update']
        }
        save_json(country_data, f'platinsport_{country_safe}.json')
    
    # Statistiche finali
    print("\n" + "=" * 60)
    print("STATISTICHE FINALI:")
    print(f"  ✅ Eventi totali: {len(data['events'])}")
    print(f"  ✅ Nazioni: {len(countries)}")
    print(f"  ✅ Link Acestream: {data['acestream_found']}")
    print(f"  ✅ Pagine scrapate: {len(data.get('pagination_links', []))}")
    print()
    for country, events in sorted(countries.items()):
        print(f"    • {country}: {len(events)} eventi")
    print("=" * 60 + "\n")
    
    return 0

if __name__ == '__main__':
    exit(main())
