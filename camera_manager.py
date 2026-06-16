import os
from pypylon import pylon
from camera_core import hardware_core

def capture_live_frame():
    """Vrací poslední platný snímek ze sdílené paměti core modulu."""
    img, cam_name = hardware_core.get_latest_image()
    if img is not None:
        return img, cam_name
    return None, "Čekání na uvolnění sběrnice kamery..."

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