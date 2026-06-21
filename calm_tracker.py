import requests
from bs4 import BeautifulSoup
import json
import sqlite3
from datetime import datetime

# --- 1. Setup Base de Datos ---
def setup_database():
    conn = sqlite3.connect('calm_prices.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS calm_price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_scraped DATE,
            product_name TEXT,
            mattress_type TEXT,
            size TEXT,
            price INTEGER,
            regular_price INTEGER
        )
    ''')
    conn.commit()
    return conn

# --- 2. Función Recursiva para cazar productos y sus atributos ---
def extract_products(data_obj, products_dict):
    """Recorre el JSON buscando productos y sus etiquetas ocultas (attributes)"""
    if isinstance(data_obj, dict):
        if 'price' in data_obj and 'name' in data_obj and 'regular_price' in data_obj:
            price = data_obj['price']
            name = data_obj['name']
            
            if isinstance(price, (int, float)) and price > 0:
                regular = data_obj.get('regular_price', price)
                if not isinstance(regular, (int, float)) or regular == 0:
                    regular = price
                
                # Buscar las etiquetas 'attributes' de Next.js
                attrs = data_obj.get('attributes', {})
                raw_size = attrs.get('pa_tamano', '') if isinstance(attrs, dict) else ''
                
                products_dict[name] = {
                    'price': price,
                    'regular_price': regular,
                    'raw_size': raw_size
                }
                
        for key, value in data_obj.items():
            extract_products(value, products_dict)
    elif isinstance(data_obj, list):
        for item in data_obj:
            extract_products(item, products_dict)

# --- 3. Clasificador de Tamaño y Tipo ---
def parse_attributes(name, raw_size):
    """Clasifica el colchón cruzando la etiqueta oculta y el nombre"""
    name_lower = name.lower()
    
    # --- Determinar el Tipo ---
    if "híbrido" in name_lower or "hibrido" in name_lower:
        m_type = "Híbrido"
    elif "resorte" in name_lower:
        m_type = "Resortes"
    else:
        # Los Original, Original Plus, Elemental y Grado Sur base son de espuma
        m_type = "Espuma"
        
    # --- Determinar el Tamaño ---
    size = "Desconocido"
    # Comparamos la etiqueta oficial (raw_size) o buscamos las medidas en el string
    if raw_size == "1plaza" or "80x190" in name_lower or "80×190" in name_lower:
        size = "1 Plaza (80x190)"
    elif raw_size == "plaza-y-media-90-190" or "90x190" in name_lower or "90×190" in name_lower:
        size = "1.5 Plaza (90x190)"
    elif raw_size == "plaza-y-media" or "100x190" in name_lower or "100×190" in name_lower:
        size = "1.5 Plaza (100x190)"
    elif raw_size == "2plazas" or "140x190" in name_lower or "140×190" in name_lower:
        size = "2 Plazas (140x190)"
    elif raw_size == "queen" or "160x200" in name_lower or "160×200" in name_lower:
        size = "Queen (160x200)"
    elif raw_size == "king" or "180x200" in name_lower or "180×200" in name_lower:
        # Prevención: asegurarse de que no sea superking escondido
        if "200x200" in name_lower or "200×200" in name_lower:
            size = "Super King (200x200)"
        else:
            size = "King (180x200)"
    elif raw_size == "superking" or "200x200" in name_lower or "200×200" in name_lower:
        size = "Super King (200x200)"
        
    return m_type, size

# --- 4. Flujo Principal ---
def main():
    url = "https://calmessimple.com.ar/colchones"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"\nIniciando rastreo estático de Calm es Simple ({today})...")
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(" [!] Error al acceder a la página de Calm.")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    next_data_script = soup.find('script', id='__NEXT_DATA__')
    
    if not next_data_script:
        print(" [!] No se encontró la estructura de datos oculta.")
        return
        
    try:
        data = json.loads(next_data_script.string)
        products = {}
        
        extract_products(data, products)
        
        if not products:
            print(" [!] No se encontraron productos en el JSON.")
            return
            
        conn = setup_database()
        cursor = conn.cursor()
        count = 0
        
        for name, data_dict in products.items():
            if "Colchón" in name or "Colchon" in name:
                
                # Clasificamos usando nuestra función parse_attributes
                m_type, size = parse_attributes(name, data_dict['raw_size'])
                
                cursor.execute('''
                    INSERT INTO calm_price_history (date_scraped, product_name, mattress_type, size, price, regular_price)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (today, name, m_type, size, data_dict['price'], data_dict['regular_price']))
                count += 1
                
                precio_fmt = f"${data_dict['price']:,.0f}".replace(",", ".")
                print(f"  -> Guardado: {m_type} | {size} | {name} | {precio_fmt}")
        
        conn.commit()
        conn.close()
        print(f"\nRastreo finalizado. Se guardaron {count} variantes de colchones Calm.")
        
    except Exception as e:
        print(f" [!] Error procesando los datos: {e}")

if __name__ == "__main__":
    main()