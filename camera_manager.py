import time
from PIL import Image
from pypylon import pylon

_camera = None

def get_camera():
    global _camera
    if _camera is None:
        try:
            tl_factory = pylon.TlFactory.GetInstance()
            devices = tl_factory.EnumerateDevices()
            if not devices: 
                return None
            
            _camera = pylon.InstantCamera(tl_factory.CreateDevice(devices[0]))
            _camera.Open()
            
            # Pokus o načtení továrního průmyslového profilu
            try:
                if hasattr(_camera, 'UserSetSelector'):
                    _camera.UserSetSelector.SetValue("UserSet1")
                    _camera.UserSetLoad.Execute()
            except: 
                pass
            
            _camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        except Exception as e:
            print(f"⚠️ Chyba inicializace kamery: {e}")
            return None
    return _camera

def capture_live_frame(*args, **kwargs):
    """
    Robustní zachycení snímku z Basler kamery.
    Zápis do registrů je plně izolován, aby chybějící uzel (Node) neshodil stream.
    """
    exposure_time = kwargs.get('exposure_time', args[0] if len(args) > 0 else None)
    gain = kwargs.get('gain', args[1] if len(args) > 1 else None)
    
    cam = get_camera()
    if cam and cam.IsGrabbing():
        # --- IZOLOVANÝ BLOK PRO HARDWAROVÝ ZÁPIS GAINU (OPRAVA PRO VALEO KAMERU) ---
        if gain is not None:
            try:
                nodemap = cam.GetNodeMap()
                gain_auto_node = nodemap.GetNode("GainAuto")
                gain_node = nodemap.GetNode("Gain")
                gain_raw_node = nodemap.GetNode("GainRaw")

                # 1. Nejprve natvrdo vypneme automatiku gainu, jinak čip ignoruje manuální slider
                if gain_auto_node is not None and gain_auto_node.IsValid():
                    gain_auto_node.SetValue("Off")

                # 2. Zápis do standardního float uzlu 'Gain'
                if gain_node is not None and gain_node.IsValid():
                    # Zkontrolujeme min/max limity kamery, abychom nepřestřelili rozsah
                    val_to_set = max(gain_node.GetMin(), min(gain_node.GetMax(), float(gain)))
                    gain_node.SetValue(val_to_set)
                    
                # 3. Fallback pro starší modely s celočíselným uzlem 'GainRaw'
                elif gain_raw_node is not None and gain_raw_node.IsValid():
                    val_to_set = max(gain_raw_node.GetMin(), min(gain_raw_node.GetMax(), int(round(float(gain)))))
                    gain_raw_node.SetValue(val_to_set)
                    
            except Exception as e_gain:
                print(f"❌ Nelze vynutit manuální Gain na tomto čipu: {e_gain}")
        
        # --- SAMOTNÉ ZÍSKÁNÍ SNÍMKU (NESMÍ SPADNUTÍM HARDWARU SELHAT) ---
        try:
            grab_result = cam.RetrieveResult(2000, pylon.TimeoutHandling_Return)
            if grab_result.GrabSucceeded():
                img = Image.fromarray(grab_result.Array).convert("RGB")
                grab_result.Release()
                return img, "OK"
            grab_result.Release()
        except Exception as e:
            return None, f"Chyba vytažení dat z bufferu: {e}"
            
    return None, "Kamera negrebuje nebo vypršel timeout."