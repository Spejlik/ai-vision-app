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

# --- 2. TRÉNOVACÍ PROCES (UČENÍ) ---
# --- UPRAVENÝ HISTORICKÝ DATASET PRO KONKRÉTNÍ ZÓNU ---
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

        # Inicializace datasetu s filtrem na konkrétní zónu (roi_name)
        dataset = CustomProjectDataset(ok_dir, nok_dir, data_transforms, roi_name)
        if len(dataset) < 4:
            return False, f"Nedostatek snímků pro zónu '{roi_name}'. Zařaďte v historii aspoň 2x ok a 2x nok pro tuto zónu."
            
        dataloader = DataLoader(dataset, batch_size=4, shuffle=True)
        
        model = get_model()
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=0.001)
        
        model.train()
        epochs = 5
        for epoch in range(epochs):
            running_loss = 0.0
            for inputs, labels in dataloader: # ZDE JE OPRAVENÝ PŘEKLEP
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()
                running_loss += loss.item() * inputs.size(0)
                
            if progress_bar_callback:
                progress_bar_callback((epoch + 1) / epochs, f"Epocha {epoch+1}/{epochs} dokončena...")
                
        # Uložení modelu se jménem projektu I ZÓNY
        model_dir = "models"
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
            
        model_path = os.path.join(model_dir, f"model_ai_{project_name}_{roi_name}.pth")
        torch.save(model.state_dict(), model_path)
        return True, model_path

# --- 3. INFERENCE (OSTRE VYHODNOCENÍ NA LINCE) ---
def predict_with_ai(model_path, pil_image):
    """
    Vezme živý výřez z kamery, prožene ho natrénovanou AI sítí
    --- Vrací: True (pokud je díl OK), False (pokud je díl NOK) a procentuální jistotu
    """
    if not os.path.exists(model_path):
        return True, 1.0 # Pokud model není natrénovaný, propustíme jako OK
        
    # Transformace živého obrazu na formát sítě
    eval_transforms = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    img_t = eval_transforms(pil_image).unsqueeze(0)
    
    # Načtení modelu
    model = get_model()
    model.load_state_dict(torch.load(model_path))
    model.eval()
    
    with torch.no_grad():
        outputs = model(img_t)
        probabilities = torch.nn.functional.softmax(outputs[0], dim=0)
        # Třída 0 = NOK, Třída 1 = OK
        confidence_nok = probabilities[0].item()
        confidence_ok = probabilities[1].item()
        
    if confidence_ok > confidence_nok:
        return True, confidence_ok
    else:
        return False, confidence_nok