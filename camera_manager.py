import time
import os
from PIL import Image
from pypylon import pylon
import streamlit as st

_camera = None
_last_exposure = None
_last_gain = None
_last_valid_img = None

def get_camera():
    if "pylon_camera_instance" in st.session_state and st.session_state.pylon_camera_instance is not None:
        try:
            if st.session_state.pylon_camera_instance.IsOpen():
                return st.session_state.pylon_camera_instance
        except:
            pass

    try:
        tl_factory = pylon.TlFactory.GetInstance()
        devices = tl_factory.EnumerateDevices()
        if not devices: 
            return None
        
        cam = pylon.InstantCamera(tl_factory.CreateDevice(devices[0]))
        cam.Open()
        
        try:
            grabber_nodemap = cam.GetStreamGrabberNodeMap()
            max_buffers = grabber_nodemap.GetNode("MaxNumBuffer")
            if max_buffers is not None:
                max_buffers.SetValue(30)
        except:
            pass
            
        cam.StartGrabbingMax(30, pylon.GrabStrategy_LatestImageOnly)
        st.session_state.pylon_camera_instance = cam
        print("🍏 [HARDWARE] Permanentní instance kamery uzamčena pro aplikaci.")
        return cam
    except Exception as e:
        st.session_state.pylon_camera_instance = None
        return None

def capture_live_frame(*args, **kwargs):
    """
    Vysoce stabilní snímání pro 5MPx starší Basler čipy (SFNC v1).
    Ověřuje alternativní registry GainAll / Gain / GainRaw pro starší firmware.
    """
    global _last_exposure, _last_gain, _last_valid_img
    
    # Načtení živých hodnot ze sliderů
    exposure_time = st.session_state.get("exp_slider_val", 30000)
    gain = st.session_state.get("gain_slider_val", 12)
    
    cam = get_camera()
    
    if cam is None or not cam.IsOpen():
        if _last_valid_img is not None:
            return _last_valid_img, "OK (Záložní buffer)"
        return None, "Kamera je momentálně blokována jinými thready lisu."

    try:
        if not cam.IsGrabbing():
            cam.StartGrabbingMax(30, pylon.GrabStrategy_LatestImageOnly)

        nodemap = cam.GetNodeMap()
        
        exp_changed = _last_exposure is None or float(exposure_time) != _last_exposure
        gain_changed = _last_gain is None or float(gain) != _last_gain

        if exp_changed or gain_changed:
            # Vypnutí automatik (bezpečně)
            for auto_node in ["ExposureAuto", "GainAuto"]:
                try:
                    node = nodemap.GetNode(auto_node)
                    if node: node.SetValue("Off")
                except: pass

            # --- 🍏 1. NEPRŮSTŘELNÝ ZÁPIS EXPOZICE ---
            if exp_changed:
                try:
                    exp_node = nodemap.GetNode("ExposureTime") or nodemap.GetNode("ExposureTimeAbs") or nodemap.GetNode("ExposureTimeRaw")
                    if exp_node is not None:
                        # Zkusíme nastavit jako float, pokud selže, tak jako int
                        try:
                            exp_node.SetValue(float(exposure_time))
                        except:
                            exp_node.SetValue(int(round(float(exposure_time))))
                    _last_exposure = float(exposure_time)
                except:
                    pass

            # --- 🍏 2. ELVAC ROZŠÍŘENÝ ZÁPIS GAINU (ZISKU) ---
            if gain_changed:
                gain_written = False
                # Projdeme postupně všechny možné názvy registru, které starší 5MPx čipy používají
                for gain_name in ["GainAll", "Gain", "GainRaw"]:
                    try:
                        g_node = nodemap.GetNode(gain_name)
                        if g_node is not None:
                            # Podle typu uzlu určíme, zda zapsat Int nebo Float
                            node_type = g_node.GetPrincipalInterfaceType() if hasattr(g_node, 'GetPrincipalInterfaceType') else None
                            
                            if node_type == pylon.intfIInteger or "Raw" in gain_name:
                                g_node.SetValue(int(round(float(gain))))
                            else:
                                g_node.SetValue(max(g_node.GetMin(), min(g_node.GetMax(), float(gain))))
                            
                            gain_written = True
                            break # Jakmile se jeden zápis povede, končíme smyčku
                    except:
                        continue
                
                if gain_written:
                    _last_gain = float(gain)
                else:
                    print("⚠️ Žádný z uzlů [GainAll, Gain, GainRaw] nebyl v této kameře nalezen.")

        # Stažení snímku z kamery
        grab_result = cam.RetrieveResult(250, pylon.TimeoutHandling_Return)
        if grab_result and grab_result.GrabSucceeded():
            img = Image.fromarray(grab_result.Array).convert("RGB")
            _last_valid_img = img
            grab_result.Release()
            return img, "OK"
        
        if grab_result:
            grab_result.Release()
            
    except Exception as e_grab:
        pass

    if _last_valid_img is not None:
        return _last_valid_img, "OK (Záložní buffer)"
        
    return None, "Čekání na uvolnění sběrnice kamery..."

def load_camera_features_from_pfs(project_name, position_num):
    cam = get_camera()
    if cam:
        # Vyhledáme jakýkoliv .pfs soubor ve složce profiles, který začíná správným projektem a číslem pozice
        profiles_dir = "profiles"
        if os.path.exists(profiles_dir):
            prefix = f"{project_name}_pos_{position_num}"
            found_files = [f for f in os.listdir(profiles_dir) if f.startswith(prefix) and f.endswith(".pfs")]
            
            if found_files:
                pfs_path = os.path.join(profiles_dir, found_files[0])
                try:
                    is_grabbing = cam.IsGrabbing()
                    if is_grabbing: cam.StopGrabbing()
                    pylon.FeaturePersistence.Load(pfs_path, cam.GetNodeMap(), True)
                    if is_grabbing: cam.StartGrabbingMax(30, pylon.GrabStrategy_LatestImageOnly)
                    
                    # Extrahujeme textový popis z názvu souboru pro zobrazení operátorovi
                    desc_part = found_files[0].replace(prefix, "").replace(".pfs", "").replace("_", " ")
                    display_desc = desc_part.strip() if desc_part.strip() else "Bez popisu"
                    return True, f"Profil načten: {display_desc}"
                except Exception as e:
                    return False, f"Chyba při nahrávání PFS profilu: {e}"
        
        return False, f"Profil pro pozici {position_num} zatím neexistuje."
    return False, "Kamera není inicializována."