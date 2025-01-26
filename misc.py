from datetime import time as dt_time, datetime
from typing import Callable, Tuple, Optional
from ultralytics import YOLO
import threading
import schedule
import serial
import time
import json
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
        self._do_value = 0
        
    def read_serial(self):
        while True:
            data = self._serial.readline().decode('utf-8').strip()
            status_data = data.split(',')
            if data:
                self._ph_value = status_data[0]
                self._do_value = status_data[1]

    def get_ph_value(self):
        return self._ph_value
    
    def get_do_value(self):
        return self._do_value
    
class LCD_display:
    def __init__(self, lcd_display, dht_device, serial_com):
        self._lcd_display = lcd_display
        self._dht_device = dht_device
        self._serial_com = serial_com
        self._temp_format = "Celsius"
        self._thread = threading.Thread(target=self.status_stream, daemon=True).start()

    def status_stream(self):
        while True:
            if self._dht_device is None:
                continue
            temp = self._dht_device.temperature
            humid = self._dht_device.humidity
            print(f"Temperature: {temp}, Humidity: {humid}")
            if self._serial_com is None:
                continue
            do_value = self._serial_com.get_do_value()
            ph_value = self._serial_com.get_ph_value()
            print(f"DO Value: {do_value}, PH Value: {ph_value}")
            if self._lcd_display is None:
                continue
            self._lcd_display.text(f"Temp   | {temp} {"C" if self._temp_format == "Celsius" else "F"}", 1)
            self._lcd_display.text(f"Humid  | {humid}%", 2)
            self._lcd_display.text(f"DO     | {do_value}mg/L", 3)
            self._lcd_display.text(f"pH     | {ph_value} pH", 4)
            time.sleep(1)

class TaskScheduler:
    def __init__(self,
                 interval: Optional[Tuple[int, int, int]] = None, 
                 time_based: bool = False, 
                 schedule_time: Optional[dt_time] = None, 
                 frequency: Optional[str] = None, 
                 day_of_week: Optional[str] = None):
        self.time_based = time_based
        self._frequency = frequency
        self._interval = interval
        self._schedule_time = schedule_time
        self._day_of_week = day_of_week
        self._job:schedule.Job = None  
        self._lock = threading.Lock()  # Thread-safe lock

    @property
    def interval(self) -> Optional[Tuple[int, int, int]]:
        return self._interval

    @interval.setter
    def interval(self, interval: Optional[Tuple[int, int, int]]):
        if self.time_based:
            self._interval = None
            return
        if interval is not None:
            if not (isinstance(interval, tuple) and len(interval) == 3):
                raise ValueError("Interval must be a tuple of three integers: (hours, minutes, seconds).")
            hours, minutes, seconds = interval
            if not (0 <= hours < 24):
                raise ValueError("Hours must be between 0 and 23.")
            if not (0 <= minutes < 60):
                raise ValueError("Minutes must be between 0 and 59.")
            if not (0 <= seconds < 60):
                raise ValueError("Seconds must be between 0 and 59.")
        self._interval = interval

    @property
    def schedule_time(self) -> Optional[dt_time]:
        return self._schedule_time

    @schedule_time.setter
    def schedule_time(self, schedule_time: Optional[dt_time]):
        if not self.time_based:
            self._schedule_time = None
            return
        if schedule_time is not None and not isinstance(schedule_time, dt_time):
            raise ValueError("Schedule time must be a valid datetime.time object.")
        self._schedule_time = schedule_time

    @property
    def frequency(self) -> Optional[str]:
        return self._frequency

    @frequency.setter
    def frequency(self, frequency: Optional[str]):
        valid_frequencies = {"daily", "weekly", "monthly", "custom"}
        if self.time_based and frequency not in valid_frequencies:
            raise ValueError(f"Frequency must be one of {valid_frequencies} for time-based tasks.")
        self._frequency = frequency

    @property
    def day_of_week(self) -> Optional[str]:
        return self._day_of_week

    @day_of_week.setter
    def day_of_week(self, day_of_week: Optional[str]):
        valid_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
        if self.time_based and self.frequency == "weekly":
            if day_of_week and day_of_week.lower() not in valid_days:
                raise ValueError(f"Invalid day_of_week. Must be one of {valid_days}.")
        self._day_of_week = day_of_week.lower() if day_of_week else None

    def stop_schedule(self):
        with self._lock:  # Ensure thread-safe access
            if self._job:
                print(self._job)
                schedule.cancel_job(self._job)

    def set_schedule(self, func: Callable):
        with self._lock:  # Ensure thread-safe access
            if self._job:
                print(self._job)
                schedule.cancel_job(self._job)
            if self.time_based:
                if self.frequency == "daily":
                    self._job = schedule.every().day.at(self.schedule_time.strftime("%H:%M:%S")).do(func)
                elif self.frequency == "weekly":
                    if not self.day_of_week:
                        raise ValueError("Day of the week must be specified for weekly scheduling.")
                    self._job = getattr(schedule.every(), self.day_of_week).at(
                        self.schedule_time.strftime("%H:%M:%S")).do(func)
                else:
                    raise ValueError("Unsupported frequency for time-based tasks.")
            else:
                if self.interval:
                    hours, minutes, seconds = self.interval
                    total_seconds = hours * 3600 + minutes * 60 + seconds
                    self._job = schedule.every(total_seconds).seconds.do(func)
                else:
                    raise ValueError("Interval must be set for interval-based scheduling.")

    def modify_schedule(self, func: Callable, **kwargs):
        with self._lock:  # Ensure thread-safe access
            if "interval" in kwargs:
                self.interval = kwargs["interval"]
            if "time_based" in kwargs:
                self.time_based = kwargs["time_based"]
            if "schedule_time" in kwargs:
                self.schedule_time = kwargs["schedule_time"]
            if "frequency" in kwargs:
                self.frequency = kwargs["frequency"]
            if "day_of_week" in kwargs:
                self.day_of_week = kwargs["day_of_week"]

            self.set_schedule(func)

    def save_to_json(self, filepath: str):
        schedule_data = {
            "time_based": self.time_based,
            "interval": self.interval,
            "schedule_time": self.schedule_time.strftime("%H:%M:%S") if self.schedule_time else None,
            "frequency": self.frequency,
            "day_of_week": self.day_of_week,
        }
        with open(filepath, "w") as file:
            json.dump(schedule_data, file, indent=4)

    @staticmethod
    def load_from_json(filepath: str) -> "TaskScheduler":
        with open(filepath, "r") as file:
            data = json.load(file)

        scheduler = TaskScheduler(
            time_based=data["time_based"],
            interval=tuple(data["interval"]) if data["interval"] else None,
            schedule_time=datetime.strptime(data["schedule_time"], "%H:%M:%S").time() if data["schedule_time"] else None,
            frequency=data["frequency"],
            day_of_week=data["day_of_week"],
        )
        return scheduler

    @staticmethod
    def run_pending():
        while True:
            schedule.run_pending()
            time.sleep(1)


