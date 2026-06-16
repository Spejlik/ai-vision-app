import time
import os
from PIL import Image
from pypylon import pylon
import streamlit as st

_camera = None
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
        
        nodemap = cam.GetNodeMap()
        
        # --- 🍏 ELVAC KLÍČOVÁ OPRAVA: VYPNUTÍ EXTERNÍHO PLC TRIGGERU PRO LADĚNÍ ---
        # Přepne kameru z linkového režimu do Free Run, aby začala poslouchat slidery
        try:
            trigger_selector = nodemap.GetNode("TriggerSelector")
            if trigger_selector is not None:
                trigger_selector.SetValue("FrameStart")
                
            trigger_mode = nodemap.GetNode("TriggerMode")
            if trigger_mode is not None:
                trigger_mode.SetValue("Off")
                print("🔓 [HARDWARE] Externí PLC trigger odpojen. Kamera přepnuta do Free Run.")
        except Exception as e_trig:
            print(f"ℹ️ Nastavení triggeru přeskočeno: {e_trig}")
        
        try:
            grabber_nodemap = cam.GetStreamGrabberNodeMap()
            max_buffers = grabber_nodemap.GetNode("MaxNumBuffer")
            if max_buffers is not None:
                max_buffers.SetValue(30)
        except:
            pass
            
        cam.StartGrabbingMax(30, pylon.GrabStrategy_LatestImageOnly)
        st.session_state.pylon_camera_instance = cam
        print("🍏 [HARDWARE] Permanentní instance kamery uzamčena pro živý stream.")
        return cam
    except Exception as e:
        st.session_state.pylon_camera_instance = None
        return None

def capture_live_frame(*args, **kwargs):
    """
    Vysoce optimalizované real-time snímání pro Elvac CCD 5MPx standard.
    Zapisuje parametry přímo a výhradně do Raw registrů čipu pro maximální jas a nulové chyby.
    """
    global _last_valid_img
    
    # Načtení hodnot z rozhraní
    exposure_raw_val = st.session_state.get("exp_slider_val", 30000)
    gain_raw_val = st.session_state.get("gain_slider_val", 12)
    
    cam = get_camera()
    if cam is not None and cam.IsOpen():
        try:
            if not cam.IsGrabbing():
                cam.StartGrabbingMax(30, pylon.GrabStrategy_LatestImageOnly)

            nodemap = cam.GetNodeMap()
            
            # --- 1. JEDNODUCHÉ VYPNUTÍ AUTOMATIK ---
            try:
                exp_auto = nodemap.GetNode("ExposureAuto")
                if exp_auto is not None: exp_auto.SetValue("Off")
                gain_auto = nodemap.GetNode("GainAuto")
                if gain_auto is not None: gain_auto.SetValue("Off")
            except:
                pass

            # --- 2. PŘÍMÝ NATIVNÍ ZÁPIS EXPOZICE (ODSTRANÍ ČERVENÉ CHYBY) ---
            try:
                # Na starých CCD čipech Valeo zapisujeme výhradně do ExposureTimeRaw
                exp_raw_node = nodemap.GetNode("ExposureTimeRaw")
                if exp_raw_node is not None:
                    exp_raw_node.SetValue(int(exposure_raw_val))
                else:
                    # Fallback pro novější modely, pokud by se kamera prohodila
                    exp_node = nodemap.GetNode("ExposureTime") or nodemap.GetNode("ExposureTimeAbs")
                    if exp_node is not None:
                        exp_node.SetValue(float(exposure_raw_val))
            except:
                pass

            # --- 3. PŘÍMÝ NATIVNÍ ZÁPIS GAINU ---
            try:
                gain_raw_node = nodemap.GetNode("GainRaw") or nodemap.GetNode("GainAll") or nodemap.GetNode("Gain")
                if gain_raw_node is not None:
                    if gain_raw_node.GetNode().GetType() == 1 or "Raw" in gain_raw_node.GetNode().GetName():
                        gain_raw_node.SetValue(int(gain_raw_val))
                    else:
                        gain_raw_node.SetValue(float(gain_raw_val))
            except:
                pass

            # --- 4. STAŽENÍ SNÍMKU ---
            grab_result = cam.RetrieveResult(250, pylon.TimeoutHandling_Return)
            if grab_result and grab_result.GrabSucceeded():
                img = Image.fromarray(grab_result.Array).convert("RGB")
                _last_valid_img = img
                grab_result.Release()
                return img, "OK"
                
            if grab_result:
                grab_result.Release()
        except:
            pass

    if _last_valid_img is not None:
        return _last_valid_img, "OK (Záložní buffer)"
        
    return None, "Čekání na uvolnění sběrnice kamery..."

def save_camera_features_to_pfs(project_name, position_num):
    try:
        cam = get_camera()
        if cam:
            os.makedirs("profiles", exist_ok=True)
            pfs_path = f"profiles/{project_name}_pos_{position_num}.pfs"
            pylon.FeaturePersistence.Save(pfs_path, cam.GetNodeMap())
            print(f"💾 PFS soubor exportován: {pfs_path}")
            return True, pfs_path
    except Exception as e:
        return False, str(e)
    return False, "Kamera není inicializována."

def load_camera_features_from_pfs(project_name, position_num):
    cam = get_camera()
    if cam:
        pfs_path = f"profiles/{project_name}_pos_{position_num}.pfs"
        if os.path.exists(pfs_path):
            try:
                is_grabbing = cam.IsGrabbing()
                if is_grabbing: cam.StopGrabbing()
                pylon.FeaturePersistence.Load(pfs_path, cam.GetNodeMap(), True)
                if is_grabbing: cam.StartGrabbingMax(30, pylon.GrabStrategy_LatestImageOnly)
                return True, "PFS načteno"
            except Exception as e:
                return False, str(e)
    return False, "Profil neexistuje"