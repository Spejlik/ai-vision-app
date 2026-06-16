import threading
import time
from pypylon import pylon
from PIL import Image

class BaslerHardwareCore:
    def __init__(self):
        self.camera = None
        self.last_frame = None
        self.is_running = False
        self.lock = threading.Lock()
        self.camera_name = "Nenalezena"

    def initialize_camera(self):
        """Jednorázová hardwarová inicializace čipu při startu OS."""
        try:
            tl_factory = pylon.TlFactory.GetInstance()
            devices = tl_factory.EnumerateDevices()
            if not devices:
                print("❌ [CORE] Žádná GigE kamera nebyla v síti nalezena!")
                return False
            
            self.camera = pylon.InstantCamera(tl_factory.CreateDevice(devices[0]))
            self.camera.Open()
            self.camera_name = self.camera.GetDeviceInfo().GetModelName()
            
            # Výchozí stabilizační registry proti blikání 50Hz sítě
            nodemap = self.camera.GetNodeMap()
            for node_name, value in [("TriggerMode", "Off"), ("ExposureMode", "Timed"), ("AcquisitionFrameRateEnable", False)]:
                node = nodemap.GetNode(node_name)
                if node: node.SetValue(value)
            
            # Aktivace nativního anti-flickeru
            try:
                flicker_sel = nodemap.GetNode("AntiFlickerSelector") or nodemap.GetNode("LightSourceSelector")
                if flicker_sel and "Frequency50Hz" in flicker_sel.GetSymbolics():
                    flicker_sel.SetValue("Frequency50Hz")
            except:
                pass

            self.camera.StartGrabbingMax(30, pylon.GrabStrategy_LatestImageOnly)
            self.is_running = True
            print(f"✅ [CORE] Kamera {self.camera_name} úspěšně uzamčena a spuštěna.")
            return True
        except Exception as e:
            print(f"❌ [CORE] Selhala hardwarová inicializace: {e}")
            return False

    def start_capture_loop(self):
        """Smyčka ve vlastním vlákně oddělená od UI."""
        threading.Thread(target=self._capture_worker, daemon=True).start()

    def _capture_worker(self):
        while self.is_running:
            try:
                if self.camera and self.camera.IsGrabbing():
                    grab_result = self.camera.RetrieveResult(100, pylon.TimeoutHandling_Return)
                    if grab_result and grab_result.GrabSucceeded():
                        img = Image.fromarray(grab_result.Array).convert("RGB")
                        with self.lock:
                            self.last_frame = img
                        grab_result.Release()
            except Exception as e:
                print(f"⚠️ [CORE] Vynechaný frame nebo chyba sběrnice: {e}")
            time.sleep(0.02)

    def get_latest_image(self):
        with self.lock:
            return self.last_frame, self.camera_name

# Globální instance, která přežije jakýkoliv refresh Streamlitu
if "hardware_core" not in globals():
    hardware_core = BaslerHardwareCore()
    hardware_core.initialize_camera()
    hardware_core.start_capture_loop()