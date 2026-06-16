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
    Vysoce stabilní snímání pro 5MPx starší Basler čipy.
    Řeší synchronizaci parametrů přímo ze session state aplikace.
    """
    global _last_exposure, _last_gain, _last_valid_img
    
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
        
        exp_changed = _last_exposure is None or float(exposure_time) != _last_exposure
        gain_changed = _last_gain is None or float(gain) != _last_gain

        if exp_changed or gain_changed:
            # Tichá deaktivace automatik
            for auto_node in ["ExposureAuto", "GainAuto"]:
                try:
                    node = nodemap.GetNode(auto_node)
                    if node: node.SetValue("Off")
                except: pass

            # Bezpečný zápis expozice
            if exp_changed:
                try:
                    exp_node = nodemap.GetNode("ExposureTime") or nodemap.GetNode("ExposureTimeAbs")
                    if exp_node is not None:
                        exp_node.SetValue(max(exp_node.GetMin(), min(exp_node.GetMax(), float(exposure_time))))
                    else:
                        exp_raw = nodemap.GetNode("ExposureTimeRaw")
                        if exp_raw is not None:
                            exp_raw.SetValue(max(exp_raw.GetMin(), min(exp_raw.GetMax(), int(round(float(exposure_time))))))
                    _last_exposure = float(exposure_time)
                except:
                    pass

            # Bezpečný zápis zisku (Gain)
            if gain_changed:
                try:
                    gain_node = nodemap.GetNode("Gain") or nodemap.GetNode("GainAll")
                    if gain_node is not None:
                        # Vyhodnocení typu uzlu (či celočíselný index nebo float)
                        if "Raw" in gain_node.GetNode().GetName() or gain_node.GetNode().GetType() == 1:
                            gain_node.SetValue(int(round(float(gain))))
                        else:
                            gain_node.SetValue(max(gain_node.GetMin(), min(gain_node.GetMax(), float(gain))))
                    else:
                        gain_raw = nodemap.GetNode("GainRaw")
                        if gain_raw is not None:
                            gain_raw.SetValue(max(gain_raw.GetMin(), min(gain_raw.GetMax(), int(round(float(gain))))))
                    _last_gain = float(gain)
                except:
                    pass

        # Vytažení snímku z čipu
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
        pfs_path = f"profiles/{project_name}_pos_{position_num}.pfs"
        if os.path.exists(pfs_path):
            try:
                is_grabbing = cam.IsGrabbing()
                if is_grabbing: cam.StopGrabbing()
                pylon.FeaturePersistence.Load(pfs_path, cam.GetNodeMap(), True)
                if is_grabbing: cam.StartGrabbingMax(30, pylon.GrabStrategy_LatestImageOnly)
                return True, "OK"
            except Exception as e:
                return False, f"Chyba při nahrávání PFS profilu: {e}"
        return False, f"Profil pro pozici {position_num} zatím neexistuje."
    return False, "Kamera není inicializována."

def save_camera_features_to_pfs(project_name, position_num):
    cam = get_camera()
    if cam:
        try:
            os.makedirs("profiles", exist_ok=True)
            pfs_path = f"profiles/{project_name}_pos_{position_num}.pfs"
            pylon.FeaturePersistence.Save(pfs_path, cam.GetNodeMap())
            return True, pfs_path
        except Exception as e:
            return False, str(e)
    return False, "Kamera není inicializována."