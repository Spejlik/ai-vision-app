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
            
            # --- ELVAC TVRDÝ RESET DO TOVÁRNÍHO NASTAVENÍ (VYMAŽE SKRYTÉ ZÁMKY) ---
            try:
                nodemap = _camera.GetNodeMap()
                user_set_selector = nodemap.GetNode("UserSetSelector")
                user_set_load = nodemap.GetNode("UserSetLoad")
                
                if user_set_selector is not None and user_set_load is not None:
                    # Přepneme z "UserSet1" na čistý tovární "Default" profil, 
                    # což kompletně vymaže uvízlé regulace jasu na čipu
                    user_set_selector.SetValue("Default")
                    user_set_load.Execute()
                    print("🍏 Kamera úspěšně resetována do čistého továrního stavu Default.")
            except Exception as e_preset:
                print(f"⚠️ Nepodařilo se resetovat profil kamery: {e_preset}")
            
            _camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        except Exception as e:
            print(f"⚠️ Chyba inicializace kamery: {e}")
            return None
    return _camera

def capture_live_frame(*args, **kwargs):
    """
    Tiché a robustní zachycení snímku z 5MPx Basler kamery.
    Zapisuje hodnoty bez zahlcování konzole výjimkami.
    """
    exposure_time = kwargs.get('exposure_time', args[0] if len(args) > 0 else None)
    gain = kwargs.get('gain', args[1] if len(args) > 1 else None)
    
    cam = get_camera()
    if cam and cam.IsGrabbing():
        try:
            nodemap = cam.GetNodeMap()

            # --- 1. ODSTAVENÍ AUTOMATIKY ---
            try:
                exp_mode = nodemap.GetNode("ExposureMode")
                if exp_mode is not None: exp_mode.SetValue("Timed")
                exp_auto = nodemap.GetNode("ExposureAuto")
                if exp_auto is not None: exp_auto.SetValue("Off")
                gain_auto = nodemap.GetNode("GainAuto")
                if gain_auto is not None: gain_auto.SetValue("Off")
            except:
                pass

            # --- 2. ZÁPIS ČASU EXPOZICE ---
            if exposure_time is not None:
                try:
                    exp_node = nodemap.GetNode("ExposureTime") or nodemap.GetNode("ExposureTimeAbs")
                    if exp_node is not None:
                        exp_node.SetValue(max(exp_node.GetMin(), min(exp_node.GetMax(), float(exposure_time))))
                    else:
                        exp_raw = nodemap.GetNode("ExposureTimeRaw")
                        if exp_raw is not None:
                            exp_raw.SetValue(max(exp_raw.GetMin(), min(exp_raw.GetMax(), int(round(float(exposure_time))))))
                except:
                    pass

            # --- 3. ZÁPIS GAINU ---
            if gain is not None:
                try:
                    gain_sel = nodemap.GetNode("GainSelector")
                    if gain_sel is not None and "All" in gain_sel.GetSymbolics():
                        gain_sel.SetValue("All")

                    gain_node = nodemap.GetNode("Gain") or nodemap.GetNode("GainAll")
                    if gain_node is not None:
                        gain_node.SetValue(max(gain_node.GetMin(), min(gain_node.GetMax(), float(gain))))
                    else:
                        gain_raw = nodemap.GetNode("GainRaw")
                        if gain_raw is not None:
                            gain_raw.SetValue(max(gain_raw.GetMin(), min(gain_raw.GetMax(), int(round(float(gain))))))
                except:
                    pass
        
            # --- 4. VYTAŽENÍ SNÍMKU ---
            grab_result = cam.RetrieveResult(2000, pylon.TimeoutHandling_Return)
            if grab_result.GrabSucceeded():
                img = Image.fromarray(grab_result.Array).convert("RGB")
                grab_result.Release()
                return img, "OK"
            grab_result.Release()
            
        except Exception as e:
            return None, f"Chyba bufferu kamery: {e}"
            
    return None, "Kamera negrebuje."