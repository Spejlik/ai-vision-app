import os
import time
from PIL import Image
import numpy as np

def capture_live_frame(camera_source=0):
    """
    Zachytí snímek z první dostupné GigE kamery na síťové kartě (Elvac standard).
    Není závislé na jméně ani na sériovém čísle.
    """
    try:
        from pypylon import pylon
        
        tl_factory = pylon.TlFactory.GetInstance()
        
        # ELVAC TRIK: Vytvoříme obecný filtr, který hledá jakoukoli síťovou GigE kameru
        info = pylon.DeviceInfo()
        info.SetDeviceClass("BaslerGigE")
        
        # Inicializace kamery přímo přes tento síťový filtr
        camera = pylon.InstantCamera(tl_factory.CreateDevice(info))
        camera_name = "Průmyslová GigE Kamera"

        camera.Open()
        
        # Nastavení síťových parametrů pro Valeo síť (MTU a stability buffer)
        try:
            camera.GevSCPSPacketSize.SetValue(1500)
            camera.MaxNumBuffer.SetValue(10)
        except:
            pass

        # Vynucení formátu obrazu
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
                
            grab_result.ReleaseResult()
            camera.Close()
            return pil_img, camera_name
        else:
            grab_result.ReleaseResult()
            camera.Close()
            return None, "CHYBA_SNÍMÁNÍ"
            
    except Exception as e:
        # Nouzová větev pro USB/Webkamery, pokud GigE selže
        try:
            import cv2
            cap = cv2.VideoCapture(camera_source)
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                return Image.fromarray(rgb_frame), f"USB Kamera {camera_source}"
        except:
            pass
        return None, "CHYBA_HARDWARU"

def save_live_to_unsorted(project_name, camera_id, image_pil):
    """
    Uloží živý snímek do historie.
    """
    import random
    unsorted_dir = f"C:/Image/Unsorted/{project_name}"
    if not os.path.exists(unsorted_dir):
        os.makedirs(unsorted_dir)
        
    filename = os.path.join(unsorted_dir, f"basler_{camera_id}_{int(time.time())}_{random.randint(100,999)}.jpg")
    image_pil.save(filename, "JPEG", quality=95)
    return filename