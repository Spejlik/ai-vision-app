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
            if not devices: 
                return None
            
            _camera = pylon.InstantCamera(tl_factory.CreateDevice(devices[0]))
            _camera.Open()
            
            # Pokus o načtení továrního průmyslového profilu
            try:
                if hasattr(_camera, 'UserSetSelector'):
                    _camera.UserSetSelector.SetValue("UserSet1")
                    _camera.UserSetLoad.Execute()
            except: 
                pass
            
            _camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        except Exception as e:
            print(f"⚠️ Chyba inicializace kamery: {e}")
            return None
    return _camera

def capture_live_frame(*args, **kwargs):
    """
    Robustní zachycení snímku z Basler kamery podle standardu Elvac.
    Před zápisem kritických registrů bezpečně pozastaví grabbing, 
    aby hardware nevracel Gain zpět do automatiky.
    """
    exposure_time = kwargs.get('exposure_time', args[0] if len(args) > 0 else None)
    gain = kwargs.get('gain', args[1] if len(args) > 1 else None)
    
    cam = get_camera()
    if cam:
        try:
            nodemap = cam.GetNodeMap()
            
            # --- KLÍČOVÝ KROK: PŘERUŠENÍ STREAMU PRO ZÁPIS REGISTRŮ ---
            is_grabbing_before = cam.IsGrabbing()
            if is_grabbing_before:
                cam.StopGrabbing()

            # --- 1. ODSTAVENÍ AUTOMATIKY ---
            try:
                if nodemap.GetNode("ExposureAuto") is not None:
                    cam.ExposureAuto.SetValue("Off")
                if nodemap.GetNode("GainAuto") is not None:
                    cam.GainAuto.SetValue("Off")
            except Exception as e_auto:
                print(f"⚠️ Selhalo nastavení automatických smyček: {e_auto}")

            # --- 2. ZÁPIS HARDWAROVÉ EXPOZICE ---
            if exposure_time is not None:
                try:
                    if nodemap.GetNode("ExposureTime") is not None:
                        cam.ExposureTime.SetValue(float(exposure_time))
                except Exception as e_exp:
                    print(f"❌ Nelze nastavit ExposureTime: {e_exp}")

            # --- 3. ZÁPIS HARDWAROVÉHO GAINU ---
            if gain is not None:
                try:
                    if nodemap.GetNode("GainSelector") is not None:
                        cam.GainSelector.SetValue("All")
                    
                    if nodemap.GetNode("Gain") is not None:
                        val_to_set = max(cam.Gain.GetMin(), min(cam.Gain.GetMax(), float(gain)))
                        cam.Gain.SetValue(val_to_set)
                except Exception as e_gain:
                    print(f"❌ Nelze aplikovat Gain: {e_gain}")

            # --- 4. OPĚTOVNÉ NASTARTOVÁNÍ STREAMU ---
            if is_grabbing_before:
                cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            
            # --- 5. SAMOTNÉ SEJMUTÍ SNÍMKU ---
            if cam.IsGrabbing():
                grab_result = cam.RetrieveResult(2000, pylon.TimeoutHandling_Return)
                if grab_result.GrabSucceeded():
                    img = Image.fromarray(grab_result.Array).convert("RGB")
                    grab_result.Release()
                    return img, "OK"
                grab_result.Release()
                
        except Exception as e:
            # V případě havárie se pokusíme kameru nechat běžet
            try: cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            except: pass
            return None, f"Chyba registrů kamery: {e}"
            
    return None, "Kamera negrebuje nebo vypršel timeout."