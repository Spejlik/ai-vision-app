import os
import streamlit as st
from pypylon import pylon
from PIL import Image

# ==============================================================================
# 🍏 1. CHRÁNĚNÁ MEZIPAMĚŤ PRO JEDNOTNÝ HARDWAROVÝ HANDLE (VALEO/ELVAC STANDARD)
# ==============================================================================
@st.cache_resource(show_spinner=False)
def get_cached_camera_instance(device_name):
    """
    Udržuje exkluzivní a stabilní síťové připojení ke konkrétní kameře v RAM.
    Streamlit díky tomu při obnovení stránky (Rerun) nezpůsobí kolizi socketů.
    """
    try:
        tl_factory = pylon.TlFactory.GetInstance()
        devices = tl_factory.EnumerateDevices()
        
        target_device_info = None
        for d in devices:
            if d.GetUserDefinedName() == device_name:
                target_device_info = d
                break
                
        if target_device_info is None:
            return None
            
        # Vytvoření instantní kamery z továrny Basler
        camera = pylon.InstantCamera(tl_factory.CreateDevice(target_device_info))
        camera.SetCameraContext(0)  # Prevence kolizí vláken ve Windows 11
        camera.Open()
        return camera
    except Exception as e:
        print(f"❌ [HARDWARE] Selhal pokus o inicializaci {device_name}: {e}")
        return None

# ==============================================================================
# 🍏 2. HLAVNÍ FUNKCE PRO SNÍMÁNÍ OBRAZU S AUTOMATICKÝM PŘEPÍNÁNÍM
# ==============================================================================
def capture_live_frame(device_name="Kamera1"):
    try:
        from pypylon import pylon
        
        # 🍏 1. AUTOMATICKÝ SCAN SÍTĚ (ŽÁDNÝ RUČNÍ SEZNAM!)
        tl_factory = pylon.TlFactory.GetInstance()
        devices = tl_factory.EnumerateDevices()
        
        # Samotný pylon nám vrátí seznam všech reálně zapojených kamer lisu
        all_online_cameras = [d.GetUserDefinedName() for d in devices if d.GetUserDefinedName()]
        
        # 2. DYNAMICKÉ ZAVÍRÁNÍ OSTATNÍCH KAMER
        # Ať už jich máš na lise 3, 5 nebo 10, kód automaticky uspí ty, co zrovna nesleduješ
        for cam_name in all_online_cameras:
            if cam_name != device_name:
                try:
                    other_cam_handle = get_cached_camera_instance(cam_name)
                    if other_cam_handle and other_cam_handle.IsOpen():
                        if other_cam_handle.IsGrabbing():
                            other_cam_handle.StopGrabbing()
                        other_cam_handle.Close()
                except Exception:
                    pass

        # 3. NAČTENÍ AKTIVNÍ KAMERY Z CACHE
        cam = get_cached_camera_instance(device_name)
        
        if cam is None:
            return None, f"Kamera '{device_name}' nebyla v síti nalezena nebo je obsazená."
            
        if not cam.IsOpen():
            cam.Open()

        # 4. PROVEDENÍ SNÍMKU
        grab_result = cam.GrabOne(5000)
        if grab_result.GrabSucceeded():
            converter = pylon.ImageFormatConverter()
            converter.OutputPixelFormat = pylon.PixelType_RGB8packed
            pylon_image = converter.Convert(grab_result)
            
            img = Image.fromarray(pylon_image.GetArray())
            grab_result.Release()
            return img, f"{device_name} OK"
        else:
            if 'grab_result' in locals():
                grab_result.Release()
            return None, "Chyba: Nepodařilo se vyjmout snímek z bufferu sběrnice."

    except Exception as e:
        return None, f"Chyba hardwaru kamery: {str(e)}"

# ==============================================================================
# 🍏 3. ZÁPIS PARAMETRŮ (EXPOZICE, GAIN) BEZ BLIKÁNÍ A CHYB
# ==============================================================================
def set_hardware_parameters(exposure_val, gain_val, device_name="Kamera1"):
    """Zápis hodnot přímo do aktivní cachované instance kamery a vynucení Free Run."""
    cam = get_cached_camera_instance(device_name)
    
    if cam and cam.IsOpen():
        try:
            nodemap = cam.GetNodeMap()
            
            # --- VYNUCENÝ HARDWAROVÝ RESET TRIGGERU PRO ŽIVÝ PREVIEW ---
            t_mode = nodemap.GetNode("TriggerMode")
            if t_mode is not None and t_mode.GetValue() != "Off":
                t_mode.SetValue("Off")

            # --- MATEMATICKÁ POJISTKA PRO INC = 35 (ELVAC STANDARD) ---
            raw_exposure = int(exposure_val)
            remainder = (raw_exposure - 35) % 35
            if remainder != 0:
                raw_exposure = raw_exposure - remainder  # Zaokrouhlení dolů na validní krok krokovače čipu
            
            # Zápis elektronické uzávěrky (Anti-Flicker stabilizace)
            exp_node = nodemap.GetNode("ExposureTimeRaw") or nodemap.GetNode("ExposureTime")
            if exp_node: 
                exp_node.SetValue(int(raw_exposure))
            
            # Zápis zesílení obrazu (Gain)
            gain_node = nodemap.GetNode("GainRaw") or nodemap.GetNode("Gain")
            if gain_node: 
                gain_node.SetValue(int(gain_val))
                
        except Exception as e:
            print(f"⚠️ [MANAGER] Chyba zápisu parametrů pro {device_name}: {e}")

# ==============================================================================
# 🍏 4. UKLÁDÁNÍ A NAČÍTÁNÍ PFS PROFILŮ VALEO LINCE
# ==============================================================================
def save_camera_features_to_pfs(project_name, position_num, device_name="Kamera1"):
    try:
        cam = get_cached_camera_instance(device_name)
        if cam and cam.IsOpen():
            os.makedirs("profiles", exist_ok=True)
            pfs_path = f"profiles/{project_name}_pos_{position_num}_{device_name}.pfs"
            pylon.FeaturePersistence.Save(pfs_path, cam.GetNodeMap())
            return True, pfs_path
    except Exception as e:
        return False, str(e)
    return False, "Kamera není inicializována."

def load_camera_features_from_pfs(project_name, position_num, device_name="Kamera1"):
    cam = get_cached_camera_instance(device_name)
    if cam and cam.IsOpen():
        pfs_path = f"profiles/{project_name}_pos_{position_num}_{device_name}.pfs"
        if os.path.exists(pfs_path):
            try:
                if cam.IsGrabbing():
                    cam.StopGrabbing()
                pylon.FeaturePersistence.Load(pfs_path, cam.GetNodeMap(), True)
                cam.StartGrabbingMax(30, pylon.GrabStrategy_LatestImageOnly)
                return True, "PFS profil úspěšně nahrán do registrů."
            except Exception as e:
                return False, str(e)
    return False, "Profil pro tuto pozici a kameru neexistuje."