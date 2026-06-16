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

# Na úplný začátek souboru (pod importy) přidej tyto proměnné pro hlídání změny:
_last_exposure = None
_last_gain = None

def capture_live_frame(*args, **kwargs):
    """
    Robustní zachycení snímku z Basler kamery.
    Zapisuje do hardwaru POUZE při reálné změně slideru, což eliminuje problikávání.
    """
    global _last_exposure, _last_gain
    
    exposure_time = kwargs.get('exposure_time', args[0] if len(args) > 0 else None)
    gain = kwargs.get('gain', args[1] if len(args) > 1 else None)
    
    cam = get_camera()
    if cam:
        try:
            nodemap = cam.GetNodeMap()
            
            # Zjistíme, zda operátor pohnul některým ze sliderů
            exposure_changed = exposure_time is not None and float(exposure_time) != _last_exposure
            gain_changed = gain is not None and float(gain) != _last_gain

            # --- POKUD DOŠLO KE ZMĚNĚ, ZAPÍŠEME REGISTRY (JINAK BĚŽÍ ČISTÝ STREAM) ---
            if exposure_changed or gain_changed:
                try:
                    # 1. Dočasně zastavíme grabování pro klidný zápis do čipu
                    if cam.IsGrabbing():
                        cam.StopGrabbing()
                    
                    # 2. Vypnutí linkové automatiky
                    if nodemap.GetNode("ExposureAuto") is not None:
                        cam.ExposureAuto.SetValue("Off")
                    if nodemap.GetNode("GainAuto") is not None:
                        cam.GainAuto.SetValue("Off")
                    
                    # 3. Zápis Expozice (pokud se změnila)
                    if exposure_changed and nodemap.GetNode("ExposureTime") is not None:
                        cam.ExposureTime.SetValue(float(exposure_time))
                        _last_exposure = float(exposure_time)
                        
                    # 4. Zápis Gainu (pokud se změnil)
                    if gain_changed:
                        if nodemap.GetNode("GainSelector") is not None:
                            cam.GainSelector.SetValue("All")
                        if nodemap.GetNode("Gain") is not None:
                            val_to_set = max(cam.Gain.GetMin(), min(cam.Gain.GetMax(), float(gain)))
                            cam.Gain.SetValue(val_to_set)
                            _last_gain = float(gain)

                except Exception as e_reg:
                    print(f"⚠️ Chyba při zápisu registru: {e_reg}")
                finally:
                    # 5. Vždy stream znovu nahodíme
                    if not cam.IsGrabbing():
                        cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

            # --- SAMOTNÉ SEJMUTÍ SNÍMKU (BĚŽÍ MAXIMÁLNÍ RYCHLOSTÍ) ---
            if cam.IsGrabbing():
                grab_result = cam.RetrieveResult(2000, pylon.TimeoutHandling_Return)
                if grab_result.GrabSucceeded():
                    img = Image.fromarray(grab_result.Array).convert("RGB")
                    grab_result.Release()
                    return img, "OK"
                grab_result.Release()
                
        except Exception as e:
            # Sychr pro případ nečekaného pádu
            try: 
                if not cam.IsGrabbing(): cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            except: pass
            return None, f"Chyba lupu kamery: {e}"
            
    return None, "Kamera negrebuje nebo vypršel timeout."