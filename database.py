import sqlite3
import mysql.connector
from datetime import datetime

# --- LOKÁLNÍ SQLITE (pro konfiguraci zón) ---

def init_db():
    """Tato funkce vytvoří lokální databázi vision_system.db, pokud neexistuje."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    # Tabulka pro Master obrázky
    c.execute('''CREATE TABLE IF NOT EXISTS masters 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, image_path TEXT)''')
    # Tabulka pro ROI (zóny) - přidaný sloupec master_id pro propojení
    c.execute('''CREATE TABLE IF NOT EXISTS rois 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  master_id INTEGER, 
                  name TEXT, 
                  x INTEGER, y INTEGER, w INTEGER, h INTEGER, 
                  nok_type INTEGER)''')
    conn.commit()
    conn.close()
    print("✅ Lokální SQLite databáze byla inicializována.")

def get_rois(master_id):
    """Načte zóny pro konkrétní projekt/master."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("SELECT * FROM rois WHERE master_id=?", (master_id,))
    data = c.fetchall()
    conn.close()
    return data

# --- VZDÁLENÁ MARIADB (pro výsledky do centrálního systému Elvac) ---

def save_result_to_mariadb(host, project_name, result_bool):
    """Zapíše výsledek do velkého SQL serveru na hale."""
    try:
        conn = mysql.connector.connect(
            host=host,
            user="root",
            password="",
            database="elvac_rtvision",
            connect_timeout=2  # Důležité, aby program doma nezamrzl
        )
        cursor = conn.cursor()
        result_str = "PASS" if result_bool else "FAIL"
        query = "INSERT INTO inspection_results (project, result, timestamp) VALUES (%s, %s, %s)"
        cursor.execute(query, (project_name, result_str, datetime.now()))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        # Pokud jsi doma (offline), jen to vypíše hlášku místo pádu programu
        print(f"ℹ️ SQL Server nedostupný: {e}")