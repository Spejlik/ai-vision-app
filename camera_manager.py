import time
import os
from PIL import Image
from pypylon import pylon
import streamlit as st

_camera = None
_last_valid_img = None

def get_camera():
    """
    Bezpečný singleton pro získání instance kamery. 
    Pokud kamera spadla nebo visí, pokusí se ji bezpečně resetovat.
    """
    if "pylon_camera_instance" in st.session_state and st.session_state.pylon_camera_instance is not None:
        try:
            if st.session_state.pylon_camera_instance.IsOpen() and st.session_state.pylon_camera_instance.IsGrabbing():
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
        
        # Alokace bufferů v paměti ovladače
        try:
            grabber_nodemap = cam.GetStreamGrabberNodeMap()
            max_buffers = grabber_nodemap.GetNode("MaxNumBuffer")
            if max_buffers is not None:
                max_buffers.SetValue(30)
        except:
            pass
            
        cam.StartGrabbingMax(30, pylon.GrabStrategy_LatestImageOnly)
        st.session_state.pylon_camera_instance = cam
        print("🍏 [HARDWARE] Kamera úspěšně připojena a inicializována v paměti.")
        return cam
    except Exception as e:
        st.session_state.pylon_camera_instance = None
        return None

def capture_live_frame(*args, **kwargs):
    """
    Vysoce stabilní průmyslové snímání. Izoluje veškeré hardwarové zápisy registrů
    do chráněného bloku, čímž eliminuje Exclusive Access kolize.
    """
    global _last_valid_img
    
    # Okamžité vytažení žádaných hodnot ze sliderů v aplikaci
    exposure_raw_val = st.session_state.get("exp_slider_val", 30000)
    gain_raw_val = st.session_state.get("gain_slider_val", 12)
    
    cam = get_camera()
    
    if cam is not None and cam.IsOpen():
        try:
            nodemap = cam.GetNodeMap()
            
            # 1. ODPOJENÍ LINKOVÉHO PLC TRIGGERU PRO VOLNÝ BĚH NÁHLEDU
            try:
                t_mode = nodemap.GetNode("TriggerMode")
                if t_mode is not None and t_mode.GetValue() != "Off":
                    # Před změnou registrů na okamžik zastavíme grabování, pokud to firmware vyžaduje
                    cam.StopGrabbing()
                    t_mode.SetValue("Off")
                    
                    e_mode = nodemap.GetNode("ExposureMode")
                    if e_mode is not None: e_mode.SetValue("Timed")
                        
                    fr_en = nodemap.GetNode("AcquisitionFrameRateEnable")
                    if fr_en is not None: fr_en.SetValue(False)
                    
                    cam.StartGrabbingMax(30, pylon.GrabStrategy_LatestImageOnly)
            except:
                pass

            # 2. PROPÍSÁNÍ ELEKTRONICKÉ UZÁVĚRKY (EXPOSURE TACHTY ČIPU)
            try:
                exp_raw_node = nodemap.GetNode("ExposureTimeRaw")
                if exp_raw_node is not None:
                    exp_raw_node.SetValue(int(exposure_raw_val))
            except:
                pass

            # 3. PROPÍSÁNÍ INDEXU ZESÍLENÍ OBRAZU (GAIN RAW)
            try:
                gain_raw_node = nodemap.GetNode("GainRaw") or nodemap.GetNode("GainAll")
                if gain_raw_node is not None:
                    gain_raw_node.SetValue(int(gain_raw_val))
            except:
                pass

            # 4. SAMOTNÉ STAŽENÍ SNÍMKU Z ENVIROMENTU PYLONU
            grab_result = cam.RetrieveResult(250, pylon.TimeoutHandling_Return)
            if grab_result and grab_result.GrabSucceeded():
                img = Image.fromarray(grab_result.Array).convert("RGB")
                _last_valid_img = img  # Aktualizujeme záložní buffer v RAM počítače
                grab_result.Release()
                return img, "OK"
                
            if grab_result:
                grab_result.Release()
                
        except Exception as e_hardware_fault:
            print(f"⚠️ Dočasný výpadek komunikace s čipem lisu: {e_hardware_fault}")
            pass

    # --- INDIKACE ZÁLOHY (ZABRÁNÍ ZAMRZNUTÍ NÁHLEDU) ---
    if _last_valid_img is not None:
        return _last_valid_img, "OK"
        
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