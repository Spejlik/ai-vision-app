import time
from PIL import Image
from pypylon import pylon

_camera = None
_last_exposure = None
_last_gain = None

def get_camera():
    global _camera
    if _camera is None:
        try:
            tl_factory = pylon.TlFactory.GetInstance()
            devices = tl_factory.EnumerateDevices()
            if not devices: 
                return None
            
            # Elvac sychr: Vytvoříme zařízení s požadavkem na kontrolu (Exclusive Access)
            device_info = devices[0]
            _camera = pylon.InstantCamera(tl_factory.CreateDevice(device_info))
            _camera.Open()
            
            # Pokud se druhá aplikace pokouší kameru ovládat, toto vynutí ignorování externích triggerů
            try:
                nodemap = _camera.GetNodeMap()
                # Pokud kamera visí v režimu Continuous triggeru z Moxa modulu, přepneme ji na softwarový
                trigger_selector = nodemap.GetNode("TriggerSelector")
                if trigger_selector is not None:
                    trigger_selector.SetValue("FrameStart")
                    trigger_mode = nodemap.GetNode("TriggerMode")
                    if trigger_mode is not None:
                        trigger_mode.SetValue("Off")
            except:
                pass
                
            _camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            print("🍏 Kamera úspěšně otevřena v režimu Exclusive Access.")
        except Exception as e:
            print(f"⚠️ Chyba inicializace kamery (přístup blokován jinou aplikací): {e}")
            _camera = None
            return None
    return _camera

def capture_live_frame(*args, **kwargs):
    """
    Robustní průmyslové snímání. Zapisuje parametry do registrů POUZE tehdy,
    když operátor pohne sliderem, což zamezuje zahlcování GigE sběrnice a problikávání.
    """
    global _last_exposure, _last_gain
    
    exposure_time = kwargs.get('exposure_time', args[0] if len(args) > 0 else None)
    gain = kwargs.get('gain', args[1] if len(args) > 1 else None)
    
    cam = get_camera()
    if cam and cam.IsGrabbing():
        try:
            nodemap = cam.GetNodeMap()
            
            # Kontrola, zda operátor reálně pohnul slidery v rozhraní
            exp_changed = exposure_time is not None and float(exposure_time) != _last_exposure
            gain_changed = gain is not None and float(gain) != _last_gain

            # --- ZÁPIS DO HARDWARU PROBĚHNE POUZE PŘI ZMĚNĚ HODNOTY SLIDERU ---
            if exp_changed or gain_changed:
                try:
                    # Vypnutí automatických smyček
                    exp_auto = nodemap.GetNode("ExposureAuto")
                    if exp_auto is not None: exp_auto.SetValue("Off")
                    gain_auto = nodemap.GetNode("GainAuto")
                    if gain_auto is not None: gain_auto.SetValue("Off")

                    # Zápis expozice při změně
                    if exp_changed:
                        exp_node = nodemap.GetNode("ExposureTime") or nodemap.GetNode("ExposureTimeAbs")
                        if exp_node is not None:
                            exp_node.SetValue(max(exp_node.GetMin(), min(exp_node.GetMax(), float(exposure_time))))
                        else:
                            exp_raw = nodemap.GetNode("ExposureTimeRaw")
                            if exp_raw is not None:
                                exp_raw.SetValue(max(exp_raw.GetMin(), min(exp_raw.GetMax(), int(round(float(exposure_time))))))
                        _last_exposure = float(exposure_time)

                    # Zápis zisku (gain) při změně
                    if gain_changed:
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
                        _last_gain = float(gain)
                        
                except Exception as e_reg:
                    print(f"⚠️ Nelze zapsat změněný registr: {e_reg}")

            # --- ČISTÝ RYCHLÝ STREAM BEZ BOMBARDOVÁNÍ REGISTRŮ ---
            grab_result = cam.RetrieveResult(2000, pylon.TimeoutHandling_Return)
            if grab_result.GrabSucceeded():
                img = Image.fromarray(grab_result.Array).convert("RGB")
                grab_result.Release()
                return img, "OK"
            grab_result.Release()
            
        except Exception as e:
            return None, f"Chyba bufferu kamery: {e}"
            
    return None, "Kamera negrebuje."
    
import os

def load_camera_features_from_pfs(project_name, position_num):
    """
    Ekvivalent tlačítka 'AKTUALIZOVAT PFS'.
    Načte kompletní hardwarovou konfiguraci kamery (včetně expozice, gainu, 
    triggerů a filtrů) ze souboru .pfs pro konkrétní pozici lisu.
    """
    cam = get_camera()
    if cam:
        pfs_path = f"profiles/{project_name}_pos_{position_num}.pfs"
        if os.path.exists(pfs_path):
            try:
                # Pro klidný import parametrů do čipu dočasně zastavíme stream
                is_grabbing = cam.IsGrabbing()
                if is_grabbing:
                    cam.StopGrabbing()
                
                # Průmyslový import celého stromu funkcí přes Pylon Feature Stream
                pylon.FeaturePersistence.Load(pfs_path, cam.GetNodeMap(), True)
                
                if is_grabbing:
                    cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
                print(f"🍏 PFS konfigurace úspěšně zavedena do kamery: {pfs_path}")
                return True, "OK"
            except Exception as e:
                return False, f"Chyba při nahrávání PFS profilu: {e}"
        else:
            return False, f"Profil pro pozici {position_num} zatím neexistuje (PFS soubor nenalezen)."
    return False, "Kamera není inicializována."


def save_camera_features_to_pfs(project_name, position_num):
    """
    Ekvivalent tlačítka 'VYTVOŘIT PFS'.
    Vezme aktuální kompletní nastavení z kamery (tak, jak ho operátor vyladil slidery)
    a uloží ho do souboru .pfs na disk pro pozdější automatické načtení.
    """
    cam = get_camera()
    if cam:
        try:
            os.makedirs("profiles", exist_ok=True)
            pfs_path = f"profiles/{project_name}_pos_{position_num}.pfs"
            
            # Průmyslový export celého registrového stromu do textového PFS souboru
            pylon.FeaturePersistence.Save(pfs_path, cam.GetNodeMap())
            print(f"💾 Aktuální hardwarový stav kamery uložen do PFS: {pfs_path}")
            return True, pfs_path
        except Exception as e:
            return False, str(e)
    return False, "Kamera není inicializována."    