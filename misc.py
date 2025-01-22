import threading
from typing import Optional
from ultralytics import YOLO
import serial
import cv2

# Camera Object Instance
class CameraStream:
    def __init__(self, cam_id:int=0, model:Optional[str]=None):
        self._cam_id = cam_id
        self._frame = None
        self._camera = cv2.VideoCapture(cam_id)
        self._stream_thread = None
        self._model_name = model

        self._model = YOLO(self._model_name) if self._model_name else None

    def generate_frames(self):
        while True:
            if self._frame is None:
                if self._stream_thread is None:
                    self.start_stream()
                continue
            ret, buffer = cv2.imencode('.jpg', self._frame)
            yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    def generate_results(self):
        while True:
            ret, cap = self._camera.read()
            if not ret:
                continue
            if self._model:
                results = self._model.predict(cap, conf=0.5, verbose=False)[0]
                self._frame = results.plot()
                continue
            self._frame = cap

    def start_stream(self):
        self._stream_thread = threading.Thread(target=self.generate_results, daemon=True)
        self._stream_thread.start()

# Arduino Connetion Instance
class Arduino_Serial:
    def __init__(self, serial_port:str='/dev/ttyACM0', baud_rate:int=115200):
        self._serial = serial.Serial(serial_port, baud_rate, timeout=1)
        self._serial.readline()
        self._thread = threading.Thread(target=self.read_serial, daemon=True)
        self._thread.start()
        self._ph_value = 0
        self._ppm_value = 0
        
    def read_serial(self):
        while True:
            data = self._serial.readline().decode('utf-8').strip()
            status_data = data.split(',')
            if data:
                self._ph_value = status_data[0]
                self._ppm_value = status_data[1]

    def get_ph_value(self):
        return self._ph_value
    
    def get_ppm_value(self):
        return self._ppm_value




