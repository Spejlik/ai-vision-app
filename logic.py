import random
import os
import base64

def get_ai_prediction(name):
    # Simulace pro tvůj produkt
    if random.random() > 0.1: # 90% šance na OK
        return random.randint(95, 99), "OK", "#44ff44"
    else:
        return random.randint(40, 60), "NOK", "#ff4444"

def get_real_image_base64(name, status):
    # DŮLEŽITÉ: Tady musí být názvy, které máš ve složce img/
    # Pokud máš jen guma_ok.jpg a guma_nok.jpg, namapujeme vše na ně
    path = f"img/guma_{status.lower()}.jpg"
    
    if not os.path.exists(path):
        # Pokud obrázek neexistuje, vrátíme prázdný string místo pádu
        return ""

    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except Exception:
        return ""