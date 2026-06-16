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

def capture_live_frame(*args, **kwargs):
    """
    Univerzální průmyslové zachycení snímku z Basler kamery.
    Bezpečně parsuje parametry a zapisuje je pouze do existujících uzlů.
    """
    exposure_time = kwargs.get('exposure_time', args[0] if len(args) > 0 else None)
    gain = kwargs.get('gain', args[1] if len(args) > 1 else None)
    
    cam = get_camera()
    if cam and cam.IsGrabbing():
        try:
            # --- BEZPEČNÝ ZÁPIS EXPOZICE ---
            if exposure_time is not None and hasattr(cam, 'ExposureTime'):
                try:
                    if hasattr(cam, 'ExposureAuto') and cam.ExposureAuto.GetNode().IsValid():
                        cam.ExposureAuto.SetValue("Off")
                    cam.ExposureTime.SetValue(float(exposure_time))
                except Exception as e_exp:
                    print(f"⚠️ Nepodařilo se zapsat ExposureTime: {e_exp}")
                
            # --- BEZPEČNÝ ZÁPIS GAINU S KONTROLOU EXISTENCE UZLU ---
            if gain is not None:
                # Ověření standardního názvu 'Gain'
                if hasattr(cam, 'Gain') and cam.Gain.GetNode().IsValid():
                    try:
                        if hasattr(cam, 'GainAuto') and cam.GainAuto.GetNode().IsValid():
                            cam.GainAuto.SetValue("Off")
                        cam.Gain.SetValue(float(gain))
                    except Exception as e_gain:
                        print(f"⚠️ Nepodařilo se zapsat Gain: {e_gain}")
                # Fallback pro starší typy kamer používající 'GainRaw'
                elif hasattr(cam, 'GainRaw') and cam.GainRaw.GetNode().IsValid():
                    try:
                        cam.GainRaw.SetValue(int(gain))
                    except: pass
            
            # Samotné zachycení snímku z čipu
            grab_result = cam.RetrieveResult(2000, pylon.TimeoutHandling_Return)
            if grab_result.GrabSucceeded():
                img = Image.fromarray(grab_result.Array).convert("RGB")
                grab_result.Release()
                return img, "OK"
            grab_result.Release()
        except Exception as e:
            return None, f"Chyba registrů kamery: {e}"
    return None, "Kamera negrebuje nebo vypršel timeout."