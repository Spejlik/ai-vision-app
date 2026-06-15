import os
import time
from PIL import Image
from pypylon import pylon

# Globální proměnná pro udržení kamery v paměti
_camera = None

def get_camera():
    global _camera
    if _camera is None:
        try:
            tl_factory = pylon.TlFactory.GetInstance()
            devices = tl_factory.EnumerateDevices()
            if not devices:
                info = pylon.DeviceInfo()
                info.SetDeviceClass("BaslerGigE")
                _camera = pylon.InstantCamera(tl_factory.CreateDevice(info))
            else:
                _camera = pylon.InstantCamera(tl_factory.CreateDevice(devices[0]))
            
            _camera.Open()
            # Načtení User Set 1 (tvůj zafixovaný profil)
            try:
                _camera.UserSetSelector.SetValue("UserSet1")
                _camera.UserSetLoad.Execute()
            except: pass
            
            # Spuštění kontinuálního snímání
            _camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        except Exception as e:
            print(f"Chyba při inicializaci: {e}")
            return None
    return _camera

def capture_live_frame():
    cam = get_camera()
    if cam and cam.IsGrabbing():
        try:
            # Vyzobne nejnovější snímek z bufferu bez čekání na hardware
            grab_result = cam.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            if grab_result.GrabSucceeded():
                img_array = grab_result.Array
                pil_img = Image.fromarray(img_array).convert("RGB")
                grab_result.Release()
                return pil_img, "Kamera Lisu (Cont. Mode)"
            grab_result.Release()
        except:
            return None, "CHYBA_STREAMU"
    return None, "KAMERA_NEBĚŽÍ"