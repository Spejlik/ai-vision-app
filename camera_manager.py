import os
import time
from PIL import Image
import numpy as np

def capture_live_frame(camera_source=0, exposure_time=None):
    try:
        from pypylon import pylon
        tl_factory = pylon.TlFactory.GetInstance()
        devices = tl_factory.EnumerateDevices()
        
        if not devices:
            info = pylon.DeviceInfo()
            info.SetDeviceClass("BaslerGigE")
            camera = pylon.InstantCamera(tl_factory.CreateDevice(info))
        else:
            camera = pylon.InstantCamera(tl_factory.CreateDevice(devices[0]))
            
        camera.Open()
        
        # --- 1. ZÁKAZ AUTOMATIKY (Hluboký přístup přes NodeMap) ---
        nodemap = camera.GetNodeMap()
        for auto_feature in ["ExposureAuto", "GainAuto", "BalanceWhiteAuto"]:
            try:
                node = nodemap.GetNode(auto_feature)
                if node and node.IsWritable():
                    node.SetValue("Off")
            except: pass

        # --- 2. MANUÁLNÍ EXPOZICE (Vynucení hodnoty z posuvníku) ---
        if exposure_time is not None:
            try:
                exp_mode = nodemap.GetNode("ExposureMode")
                if exp_mode and exp_mode.IsWritable():
                    exp_mode.SetValue("Timed")
            except: pass
            
            try:
                exp_time = nodemap.GetNode("ExposureTime")
                if exp_time and exp_time.IsWritable():
                    exp_time.SetValue(float(exposure_time))
                else:
                    exp_time_abs = nodemap.GetNode("ExposureTimeAbs")
                    if exp_time_abs and exp_time_abs.IsWritable():
                        exp_time_abs.SetValue(float(exposure_time))
            except: pass
        
        # --- 3. SÍŤ A FORMÁT ---
        try: camera.GevSCPSPacketSize.SetValue(1500)
        except: pass
        try: camera.MaxNumBuffer.SetValue(10)
        except: pass

        try: camera.PixelFormat.SetValue("Mono8")
        except:
            try: camera.PixelFormat.SetValue("RGB8")
            except: pass
            
        grab_result = camera.GrabOne(1000)
        if grab_result.GrabSucceeded():
            img_array = grab_result.Array
            if len(img_array.shape) == 2:
                pil_img = Image.fromarray(img_array).convert("RGB")
            else:
                pil_img = Image.fromarray(img_array)
            
            grab_result.Release()
            camera.Close()
            return pil_img, "Kamera Lisu"
        
        grab_result.Release()
        camera.Close()
        return None, "CHYBA_SNÍMÁNÍ"
        
    except Exception as e:
        return None, str(e)

def save_live_to_unsorted(project_name, camera_id, image_pil):
    import random
    unsorted_dir = f"C:/Image/Unsorted/{project_name}"
    if not os.path.exists(unsorted_dir):
        os.makedirs(unsorted_dir)
    filename = os.path.join(unsorted_dir, f"basler_{camera_id}_{int(time.time())}_{random.randint(100,999)}.jpg")
    image_pil.save(filename, "JPEG", quality=95)
    return filename