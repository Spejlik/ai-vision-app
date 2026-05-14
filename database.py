import sqlite3
import mysql.connector
from datetime import datetime

# --- LOKÁLNÍ SQLITE (Konfigurace) ---

def init_db():
    """Inicializace lokální databáze vision_system.db."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    # Tabulka pro Master obrázky (projekty)
    c.execute('''CREATE TABLE IF NOT EXISTS masters 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, image_path TEXT)''')
    # Tabulka pro ROI (zóny)
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
    """Uloží nový název projektu do databáze."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("INSERT INTO masters (name, image_path) VALUES (?, ?)", (name, ""))
    conn.commit()
    conn.close()
    print(f"✅ Projekt '{name}' byl uložen.")

def get_projects():
    """Načte všechny dostupné mastery/projekty."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("SELECT id, name, image_path FROM masters")
    data = c.fetchall()
    conn.close()
    return data

def delete_project(project_id):
    """Smaže projekt a jeho zóny."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("DELETE FROM masters WHERE id=?", (project_id,))
    c.execute("DELETE FROM rois WHERE master_id=?", (project_id,))
    conn.commit()
    conn.close()

def get_rois(master_id):
    """Načte zóny pro konkrétní projekt."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("SELECT * FROM rois WHERE master_id=?", (master_id,))
    data = c.fetchall()
    conn.close()
    return data

# --- VZDÁLENÁ MARIADB (Výsledky na hale) ---

def save_result_to_mariadb(host, project_name, result_bool):
    """Zapíše výsledek do centrálního SQL na hale."""
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
        print(f"ℹ️ SQL Server nedostupný (Simulace): {e}")