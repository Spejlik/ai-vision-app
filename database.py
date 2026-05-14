@ -62,17 +62,19 @@ def get_masters(proj_name):
    conn.close()
    return data

def save_roi(master_id, name, x, y, w, h, nok, roi_id=None):
    conn = sqlite3.connect('database.db')
def save_roi(master_id, name, x, y, w, h, error_code, roi_id=None):
    conn = sqlite3.connect('inspections.db') # Pozor, máš tam název inspections.db
    cursor = conn.cursor()
    
    if roi_id:
        # AKTUALIZACE STÁVAJÍCÍ
        cursor.execute("UPDATE rois SET name=?, x=?, y=?, w=?, h=?, nok=? WHERE id=?",
                       (name, x, y, w, h, nok, roi_id))
        # Tady místo 'nok' napiš 'error_code'
        cursor.execute("""UPDATE rois SET name=?, x=?, y=?, w=?, h=?, error_code=? 
                          WHERE id=?""", (name, x, y, w, h, error_code, roi_id))
    else:
        # NOVÁ ZÓNA
        cursor.execute("INSERT INTO rois (master_id, name, x, y, w, h, nok) VALUES (?,?,?,?,?,?,?)",
                       (master_id, name, x, y, w, h, nok))
        # Tady taky místo 'nok' napiš 'error_code'
        cursor.execute("""INSERT INTO rois (master_id, name, x, y, w, h, error_code) 
                          VALUES (?,?,?,?,?,?,?)""", (master_id, name, x, y, w, h, error_code))
    
    conn.commit()
    conn.close()

