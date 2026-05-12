import sqlite3

def init_db():
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    # Tabulka pro seznam produktů
    c.execute('''CREATE TABLE IF NOT EXISTS products 
                 (id INTEGER PRIMARY KEY, name TEXT UNIQUE)''')
    # Tabulka pro ROI (vázaná na jméno produktu)
    c.execute('''CREATE TABLE IF NOT EXISTS roi_templates 
                 (id INTEGER PRIMARY KEY, product_name TEXT, name TEXT, 
                  x INTEGER, y INTEGER, w INTEGER, h INTEGER)''')
    conn.commit()
    conn.close()

def add_product(name):
    conn = sqlite3.connect('inspections.db')
    try:
        conn.execute("INSERT INTO products (name) VALUES (?)", (name,))
        conn.commit()
    except:
        pass # Pokud jméno už existuje, nic se neděje
    conn.close()

def get_products():
    conn = sqlite3.connect('inspections.db')
    res = conn.execute("SELECT name FROM products").fetchall()
    conn.close()
    return [r[0] for r in res]

def delete_product(name):
    conn = sqlite3.connect('inspections.db')
    conn.execute("DELETE FROM products WHERE name = ?", (name,))
    conn.execute("DELETE FROM roi_templates WHERE product_name = ?", (name,))
    conn.commit()
    conn.close()

def save_roi_template(product_name, name, x, y, w, h):
    conn = sqlite3.connect('inspections.db')
    conn.execute('''INSERT INTO roi_templates (product_name, name, x, y, w, h)
                    VALUES (?, ?, ?, ?, ?, ?)''', (product_name, name, x, y, w, h))
    conn.commit()
    conn.close()

def get_roi_templates(product_name):
    conn = sqlite3.connect('inspections.db')
    res = conn.execute("SELECT id, product_name, name, x, y, w, h FROM roi_templates WHERE product_name = ?", (product_name,)).fetchall()
    conn.close()
    return res

def delete_roi_template(roi_id):
    conn = sqlite3.connect('inspections.db')
    conn.execute("DELETE FROM roi_templates WHERE id = ?", (roi_id,))
    conn.commit()
    conn.close()