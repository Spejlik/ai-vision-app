import os
import time
from PIL import Image
import numpy as np

def capture_live_frame(camera_source=0):
    """
    Vrátí jeden snímek z první dostupné GigE kamery Basler. 
    Pokud kamera chybí, vrátí None a přesný text chyby.
    """
    try:
        from pypylon import pylon
        tl_factory = pylon.TlFactory.GetInstance()
        devices = tl_factory.EnumerateDevices()
        
        if not devices:
            info = pylon.DeviceInfo()
            info.SetDeviceClass("BaslerGigE")
            camera = pylon.InstantCamera(tl_factory.CreateDevice(info))
        else:
            camera = pylon.InstantCamera(tl_factory.CreateDevice(devices[0]))
            
        camera.Open()
        
        # --- ZAFIXOVÁNÍ JASU A EXPOZICE (Průmyslový standard) ---
        try:
            camera.ExposureAuto.SetValue("Off")
            camera.GainAuto.SetValue("Off")
        except:
            pass
        
        # Nastavení stability pro síť Valeo
        # ... zbytek kódu pokračuje ...

        try: camera.PixelFormat.SetValue("Mono8")
        except:
            try: camera.PixelFormat.SetValue("RGB8")
            except: pass
            
        grab_result = camera.GrabOne(1000)
        if grab_result.GrabSucceeded():
            img_array = grab_result.Array
            if len(img_array.shape) == 2:
                pil_img = Image.fromarray(img_array).convert("RGB")
            else:
                pil_img = Image.fromarray(img_array)
            
            # ZDE JE OPRAVA:
            grab_result.Release()
            camera.Close()
            return pil_img, "Průmyslová GigE Kamera"
        
        # ZDE JE OPRAVA:
        grab_result.Release()
        camera.Close()
        return None, "CHYBA_SNÍMÁNÍ"
        
    except Exception as e:
        return None, str(e)

def save_live_to_unsorted(project_name, camera_id, image_pil):
    import random
    unsorted_dir = f"C:/Image/Unsorted/{project_name}"
    if not os.path.exists(unsorted_dir):
        os.makedirs(unsorted_dir)
    filename = os.path.join(unsorted_dir, f"basler_{camera_id}_{int(time.time())}_{random.randint(100,999)}.jpg")
    image_pil.save(filename, "JPEG", quality=95)
    return filename