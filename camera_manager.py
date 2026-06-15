import os
import time
from PIL import Image
import numpy as np

def capture_live_frame(camera_source=0):
    """
    Zachytí snímek z první fyzicky detekované průmyslové kamery v síti (Elvac standard).
    Kompletně ignoruje webkamery notebooku.
    """
    try:
        from pypylon import pylon
        import streamlit as st
        
        tl_factory = pylon.TlFactory.GetInstance()
        devices = tl_factory.EnumerateDevices()
        
        # Pokud systém v seznamu vidí jakoukoli průmyslovou kameru (jako v našem CMD)
        if devices and len(devices) > 0:
            # Vezmeme natvrdo první dostupné síťové zařízení ze seznamu
            target_device = devices[0]
            camera = pylon.InstantCamera(tl_factory.CreateDevice(target_device))
            camera_name = target_device.GetFriendlyName().split("(")[0].strip()
        else:
            # Pokud je seznam prázdný, zkusíme nouzové otevření GigE třídy
            info = pylon.DeviceInfo()
            info.SetDeviceClass("BaslerGigE")
            camera = pylon.InstantCamera(tl_factory.CreateDevice(info))
            camera_name = "Obecná GigE Kamera"

        # Otevření hardwaru
        camera.Open()
        
        # Vynucení paketů pro Valeo infrastrukturu (Zamezení dropování snímků)
        if camera.GetDeviceInfo().GetDeviceClass() == "BaslerGigE":
            try:
                camera.GevSCPSPacketSize.SetValue(1500)
                camera.MaxNumBuffer.SetValue(10)
            except:
                pass

        # Formátování obrazu na černobílý standard (Mono8) nebo barevný (RGB8)
        try: camera.PixelFormat.SetValue("Mono8")
        except:
            try: camera.PixelFormat.SetValue("RGB8")
            except: pass
            
        grab_result = camera.GrabOne(3000)
        
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
            return None, "CHYBA_TIMEOUT_GIGE"
            
    except Exception as e:
        # Vypíšeme hardwarovou chybu přímo na webovou plochu místo spouštění webkamery
        import streamlit as st
        st.error(f"💥 Hardwarový zásek Pylonu: {str(e)}")
        return None, "CHYBA_HARDWARU"

def save_live_to_unsorted(project_name, camera_id, image_pil):
    import random
    unsorted_dir = f"C:/Image/Unsorted/{project_name}"
    if not os.path.exists(unsorted_dir):
        os.makedirs(unsorted_dir)
    filename = os.path.join(unsorted_dir, f"basler_{camera_id}_{int(time.time())}_{random.randint(100,999)}.jpg")
    image_pil.save(filename, "JPEG", quality=95)
    return filename