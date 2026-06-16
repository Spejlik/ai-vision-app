import time
from PIL import Image
from pypylon import pylon

_camera = None
_last_exposure = None
_last_gain = None

import time
from PIL import Image
from pypylon import pylon
import streamlit as st

# Bezpečné sdílení jedné instance kamery napříč celým Streamlitem
import time
from PIL import Image
from pypylon import pylon
import streamlit as st

import time
from PIL import Image
from pypylon import pylon
import streamlit as st

def get_camera():
    # Pokud kamera už existuje a běží, okamžitě ji vrátíme
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
        
        # --- ELVAC OPTIMALIZACE GIGE PŘENOSU ---
        try:
            # Bezpečné získání uzlové mapy síťového grabberu
            grabber_nodemap = cam.GetStreamGrabberNodeMap()
            
            # Zvýšíme počet interních bufferů přímo v ovladači na maximum (30)
            max_buffers = grabber_nodemap.GetNode("MaxNumBuffer")
            if max_buffers is not None:
                max_buffers.SetValue(30)
        except Exception as e_grabber:
            print(f"ℹ️ Specifické nastavení grabberu přeskočeno: {e_grabber}")
        
        # Spuštění grabování s alokací paměťového poolu v C++
        cam.StartGrabbingMax(30, pylon.GrabStrategy_LatestImageOnly)
        
        st.session_state.pylon_camera_instance = cam
        print("🍏 [HARDWARE] Kamera úspěšně inicializována přes GetStreamGrabberNodeMap.")
        return cam
    except Exception as e:
        print(f"⚠️ [HARDWARE] Kritická chyba otevírání kamery: {e}")
        st.session_state.pylon_camera_instance = None
        return None
    return _camera

def capture_live_frame(*args, **kwargs):
    """
    Robustní zachycení snímku z 5MPx Basler kamery – Elvac / Valeo Standard.
    Pokud se fronta bufferů vyprázdní, automaticky stream okamžitě restartuje.
    """
    exposure_time = kwargs.get('exposure_time', args[0] if len(args) > 0 else None)
    gain = kwargs.get('gain', args[1] if len(args) > 1 else None)
    
    cam = get_camera()
    if cam:
        try:
            # --- POJISTKA PROTI VYPRÁZDNĚNÍ FRONTY (ELVAC STANDARD) ---
            if not cam.IsGrabbing():
                # Pokud fronta 30 snímků došla na konec, okamžitě ji znovu nahodíme
                cam.StartGrabbingMax(30, pylon.GrabStrategy_LatestImageOnly)

            nodemap = cam.GetNodeMap()
            
            # Kontrola změny sliderů pro jednorázový zápis
            global _last_exposure, _last_gain
            exp_changed = exposure_time is not None and float(exposure_time) != _last_exposure
            gain_changed = gain is not None and float(gain) != _last_gain

            if exp_changed or gain_changed:
                try:
                    # Vypnutí vnitřních automatických regulací
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
                        gain_sel = nodemap.GetNode("GainSelector")
                        if gain_sel is not None and "All" in gain_sel.GetSymbolics():
                            gain_sel.SetValue("All")

                        gain_node = nodemap.GetNode("Gain") or nodemap.GetNode("GainAll")
                        if gain_node:
                            gain_node.SetValue(max(gain_node.GetMin(), min(gain_node.GetMax(), float(gain))))
                        else:
                            gain_raw = nodemap.GetNode("GainRaw")
                            if gain_raw is not None:
                                gain_raw.SetValue(max(gain_raw.GetMin(), min(gain_raw.GetMax(), int(round(float(gain))))))
                        _last_gain = float(gain)
                except:
                    pass

            # --- SAMOTNÉ BEZPEČNÉ VYTAŽENÍ SNÍMKU ---
            grab_result = cam.RetrieveResult(2000, pylon.TimeoutHandling_Return)
            if grab_result.GrabSucceeded():
                img = Image.fromarray(grab_result.Array).convert("RGB")
                grab_result.Release()
                return img, "OK"
            grab_result.Release()
            
        except Exception as e:
            return None, f"Chyba bufferu kamery: {e}"
            
    return None, "Kamera negrebuje."