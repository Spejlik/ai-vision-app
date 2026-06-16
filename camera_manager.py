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
    Robustní zachycení snímku z Basler kamery.
    Kompletně vypíná hardwarové automatiky lisu, aby nedocházelo k přepisování Gainu.
    """
    exposure_time = kwargs.get('exposure_time', args[0] if len(args) > 0 else None)
    gain = kwargs.get('gain', args[1] if len(args) > 1 else None)
    
    cam = get_camera()
    if cam and cam.IsGrabbing():
        try:
            nodemap = cam.GetNodeMap()

            # --- 1. VYPNUTÍ VEŠKERÝCH HARDWAROVÝCH AUTOMATIK (KLÍČOVÝ KROK) ---
            try:
                # Vypnutí automatické expozice
                if nodemap.GetNode("ExposureAuto") is not None:
                    cam.ExposureAuto.SetValue("Off")
                
                # Vypnutí automatického zesílení (Continuous/Once -> Off)
                if nodemap.GetNode("GainAuto") is not None:
                    cam.GainAuto.SetValue("Off")
            except Exception as e_auto:
                print(f"⚠️ Nelze vypnout automatické smyčky jasu: {e_auto}")

            # --- 2. HARDWAROVÝ ZÁPIS EXPOZICE ---
            if exposure_time is not None:
                try:
                    if nodemap.GetNode("ExposureTime") is not None:
                        cam.ExposureTime.SetValue(float(exposure_time))
                except Exception as e_exp:
                    print(f"❌ Nelze nastavit ExposureTime: {e_exp}")

            # --- 3. HARDWAROVÝ ZÁPIS GAINU S UZAMČENÍM ---
            if gain is not None:
                try:
                    # Nastavení selectoru na hlavní kanál před zápisem
                    if nodemap.GetNode("GainSelector") is not None:
                        if "All" in cam.GainSelector.GetSymbolics():
                            cam.GainSelector.SetValue("All")
                    
                    # Zápis do standardního float registru 'Gain'
                    if nodemap.GetNode("Gain") is not None:
                        val_to_set = max(cam.Gain.GetMin(), min(cam.Gain.GetMax(), float(gain)))
                        cam.Gain.SetValue(val_to_set)
                        
                    # Fallback pro starší modely s 'GainRaw'
                    elif nodemap.GetNode("GainRaw") is not None:
                        val_to_set = max(cam.GainRaw.GetMin(), min(cam.GainRaw.GetMax(), int(round(float(gain)))))
                        cam.GainRaw.SetValue(val_to_set)
                        
                except Exception as e_gain:
                    print(f"❌ Nelze aplikovat manuální Gain: {e_gain}")
        
            # --- 4. ZÍSKÁNÍ SNÍMKU Z BUFFERU ---
            grab_result = cam.RetrieveResult(2000, pylon.TimeoutHandling_Return)
            if grab_result.GrabSucceeded():
                img = Image.fromarray(grab_result.Array).convert("RGB")
                grab_result.Release()
                return img, "OK"
            grab_result.Release()
        except Exception as e:
            return None, f"Chyba registrů kamery: {e}"
            
    return None, "Kamera negrebuje nebo vypršel timeout."