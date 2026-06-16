import time
from PIL import Image
from pypylon import pylon

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
            
            # Nastavení profilu z kamery
            try:
                _camera.UserSetSelector.SetValue("UserSet1")
                _camera.UserSetLoad.Execute()
            except: pass
            
            _camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        except Exception as e:
            print(f"Chyba inicializace kamery: {e}")
            return None
    return _camera

def capture_live_frame(exposure_time=None, gain=None):
    cam = get_camera()
    if cam and cam.IsGrabbing():
        try:
            # --- ZÁPIS EXPOZICE DO HARDWARU KAMERY ---
            if exposure_time is not None:
                # Vypneme automatiku, aby nás neposlouchala, a zapíšeme hodnotu
                cam.ExposureAuto.SetValue("Off")
                cam.ExposureTime.SetValue(float(exposure_time))
                
            if gain is not None:
                cam.GainAuto.SetValue("Off")
                cam.Gain.SetValue(float(gain))
            
            # Čekáme na snímek (timeout 2s)
            grab_result = cam.RetrieveResult(2000, pylon.TimeoutHandling_Return)
            if grab_result.GrabSucceeded():
                img = Image.fromarray(grab_result.Array).convert("RGB")
                grab_result.Release()
                return img, "OK"
            grab_result.Release()
        except Exception as e:
            return None, f"Chyba nastavení parametrů: {e}"
    return None, "Kamera neběží / Timeout"