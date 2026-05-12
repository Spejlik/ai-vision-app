import sqlite3
import time

def init_db():
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    
    # 1. Tabulka pro výsledky (tu už tam máš)
    c.execute('''CREATE TABLE IF NOT EXISTS results
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  cycle_id TEXT,
                  part_name TEXT,
                  roi_name TEXT,
                  confidence REAL,
                  status TEXT,
                  image_path TEXT)''')

    # 2. NOVÁ TABULKA pro šablony ROI (tohle tam přidej)
    # Sem se uloží souřadnice, které nakreslíš myší v nastavení
    c.execute('''CREATE TABLE IF NOT EXISTS roi_templates
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  product_name TEXT,
                  roi_name TEXT,
                  x INTEGER, y INTEGER, w INTEGER, h INTEGER)''')
    
    conn.commit()
    conn.close()

def save_result(cycle_id, part_name, roi_name, confidence, status, img_path):
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    c.execute("INSERT INTO results (timestamp, cycle_id, part_name, roi_name, confidence, status, image_path) VALUES (?,?,?,?,?,?,?)",
              (ts, cycle_id, part_name, roi_name, confidence, status, img_path))
    conn.commit()
    conn.close()

# TATO FUNKCE JE KLÍČOVÁ - seskupuje inspekce do jedné tečky
def get_last_cycles(limit=15):
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    # Pokud je v cyklu aspoň jedno NOK, celý cyklus je NOK
    c.execute('''SELECT cycle_id, MAX(timestamp), 
                 CASE WHEN MIN(status) = 'NOK' THEN 'NOK' ELSE 'OK' END as final_status
                 FROM results 
                 GROUP BY cycle_id 
                 ORDER BY MAX(timestamp) DESC 
                 LIMIT ?''', (limit,))
    data = c.fetchall()
    conn.close()
    return data
    
def get_history(limit=8):
    """Tato funkce vrací jednotlivé ROI karty (to, co ti teď hází chybu)"""
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    # Seřadíme podle ID sestupně, abychom viděli nejnovější výsledky
    c.execute("SELECT * FROM results ORDER BY id DESC LIMIT ?", (limit,))
    data = c.fetchall()
    conn.close()
    return data

def get_cycle_details(cycle_id):
    """Vrátí všechny ROI pro jeden konkrétní výstřel lisu"""
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    c.execute("SELECT * FROM results WHERE cycle_id = ?", (cycle_id,))
    data = c.fetchall()
    conn.close()
    return data

def create_config_tables():
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    # Tabulka pro definici inspekčních zón
    c.execute('''CREATE TABLE IF NOT EXISTS roi_templates
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  product_name TEXT,
                  roi_name TEXT,
                  x INTEGER, y INTEGER, w INTEGER, h INTEGER)''')
    conn.commit()
    conn.close()    