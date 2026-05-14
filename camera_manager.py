import cv2
import numpy as np
import os

class BaslerCam:
    def __init__(self):
        self.demo_mode = False
        try:
            from pypylon import pylon
            self.camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
            self.camera.Open()
            print("✅ Kamera Basler připojena.")
        except Exception:
            self.demo_mode = True
            print("⚠️ Kamera nenalezena. Aktivován DEMO REŽIM (načítám test_image.jpg).")

    def get_frame(self):
        if self.demo_mode:
            # Zkusí načíst obrázek z disku, jinak vytvoří šedý obdélník
            if os.path.exists("test_image.jpg"):
                frame = cv2.imread("test_image.jpg")
            else:
                frame = np.full((1080, 1920, 3), 128, dtype=np.uint8)
                cv2.putText(frame, "DEMO: Chybi test_image.jpg", (500, 500), 
                            cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
            return frame
        else:
            # Standardní snímání z Pylonu
            self.camera.StartGrabbingMax(1)
            res = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            frame = res.Array
            res.Release()
            return frame