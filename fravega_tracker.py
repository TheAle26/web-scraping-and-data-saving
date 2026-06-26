import requests
from bs4 import BeautifulSoup
import sqlite3
from datetime import datetime
import re

# --- 1. Setup Base de Datos ---
def setup_database():
    conn = sqlite3.connect('fravega_prices.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fravega_price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_scraped DATE,
            product_name TEXT,
            product_url TEXT,
            price INTEGER,
            regular_price INTEGER
        )
    ''')
    conn.commit()
    return conn

# --- 2. Limpieza de Texto de Precio ---
def clean_price(price_str):
    if not price_str:
        return None
    # Extraemos solo los números
    clean_num = re.sub(r'[^\d]', '', price_str)
    return int(clean_num) if clean_num else None


def main():
    for i in range(1, 10):  # Iteramos 3 veces para simular diferentes páginas o filtros
        
        print(f"Iteración {i}:")
        try:
            scrape_fravega(f"https://www.fravega.com/l/heladeras-freezers-y-cavas/heladeras/?keyword=heladera&sorting=LOWEST_SALE_PRICE&categorias=heladeras-freezers-y-cavas%2Fheladeras&tipo-de-heladera=heladeras-con-freezer&precio=700000-a-1500000{i}")
        except Exception as e:
            print(f" [!] Error en la iteración {i}: {e}")
            break
        print("\n")

# --- 3. Flujo Principal ---
def scrape_fravega(url):
    # La URL base que pasaste, con filtros aplicados (heladeras con freezer, entre $700k y $1.5M)
    url = "https://www.fravega.com/l/heladeras-freezers-y-cavas/heladeras/?keyword=heladera&sorting=LOWEST_SALE_PRICE&categorias=heladeras-freezers-y-cavas%2Fheladeras&tipo-de-heladera=heladeras-con-freezer&precio=700000-a-1500000"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-AR,es;q=0.8,en-US;q=0.5,en;q=0.3"
    }
    
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"\nIniciando rastreo estático de Fravega ({today})...")
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f" [!] Error al acceder a Fravega: Código {response.status_code}")
            return
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Buscamos todos los artículos de productos
        # En Fravega, usan data-test-id="result-item" o class="sc-87b0945d-1"
        products = soup.find_all('article', {'data-test-id': 'result-item'})
        
        # Si no encuentra por data-test-id, intentamos con el tag article genérico que tenga un enlace
        if not products:
             products = soup.find_all('article')
             
        if not products:
            print(" [!] No se encontraron productos en el HTML.")
            return

        conn = setup_database()
        cursor = conn.cursor()
        count = 0
        
        for item in products:
            # 1. Buscar Nombre
            name_tag = item.find('span', {'class': re.compile(r'sc-1fa74e6c-0')})
            if not name_tag:
                 # Backup si cambian las clases dinámicas de Styled Components
                 name_tag = item.find('span', {'data-test-id': 'product-title'})
                 
            if not name_tag:
                continue
                
            name = name_tag.text.strip()
            
            # 2. Buscar Link
            link_tag = item.find('a', href=True)
            link = f"https://www.fravega.com{link_tag['href']}" if link_tag else "Sin link"
            
            # 3. Buscar Precios
            # El precio de oferta suele estar en un span con $
            price_container = item.find('div', {'data-test-id': 'product-price'})
            
            if not price_container:
                continue

            # Extraemos todos los textos que parezcan precios
            price_texts = price_container.find_all(string=re.compile(r'\$'))
            prices = [clean_price(p) for p in price_texts if clean_price(p)]
            
            if not prices:
                continue
                
            # Logica de precios en Fravega:
            # Si hay varios precios, el de oferta (final) suele ser el más bajo, 
            # y el regular (tachado) el más alto. A veces también está el precio "sin impuestos", lo ignoramos asumiendo que los principales son los primeros.
            
            # Ordenamos los precios detectados de menor a mayor
            prices.sort()
            
            # Asumimos que el precio final que paga el usuario es el más bajo publicado en la tarjeta
            final_price = prices[0]
            # Si hay más de un precio, asumimos que el mayor (dentro de los razonables) es el regular
            regular_price = prices[-1] if len(prices) > 1 else final_price
            
            cursor.execute('''
                INSERT INTO fravega_price_history (date_scraped, product_name, product_url, price, regular_price)
                VALUES (?, ?, ?, ?, ?)
            ''', (today, name, link, final_price, regular_price))
            
            count += 1
            precio_fmt = f"${final_price:,.0f}".replace(",", ".")
            print(f"  -> Guardado: {name[:30]}... | {precio_fmt}")

        conn.commit()
        conn.close()
        print(f"\nRastreo finalizado. Se guardaron {count} heladeras de Fravega.")
        
    except Exception as e:
        print(f" [!] Error durante el scraping: {e}")

if __name__ == "__main__":
    main()