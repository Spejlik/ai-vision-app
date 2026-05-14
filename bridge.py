import time
import cv2
import numpy as np
from pyModbusTCP.client import ModbusClient
import database
import camera_manager

# Konfigurace z haly
CONFIG = {
    "MOXA_IP": "10.42.0.167",
    "SQL_IP": "10.42.0.100",
    "REG_RESULT": 0,
    "REG_WATCHDOG": 7,
    "REG_TRIGGER": 8
}

def main():
    cam = camera_manager.BaslerCam()
    moxa = ModbusClient(host=CONFIG["MOXA_IP"], port=502, auto_open=True)
    
    # Zkusíme se připojit k Moxe
    online_moxa = moxa.open()
    
    print("\n" + "="*30)
    print("🚀 VISION BRIDGE STARTUJE")
    print("="*30)
    
    if online_moxa:
        print("✅ MODBUS: PŘIPOJENO (Online režim)")
    else:
        print("⚠️ MODBUS: ODPOJENO (Simulační režim - Trigger každých 5s)")

    last_trigger = False
    watchdog = 0

    while True:
        trigger_active = False
        
        if online_moxa:
            # Srdce systému (Watchdog)
            watchdog = (watchdog + 1) % 1000
            moxa.write_single_register(CONFIG["REG_WATCHDOG"], watchdog)
            
            # Čtení registru od robota
            regs = moxa.read_holding_registers(CONFIG["REG_TRIGGER"], 1)
            if regs:
                trigger_active = (regs[0] == 1)
        else:
            # JSME DOMA: Simulujeme trigger každých 5 sekund
            time.sleep(5)
            trigger_active = True

        # Logika náběžné hrany (zpracujeme jen když se signál změní z 0 na 1)
        if trigger_active and not last_trigger:
            print("\n📸 --- NOVÁ INSPEKCE ---")
            frame = cam.get_frame()
            
            # Načtení tvých zón ze Streamlitu
            active_rois = database.get_rois(1)
            
            # --- Tady se spustí tvůj model ---
            is_ok = True 
            
            # Odeslání výsledku robotovi (jen pokud jsme online)
            if online_moxa:
                moxa.write_single_register(CONFIG["REG_RESULT"], 1 if is_ok else 2)
            
            # Zápis do centrální DB (ošetřeno v database.py)
            database.save_result_to_mariadb(CONFIG["SQL_IP"], "Projekt_Rakovnik", is_ok)
            
            print(f"🏁 Hotovo. Výsledek: {'PASS' if is_ok else 'FAIL'}")

        # Reset triggeru pro simulaci
        if not online_moxa:
            trigger_active = False
            
        last_trigger = trigger_active
        time.sleep(0.1)

if __name__ == "__main__":
    main()