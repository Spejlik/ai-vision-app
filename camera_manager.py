import os
import time
from PIL import Image
import numpy as np

def capture_live_frame(camera_source=0):
    """
    Zachytí snímek z reálné kamery Basler a vytáhne její hardwarové jméno z Pylonu.
    Vrací: (pil_image, camera_name)
    """
    try:
        from pypylon import pylon
        
        tl_factory = pylon.TlFactory.GetInstance()
        devices = tl_factory.EnumerateDevices()
        
        camera = None
        camera_name = "Kamera_Neznama"
        
        # 1. Pokud detekujeme reálnou kameru
        if devices:
            target_device = devices[0]
            for d in devices:
                if "Emulation" not in d.GetFriendlyName():
                    target_device = d
                    break
            
            # Vytáhneme uživatelské jméno kamery nastavené v Pylonu (UserDefinedName), 
            # pokud není, vezmeme modelové označení (FriendlyName)
            camera_name = target_device.GetUserDefinedName()
            if not camera_name:
                camera_name = target_device.GetFriendlyName().split("(")[0].strip()
                
            camera = pylon.InstantCamera(tl_factory.CreateDevice(target_device))
        
        # 2. Pokud jedeme na emulátor (Příprava v kanclu)
        else:
            info = pylon.DeviceInfo()
            info.SetDeviceClass("BaslerCamEmu")
            camera = pylon.InstantCamera(tl_factory.CreateDevice(info))
            camera_name = "Basler Emulátor (Kamera 4)"

        camera.Open()
        
        try: camera.PixelFormat.SetValue("Mono8")
        except:
            try: camera.PixelFormat.SetValue("RGB8")
            except: pass
            
        grab_result = camera.GrabOne(2000)
        
        if grab_result.GrabSucceeded():
            img_array = grab_result.Array
            if len(img_array.shape) == 2:
                pil_img = Image.fromarray(img_array).convert("RGB")
            else:
                pil_img = Image.fromarray(img_array)
                
            grab_result.ReleaseResult()
            camera.Close()
            return pil_img, camera_name # Vracíme obrázek i s vyčteným jménem z lisu
        else:
            grab_result.ReleaseResult()
            camera.Close()
            return None, "CHYBA_SNÍMÁNÍ"
            
    except Exception as e:
        # Fallback pro USB webkamery nebo situaci bez pypylonu
        try:
            import cv2
            cap = cv2.VideoCapture(camera_source)
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                return Image.fromarray(rgb_frame), f"USB Kamera {camera_source}"
        except:
            pass
        return None, "CHYBA_HARDWARU"

def save_live_to_unsorted(project_name, camera_id, image_pil):
    """
    Uloží živý snímek do průběžného sběru pro Historii.
    """
    import random
    unsorted_dir = f"C:/Image/Unsorted/{project_name}"
    if not os.path.exists(unsorted_dir):
        os.makedirs(unsorted_dir)
        
    filename = os.path.join(unsorted_dir, f"basler_{camera_id}_{int(time.time())}_{random.randint(100,999)}.jpg")
    image_pil.save(filename, "JPEG", quality=95)
    return filename