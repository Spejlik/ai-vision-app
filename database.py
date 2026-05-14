import sqlite3
import mysql.connector
from datetime import datetime

# Lokální SQLite (vždy funguje)
def get_rois(master_id):
    try:
        conn = sqlite3.connect('vision_system.db')
        c = conn.cursor()
        c.execute("SELECT * FROM rois WHERE master_id=?", (master_id,))
        data = c.fetchall()
        conn.close()
        return data
    except Exception as e:
        print(f"❌ Chyba SQLite: {e}")
        return []

# Vzdálená MariaDB (ošetřená proti pádu)
def save_result_to_mariadb(host, project_name, result_bool):
    try:
        # Nastavení timeoutu na 2 sekundy, aby program doma nezamrzl
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
        print("✅ Výsledek úspěšně zapsán do MariaDB.")
    except Exception as e:
        # Tady je to klíčové - místo pádu jen vypíšeme info
        print(f"ℹ️ SQL Server nedostupný (jsi offline?). Výsledek nebyl uložen: {e}")