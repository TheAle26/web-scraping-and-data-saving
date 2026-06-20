import json
import sqlite3
import re
from datetime import datetime
import asyncio
from playwright.async_api import async_playwright
import random

# --- 1. Setup SQLite Database para Mercado Libre ---
def setup_database():
    conn = sqlite3.connect('mercadolibre_prices.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ml_price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_scraped DATE,
            product_name TEXT,
            url TEXT,
            price INTEGER
        )
    ''')
    conn.commit()
    return conn

# --- 2. Helper para limpiar links ---
def clean_ml_url(url):
    return url.split('?')[0].split('#')[0]

# --- 3. Extraer el Precio (Corregido con tu HTML) ---
async def get_ml_price_playwright(page, url):
    try:
        print(f"  -> Navegando a: {url}")
        
        # Vamos a la página
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        # Pequeña pausa para que el JavaScript renderice la página
        await page.wait_for_timeout(random.uniform(2000, 4000))
        
        # --- ESTRATEGIA 1: La etiqueta Meta (La que descubrimos en tu HTML) ---
        # Buscamos la etiqueta meta exacta. Usamos .count() para que no se cuelgue si no existe.
        meta_locator = page.locator("meta[itemprop='price']")
        if await meta_locator.count() > 0:
            price_content = await meta_locator.first.get_attribute("content")
            if price_content:
                return int(float(price_content))

        # --- ESTRATEGIA 2: La clase visible (Segunda opción de tu HTML) ---
        ui_locator = page.locator(".ui-pdp-price__second-line .andes-money-amount__fraction")
        if await ui_locator.count() > 0:
            price_text = await ui_locator.first.inner_text()
            numbers_only = re.sub(r'\D', '', price_text)
            if numbers_only:
                return int(numbers_only)

        # --- ESTRATEGIA 3: JSON-LD SEO (Respaldo final) ---
        json_ld_price = await page.evaluate('''() => {
            const scripts = document.querySelectorAll('script[type="application/ld+json"]');
            for (let script of scripts) {
                try {
                    let data = JSON.parse(script.innerText);
                    if (Array.isArray(data)) {
                        for (let item of data) {
                            if (item['@type'] === 'Product' && item.offers && item.offers.price) return item.offers.price;
                        }
                    } else if (data['@type'] === 'Product' && data.offers && data.offers.price) {
                        return data.offers.price;
                    }
                } catch(e) {}
            }
            return null;
        }''')
        
        if json_ld_price is not None:
            return int(float(json_ld_price))

        # Si agotamos las 3 estrategias y no encontró nada
        title = await page.title()
        # Si agotamos las 3 estrategias y no encontró nada
        title = await page.title()
        print(f"  [!] No se encontró el precio. Título de la página: '{title}'")
        
        # --- EL VOLCADO DE HTML QUE SUGERISTE ---
        html_content = await page.content()
        print("\n--- INICIO DEL HTML DE LA PÁGINA (Resumen) ---")
        print(html_content[:2000]) # Imprimimos los primeros 2000 caracteres para no romper la consola
        print("--- FIN DEL HTML DE LA PÁGINA ---\n")
        
        return None
    
        print(f"  [!] No se encontró el precio. Título de la página: '{title}'")
        return None

    except Exception as e:
        print(f"  [!] Error de ejecución: {e}")
        return None

# --- 4. Flujo Principal Asíncrono ---
async def main_tracker():
    conn = setup_database()
    cursor = conn.cursor()
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\nIniciando rastreo de ML con Navegador Real ({today_date})...")
    
    try:
        with open('ml_links.json', 'r', encoding='utf-8') as f:
            links_dict = json.load(f)
    except FileNotFoundError:
        print("Error: No se encontró el archivo 'ml_links.json'.")
        return

    async with async_playwright() as p:
        # CAMBIAR A FALSO PARA VER LA MAGIA
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for name, raw_url in links_dict.items():
            print(f"\nBuscando: {name}...")
            clean_url = clean_ml_url(raw_url)
            
            price = await get_ml_price_playwright(page, clean_url)
            
            if price is not None:
                cursor.execute('''
                    INSERT INTO ml_price_history (date_scraped, product_name, url, price)
                    VALUES (?, ?, ?, ?)
                ''', (today_date, name, clean_url, price))
                print(f"  -> Guardado exitosamente: ${price:,}")
            else:
                print(f"  -> Falló la extracción para este producto.")
                
        await browser.close()

    conn.commit()
    conn.close()
    print("\nRastreo finalizado.")

if __name__ == "__main__":
    asyncio.run(main_tracker())