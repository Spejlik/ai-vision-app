import os
import time
from PIL import Image
import numpy as np

def capture_live_frame(camera_source=0):
    """
    Zachytí snímek z reálné průmyslové kamery Basler nebo z Emulátoru přes Pylon SDK.
    """
    try:
        from pypylon import pylon
        
        tl_factory = pylon.TlFactory.GetInstance()
        devices = tl_factory.EnumerateDevices()
        
        if not devices:
            print("❌ Chyba: V systému není dostupná žádná Basler kamera ani emulátor.")
            return None
            
        # Třídění: Pokud detekujeme reálnou kameru, vezmeme ji. Jinak bereme emulátor.
        target_device = devices[0]
        for d in devices:
            if "Emulation" not in d.GetFriendlyName():
                target_device = d
                break
                
        print(f"🔌 Připojuji se k zařízení: {target_device.GetFriendlyName()}")
        camera = pylon.InstantCamera(tl_factory.CreateDevice(target_device))
        camera.Open()
        
        # Nastavení základního formátu (Mono8 nebo RGB8 podle typu kamery)
        try:
            camera.PixelFormat.SetValue("Mono8")
        except:
            try: camera.PixelFormat.SetValue("RGB8")
            except: pass
            
        # Zachycení jednoho snímku (timeout 2000 ms)
        grab_result = camera.GrabOne(2000)
        
        if grab_result.GrabSucceeded():
            img_array = grab_result.Array
            
            # Převedeme jednovrstvý černobílý obraz do pseudo-RGB pro Streamlit mřížku
            if len(img_array.shape) == 2:
                pil_img = Image.fromarray(img_array).convert("RGB")
            else:
                pil_img = Image.fromarray(img_array)
                
            grab_result.ReleaseResult()
            camera.Close()
            return pil_img
        else:
            print(f"❌ Chyba snímání z Pylonu: {grab_result.ErrorCode}")
            grab_result.ReleaseResult()
            camera.Close()
            return None
            
    except ImportError:
        print("❌ Chyba: Spusťte v CMD příkaz: pip install pypylon")
        return None
    except Exception as e:
        print(f"💥 Výjimka Basler Pylonu: {str(e)}")
        return None

def save_live_to_unsorted(project_name, camera_id, image_pil):
    """
    Uloží živý snímek do průběžného sběru pro Historii.
    """
    import random
    unsorted_dir = f"C:/Image/Unsorted/{project_name}"
    if not os.path.exists(unsorted_dir):
        os.makedirs(unsorted_dir)
        
    filename = os.path.join(unsorted_dir, f"basler_{camera_id}_{int(time.time())}_{random.randint(100,999)}.jpg")
    image_pil.save(filename, "JPEG", quality=95)
    return filename