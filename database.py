import sqlite3
from datetime import datetime

DB_NAME = "vision_history.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS inspections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            projekt TEXT,
            roi_name TEXT,
            confidence REAL,
            status TEXT,
            image_path TEXT  -- PŘIDÁNO: Cesta k obrázku
        )
    ''')
    conn.commit()
    conn.close()

def save_result(projekt, roi_name, confidence, status, image_path):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO inspections (timestamp, projekt, roi_name, confidence, status, image_path)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (datetime.now(), projekt, roi_name, confidence, status, image_path))
    conn.commit()
    conn.close()

def get_history(limit=20):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Načítáme i image_path (index 5)
    c.execute("SELECT timestamp, projekt, roi_name, confidence, status, image_path FROM inspections ORDER BY timestamp DESC LIMIT ?", (limit,))
    data = c.fetchall()
    conn.close()
    return data