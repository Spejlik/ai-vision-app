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
            
            nodemap = self.camera.GetNodeMap()
            
            # --- 🍏 NATVRDO RUČNÍ VYPNUTÍ TRIGGERU (ELVAC STANDARD) ---
            # Vypneme jakýkoliv linkový nebo softwarový trigger, aby kamera běžela v čistém Free Run
            t_mode = nodemap.GetNode("TriggerMode")
            if t_mode is not None:
                t_mode.SetValue("Off")
                
            e_mode = nodemap.GetNode("ExposureMode")
            if e_mode is not None: 
                e_mode.SetValue("Timed")
                
            fr_en = nodemap.GetNode("AcquisitionFrameRateEnable")
            if fr_en is not None: 
                fr_en.SetValue(False)
            
            # Aktivace nativního anti-flickeru proti blikání haly lisu
            try:
                flicker_sel = nodemap.GetNode("AntiFlickerSelector") or nodemap.GetNode("LightSourceSelector")
                if flicker_sel and "Frequency50Hz" in flicker_sel.GetSymbolics():
                    flicker_sel.SetValue("Frequency50Hz")
            except:
                pass

            # 🍏 ZMĚNA: StartGrabbing namísto StartGrabbingMax – nekonečný proud snímků bez omezení!
            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            self.is_running = True
            print(f"✅ [CORE] Kamera {self.camera_name} úspěšně uzamčena v NEKONEČNÉM Free Run režimu.")
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
                    grab_result = self.camera.RetrieveResult(200, pylon.TimeoutHandling_Return)
                    if grab_result and grab_result.GrabSucceeded():
                        img = Image.fromarray(grab_result.Array).convert("RGB")
                        with self.lock:
                            self.last_frame = img
                        grab_result.Release()
                    elif grab_result:
                        grab_result.Release()
            except Exception as e:
                print(f"⚠️ [CORE] Vynechaný frame nebo chyba sběrnice: {e}")
            time.sleep(0.03)  # Stabilní diagnostický takt ~30 FPS

    def get_latest_image(self):
        with self.lock:
            return self.last_frame, self.camera_name

# Globální instance, která přežije jakýkoliv refresh Streamlitu
if "hardware_core" not in globals():
    hardware_core = BaslerHardwareCore()
    hardware_core.initialize_camera()
    hardware_core.start_capture_loop()