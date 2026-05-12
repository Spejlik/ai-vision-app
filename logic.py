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
    
def augment_image(image, count=10):
    """Vytvoří 'count' variant obrázku pro trénování."""
    variants = []
    for _ in range(count):
        # Náhodná změna jasu
        brightness = np.random.uniform(0.9, 1.1)
        aug_img = cv2.convertScaleAbs(image, alpha=brightness, beta=0)
        
        # Náhodný drobný posun
        M = np.float32([[1, 0, np.random.randint(-2, 2)], [0, 1, np.random.randint(-2, 2)]])
        aug_img = cv2.warpAffine(aug_img, M, (image.shape[1], image.shape[2]))
        
        variants.append(aug_img)
    return variants

def save_cropped_image(pil_image, roi_name, label):
    # Vytvoření cesty: dataset/OK/Zebro_P1/
    target_dir = os.path.join("dataset", label, roi_name)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    # Generování názvu souboru podle času
    import time
    filename = f"crop_{int(time.time())}.jpg"
    final_path = os.path.join(target_dir, filename)
    
    # Uložení (převedeme na RGB pro jistotu, kdyby byl vstup v PNG s alfou)
    pil_image.convert('RGB').save(final_path, "JPEG")
    return final_path    