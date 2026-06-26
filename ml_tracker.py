import requests
import json
import sqlite3
import re
import urllib.parse
from datetime import datetime
import time

# --- 1. Setup Base de Datos ---
def setup_database():
    conn = sqlite3.connect('mercadolibre_prices.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ml_price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_scraped DATE,
            product_name TEXT,
            price INTEGER
        )
    ''')
    conn.commit()
    return conn

# --- 2. Extraer el título de la URL y usar la API de Búsqueda ---
def get_price_from_search(url):
    # Capturamos todo lo que está entre ".com.ar/" y el siguiente "/"
    match = re.search(r'\.com\.ar/([^/\?#]+)', url)
    if not match:
        return None
        
    slug = match.group(1)
    # Convertimos los guiones en espacios para armar la búsqueda
    query = slug.replace('-', ' ')
    
    # Codificamos la URL (para que los espacios sean seguros)
    safe_query = urllib.parse.quote(query)
    
    # Esta API es 100% pública y no requiere token de autenticación
    api_url = f"https://api.mercadolibre.com/sites/MLA/search?q={safe_query}&limit=1"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        resp = requests.get(api_url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get('results', [])
            if results:
                # El resultado [0] siempre será nuestro producto exacto
                return results[0].get('price')
        else:
            print(f"  [!] Error de la API: Código {resp.status_code}")
    except Exception as e:
        print(f"  [!] Error de red: {e}")
        
    return None

# --- 3. Flujo Principal ---
def main():
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"\nIniciando rastreo de ML vía API Pública ({today})...")
    
    try:
        with open('ml_links.json', 'r', encoding='utf-8') as f:
            links = json.load(f)
    except FileNotFoundError:
        print(" [!] No se encontró el archivo ml_links.json")
        return

    conn = setup_database()
    cursor = conn.cursor()
    count = 0
    
    for name, url in links.items():
        print(f"Buscando: {name[:45]}...")
        
        price = get_price_from_search(url)
        
        if price:
            cursor.execute('''
                INSERT INTO ml_price_history (date_scraped, product_name, price)
                VALUES (?, ?, ?)
            ''', (today, name, price))
            count += 1
            precio_fmt = f"${price:,.0f}".replace(",", ".")
            print(f"  -> Guardado exitosamente: {precio_fmt}")
        else:
            print(f"  [!] No se encontró el precio.")
            
        time.sleep(1) # Una leve pausa para no saturar su servidor de búsquedas
        
    conn.commit()
    conn.close()
    print(f"\nRastreo finalizado. Se guardaron {count} precios de Mercado Libre.")

if __name__ == "__main__":
    main()