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
        print("🍏 [HARDWARE] Permanentní instance kamery uzamčena pro aplikaci.")
        return cam
    except Exception as e:
        st.session_state.pylon_camera_instance = None
        return None

def capture_live_frame(*args, **kwargs):
    """
    Vysoce optimalizované real-time snímání pro Elvac CCD 5MPx standard.
    Vynucuje režim Timed a vypíná limity snímkové frekvence pro odemčení ExposureTimeRaw.
    """
    global _last_valid_img
    
    exposure_raw_val = st.session_state.get("exp_slider_val", 30000)
    gain_raw_val = st.session_state.get("gain_slider_val", 12)
    
    cam = get_camera()
    if cam is not None and cam.IsOpen():
        try:
            if not cam.IsGrabbing():
                cam.StartGrabbingMax(30, pylon.GrabStrategy_LatestImageOnly)

            nodemap = cam.GetNodeMap()
            
            # --- 1. ODPOJENÍ TRIGGERU A REŽIMU AUTOMATIK ---
            try:
                trigger_mode_node = nodemap.GetNode("TriggerMode")
                if trigger_mode_node is not None and trigger_mode_node.GetValue() != "Off":
                    trigger_mode_node.SetValue("Off")
                    
                exp_auto = nodemap.GetNode("ExposureAuto")
                if exp_auto is not None: exp_auto.SetValue("Off")
                gain_auto = nodemap.GetNode("GainAuto")
                if gain_auto is not None: gain_auto.SetValue("Off")
            except:
                pass

            # --- 🍏 2. ELVAC ODEMČENÍ ELEKTRONICKÉ UZÁVĚRKY (KLÍČ K NÁPRAVĚ) ---
            try:
                # Nastavíme režim expozice na "Timed" (řízeno časem, nikoliv pulzem)
                exp_mode = nodemap.GetNode("ExposureMode")
                if exp_mode is not None:
                    exp_mode.SetValue("Timed")
                
                # Vypneme interní limit snímkové frekvence, který u starých CCD blokuje dlouhé časy
                fr_enable = nodemap.GetNode("AcquisitionFrameRateEnable") or nodemap.GetNode("AcquisitionFrameRateAuto")
                if fr_enable is not None:
                    try:
                        fr_enable.SetValue(False)
                    except:
                        fr_enable.SetValue("Off")
            except:
                pass

            # --- 3. REAL-TIME ZÁPIS EXPOZICE DO RAW REGISTRU ---
            try:
                exp_raw_node = nodemap.GetNode("ExposureTimeRaw")
                if exp_raw_node is not None:
                    # Ošetříme rozsah podle hardwarových limitů dané kamery
                    val_to_set = max(exp_raw_node.GetMin(), min(exp_raw_node.GetMax(), int(exposure_raw_val)))
                    exp_raw_node.SetValue(val_to_set)
                else:
                    exp_node = nodemap.GetNode("ExposureTime") or nodemap.GetNode("ExposureTimeAbs")
                    if exp_node is not None:
                        exp_node.SetValue(float(exposure_raw_val))
            except:
                pass

            # --- 4. REAL-TIME ZÁPIS GAINU DO RAW REGISTRU ---
            try:
                gain_raw_node = nodemap.GetNode("GainRaw") or nodemap.GetNode("GainAll")
                if gain_raw_node is not None:
                    gain_raw_node.SetValue(int(gain_raw_val))
            except:
                pass

            # Stažení snímku z čipu
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
    cam = get_camera()
    if cam:
        try:
            nodemap = cam.GetNodeMap()
            
            # --- 🍏 ELVAC POJISTKA: Ukládáme se ZAPNUTÝM triggerem pro linkový cyklus lisu ---
            try:
                trigger_mode_node = nodemap.GetNode("TriggerMode")
                if trigger_mode_node is not None:
                    trigger_mode_node.SetValue("On")
            except:
                pass
                
            os.makedirs("profiles", exist_ok=True)
            pfs_path = f"profiles/{project_name}_pos_{position_num}.pfs"
            pylon.FeaturePersistence.Save(pfs_path, nodemap)
            print(f"💾 PFS soubor exportován se zapnutým linkovým triggerem: {pfs_path}")
            return True, pfs_path
        except Exception as e:
            return False, str(e)
    return False, "Kamera není inicializována."    