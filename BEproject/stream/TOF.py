import time
from DFRobot_TMF8x01.python.raspberry.DFRobot_TMF8x01 import DFRobot_TMF8801 as tof

class TMF:
    def __init__(self):
        self.tof = tof(enPin=-1, intPin=-1, bus_id=1)

        print("Initializing TMF8801 sensor...", end=" ")
        while self.tof.begin() != 0:
            print("Initialization failed. Retrying...")
            time.sleep(1)
        print("Initialization successful.")

        print(f"Software Version: {self.tof.get_software_version()}")
        print(f"Unique ID: {hex(self.tof.get_unique_id())}")
        print(f"Model: {self.tof.get_sensor_model()}")

        self.tof.start_measurement(calib_m=self.tof.eMODE_CALIB, mode=self.tof.ePROXIMITY)

    def get_distance(self):
        try:
            if self.tof.is_data_ready():
                return self.tof.get_distance_mm()
            else:
                return None
        except KeyError as e:
            print(f"[TMF Error] Missing key in result_dict: {e}")
            return None
        except Exception as e:
            print(f"[TMF Error] Unexpected: {e}")
            return None
