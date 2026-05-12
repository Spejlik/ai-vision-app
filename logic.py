import cv2
import numpy as np
import os
import base64

def get_ai_prediction(name):
    # Pro testování teď porovnáme guma_nok proti guma_ok
    img_path = "img/guma_nok.jpg"   # To co vidí kamera
    tpl_path = "img/guma_ok.jpg"    # Náš ideál
    
    if not os.path.exists(img_path) or not os.path.exists(tpl_path):
        return 0, "Chybí foto", "#888888"

    # Načtení v šedotónu (stačí pro detekci přítomnosti)
    img = cv2.imread(img_path, 0)
    tpl = cv2.imread(tpl_path, 0)
    
    # Samotné porovnání
    res = cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    
    confidence = round(max_val * 100, 1)
    status = "OK" if confidence > 85 else "NOK"
    color = "#44ff44" if status == "OK" else "#ff4444"
    
    return confidence, status, color

def get_real_image_base64(name, status):
    """Zakóduje obrázek pro zobrazení v HTML kartě"""
    path = f"img/guma_{status.lower()}.jpg"
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""