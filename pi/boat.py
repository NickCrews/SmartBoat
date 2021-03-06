'''
bigboat.py
The main entry point for the code run the Raspberry Pi on the big boat.
Listens for data from the skiff, filters it, and saves it for later analysis.

dependencies:
github.com/jkittley/RFM69
'''

# import logging
# logger = logging.getLogger(__name__)

import time
import numpy as np

from gps3 import gps3 #https://pypi.org/project/gps3/
#hookup from Pi to Adafruit Ultimate GPS
#5v        <---> Vin
#GND       <---> GND
#Pin8(TX)  <---> RX
#Pin10(RX) <---> TX
import compass
from pressuregauge import PressureGauge

class Boat(object):

    DEFAULT_CALIBRATION_FILE_PATH = "/home/pi/Documents/SmartSeiner/pi/calibrations/boat.txt"

    def __init__(self, compass_file=None, gps_timeout=5):

        self.compass_file = compass_file
        self.gps_timeout = gps_timeout

        #assumes gpsd daemon has already been started
        self.gps_socket = gps3.GPSDSocket()
        self.data_stream = gps3.DataStream()
        self.gps_socket.connect()
        self.gps_socket.watch()
        self.gps_data = dict(datetime=np.nan,
                         lat=np.nan,
                         lon=np.nan,
                         COG=np.nan,
                         speed=np.nan)

        self._init_pressure_gauge()
        self._init_compass()
        self.last_gps_read_time = time.time()

    def _init_pressure_gauge(self):
        if not hasattr(self, 'pressure_gauge') or self.pressure_gauge is None:
            try:
                self.pressure_gauge = PressureGauge()
            except OSError:
                # couldnt talk to LSM303
                self.pressure_gauge = None

    def _init_compass(self):
        if not hasattr(self, 'compass') or self.compass is None:
            try:
                self.compass = compass.BoatCompass(self.compass_file)
            except OSError:
                # couldnt talk to LSM303
                self.compass = None

    def has_gps(self):
        self._update_gps()
        time_since_last_gps = time.time() - self.last_gps_read_time
        return time_since_last_gps < self.gps_timeout

    def has_gps_fix(self):
        self._update_gps()
        return not np.isnan(self.gps_data['lat'])

    def get_heading(self):
        self._init_compass()
        if self.compass is None:
            return np.nan
        try:
            return self.compass.get_heading()
        except OSError:
            # lost connection to compass
            self.compass = None
            return np.nan

    def get_pressure_and_temp(self):
        '''Read the pressure and temp in the fish hold'''
        self._init_pressure_gauge()
        if self.pressure_gauge is None:
            pressure, temp = np.nan, np.nan
            return pressure, temp
        try:
            pressure, temp = self.pressure_gauge.read()
            return pressure, temp
        except OSError:
            # sometimes we just lose a connection, forget it for now
            self.pressure_gauge = None
            pressure, temp = np.nan, np.nan
            return pressure, temp

    def get_location(self):
        self._update_gps()
        coords = self.gps_data['lat'], self.gps_data['lon']
        return coords

    def get_COG(self):
        self._update_gps()
        return self.gps_data['heading']

    def get_time(self):
        self._update_gps()
        return self.gps_data['time']

    def get_data(self):
        '''Get the GPS, compass, and pressure data in a dict.

        All available GPS attributes at http://www.catb.org/gpsd/gpsd_json.html
        '''
        self._update_gps()
        data = {}
        data['lat']        = self.gps_data['lat']
        data['lon']        = self.gps_data['lon']
        data['datetime']   = self.gps_data['time'] #in ISO8601 format, UTC.
        data['COG']        = self.gps_data['track'] # Course Over Ground
        data['speed']      = self.gps_data['speed']
        data['heading']    = self.get_heading()
        data['pressure'], data['temp'] = self.get_pressure_and_temp()

        return data

    def _update_gps(self):
        for new_data in self.gps_socket:
            if new_data:
                self.last_gps_read_time = time.time()
                self.data_stream.unpack(new_data)
                self.gps_data = {}
                for (key, value) in self.data_stream.TPV.items():
                    if value == 'n/a':
                        value = np.nan
                    self.gps_data[key] = value
            return

if __name__ == '__main__':
##    import time
##    print("Beginning boat test")
    boat = Boat()
##    while True:
##        print(boat.get_location())
##        print(boat.get_time())
##        print(boat.get_heading())
##        time.sleep(1)
    print("rotate boat compass in all directions for 15 seconds...")
    boat.calibrate_compass()
