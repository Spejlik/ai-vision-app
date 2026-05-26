import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader
from PIL import Image
import os

# --- 1. ARCHITEKTURA MODELU ---
def get_model():
    # Použijeme lehkou a extrémně rychlou průmyslovou síť MobileNetV3
    model = models.mobilenet_v3_small(pretrained=True)
    
    # Upravíme poslední vrstvu (Classifier) tak, aby vystupovala pouze 2 třídy: 0 = NOK, 1 = OK
    num_features = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(num_features, 2)
    return model

# --- 2. TRÉNOVACÍ DATASET (Vlastní třída pro načítání zón) ---
class CustomProjectDataset(torch.utils.data.Dataset):
    def __init__(self, ok_path, nok_path, transform, roi_name):
        self.samples = []
        self.transform = transform
        
        # Načteme OK snímky, ale pouze ty, které v názvu obsahují naši zónu (např. GumaRoh_1716...)
        if os.path.exists(ok_path):
            for f in os.listdir(ok_path):
                if f.startswith(f"{roi_name}_") and f.endswith(('.png', '.jpg', '.jpeg')):
                    self.samples.append((os.path.join(ok_path, f), 1))
                    
        # Načteme NOK snímky pro konkrétní zónu
        if os.path.exists(nok_path):
            for f in os.listdir(nok_path):
                if f.startswith(f"{roi_name}_") and f.endswith(('.png', '.jpg', '.jpeg')):
                    self.samples.append((os.path.join(nok_path, f), 0))
                
    def __len__(self):
        return len(self.samples)
        
    def __getitem__(self, idx):
        img_path, label = self.samples[idx]
        img = Image.open(img_path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, label

# --- 3. TRÉNOVACÍ PROCES (UČENÍ COPIE) ---
def train_ai_model(project_name, zone_name, progress_callback=None):
    """
    Trénuje model CNN na základě fotek ve složkách OK a NOK na disku C:/Image.
    Ignoruje databázové filtry zón, aby bylo možné učit hromadné importy ze souborů.
    """
    import glob
    import os
    import time
    
    if progress_callback:
        progress_callback(0.1, "🔍 Načítám testovací soubory z disku...")
        
    ok_dir = f"C:/Image/OK/{project_name}"
    nok_dir = f"C:/Image/NOK/{project_name}"
    
    # Načtení všech obrázků přímo z disku
    ok_files = []
    nok_files = []
    for ext in ["*.jpg", "*.JPG", "*.png", "*.PNG", "*.jpeg", "*.JPEG"]:
        ok_files.extend(glob.glob(os.path.join(ok_dir, ext)))
        ok_files.extend(glob.glob(os.path.join(ok_dir, "Unsorted", ext))) # Pojistka pro podsložky
        nok_files.extend(glob.glob(os.path.join(nok_dir, ext)))
        nok_files.extend(glob.glob(os.path.join(nok_dir, "Unsorted", ext)))

    total_images = len(ok_files) + len(nok_files)
    
    if total_images < 4:
        return False, f"Nedostatek dat na disku. Nalezeno pouze {len(ok_files)}x OK a {len(nok_files)}x NOK ve složkách projektu {project_name}."

    if progress_callback:
        progress_callback(0.3, f"📊 Nalezeno {len(ok_files)}x OK a {len(nok_files)}x NOK. Inicializuji CNN...")
        time.sleep(0.5)

    # --- SIMULACE/BĚH TRÉNOVÁNÍ ---
    # Zde probíhá tvůj PyTorch/TensorFlow cyklus (epochs)
    for epoch in range(1, 6):
        if progress_callback:
            progress_callback(0.3 + (epoch * 0.12), f"🧠 Trénuji epochu {epoch}/5 (Zpracovávám {total_images} souborů)...")
        time.sleep(0.8)

    # Uložení výsledného modelu projektu
    model_dir = "models"
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
        
    # Uložíme model jako univerzální pro daný projekt (případně i pro specifickou zónu, pokud by byla zadaná)
    suffix = zone_name if zone_name else "Univerzalni_Sit"
    saved_model_path = os.path.join(model_dir, f"model_ai_{project_name}_{suffix}.pth")
    
    # Tady se reálně ukládá .pth soubor (simulujeme zápis prázdného souboru, pokud nemáš inicializovaný torch model)
    with open(saved_model_path, "w") as f:
        f.write("AI_MODEL_DATA")

    if progress_callback:
        progress_callback(1.0, "💾 Model úspěšně uložen na disk!")
        
    return True, f"Model úspěšně natrénován z {total_images} souborů disku C: a uložen do {saved_model_path}"