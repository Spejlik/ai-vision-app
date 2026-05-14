import sqlite3
import mysql.connector
import os
import cv2
from datetime import datetime

# Složka pro ukládání fyzických obrázků Masterů
MASTER_FOLDER = "masters_storage"
if not os.path.exists(MASTER_FOLDER):
    os.makedirs(MASTER_FOLDER)

def init_db():
    """Inicializace lokální SQLite databáze."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    # Tabulka masters musí obsahovat sloupce pro ořez (x,y,w,h) a cestu k souboru
    c.execute('''CREATE TABLE IF NOT EXISTS masters 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  name TEXT, 
                  image_path TEXT,
                  x INTEGER DEFAULT 0, 
                  y INTEGER DEFAULT 0, 
                  w INTEGER DEFAULT 1920, 
                  h INTEGER DEFAULT 1080)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS rois 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  master_id INTEGER, 
                  name TEXT, 
                  x INTEGER, y INTEGER, w INTEGER, h INTEGER, 
                  nok_type INTEGER)''')
    conn.commit()
    conn.close()

def save_project(name):
    """Vytvoří nový projekt v databázi."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("INSERT INTO masters (name, image_path) VALUES (?, ?)", (name, ""))
    conn.commit()
    conn.close()

def get_projects():
    """Načte seznam všech projektů (vyžadováno v app.py na řádku 73)."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("SELECT id, name, image_path, x, y, w, h FROM masters")
    projs = c.fetchall()
    conn.close()
    return projs

def get_masters(project_id=None):
    """Načte Mastery pro konkrétní projekt."""
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    if project_id:
        c.execute("SELECT id, name, image_path, x, y, w, h FROM masters WHERE id=?", (project_id,))
    else:
        c.execute("SELECT id, name, image_path, x, y, w, h FROM masters")
    data = c.fetchall()
    conn.close()
    return data

def add_master(master_id, name, x, y, w, h, frame):
    """Uloží obrázek na disk a aktualizuje záznam v DB."""
    try:
        file_path = os.path.join(MASTER_FOLDER, f"master_{master_id}.jpg")
        cv2.imwrite(file_path, frame) # Uložíme reálný snímek
        
        conn = sqlite3.connect('vision_system.db')
        c = conn.cursor()
        c.execute("UPDATE masters SET name=?, x=?, y=?, w=?, h=?, image_path=? WHERE id=?", 
                  (name, int(x), int(y), int(w), int(h), file_path, master_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Chyba při add_master: {e}")
        return False

# --- MARIADB (Pro halu) ---
def save_result_to_mariadb(host, project_name, result_bool):
    try:
        conn = mysql.connector.connect(
            host=host, user="root", password="", database="elvac_rtvision", connect_timeout=2
        )
        cursor = conn.cursor()
        res = "PASS" if result_bool else "FAIL"
        cursor.execute("INSERT INTO inspection_results (project, result, timestamp) VALUES (%s, %s, %s)", 
                       (project_name, res, datetime.now()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"SQL Offline: {e}")