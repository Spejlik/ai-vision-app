import time
from PIL import Image
from pypylon import pylon
import streamlit as st

_camera = None
_last_exposure = None
_last_gain = None
_last_valid_img = None  # Průmyslová záloha pro překonání Exclusive Access kolizí

def get_camera():
    # Pokud kamera už existuje v session a komunikuje, okamžitě ji předáme dál
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
        
        # Otevření kamery s Exclusive Access požadavkem
        cam = pylon.InstantCamera(tl_factory.CreateDevice(devices[0]))
        cam.Open()
        
        # Bezpečné nafouknutí bufferu přímo v nízkoúrovňovém C++ ovladači
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
        # Tiché zachycení kolize – pokud ji zrovna drží předchozí thread, nepadáme
        st.session_state.pylon_camera_instance = None
        return None

def capture_live_frame(*args, **kwargs):
    """
    Vysoce stabilní snímání. Bere hodnoty sliderů přímo ze session_state Streamlitu.
    Zápis provádí pouze při skutečné změně polohy slideru operátorem.
    """
    global _last_exposure, _last_gain, _last_valid_img
    
    # 🍏 OPRAVA VALEO/ELVAC: Taháme hodnoty přímo ze session state sliderů pod obrazem
    exposure_time = st.session_state.get("exp_slider_val", 20000)
    gain = st.session_state.get("gain_slider_val", 0.0)
    
    cam = get_camera()
    
    if cam is None or not cam.IsOpen():
        if _last_valid_img is not None:
            return _last_valid_img, "OK (Záložní buffer)"
        return None, "Kamera je momentálně blokována jinými thready lisu."

    try:
        if not cam.IsGrabbing():
            cam.StartGrabbingMax(30, pylon.GrabStrategy_LatestImageOnly)

        nodemap = cam.GetNodeMap()
        
        # Srovnáváme přímo s float hodnotami vytaženými ze Streamlitu
        exp_changed = _last_exposure is None or float(exposure_time) != _last_exposure
        gain_changed = _last_gain is None or float(gain) != _last_gain

        if exp_changed or gain_changed:
            try:
                exp_auto = nodemap.GetNode("ExposureAuto")
                if exp_auto is not None: exp_auto.SetValue("Off")
                gain_auto = nodemap.GetNode("GainAuto")
                if gain_auto is not None: gain_auto.SetValue("Off")

                if exp_changed:
                    exp_node = nodemap.GetNode("ExposureTime") or nodemap.GetNode("ExposureTimeAbs")
                    if exp_node:
                        exp_node.SetValue(max(exp_node.GetMin(), min(exp_node.GetMax(), float(exposure_time))))
                    else:
                        exp_raw = nodemap.GetNode("ExposureTimeRaw")
                        if exp_raw is not None:
                            exp_raw.SetValue(max(exp_raw.GetMin(), min(exp_raw.GetMax(), int(round(float(exposure_time))))))
                    _last_exposure = float(exposure_time)

                if gain_changed:
                    gain_node = nodemap.GetNode("Gain") or nodemap.GetNode("GainAll")
                    if gain_node:
                        gain_node.SetValue(max(gain_node.GetMin(), min(gain_node.GetMax(), float(gain))))
                    else:
                        gain_raw = nodemap.GetNode("GainRaw")
                        if gain_raw is not None:
                            gain_raw.SetValue(max(gain_raw.GetMin(), min(gain_raw.GetMax(), int(round(float(gain))))))
                    _last_gain = float(gain)
            except Exception as e_reg:
                print(f"⚠️ Nepodařilo se propsat změnu registru: {e_reg}")

        # Bezpečné vytažení snímku
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