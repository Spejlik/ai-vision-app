import os
import time
from PIL import Image
from pypylon import pylon

_camera = None

def get_camera():
    global _camera
    if _camera is None:
        tl_factory = pylon.TlFactory.GetInstance()
        _camera = pylon.InstantCamera(tl_factory.CreateFirstDevice())
        _camera.Open()
        # Vypínáme vše, co by mohlo měnit jas (včetně Auto-Exposure)
        _camera.ExposureAuto.SetValue("Off")
        _camera.GainAuto.SetValue("Off")
        # Kontinuální grab zapneme jen jednou
        _camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
    return _camera

def capture_live_frame():
    cam = get_camera()
    if cam and cam.IsGrabbing():
        try:
            # Čekáme na snímek bez nutnosti "startovat" kameru
            grab_result = cam.RetrieveResult(1000, pylon.TimeoutHandling_Return)
            if grab_result.GrabSucceeded():
                img_array = grab_result.Array
                pil_img = Image.fromarray(img_array).convert("RGB")
                grab_result.Release()
                return pil_img, "Kamera Lisu - Profi Mode"
            grab_result.Release()
        except: pass
    return None, "Kamera čeká..."