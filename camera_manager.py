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
        
        try:
            grabber_nodemap = cam.GetStreamGrabberNodeMap()
            max_buffers = grabber_nodemap.GetNode("MaxNumBuffer")
            if max_buffers is not None:
                max_buffers.SetValue(30)
        except:
            pass
            
        cam.StartGrabbingMax(30, pylon.GrabStrategy_LatestImageOnly)
        st.session_state.pylon_camera_instance = cam
        print("🍏 [HARDWARE]Permanentní instance kamery uzamčena pro živý stream.")
        return cam
    except Exception as e:
        st.session_state.pylon_camera_instance = None
        return None

def capture_live_frame(*args, **kwargs):
    """
    Vysoce citlivé real-time snímání pro 5MPx starší Basler čipy (SFNC v1).
    Natvrdo propisuje hodnoty sliderů do hardwaru při každém snímku pro okamžitou změnu jasu.
    """
    global _last_valid_img
    
    # Okamžité vytažení aktuální polohy sliderů ze Streamlitu
    exposure_time = st.session_state.get("exp_slider_val", 30000)
    gain_val = st.session_state.get("gain_slider_val", 0)
    
    cam = get_camera()
    
    if cam is not None and cam.IsOpen():
        try:
            if not cam.IsGrabbing():
                cam.StartGrabbingMax(30, pylon.GrabStrategy_LatestImageOnly)

            nodemap = cam.GetNodeMap()
            
            # --- 1. NATVRDO VYPNEME AUTOMATIKY V KAŽDÉM KROKU ---
            try:
                exp_auto = nodemap.GetNode("ExposureAuto")
                if exp_auto is not None: exp_auto.SetValue("Off")
                gain_auto = nodemap.GetNode("GainAuto")
                if gain_auto is not None: gain_auto.SetValue("Off")
            except:
                pass

            # --- 2. AGRESIVNÍ REAL-TIME ZÁPIS EXPOZICE ---
            try:
                exp_node = nodemap.GetNode("ExposureTime") or nodemap.GetNode("ExposureTimeAbs")
                if exp_node is not None:
                    exp_node.SetValue(float(exposure_time))
                else:
                    exp_raw = nodemap.GetNode("ExposureTimeRaw")
                    if exp_raw is not None:
                        exp_raw.SetValue(int(exposure_time))
            except Exception as e_exp:
                print(f"❌ Real-time chyba zápisu expozice: {e_exp}")

            # --- 3. AGRESIVNÍ REAL-TIME ZÁPIS GAINU (ZISKU) ---
            gain_written = False
            for gain_name in ["GainRaw", "Gain", "GainAll"]:
                try:
                    g_node = nodemap.GetNode(gain_name)
                    if g_node is not None:
                        # Rozlišení zda uzel bere integer nebo float
                        if "Raw" in gain_name or g_node.GetNode().GetType() == 1:
                            g_node.SetValue(int(gain_val))
                        else:
                            g_node.SetValue(float(gain_val))
                        gain_written = True
                        break
                except:
                    continue

            if not gain_written:
                # Fallback pro případ, že kamera nemá zisk – nouzově pomůžeme expozici
                pass

            # --- 4. STAŽENÍ SNÍMKU Z ČIPU ---
            grab_result = cam.RetrieveResult(250, pylon.TimeoutHandling_Return)
            if grab_result and grab_result.GrabSucceeded():
                img = Image.fromarray(grab_result.Array).convert("RGB")
                _last_valid_img = img
                grab_result.Release()
                return img, "OK"
                
            if grab_result:
                grab_result.Release()
        except Exception as e_loop:
            print(f"⚠️ Výpadek smyčky grabberu: {e_loop}")

    # Fallback přes záložní buffer pro plynulost rozhraní
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