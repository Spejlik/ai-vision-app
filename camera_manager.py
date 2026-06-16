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
    Robustní zachycení snímku z 5MPx Basler kamery – SFNC v1/v2 hybridní standard.
    Natvrdo odstaví automatiku a zapíše parametry bez chyb v genicam_wrap.
    """
    exposure_time = kwargs.get('exposure_time', args[0] if len(args) > 0 else None)
    gain = kwargs.get('gain', args[1] if len(args) > 1 else None)
    
    cam = get_camera()
    if cam and cam.IsGrabbing():
        try:
            nodemap = cam.GetNodeMap()

            # --- 1. ODSTAVENÍ AUTOMATIKY (STARŠÍ OVLÁDÁNÍ 5MPX ČIPŮ) ---
            try:
                # Nastavení módu expozice na časový (Timed)
                exp_mode = nodemap.GetNode("ExposureMode")
                if exp_mode is not None and exp_mode.IsValid():
                    exp_mode.SetValue("Timed")

                # Vypnutí automatické expozice (SFNC v1/v2 sychr)
                exp_auto = nodemap.GetNode("ExposureAuto")
                if exp_auto is not None and exp_auto.IsValid():
                    exp_auto.SetValue("Off")

                # Vypnutí automatického Gainu
                gain_auto = nodemap.GetNode("GainAuto")
                if gain_auto is not None and gain_auto.IsValid():
                    gain_auto.SetValue("Off")
            except Exception as e_auto:
                print(f"⚠️ Selhalo nastavení režimu automatiky: {e_auto}")

            # --- 2. ZÁPIS ČASU EXPOZICE ---
            if exposure_time is not None:
                try:
                    exp_time_node = nodemap.GetNode("ExposureTime")
                    if exp_time_node is not None and exp_time_node.IsValid():
                        val = max(exp_time_node.GetMin(), min(exp_time_node.GetMax(), float(exposure_time)))
                        exp_time_node.SetValue(val)
                    else:
                        exp_time_raw = nodemap.GetNode("ExposureTimeRaw")
                        if exp_time_raw is not None and exp_time_raw.IsValid():
                            val = max(exp_time_raw.GetMin(), min(exp_time_raw.GetMax(), int(round(float(exposure_time)))))
                            exp_time_raw.SetValue(val)
                except Exception as e_exp:
                    print(f"❌ Chyba zápisu expozice: {e_exp}")

            # --- 3. ZÁPIS GAINU (ZESÍLENÍ) ---
            if gain is not None:
                try:
                    # Nastavení selektoru (u 5MPx modelů často nepovinné, ale sychr)
                    gain_sel = nodemap.GetNode("GainSelector")
                    if gain_sel is not None and gain_sel.IsValid():
                        if "All" in gain_sel.GetSymbolics():
                            gain_sel.SetValue("All")

                    # Zápis do hlavního uzlu jasu
                    gain_node = nodemap.GetNode("Gain")
                    if gain_node is not None and gain_node.IsValid():
                        val = max(gain_node.GetMin(), min(gain_node.GetMax(), float(gain)))
                        gain_node.SetValue(val)
                    else:
                        gain_raw = nodemap.GetNode("GainRaw")
                        if gain_raw is not None and gain_raw.IsValid():
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