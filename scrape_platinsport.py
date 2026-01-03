#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script automatico per scraping eventi live da Platinsport.com
Bypassa CloudFlare e genera JSON compatibile con MandraKodi
"""

import cloudscraper
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re

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
    """
    Estrae la nazione dal testo della lega
    Es: "England - Premier League" -> "UNITED KINGDOM"
    """
    for key, country in LEAGUE_TO_COUNTRY.items():
        if key.lower() in league_text.lower():
            return country
    return 'INTERNATIONAL'

def scrape_platinsport():
    """
    Scrape eventi live da Platinsport.com usando CloudScraper
    """
    print("[INFO] Inizializzazione CloudScraper...")
    
    # Crea scraper con browser fingerprint
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        },
        delay=10  # Ritardo per bypassare CloudFlare
    )
    
    url = "https://platinsport.com/"
    print(f"[INFO] Richiesta a {url}")
    
    try:
        response = scraper.get(url, timeout=30)
        
        if response.status_code != 200:
            print(f"[ERRORE] Status code: {response.status_code}")
            return None
        
        print(f"[OK] Pagina scaricata ({len(response.content)} bytes)")
        
        # Parsing HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Estrai data
        date_div = soup.find('div', class_='div-1')
        event_date = date_div.get_text(strip=True) if date_div else "Unknown Date"
        print(f"[INFO] Data eventi: {event_date}")
        
        eventi = []
        current_league = ""
        current_country = ""
        
        # Trova tutte le righe della tabella
        table = soup.find('table')
        if not table:
            print("[ERRORE] Tabella eventi non trovata!")
            return None
        
        for row in table.find_all('tr'):
            # Riga intestazione lega
            league_header = row.find('td', class_='stil')
            if league_header:
                current_league = league_header.get_text(strip=True)
                current_country = extract_country_from_league(current_league)
                print(f"[LEGA] {current_league} -> {current_country}")
                continue
            
            # Riga evento
            cells = row.find_all('td')
            if len(cells) == 3:
                time_elem = cells[0].find('time')
                if time_elem and time_elem.get('datetime'):
                    match_text = cells[1].get_text(strip=True)
                    datetime_utc = time_elem['datetime']
                    
                    # Crea ID univoco
                    event_id = f"platin_{datetime_utc}_{match_text}".replace(' ', '_').replace(':', '')
                    
                    evento = {
                        'id': event_id,
                        'title': match_text,
                        'league': current_league,
                        'country': current_country,
                        'datetime': datetime_utc,
                        'source': 'platinsport',
                        'url': url,
                        'thumbnail': 'https://www.platinsport.com/resim/Logo.webp'
                    }
                    eventi.append(evento)
        
        print(f"[OK] Estratti {len(eventi)} eventi")
        return {
            'date': event_date,
            'events': eventi,
            'last_update': datetime.utcnow().isoformat() + 'Z',
            'source': 'platinsport.com'
        }
        
    except Exception as e:
        print(f"[ERRORE] Eccezione durante scraping: {e}")
        import traceback
        traceback.print_exc()
        return None

def organize_by_country(data):
    """
    Organizza eventi per nazione (formato MandraKodi cartelle)
    """
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
    """
    Salva dati in formato JSON
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[OK] File salvato: {filename}")
        return True
    except Exception as e:
        print(f"[ERRORE] Impossibile salvare {filename}: {e}")
        return False

def main():
    """
    Funzione principale
    """
    print("=" * 60)
    print("PLATINSPORT SCRAPER - GitHub Actions")
    print("=" * 60)
    
    # Scrape dati
    data = scrape_platinsport()
    
    if not data:
        print("[ERRORE] Scraping fallito!")
        return 1
    
    # Salva JSON principale
    save_json(data, 'platinsport_events.json')
    
    # Organizza per nazione (compatibile MandraKodi)
    countries = organize_by_country(data)
    
    # Salva JSON per nazione
    for country, events in countries.items():
        country_safe = country.replace(' ', '_').upper()
        country_data = {
            'country': country,
            'events': events,
            'count': len(events),
            'last_update': data['last_update']
        }
        save_json(country_data, f'platinsport_{country_safe}.json')
    
    # Statistiche
    print("\n" + "=" * 60)
    print("STATISTICHE:")
    print(f"  - Totale eventi: {len(data['events'])}")
    print(f"  - Nazioni: {len(countries)}")
    for country, events in sorted(countries.items()):
        print(f"    • {country}: {len(events)} eventi")
    print("=" * 60)
    
    return 0

if __name__ == '__main__':
    exit(main())
