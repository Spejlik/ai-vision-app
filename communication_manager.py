import time
from pymodbus.client import ModbusTcpClient

class LisModbusManager:
    def __init__(self, ip_address="192.168.1.200", port=502):
        self.ip_address = ip_address
        self.port = port
        self.client = None
        self.last_trigger_state = 0
        self.current_position_counter = 1
        
    def connect(self):
        """Naváže spojení s I/O modulem Moxa lisu."""
        return True
        
    def check_trigger_and_sequence(self, max_positions=2):
        """Simulované čtení registru lisu - upraveno pro test kamer."""
        return False, None

        try:
            # Čteme holding registry od adresy 8 (přesně jako Elvac read_holding_registers(0x08, 8))
            response = self.client.read_holding_registers(address=8, count=8)
            
            if response and not response.isError():
                registers = response.registers
                
                # Podle Elvac schématu je Trigger na indexu 1 nebo 2 (zkusíme index 1 jako 'Trigger')
                # Pokud PLC poslalo signál, hodnota v registru skočí na 1
                current_trigger = registers[1] 
                
                # HLÍDÁNÍ NÁBĚŽNÉ HRANY (Signál přišel teď: minule byl 0, teď je 1)
                if current_trigger == 1 and self.last_trigger_state == 0:
                    self.last_trigger_state = 1
                    
                    # Vznikl trigger -> zachytíme aktuální polohu taktu robota
                    triggered_position = self.current_position_counter
                    
                    # Automaticky posuneme počítadlo pro další takt (např. z Pozice 1 na Pozice 2)
                    self.current_position_counter += 1
                    if self.current_position_counter > max_positions:
                        self.current_position_counter = 1 # Po projetí všech pozic jdeme od startu
                        
                    return True, triggered_position
                
                # Resetujeme stav, pokud lis signál triggeru shodil zpět na 0
                if current_trigger == 0:
                    self.last_trigger_state = 0
                    
        except Exception as e:
            print(f"💥 Chyba komunikace s rozvaděčem lisu: {str(e)}")
            
        return False, None

    def close(self):
        if self.client:
            self.client.close()