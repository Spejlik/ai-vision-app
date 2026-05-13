import numpy as np
import cv2
try:
    from pypylon import pylon
    PYPYLON_INSTALLED = True
except ImportError:
    PYPYLON_INSTALLED = False

class BaslerCam:
    def __init__(self):
        self.camera = None
        if PYPYLON_INSTALLED:
            try:
                self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
                self.camera.Open()
            except:
                self.camera = None

    def get_frame(self, aoi=None):
        if self.camera:
            # Tady by byla logika pro skutečný grab z Pylonu s AOI
            # Pro zjednodušení teď vracíme dummy, dokud neodladíme připojení
            return np.zeros((1000, 1200), dtype=np.uint8) + 128
        else:
            # Simulační režim - načte tvůj master z disku
            img = cv2.imread('master_dummy.jpg', 0)
            if img is None: return np.zeros((1000, 1200), dtype=np.uint8)
            return img