import sqlite3
import mysql.connector
import os
from datetime import datetime

# --- KONFIGURACE CEST ---
# Vytvoříme složku 'masters' v adresáři projektu, pokud neexistuje
MASTER_FOLDER = "masters_storage"
if not os.path.exists(MASTER_FOLDER):
    os.makedirs(MASTER_FOLDER)

# --- LOKÁLNÍ SQLITE ---

def init_db():
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
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

def add_master(master_id, name, x, y, w, h, frame):
    """
    Uloží fyzický obrázek na disk a zapíše cestu a souřadnice do DB.
    'frame' je obrázek z kamery/OpenCV.
    """
    import cv2
    try:
        # 1. Definujeme cestu k souboru
        file_name = f"master_{master_id}.jpg"
        file_path = os.path.join(MASTER_FOLDER, file_name)
        
        # 2. Uložíme fyzický obrázek na disk
        cv2.imwrite(file_path, frame)
        
        # 3. Zapíšeme data do SQL
        conn = sqlite3.connect('vision_system.db')
        c = conn.cursor()
        c.execute("UPDATE masters SET name=?, x=?, y=?, w=?, h=?, image_path=? WHERE id=?", 
                  (name, int(x), int(y), int(w), int(h), file_path, master_id))
        conn.commit()
        conn.close()
        print(f"✅ Master uložen do: {file_path}")
        return True
    except Exception as e:
        print(f"❌ Chyba při ukládání Masteru: {e}")
        return False

def get_masters(project_id=None):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    if project_id:
        c.execute("SELECT id, name, image_path, x, y, w, h FROM masters WHERE id=?", (project_id,))
    else:
        c.execute("SELECT id, name, image_path, x, y, w, h FROM masters")
    data = c.fetchall()
    conn.close()
    return data

def save_project(name):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("INSERT INTO masters (name, image_path) VALUES (?, ?)", (name, ""))
    conn.commit()
    conn.close()

def get_rois(master_id):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("SELECT * FROM rois WHERE master_id=?", (master_id,))
    data = c.fetchall()
    conn.close()
    return data

# --- MARIADB (Elvac) ---
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
        print(f"ℹ️ SQL Offline: {e}")