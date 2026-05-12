import random
import os
import base64

def get_ai_prediction(name):
    if "Zámek" in name:
        return random.randint(48, 62), "NOK", "#ff4444"
    return random.randint(95, 99), "OK", "#44ff44"

def get_real_image_base64(name, status):
    mapping = {"Konektor": "konektor", "Zobáček P1": "zobacek", "Zobáček P2": "zobacek", "Zámek": "zamek"}
    base_name = mapping.get(name, "default")
    suffix = "ok" if status == "OK" else "nok"
    path = f"img/{base_name}_{suffix}.jpg"
    
    if not os.path.exists(path):
        return "" # Vrátí prázdný, pokud foto chybí

    with open(path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')