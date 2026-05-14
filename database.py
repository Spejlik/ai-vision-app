import sqlite3
import mysql.connector
from datetime import datetime

# --- LOKÁLNÍ SQLITE (Konfigurace systému) ---

def init_db():
    """Inicializace lokální databáze vision_system.db."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    # Tabulka pro Master obrázky (projekty) a jejich AOI (ořez)
    c.execute('''CREATE TABLE IF NOT EXISTS masters 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  name TEXT, 
                  image_path TEXT,
                  x INTEGERDEFAULT 0, 
                  y INTEGER DEFAULT 0, 
                  w INTEGER DEFAULT 1920, 
                  h INTEGER DEFAULT 1080)''')
    # Tabulka pro ROI (zóny inspekce)
    c.execute('''CREATE TABLE IF NOT EXISTS rois 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  master_id INTEGER, 
                  name TEXT, 
                  x INTEGER, y INTEGER, w INTEGER, h INTEGER, 
                  nok_type INTEGER)''')
    conn.commit()
    conn.close()
    print("✅ Lokální SQLite databáze byla inicializována.")

def save_project(name):
    """Vytvoří nový projekt v databázi."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("INSERT INTO masters (name, image_path) VALUES (?, ?)", (name, ""))
    conn.commit()
    conn.close()

def add_master(master_id, name, x, y, w, h, path):
    """Uloží/Aktualizuje data pro Master obrázek (funkce, která ti chyběla)."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    # Zjistíme, jestli už projekt existuje
    c.execute("UPDATE masters SET name=?, x=?, y=?, w=?, h=?, image_path=? WHERE id=?", 
              (name, x, y, w, h, path, master_id))
    conn.commit()
    conn.close()
    print(f"✅ Master '{name}' pro projekt ID {master_id} byl aktualizován.")

def get_projects():
    """Načte seznam všech projektů pro výběr v aplikaci."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("SELECT id, name, image_path, x, y, w, h FROM masters")
    data = c.fetchall()
    conn.close()
    return data

def get_rois(master_id):
    """Načte inspekční zóny pro vybraný projekt."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("SELECT * FROM rois WHERE master_id=?", (master_id,))
    data = c.fetchall()
    conn.close()
    return data

# --- VZDÁLENÁ MARIADB (Výsledky pro Elvac systém) ---

def save_result_to_mariadb(host, project_name, result_bool):
    """Zapíše výsledek inspekce na centrální SQL server."""
    try:
        conn = mysql.connector.connect(
            host=host,
            user="root",
            password="",
            database="elvac_rtvision",
            connect_timeout=2
        )
        cursor = conn.cursor()
        result_str = "PASS" if result_bool else "FAIL"
        query = "INSERT INTO inspection_results (project, result, timestamp) VALUES (%s, %s, %s)"
        cursor.execute(query, (project_name, result_str, datetime.now()))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        # Vypíše chybu do konzole (např. bridge.py), ale nezastaví program
        print(f"ℹ️ SQL Server nedostupný: {e}")