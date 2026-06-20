import requests
from bs4 import BeautifulSoup
import json
import sqlite3
from datetime import datetime

# --- Helper function to clean price strings into integers ---
def clean_price(price_str):
    if not price_str or price_str == "N/A":
        return 0
    # Remove '$', '.', ' ', and 'ARS' to get a clean integer
    clean_str = price_str.replace("$", "").replace(".", "").replace(" ", "").replace("ARS", "")
    try:
        return int(clean_str)
    except ValueError:
        return 0

# --- 1. Setup SQLite Database ---
def setup_database():
    # This creates a file named 'mattress_prices.db' in your current folder
    conn = sqlite3.connect('mattress_prices.db')
    cursor = conn.cursor()
    
    # Create the table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_scraped DATE,
            product_name TEXT,
            size TEXT,
            regular_price INTEGER,
            discount_price INTEGER
        )
    ''')
    conn.commit()
    return conn

# --- 2. The Main Scraper ---
def run_scraper():
    conn = setup_database()
    cursor = conn.cursor()
    
    # Get today's date in YYYY-MM-DD format
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    url = "https://www.duvet.com.ar/colchones-sommiers/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        product_containers = soup.find_all("div", class_="js-product-item-private")
        
        for container in product_containers:
            link_tag = container.find("a", class_="js-product-item-image-link-private")
            product_name = link_tag.get("title") if link_tag else "Unknown Product"

            variants_json_str = container.get("data-variants")
            
            if variants_json_str:
                try:
                    variants = json.loads(variants_json_str)
                    
                    for variant in variants:
                        size = variant.get("option0", "Standard")
                        
                        # Get raw strings
                        raw_price = variant.get("price_short", "0")
                        raw_discount = variant.get("price_with_payment_discount_short", "0")
                        
                        # Clean to integers
                        clean_regular_price = clean_price(raw_price)
                        clean_discount_price = clean_price(raw_discount)
                        
                        # Insert into the database
                        cursor.execute('''
                            INSERT INTO price_history (date_scraped, product_name, size, regular_price, discount_price)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (today_date, product_name, size, clean_regular_price, clean_discount_price))
                        
                        print(f"Saved: {product_name} ({size}) - Date: {today_date}")
                        
                except json.JSONDecodeError:
                    print(f"Could not parse data for {product_name}")
        
        # Commit the transaction after looping through everything
        conn.commit()
        print("\nSuccessfully saved all prices to the database.")
    else:
        print(f"Failed to retrieve page. Status code: {response.status_code}")

    # Always close the connection
    conn.close()

# Run the script
if __name__ == "__main__":
    run_scraper()