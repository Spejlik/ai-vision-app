import os
import time
from PIL import Image
import numpy as np

def capture_live_frame(camera_source=0):
    """
    Zachytí snímek z první dostupné GigE kamery (Elvac / Valeo standard).
    V případě chyby vypíše hlášku přímo na obrazovku.
    """
    try:
        from pypylon import pylon
        import streamlit as st
        
        # Inicializace továrny pro síťová zařízení
        tl_factory = pylon.TlFactory.GetInstance()
        devices = tl_factory.EnumerateDevices()
        
        # Pokud Enumerate selže, vynutíme GigE specifikaci přímo v transportní vrstvě
        if not devices:
            info = pylon.DeviceInfo()
            info.SetDeviceClass("BaslerGigE")
            camera = pylon.InstantCamera(tl_factory.CreateDevice(info))
        else:
            # Vezmeme první nalezené síťové zařízení
            camera = pylon.InstantCamera(tl_factory.CreateDevice(devices[0]))
            
        camera_name = "Průmyslová GigE Kamera"

        # Otevření kamery
        camera.Open()
        
        # Nastavení stability sítě a MTU paketů
        try:
            camera.GevSCPSPacketSize.SetValue(1500)
            camera.MaxNumBuffer.SetValue(10)
        except:
            pass

        # Vynucení formátu
        try: camera.PixelFormat.SetValue("Mono8")
        except:
            try: camera.PixelFormat.SetValue("RGB8")
            except: pass
            
        grab_result = camera.GrabOne(3000) # Prodloužený timeout na 3 sekundy
        
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
            return None, "CHYBA_TIMEOUT_SNIMANI"
            
    except Exception as e:
        # ZMĚNA: Už žádné tiché OpenCV, vypíšeme chybu přímo uživateli do Streamlitu!
        import streamlit as st
        st.error(f"💥 Hardwarová chyba Pylonu: {str(e)}")
        return None, "CHYBA_HARDWARU"

def save_live_to_unsorted(project_name, camera_id, image_pil):
    import random
    unsorted_dir = f"C:/Image/Unsorted/{project_name}"
    if not os.path.exists(unsorted_dir):
        os.makedirs(unsorted_dir)
    filename = os.path.join(unsorted_dir, f"basler_{camera_id}_{int(time.time())}_{random.randint(100,999)}.jpg")
    image_pil.save(filename, "JPEG", quality=95)
    return filename