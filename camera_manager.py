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
    Robustní zachycení snímku z 5MPx Basler kamery – Elvac / Valeo Standard.
    Bezpečně ověřuje existenci uzlů bez neexistujících metod na IEnumeration objektech.
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
                if exp_mode is not None:
                    exp_mode.SetValue("Timed")

                exp_auto = nodemap.GetNode("ExposureAuto")
                if exp_auto is not None:
                    exp_auto.SetValue("Off")

                gain_auto = nodemap.GetNode("GainAuto")
                if gain_auto is not None:
                    gain_auto.SetValue("Off")
            except Exception as e_auto:
                print(f"⚠️ Selhalo nastavení režimu automatiky: {e_auto}")

            # --- 2. ZÁPIS ČASU EXPOZICE ---
            if exposure_time is not None:
                try:
                    exp_time_node = nodemap.GetNode("ExposureTime")
                    if exp_time_node is not None:
                        val = max(exp_time_node.GetMin(), min(exp_time_node.GetMax(), float(exposure_time)))
                        exp_time_node.SetValue(val)
                    else:
                        exp_time_raw = nodemap.GetNode("ExposureTimeRaw")
                        if exp_time_raw is not None:
                            val = max(exp_time_raw.GetMin(), min(exp_time_raw.GetMax(), int(round(float(exposure_time)))))
                            exp_time_raw.SetValue(val)
                except Exception as e_exp:
                    print(f"❌ Chyba zápisu expozice: {e_exp}")

            # --- 3. ZÁPIS GAINU (ZESÍLENÍ) ---
            if gain is not None:
                try:
                    gain_sel = nodemap.GetNode("GainSelector")
                    if gain_sel is not None:
                        if "All" in gain_sel.GetSymbolics():
                            gain_sel.SetValue("All")

                    gain_node = nodemap.GetNode("Gain")
                    if gain_node is not None:
                        val = max(gain_node.GetMin(), min(gain_node.GetMax(), float(gain)))
                        gain_node.SetValue(val)
                    else:
                        gain_raw = nodemap.GetNode("GainRaw")
                        if gain_raw is not None:
                            val = max(gain_raw.GetMin(), min(cam.GainRaw.GetMax(), int(round(float(gain)))))
                            gain_raw.SetValue(val)
                except Exception as e_gain:
                    print(f"❌ Chyba zápisu zisku: {e_gain}")
        
            # --- 4. VYTAŽENÍ SNÍMKU Z BUFFERU ČIPU ---
            grab_result = cam.RetrieveResult(2000, pylon.TimeoutHandling_Return)
            if grab_result.GrabSucceeded():
                img = Image.fromarray(grab_result.Array).convert("RGB")
                grab_result.Release()
                return img, "OK"
            grab_result.Release()
            
        except Exception as e:
            return None, f"Chyba bufferu kamery: {e}"
            
    return None, "Kamera negrebuje."