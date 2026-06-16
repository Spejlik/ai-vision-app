import time
import os
from PIL import Image
from pypylon import pylon
import streamlit as st

# 🍏 GLOBÁLNÍ INSTANCE NA ÚROVNI PAMĚTI PYTHON MODULU (ZABRÁNÍ NEKONEČNÉ RE-INICIALIZACI)
_GLOBAL_CAMERA_INSTANCE = None
_last_valid_img = None

def get_camera():
    """
    Robustní průmyslový Singleton. Inicializuje kameru pouze jednou 
    za celou dobu běhu OS a drží ji trvale otevřenou.
    """
    global _GLOBAL_CAMERA_INSTANCE
    
    # Pokud instance v RAM existuje a fyzicky žije, okamžitě ji vrátíme
    if _GLOBAL_CAMERA_INSTANCE is not None:
        try:
            if _GLOBAL_CAMERA_INSTANCE.IsOpen() and _GLOBAL_CAMERA_INSTANCE.IsGrabbing():
                return _GLOBAL_CAMERA_INSTANCE
        except:
            pass

    try:
        print("🚀 [HARDWARE] Fyzická inicializace 5MPx CCD Basler kamery...")
        tl_factory = pylon.TlFactory.GetInstance()
        devices = tl_factory.EnumerateDevices()
        if not devices: 
            print("❌ [HARDWARE] Žádná GigE kamera nebyla v síti nalezena!")
            return None
        
        # Vytvoření a trvalé otevření komunikačního kanálu
        cam = pylon.InstantCamera(tl_factory.CreateDevice(devices[0]))
        cam.Open()
        
        # Inicializace registrů a odpojení linkového triggeru lisu hned při startu
        try:
            nodemap = cam.GetNodeMap()
            
            t_mode = nodemap.GetNode("TriggerMode")
            if t_mode is not None:
                t_mode.SetValue("Off")
                
            e_mode = nodemap.GetNode("ExposureMode")
            if e_mode is not None: e_mode.SetValue("Timed")
                
            fr_en = nodemap.GetNode("AcquisitionFrameRateEnable")
            if fr_en is not None: fr_en.SetValue(False)

            # --- 🍏 HARDWAROVÝ ANTI-FLICKER FILTR 50Hz (ELVAC STANDARD) ---
            # Vyhlazuje kmitání zářivek v hale lisu přímo na procesoru kamery
            try:
                flicker_sel = nodemap.GetNode("AntiFlickerSelector") or nodemap.GetNode("LightSourceSelector")
                if flicker_sel is not None:
                    symbolics = flicker_sel.GetSymbolics()
                    if "Frequency50Hz" in symbolics:
                        flicker_sel.SetValue("Frequency50Hz")
                    elif "Hz50" in symbolics:
                        flicker_sel.SetValue("Hz50")
                    elif "Lighting50Hz" in symbolics:
                        flicker_sel.SetValue("Lighting50Hz")
            except:
                pass

            try:
                flicker_mode = nodemap.GetNode("AntiFlickerMode")
                if flicker_mode is not None:
                    flicker_mode.SetValue("On")
            except:
                pass

        except Exception as e_init_reg:
            print(f"ℹ️ Inicializace registrů: {e_init_reg}")

        # Nastavení transportních vyrovnávacích pamětí
        try:
            grabber_nodemap = cam.GetStreamGrabberNodeMap()
            max_buffers = grabber_nodemap.GetNode("MaxNumBuffer")
            if max_buffers is not None:
                max_buffers.SetValue(30)
        except:
            pass
            
        cam.StartGrabbingMax(30, pylon.GrabStrategy_LatestImageOnly)
        _GLOBAL_CAMERA_INSTANCE = cam
        print("✅ [HARDWARE] Kamera je úspěšně uzamčena a běží v režimu Free Run s 50Hz filtrem.")
        return _GLOBAL_CAMERA_INSTANCE
    except Exception as e:
        print(f"❌ [HARDWARE] Selhalo navázání spojení s kamerou: {e}")
        _GLOBAL_CAMERA_INSTANCE = None
        return None

def capture_live_frame(*args, **kwargs):
    """
    Vysoce plynulé snímání frame-by-frame. 
    Natvrdo cpe hodnoty sliderů do stabilní instance registru.
    """
    global _last_valid_img
    
    exposure_raw_val = st.session_state.get("exp_slider_val", 40000)
    gain_raw_val = st.session_state.get("gain_slider_val", 3)
    
    cam = get_camera()
    if cam is not None and cam.IsOpen():
        try:
            nodemap = cam.GetNodeMap()
            
            # --- AGRESIVNÍ REAL-TIME ZÁPIS PARAMETRŮ ---
            try:
                exp_raw_node = nodemap.GetNode("ExposureTimeRaw")
                if exp_raw_node is not None:
                    exp_raw_node.SetValue(int(exposure_raw_val))
            except:
                pass

            try:
                gain_raw_node = nodemap.GetNode("GainRaw") or nodemap.GetNode("GainAll")
                if gain_raw_node is not None:
                    gain_raw_node.SetValue(int(gain_raw_val))
            except:
                pass

            # Stažení obrazových dat
            grab_result = cam.RetrieveResult(150, pylon.TimeoutHandling_Return)
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
        return _last_valid_img, "OK"
        
    return None, "Čekání na uvolnění sběrnice kamery..."

def save_camera_features_to_pfs(project_name, position_num):
    """
    Uloží aktuální hardwarovou mapu registru včetně aktivního linkového triggeru do PFS.
    """
    try:
        cam = get_camera()
        if cam:
            nodemap = cam.GetNodeMap()
            
            # --- POJISTKA PRO AUTOMATICKÝ BĚH LINKY ---
            # Do souboru PFS uložíme stav TriggerMode=On, aby lis po zavedení profilu mohl sám samofotit
            try:
                t_mode = nodemap.GetNode("TriggerMode")
                if t_mode is not None:
                    t_mode.SetValue("On")
            except:
                pass
                
            os.makedirs("profiles", exist_ok=True)
            pfs_path = f"profiles/{project_name}_pos_{position_num}.pfs"
            pylon.FeaturePersistence.Save(pfs_path, nodemap)
            
            # Po uložení ihned vrátíme Free Run (Off) pro plynulý náhled inženýra
            try:
                if t_mode is not None:
                    t_mode.SetValue("Off")
            except:
                pass
                
            return True, pfs_path
    except Exception as e:
        return False, str(e)
    return False, "Kamera není inicializována."

def load_camera_features_from_pfs(project_name, position_num):
    """
    Načte konfiguraci ze souboru PFS a přenastaví uzly kamery.
    """
    cam = get_camera()
    if cam:
        pfs_path = f"profiles/{project_name}_pos_{position_num}.pfs"
        if os.path.exists(pfs_path):
            try:
                is_grabbing = cam.IsGrabbing()
                if is_grabbing: 
                    cam.StopGrabbing()
                
                pylon.FeaturePersistence.Load(pfs_path, cam.GetNodeMap(), True)
                
                if is_grabbing: 
                    cam.StartGrabbingMax(30, pylon.GrabStrategy_LatestImageOnly)
                return True, "PFS načteno"
            except Exception as e:
                return False, str(e)
    return False, "Profil neexistuje"