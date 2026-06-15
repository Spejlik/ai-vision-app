import os
import time
from PIL import Image
import numpy as np

def capture_live_frame(camera_source=0):
    """
    Vrátí jeden snímek z první dostupné GigE kamery Basler. 
    Pokud kamera chybí, vrátí None (webkamera notebooku je přísně zakázána).
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
            
        grab_result = camera.GrabOne(1000)
        if grab_result.GrabSucceeded():
            img_array = grab_result.Array
            if len(img_array.shape) == 2:
                pil_img = Image.fromarray(img_array).convert("RGB")
            else:
                pil_img = Image.fromarray(img_array)
            grab_result.ReleaseResult()
            camera.Close()
            return pil_img, "Průmyslová GigE Kamera"
        
        grab_result.ReleaseResult()
        camera.Close()
        return None, "CHYBA_SNÍMÁNÍ"
    except:
        return None, "CHYBA_HARDWARU"

# Funkce save_live_to_unsorted zůstává stejná