import os
import time
from PIL import Image
import numpy as np

import os
import time
from PIL import Image
import numpy as np

def capture_live_frame(camera_source=0, exposure_time=None):
    """
    Vrátí jeden snímek z první dostupné GigE kamery Basler. 
    Umožňuje manuální nastavení času expozice pro korekci světlosti.
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
        
        # --- BEZPEČNÉ VYPNUTÍ AUTOMATIK ---
        try: camera.ExposureAuto.SetValue("Off")
        except: pass
        try: camera.GainAuto.SetValue("Off")
        except: pass
        try: camera.BalanceWhiteAuto.SetValue("Off")
        except: pass

        # --- BEZPEČNÉ NASTAVENÍ MANUÁLNÍ EXPOZICE ---
        if exposure_time is not None:
             try: camera.ExposureMode.SetValue("Timed")
             except: pass
             
             try:
                 camera.ExposureTime.SetValue(float(exposure_time))
             except:
                 try:
                     camera.ExposureTimeAbs.SetValue(float(exposure_time))
                 except:
                     pass
        
        # Nastavení stability pro síť Valeo
        try:
            camera.GevSCPSPacketSize.SetValue(1500)
            camera.MaxNumBuffer.SetValue(10)
        except:
            pass

        try: camera.PixelFormat.SetValue("Mono8")
        except:
            try: camera.PixelFormat.SetValue("RGB8")
            except: pass
            
        grab_result = camera.GrabOne(2000)
        if grab_result.GrabSucceeded():
            img_array = grab_result.Array
            if len(img_array.shape) == 2:
                pil_img = Image.fromarray(img_array).convert("RGB")
            else:
                pil_img = Image.fromarray(img_array)
            
            grab_result.Release()
            camera.Close()
            return pil_img, "Průmyslová GigE Kamera"
        
        grab_result.Release()
        camera.Close()
        return None, "CHYBA_SNÍMÁNÍ"
        
    except Exception as e:
        return None, str(e)

# Funkce save_live_to_unsorted zůstává stejná

def save_live_to_unsorted(project_name, camera_id, image_pil):
    import random
    unsorted_dir = f"C:/Image/Unsorted/{project_name}"
    if not os.path.exists(unsorted_dir):
        os.makedirs(unsorted_dir)
    filename = os.path.join(unsorted_dir, f"basler_{camera_id}_{int(time.time())}_{random.randint(100,999)}.jpg")
    image_pil.save(filename, "JPEG", quality=95)
    return filename