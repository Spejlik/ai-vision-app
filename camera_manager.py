import os
import time
from PIL import Image
from pypylon import pylon

# Globální instance
_camera = None

def get_camera():
    global _camera
    if _camera is None:
        try:
            tl_factory = pylon.TlFactory.GetInstance()
            devices = tl_factory.EnumerateDevices()
            if not devices: return None
            
            _camera = pylon.InstantCamera(tl_factory.CreateDevice(devices[0]))
            _camera.Open()
            
            # --- ZDE JSME DŘÍV MĚLI ÚPRAVY EXPOZICE ---
            # TEĎ VŠE MAŽEME, ABY KAMERA ZŮSTALA PŘESNĚ TAK, JAK JSI JI NASTAVIL V PYLON VIEWERU
            
            _camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        except Exception as e:
            print(f"Kamera se neotevřela: {e}")
            return None
    return _camera

def capture_live_frame():
    cam = get_camera()
    if cam and cam.IsGrabbing():
        try:
            # Vyčistíme staré snímky v bufferu, aby tam nezůstávaly "staré" expozice
            while cam.RetrieveResult(1, pylon.TimeoutHandling_Return).GrabSucceeded():
                pass
            
            # Získáme jen ten úplně nejnovější
            grab_result = cam.RetrieveResult(2000, pylon.TimeoutHandling_ThrowException)
            if grab_result.GrabSucceeded():
                img_array = grab_result.Array
                pil_img = Image.fromarray(img_array).convert("RGB")
                grab_result.Release()
                return pil_img, "OK"
            grab_result.Release()
        except Exception as e:
            return None, str(e)
    return None, "Kamera neběží"