import random
import os
import base64

def get_ai_prediction(name):
    # Simulace: 90% šance na OK
    if random.random() > 0.1:
        return random.randint(95, 99), "OK", "#44ff44"
    return random.randint(45, 55), "NOK", "#ff4444"

def get_real_image_base64(name, status):
    # Fix na tvé soubory guma_ok.jpg a guma_nok.jpg
    path = f"img/guma_{status.lower()}.jpg"
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()