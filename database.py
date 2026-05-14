import sqlite3
import mysql.connector
from datetime import datetime

# --- LOKÁLNÍ SQLITE (Konfigurace ve stylu Elvac/Vision Builder) ---

def init_db():
    """Inicializace lokální databáze vision_system.db."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    
    # Tabulka pro Master (hlavní projekty a AOI)
    c.execute('''CREATE TABLE IF NOT EXISTS masters 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  name TEXT, 
                  image_path TEXT,
                  x INTEGER DEFAULT 0, 
                  y INTEGER DEFAULT 0, 
                  w INTEGER DEFAULT 1920, 
                  h INTEGER DEFAULT 1080)''')
    
    # Tabulka pro ROI (inspekční zóny - jako v Elvacu)
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
    """Vytvoří nový projekt."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("INSERT INTO masters (name, image_path) VALUES (?, ?)", (name, ""))
    conn.commit()
    conn.close()

def add_master(master_id, name, x, y, w, h, path):
    """Aktualizuje master data (AOI)."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("UPDATE masters SET name=?, x=?, y=?, w=?, h=?, image_path=? WHERE id=?", 
              (name, x, y, w, h, path, master_id))
    conn.commit()
    conn.close()

# Tato funkce ti chyběla (v app.py voláš get_masters)
def get_masters(project_id=None):
    """Alias pro get_projects, aby seděl na tvůj app.py."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    if project_id:
        c.execute("SELECT id, name, image_path, x, y, w, h FROM masters WHERE id=?", (project_id,))
    else:
        c.execute("SELECT id, name, image_path, x, y, w, h FROM masters")
    data = c.fetchall()
    conn.close()
    return data

def get_projects():
    """Záložní funkce pro seznam projektů."""
    return get_masters()

def get_rois(master_id):
    """Načte zóny pro konkrétní projekt."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("SELECT * FROM rois WHERE master_id=?", (master_id,))
    data = c.fetchall()
    conn.close()
    return data

# --- VZDÁLENÁ MARIADB (Výsledky Elvac) ---

def save_result_to_mariadb(host, project_name, result_bool):
    """Zapíše výsledek do centrálního SQL na hale (IP 10.42.0.100)."""
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
        print(f"ℹ️ SQL Server 10.42.0.100 nedostupný: {e}")