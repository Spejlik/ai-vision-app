import cv2
import os
import time
from PIL import Image

def capture_live_frame(camera_source=0):
    """
    Připojí se k reálné kameře na lisu a zachytí aktuální snímek.
    
    Parametry:
    - camera_source: buď číslo (0, 1, 2 pro USB kamery) 
                     nebo textový řetězec (např. "rtsp://192.168.1.50/stream1" pro IP kamery)
    """
    # Inicializace spojení s kamerou přes OpenCV
    cap = cv2.VideoCapture(camera_source)
    
    # Průmyslové kamery potřebují chvilku na nastavení expozice a jasu po startu
    # Nastavíme vyrovnávací paměť na 1 snímek, ať nemáme zpožděný obraz
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    if not cap.isOpened():
        print(f"❌ Chyba: Nepodařilo se připojit ke kameře na zdroji: {camera_source}")
        return None
        
    try:
        # Přečteme snímek z čipu kamery
        ret, frame = cap.read()
        
        # Pro jistotu přečteme ještě jednou, abychom vyčistili buffer a měli 100% aktuální kus po otevření formy
        ret, frame = cap.read()
        
        if ret and frame is not None:
            # OpenCV standardně načítá v BGR formátu, převedeme na RGB pro Pillow/Streamlit
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_frame)
            return pil_img
        else:
            print("❌ Chyba: Kamera neodpovídá nebo neposílá obrazová data.")
            return None
            
    except Exception as e:
        print(f"💥 Výjimka při snímání z kamery: {str(e)}")
        return None
        
    finally:
        # Vždy korektně uvolníme kameru, aby nezůstala uzamčená pro ostatní procesy ve Windows
        cap.release()

def save_live_to_unsorted(project_name, camera_id, image_pil):
    """
    Vezme živý snímek z kamery a uloží ho do průběžného sběru pro Historii.
    """
    import random
    unsorted_dir = f"C:/Image/Unsorted/{project_name}"
    if not os.path.exists(unsorted_dir):
        os.makedirs(unsorted_dir)
        
    filename = os.path.join(unsorted_dir, f"camera_{camera_id}_{int(time.time())}_{random.randint(100,999)}.jpg")
    image_pil.save(filename, "JPEG", quality=95)
    return filename