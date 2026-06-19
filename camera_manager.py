import os
from pypylon import pylon
from camera_core import hardware_core
from PIL import Image

# Globální proměnná pro udržení instance kamery (pokud ji tak v manažeru máte)
_active_camera_device = None
_last_opened_device_name = None
_active_camera_device = None
_last_opened_device_name = None

def capture_live_frame(device_name="Kamera1"):
    global _active_camera_device, _last_opened_device_name
    
    try:
        from pypylon import pylon
        
        # 🍏 DEFINITIVNÍ POJISTKA: Pokud měníme kameru, musíme instanci kompletně smazat z RAM
        if _active_camera_device is not None:
            if _last_opened_device_name != device_name:
                try:
                    if _active_camera_device.IsOpen():
                        _active_camera_device.Close()
                    # Natvrdo zničíme vnitřní C++ pointery Basleru
                    _active_camera_device.Destroy()
                except Exception:
                    pass
                _active_camera_device = None
                _last_opened_device_name = None

        # Pokud není otevřená žádná kamera, vytvoříme úplně čisté nové spojení
        if _active_camera_device is None:
            tl_factory = pylon.TlFactory.GetInstance()
            devices = tl_factory.EnumerateDevices()
            
            target_device_info = None
            for d in devices:
                # Kontrola shody s Pylon Device User ID (Kamera1 / Kamera2)
                if d.GetUserDefinedName() == device_name:
                    target_device_info = d
                    break
            
            if target_device_info is None:
                return None, f"Kamera s názvem '{device_name}' nebyla v síti nalezena."
            
            # Inicializace "od nuly"
            _active_camera_device = pylon.InstantCamera(tl_factory.CreateDevice(target_device_info))
            _active_camera_device.Open()
            _last_opened_device_name = device_name

        # --- TADY POKRAČUJE TVŮJ KÓD PRO GRABOVÁNÍ SNÍMKU (GrabOne) ---
        grab_result = _active_camera_device.GrabOne(5000)
        if grab_result.GrabSucceeded():
            from PIL import Image
            converter = pylon.ImageFormatConverter()
            converter.OutputPixelFormat = pylon.PixelType_RGB8packed
            pylon_image = converter.Convert(grab_result)
            
            img = Image.fromarray(pylon_image.GetArray())
            grab_result.Release()
            return img, f"{device_name} OK"
        else:
            grab_result.Release()
            return None, "Grab failed"

    except Exception as e:
        # Pokud cokoliv selže, raději vyčistíme proměnnou pro příští pokus
        _active_camera_device = None
        return None, f"Chyba hardwaru kamery: {str(e)}"

def set_hardware_parameters(exposure_val, gain_val):
    """Zápis hodnot ze sliderů UI přímo do běžící instance a vynucení Free Run."""
    if hardware_core.camera and hardware_core.camera.IsOpen():
        try:
            nodemap = hardware_core.camera.GetNodeMap()
            
            # --- 🍏 VYNUCENÝ HARDWAROVÝ RESET TRIGGERU ---
            t_mode = nodemap.GetNode("TriggerMode")
            if t_mode is not None and t_mode.GetValue() != "Off":
                t_mode.SetValue("Off")

            # --- 🍏 MATEMATICKÁ POJISTKA PRO INC = 35 (ELVAC STANDARD) ---
            # Vezmeme hodnotu ze slideru a matematicky ji zarovnáme na nejbližší násobek 35
            raw_exposure = int(exposure_val)
            remainder = (raw_exposure - 35) % 35
            if remainder != 0:
                raw_exposure = raw_exposure - remainder  # Zaokrouhlíme dolů na perfektně dělitelné číslo
            
            # Zápis elektronické uzávěrky bez rizika OutOfRangeException
            exp_node = nodemap.GetNode("ExposureTimeRaw") or nodemap.GetNode("ExposureTime")
            if exp_node: 
                exp_node.SetValue(int(raw_exposure))
            
            # Zápis zesílení obrazu (Gain 0-18)
            gain_node = nodemap.GetNode("GainRaw") or nodemap.GetNode("Gain")
            if gain_node: 
                gain_node.SetValue(int(gain_val))
        except Exception as e:
            print(f"⚠️ [MANAGER] Chyba zápisu parametrů: {e}")

def save_camera_features_to_pfs(project_name, position_num):
    try:
        if hardware_core.camera:
            os.makedirs("profiles", exist_ok=True)
            pfs_path = f"profiles/{project_name}_pos_{position_num}.pfs"
            pylon.FeaturePersistence.Save(pfs_path, hardware_core.camera.GetNodeMap())
            return True, pfs_path
    except Exception as e:
        return False, str(e)
    return False, "Kamera není inicializována."

def load_camera_features_from_pfs(project_name, position_num):
    if hardware_core.camera:
        pfs_path = f"profiles/{project_name}_pos_{position_num}.pfs"
        if os.path.exists(pfs_path):
            try:
                hardware_core.camera.StopGrabbing()
                pylon.FeaturePersistence.Load(pfs_path, hardware_core.camera.GetNodeMap(), True)
                hardware_core.camera.StartGrabbingMax(30, pylon.GrabStrategy_LatestImageOnly)
                return True, "PFS načteno"
            except Exception as e:
                return False, str(e)
    return False, "Profil neexistuje"