# coding: utf-8
"""
Platinsport - Workflow Anti-Redirect AVANZATO
Script auto-esecuzione senza interazione utente

Author: Androide
Data creazione: 5/01/2026
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import time
import re
import base64
import random
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, parse_qs

def adjust_time_to_rome_timezone(datetime_attr):
    """
    Converte l'orario UTC dal datetime attr al fuso orario di Roma
    Esempio: "2026-01-05T08:00:00Z" -> "09:00" (se UTC+1)
    """
    if not datetime_attr:
        return None
    
    try:
        dt_str = datetime_attr.replace('Z', '')
        
        dt_utc = None
        for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M']:
            try:
                dt_utc = datetime.strptime(dt_str, fmt)
                break
            except:
                continue
        
        if dt_utc:
            month = dt_utc.month
            if 4 <= month <= 10:
                rome_offset = 2
            else:
                rome_offset = 1
            
            dt_rome = dt_utc + timedelta(hours=rome_offset)
            return dt_rome.strftime('%H:%M')
    
    except Exception as e:
        print(f"  Attenzione: Errore nell'aggiustamento orario {datetime_attr}: {e}")
    
    return None

def generate_platinsport_key():
    """Genera la chiave come fa il sito: base64(data + 'PLATINSPORT')"""
    today = datetime.now().strftime('%Y-%m-%d')
    key_string = today + "PLATINSPORT"
    key_bytes = key_string.encode('utf-8')
    key_base64 = base64.b64encode(key_bytes).decode('utf-8')
    return key_base64

def simulate_human_behavior(page, min_wait=0.5, max_wait=1.5):
    """Simula comportamento umano realistico"""
    try:
        time.sleep(random.uniform(min_wait, max_wait))
        
        if random.random() < 0.6:
            scroll_amount = random.randint(200, 800)
            page.evaluate(f'window.scrollBy(0, {scroll_amount})')
            time.sleep(random.uniform(0.3, 0.8))
            
            if random.random() < 0.4:
                page.evaluate(f'window.scrollBy(0, {-scroll_amount//2})')
                time.sleep(random.uniform(0.2, 0.5))
        
        if random.random() < 0.4:
            x = random.randint(50, page.viewport_size['width'] - 50)
            y = random.randint(50, page.viewport_size['height'] - 50)
            page.mouse.move(x, y)
            time.sleep(random.uniform(0.1, 0.3))
            
    except:
        pass

def simulate_ctrl_u_in_same_window(page):
    """Simula Ctrl+U nella STESSA finestra per ottenere il view-source"""
    print("  Simulazione Ctrl+U nella stessa finestra...")
    
    try:
        simulate_human_behavior(page, min_wait=0.3, max_wait=0.7)
        
        view_source_html = page.evaluate("""
            (() => {
                function getViewSource() {
                    let html = '';
                    
                    if (document.doctype) {
                        html += '<!DOCTYPE ' + document.doctype.name + 
                               (document.doctype.publicId ? ' PUBLIC "' + document.doctype.publicId + '"' : '') +
                               (document.doctype.systemId ? ' "' + document.doctype.systemId + '"' : '') + '>';
                    }
                    
                    html += document.documentElement.outerHTML;
                    
                    return html;
                }
                
                return getViewSource();
            })()
        """)
        
        print(f"  HTML ottenuto via Ctrl+U ({len(view_source_html)} bytes)")
        
        if any(x in view_source_html for x in ['TNT SPORT', 'SKY SPORT', 'DAZN', 'PREMIER SPORT', 'BEIN SPORT']):
            print("  Rilevati nomi REALI dei canali!")
            return view_source_html
        else:
            print("  Nessun nome reale trovato, provo metodo alternativo...")
            
            try:
                current_url = page.url
                print(f"  Tentativo fetch da: {current_url}")
                
                source_code = page.evaluate("""
                    async (url) => {
                        try {
                            const response = await fetch(url, {
                                method: 'GET',
                                headers: {
                                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                                    'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8',
                                    'Cache-Control': 'no-cache',
                                    'Pragma': 'no-cache'
                                },
                                credentials: 'include',
                                cache: 'no-store'
                            });
                            
                            if (!response.ok) {
                                throw new Error(`HTTP ${response.status}`);
                            }
                            
                            return await response.text();
                        } catch(e) {
                            console.error('Errore fetch:', e);
                            return document.documentElement.outerHTML;
                        }
                    }
                """, current_url)
                
                if source_code and len(source_code) > 5000:
                    print(f"  Sorgente ottenuto via fetch ({len(source_code)} bytes)")
                    
                    print("  Analisi contenuto fetch...")
                    print(f"    - Contiene 'acestream://': {'acestream://' in source_code}")
                    print(f"    - Contiene 'TNT SPORT': {'TNT SPORT' in source_code}")
                    print(f"    - Contiene 'time datetime': {'time datetime' in source_code}")
                    print(f"    - Contiene 'match-title-bar': {'match-title-bar' in source_code}")
                    
                    with open('fetch_source.html', 'w', encoding='utf-8') as f:
                        f.write(source_code)
                    return source_code
                else:
                    print(f"  Fetch ha restituito HTML troppo corto: {len(source_code) if source_code else 0} bytes")
                    
            except Exception as fetch_error:
                print(f"  Errore fetch: {fetch_error}")
        
        return view_source_html
        
    except Exception as e:
        print(f"  Errore in simulate_ctrl_u_in_same_window: {e}")
        return page.content()

def click_disclaimer_and_get_view_source(page):
    """Clicca il disclaimer e ottieni view-source con timing realistico"""
    print("  Ricerca disclaimer...")
    
    disclaimer_clicked = False
    start_time = time.time()
    
    disclaimer_selectors = [
        'button:has-text("I AGREE")',
        'button:has-text("AGREE")', 
        'button:has-text("ACCEPT")',
        'button:has-text("OK")',
        'button:has-text("Accetto")',
        'button:has-text("CONTINUE")',
        'a:has-text("CLICK HERE")',
        'button:has-text("I ACCEPT")',
        'input[type="button"][value*="OK"]',
        'input[type="submit"][value*="OK"]',
    ]
    
    try:
        page.wait_for_load_state('networkidle', timeout=10000)
    except:
        print("  Timeout networkidle, continuo comunque")
    
    simulate_human_behavior(page, min_wait=1, max_wait=2)
    
    for selector in disclaimer_selectors:
        try:
            page.wait_for_selector(selector, timeout=3000, state='visible')
            print(f"  Trovato disclaimer: {selector}")
            
            simulate_human_behavior(page, min_wait=0.5, max_wait=1)
            
            page.click(selector)
            disclaimer_clicked = True
            print("  Cliccato disclaimer!")
            
            time.sleep(1.5)
            
            break
        except Exception as e:
            continue
    
    if not disclaimer_clicked:
        print("  Nessun disclaimer trovato, procedo comunque")
        time.sleep(2)
    
    elapsed = time.time() - start_time
    print(f"  Tempo trascorso: {elapsed:.1f}s")
    
    print("  Ottenimento view-source...")
    view_source_html = simulate_ctrl_u_in_same_window(page)
    
    return view_source_html, disclaimer_clicked

def extract_structured_data_from_view_source(view_source_html):
    """
    Estrae dati strutturati dall'HTML view-source della pagina Platinsport
    """
    soup = BeautifulSoup(view_source_html, 'html.parser')
    
    results = {
        'date': None,
        'matches': [],
        'leagues': [],
    }
    
    date_patterns = [
        (re.compile(r'\w+ \d{1,2}\w+ \w+ \d{4}'), 'div', 'myDiv'),
        (re.compile(r'\d{4}-\d{2}-\d{2}'), 'div', 'myDiv'),
        (re.compile(r'\w+day \w+ \d{1,2}, \d{4}'), 'div', 'myDiv'),
    ]
    
    date_found = False
    for pattern, tag, cls in date_patterns:
        date_element = soup.find(tag, class_=cls, string=pattern)
        if date_element:
            results['date'] = date_element.get_text(strip=True)
            print(f"  Data trovata: {results['date']}")
            date_found = True
            break
    
    if not date_found:
        for div in soup.find_all('div', class_='myDiv'):
            text = div.get_text(strip=True)
            if re.search(r'\d{4}', text) and len(text) < 50:
                results['date'] = text
                print(f"  Data trovata (fallback): {results['date']}")
                break
    
    main_div = soup.find('div', class_='myDiv1')
    if not main_div:
        print("  Div principale non trovato!")
        main_div = soup.find('div', id='main') or soup.find('main') or soup.find('body')
        if not main_div:
            return results
    
    current_league = None
    league_matches = []
    
    for element in main_div.children:
        if not hasattr(element, 'name'):
            continue
            
        if element.name == 'p':
            league_text = element.get_text(strip=True)
            if league_text and len(league_text) > 2 and len(league_text) < 100:
                if current_league and league_matches:
                    results['leagues'].append({
                        'name': current_league,
                        'matches_count': len(league_matches),
                        'matches': league_matches.copy()
                    })
                    league_matches = []
                
                current_league = league_text
                print(f"  Campionato trovato: {current_league}")
        
        elif element.name == 'div' and 'match-title-bar' in element.get('class', []):
            match_data = extract_match_data_from_view_source(element, main_div)
            if match_data:
                league_matches.append(match_data)
    
    if current_league and league_matches:
        results['leagues'].append({
            'name': current_league,
            'matches_count': len(league_matches),
            'matches': league_matches.copy()
        })
    
    all_matches = []
    for league in results['leagues']:
        for match in league['matches']:
            match['league'] = league['name']
            all_matches.append(match)
    
    results['matches'] = all_matches
    
    total_streams = sum(len(m.get('streams', [])) for m in all_matches)
    real_names = sum(1 for m in all_matches for s in m.get('streams', []) 
                    if 'STREAM' not in s.get('tv_channel', '') and len(s.get('tv_channel', '')) > 5)
    
    matches_with_time = sum(1 for m in all_matches if m.get('time') and m['time'].strip())
    
    print(f"\n  STATISTICHE DETTAGLIATE:")
    print(f"    - Data evento: {results['date'] or 'Non trovata'}")
    print(f"    - Campionati: {len(results['leagues'])}")
    print(f"    - Partite totali: {len(all_matches)}")
    print(f"    - Partite con orario: {matches_with_time}/{len(all_matches)}")
    print(f"    - Stream Acestream: {total_streams}")
    print(f"    - Nomi canali REALI: {real_names}/{total_streams}")
    
    return results

def extract_match_data_from_view_source(match_div, parent_div):
    """
    Estrae i dati di una singola partita dal view-source HTML
    """
    try:
        time_element = match_div.find('time')
        match_time = None
        datetime_attr = None
        
        if time_element:
            datetime_attr = time_element.get('datetime', '')
            
            if datetime_attr:
                print(f"  Trovato datetime: {datetime_attr}")
                match_time = adjust_time_to_rome_timezone(datetime_attr)
                print(f"  Orario Roma: {match_time}")
        
        match_text = match_div.get_text(strip=True)
        
        if match_time and match_time in match_text:
            match_text = match_text.replace(match_time, '').strip()
        
        match_text = re.sub(r'\s+', ' ', match_text).strip()
        
        print(f"  Testo partita: '{match_text}'")
        
        button_group = match_div.find_next_sibling('div', class_='button-group')
        if not button_group:
            for sibling in match_div.next_siblings:
                if hasattr(sibling, 'name') and sibling.name == 'div' and 'button-group' in sibling.get('class', []):
                    button_group = sibling
                    break
        
        streams = []
        if button_group:
            links = button_group.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                if not href.startswith('acestream://'):
                    continue
                
                full_text = link.get_text(strip=True)
                
                print(f"      Link trovato: '{full_text}' -> {href[:30]}...")
                
                tv_channel = full_text
                
                if 'STREAM' in tv_channel or len(tv_channel) < 5:
                    title_attr = link.get('title', '')
                    if title_attr and len(title_attr) > 5:
                        tv_channel = title_attr
                        print(f"        Canale da title: {tv_channel}")
                    else:
                        link_html = str(link)
                        
                        patterns = [
                            r'>([A-Z][A-Z\s\d\+\.\-]+(?:HD|FHD|SD|4K)?)<',
                            r'</span>\s*([A-Z][A-Z\s\d\+\.\-]+(?:HD|FHD|SD|4K)?)',
                            r'span[^>]*>([^<]+)</span>\s*([A-Z][A-Z\s\d\+\.\-]+)',
                        ]
                        
                        for pattern in patterns:
                            match = re.search(pattern, link_html, re.IGNORECASE)
                            if match:
                                for group in match.groups():
                                    if group and len(group.strip()) > 3:
                                        found = group.strip()
                                        if not re.match(r'^[a-z]{2}$', found, re.IGNORECASE):
                                            tv_channel = found
                                            print(f"        Canale da regex: {tv_channel}")
                                            break
                                if tv_channel != full_text:
                                    break
                
                tv_channel = tv_channel.strip()
                
                stream_data = {
                    'url': href,
                    'type': 'acestream',
                    'tv_channel': tv_channel,
                    'country_code': None,
                    'full_text': full_text
                }
                
                flag_span = link.find('span', class_='fi')
                if flag_span:
                    for cls in flag_span.get('class', []):
                        if cls.startswith('fi-'):
                            stream_data['country_code'] = cls.replace('fi-', '')
                            print(f"        Bandiera: {stream_data['country_code']}")
                            break
                
                streams.append(stream_data)
        
        teams = match_text
        teams = re.sub(r'\s+vs\s+', ' vs ', teams)
        
        team_parts = teams.split(' vs ')
        if len(team_parts) >= 2:
            team1 = team_parts[0].strip()
            team2 = team_parts[1].strip()
        else:
            team1 = teams
            team2 = ""
        
        match_data = {
            'teams': f"{team1} vs {team2}" if team2 else team1,
            'team1': team1,
            'team2': team2,
            'time': match_time,
            'datetime': datetime_attr,
            'streams': streams,
            'streams_count': len(streams),
            'tv_channels': list(set([s['tv_channel'] for s in streams]))
        }
        
        print(f"  Partita estratta: {match_data['team1']} vs {match_data['team2']} - {match_time}")
        
        return match_data
        
    except Exception as e:
        print(f"  Errore nell'estrazione partita: {str(e)[:100]}")
        import traceback
        traceback.print_exc()
        return None

def format_matches_to_json(extracted_data):
    """
    Formatta i dati estratti nel formato JSON richiesto
    MANTIENE L'ORDINE DI VISUALIZZAZIONE COME NEL SITO
    """
    json_items = []
    
    default_thumbnail = "https://cdn6.aptoide.com/imgs/2/e/3/2e333438aec1b062c7ff0f3afa010f85_icon.png"
    default_fanart = "https://www.stadiotardini.it/wp-content/uploads/2016/12/mandrakata.jpg"
    
    global_date = extracted_data.get('date', '')
    print(f"\n  Data globale per JSON: {global_date}")
    
    for league in extracted_data.get('leagues', []):
        league_name = league['name']
        print(f"  Processando campionato: {league_name}")
        
        for match in league['matches']:
            team1 = match.get('team1', '')
            team2 = match.get('team2', '')
            match_time = match.get('time', '')
            
            print(f"    Partita: {team1} vs {team2} - Orario: {match_time}")
            
            for stream in match.get('streams', []):
                stream_url = stream.get('url', '')
                tv_channel = stream.get('tv_channel', 'STREAM')
                
                if match_time:
                    title = f"[COLOR aqua]{league_name}[/COLOR] [COLOR blue]{match_time}[/COLOR] [COLOR lime]{team1} vs {team2}[/COLOR] [COLOR gold]({tv_channel})[/COLOR]"
                else:
                    title = f"[COLOR aqua]{league_name}[/COLOR] [COLOR lime]{team1} vs {team2}[/COLOR] [COLOR gold]({tv_channel})[/COLOR]"
                
                item = {
                    "title": title,
                    "link": stream_url,
                    "thumbnail": default_thumbnail,
                    "fanart": default_fanart,
                    "info": "by MandraKodi"
                }
                
                json_items.append(item)
                print(f"      Aggiunto: {title[:80]}...")
    
    print(f"  Totale items JSON: {len(json_items)}")
    
    return json_items

def advanced_workflow_analysis():
    """
    Analisi workflow con protezione anti-redirect avanzata
    Versione auto-esecuzione senza domande
    """
    
    print("=" * 60)
    print("PLATINSPORT - ESTRAZIONE DATA E ORARI (Roma Timezone)")
    print("Script auto-esecuzione - Modalita HEADLESS")
    print("=" * 60)
    
    url = "https://platinsport.com"
    
    with sync_playwright() as p:
        print(f"\n[1/8] Avvio browser in modalita HEADLESS...")
        
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                '--disable-background-networking',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-breakpad',
                '--disable-client-side-phishing-detection',
                '--disable-component-update',
                '--disable-default-apps',
                '--disable-domain-reliability',
                '--disable-extensions',
                '--disable-features=AudioServiceOutOfProcess',
                '--disable-hang-monitor',
                '--disable-ipc-flooding-protection',
                '--disable-popup-blocking',
                '--disable-prompt-on-repost',
                '--disable-renderer-backgrounding',
                '--disable-sync',
                '--force-color-profile=srgb',
                '--metrics-recording-only',
                '--password-store=basic',
                '--use-mock-keychain',
                '--disable-infobars',
            ]
        )
        
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='it-IT',
            timezone_id='Europe/Rome',
            geolocation={'latitude': 41.9028, 'longitude': 12.4964},
            permissions=['geolocation'],
            color_scheme='dark',
            reduced_motion='reduce',
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
                'DNT': '1',
            }
        )
        
        page = context.new_page()
        
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['it-IT', 'it', 'en-US', 'en'] });
            window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
        """)
        
        def block_all_external_redirects(route, request):
            url_req = request.url
            
            allowed_domains = [
                'platinsport.com',
                'www.platinsport.com',
                'acestream.net',
                'play.google.com',
                '1xbet.com',
            ]
            
            is_allowed = any(domain in url_req for domain in allowed_domains)
            
            if not is_allowed:
                if request.resource_type in ['document', 'script']:
                    print(f"  BLOCCATO REDIRECT: {request.resource_type} -> {url_req[:80]}...")
                    route.abort()
                    return
            
            route.continue_()
        
        page.route("**/*", block_all_external_redirects)
        
        print(f"[2/8] Navigazione homepage con blocco redirect...")
        
        try:
            simulate_human_behavior(page, min_wait=1, max_wait=2)
            response = page.goto(
                url, 
                wait_until='domcontentloaded',
                timeout=30000,
                referer='https://www.google.com/'
            )
            
            time.sleep(random.uniform(2, 4))
            simulate_human_behavior(page)
            
            print(f"  Homepage caricata: {page.url}")
            
            print(f"[3/8] Generazione chiave...")
            key = generate_platinsport_key()
            print(f"  Chiave: {key}")
            
            target_url = f"https://www.platinsport.com/link/source-list.php?key={key}"
            print(f"  Target: {target_url}")
            
            print(f"[4/8] Navigazione pagina canali...")
            
            simulate_human_behavior(page, min_wait=1, max_wait=2)
            
            response = page.goto(
                target_url,
                wait_until='domcontentloaded',
                timeout=30000,
                referer=url
            )
            
            time.sleep(random.uniform(3, 5))
            simulate_human_behavior(page)
            
            print(f"  Pagina caricata: {page.url}")
            
            if 'source-list.php' not in page.url:
                print(f"  Non sulla pagina corretta: {page.url}")
                return None
            
            print(f"[5/8] Gestione disclaimer...")
            
            view_source_html, disclaimer_clicked = click_disclaimer_and_get_view_source(page)
            
            print(f"[6/8] Estrazione dati...")
            
            extracted_data = extract_structured_data_from_view_source(view_source_html)
            
            print(f"[7/8] Creazione JSON...")
            
            json_items = format_matches_to_json(extracted_data)
            final_json = {"items": json_items}
            
            print(f"[8/8] Salvataggio risultati...")
            
            with open('A1A115.json', 'w', encoding='utf-8') as f:
                json.dump(final_json, f, indent=2, ensure_ascii=False)
            
            total_matches = len(extracted_data.get('matches', []))
            total_items = len(json_items)
            
            print("\n" + "=" * 60)
            print("COMPLETATO!")
            print("=" * 60)
            
            print(f"\nRISULTATI:")
            print(f"  - Data globale: {extracted_data.get('date', 'N/A')}")
            print(f"  - Campionati: {len(extracted_data.get('leagues', []))}")
            print(f"  - Partite: {len(extracted_data.get('matches', []))}")
            print(f"  - Elementi JSON: {len(json_items)}")
            
            if json_items:
                print(f"\nPRIMI 3 ELEMENTI:")
                for i, item in enumerate(json_items[:3]):
                    title = item['title']
                    if len(title) > 80:
                        title = title[:77] + "..."
                    print(f"  {i+1}. {title}")
            
            print(f"\nFile salvato: A1A115.json")
            print(f"File sorgente: fetch_source.html")
            
            return final_json
            
        except Exception as e:
            print(f"\nERRORE: {e}")
            import traceback
            traceback.print_exc()
            
            return None
            
        finally:
            try:
                context.close()
                browser.close()
            except:
                pass

def main():
    """Funzione principale - Auto-esecuzione"""
    print("\nPLATINSPORT - ESTRAZIONE DATA E ORARI")
    print("Script auto-esecuzione - Modalita HEADLESS")
    print("Inizio estrazione...")
    print("\n" + "=" * 60)
    
    start_time = time.time()
    risultati = advanced_workflow_analysis()
    elapsed_time = time.time() - start_time
    
    print(f"\nTempo totale: {elapsed_time:.1f} secondi")
    
    if risultati and len(risultati.get('items', [])) > 0:
        print("\nSUCCESSO!")
        print(f"   {len(risultati['items'])} elementi JSON creati")
        print(f"   File salvato: A1A115.json")
    else:
        print("\nNessun risultato ottenuto")
        print("   Controlla i messaggi di errore")

if __name__ == "__main__":
    main()
