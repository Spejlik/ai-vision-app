import sqlite3
import os
import cv2

# Fixní cesta pro úložiště
MASTER_FOLDER = "masters"
if not os.path.exists(MASTER_FOLDER):
    os.makedirs(MASTER_FOLDER)

def init_db():
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS masters 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, image_path TEXT,
                  x INTEGER, y INTEGER, w INTEGER, h INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS rois 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, master_id INTEGER, name TEXT, 
                  x INTEGER, y INTEGER, w INTEGER, h INTEGER, nok_type INTEGER)''')
    conn.commit()
    conn.close()

def get_projects():
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("SELECT id, name FROM masters")
    data = c.fetchall()
    conn.close()
    return data

def save_project(name):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("INSERT INTO masters (name, image_path) VALUES (?, '')", (name,))
    conn.commit()
    conn.close()

def add_master(project_name, m_name, x, y, w, h, path):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    # Hledáme projekt podle jména a aktualizujeme mu data
    c.execute("UPDATE masters SET image_path=?, x=?, y=?, w=?, h=? WHERE name=?", 
              (path, x, y, w, h, project_name))
    conn.commit()
    conn.close()

def get_masters(project_name):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("SELECT id, name, image_path FROM masters WHERE name=?", (project_name,))
    data = c.fetchall()
    conn.close()
    return data

def get_rois(master_id):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("SELECT id, name, x, y, w, h, nok_type FROM rois WHERE master_id=?", (master_id,))
    data = c.fetchall()
    conn.close()
    return data

def save_roi(master_id, name, x, y, w, h, nok):
    conn = sqlite3.connect('vision_system.db')
    c = conn.cursor()
    c.execute("INSERT INTO rois (master_id, name, x, y, w, h, nok_type) VALUES (?,?,?,?,?,?,?)",
              (master_id, name, x, y, w, h, nok))
    conn.commit()
    conn.close()