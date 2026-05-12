import sqlite3
import time

def init_db():
    conn = sqlite3.connect('inspections.db')
    c = conn.cursor()
    # Tabulka musí mít sloupec cycle_id
    c.execute('''CREATE TABLE IF NOT EXISTS results
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  cycle_id TEXT,
                  part_name TEXT,
                  roi_name TEXT,
                  confidence REAL,
                  status TEXT,
                  image_path TEXT)''')
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