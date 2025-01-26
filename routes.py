from flask import Blueprint, render_template, Response, jsonify, redirect, url_for, request
from misc import CameraStream, Arduino_Serial
from werkzeug.utils import secure_filename
from forms import Settings, StatusForm
from misc import TaskScheduler
from datetime import datetime
from models import Status
import pandas as pd
import threading
import openpyxl
import time
import json
import cv2
import os

class Router:
    def __init__(self, app,
                database,
                stream=None, 
                serial_com=None,
                dht_device=None,
                router_name:str='main', 
                templates_path:str='templates', 
                static_path:str='static'):
        self._app = app
        self._stream = stream
        self._database = database
        self._serial_com = serial_com
        self._static_path = static_path
        self._router_name = router_name
        self._templates_path = templates_path
        self._dht_device = dht_device
        self._temp_format = "Celsius"
        self._main_bp = Blueprint(self._router_name, __name__, template_folder=self._templates_path, static_folder=self._static_path)
        self._record_sched = TaskScheduler([0, 0, 10])
        if os.path.exists("data/sched.json"):
            self._record_sched = TaskScheduler.load_from_json("data/sched.json")
        self._thread = threading.Thread(target=self.start_sched, daemon=True).start()

        self._main_bp.add_url_rule('/', 'home', self.home)
        self._main_bp.add_url_rule('/video_feed', 'video_feed', self.video_feed)
        self._main_bp.add_url_rule('/table', 'table', self.table)
        self._main_bp.add_url_rule('/data/datetime', 'datetime', self.get_datetime, methods=['GET'])
        self._main_bp.add_url_rule('/data/status', 'status', self.get_status, methods=['GET'])
        self._main_bp.add_url_rule('/settings', 'settings', self.settings, methods=['GET', 'POST'])
        self._main_bp.add_url_rule('/add_status', 'add_status', self.add_status, methods=['GET', 'POST'])
        self._main_bp.add_url_rule('/export-excel', 'export_excel', self.export_excel, methods=['POST', 'GET'])
        self._main_bp.add_url_rule('/clear-table', 'clear_table', self.clear_table, methods=['POST', 'GET'])

        print("Oh")
        with app.app_context():
            self._database.create_all()

    def start_routing(self, host_ip="0.0.0.0", port_num=5000):
        self._record_sched.set_schedule(self.record_status)
        file_path = os.path.join('data', 'settings.json')
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                settings = json.load(file)
                self._temp_format = settings.get('temp_unit')
        self._app.register_blueprint(self._main_bp)
        self._app.run(host=host_ip, port=port_num)

    def start_sched(self):
        while True:
            self._record_sched.run_pending()
            time.sleep(1)

    def home(self):
        return render_template('home.html')
    
    def get_status(self):
        ph_data = 0
        do_data = 0
        temp = 0
        humid = 0
        if self._serial_com:
            ph_data = self._serial_com.get_ph_value()
            do_data = self._serial_com.get_do_value()
        if self._dht_device:
            temp = self._dht_device.temperature
            humid = self._dht_device.humidity
        return jsonify({"ph_value":ph_data, "do_value": do_data, "temp": temp, "humid": humid, "temp_format": self._temp_format})
    
    def video_feed(self):
        return Response(self._stream.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    
    def get_datetime(self):
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%I:%M:%S %p")
        return jsonify({"date": current_date, "time": current_time})
    
    def table(self):
        statuses = Status.get_all_statuses()
        return render_template('table.html', statuses=statuses)

    def settings(self):
        file_path = os.path.join('data', 'settings.json')
        form = Settings()
        if request.method != 'POST':
            if os.path.exists(file_path):
                with open(file_path, 'r') as json_file:
                    settings = json.load(json_file)
                    form.time_sched.data = datetime.strptime(settings['time_sched'], '%H:%M:%S')
                    form.temp_unit.data = settings['temp_unit']
                    form.frequency.data = settings['frequency']
                    form.day_week.data = settings['day_week']
                    form.interval_hours.data = settings['interval_hours']
                    form.interval_minutes.data = settings['interval_minutes']
                    form.interval_seconds.data = settings['interval_seconds']

            return render_template('settings.html', form=form)
        
        if form.validate_on_submit():
            settings = {
                'time_sched': form.time_sched.data.strftime('%H:%M:%S'),
                'temp_unit': form.temp_unit.data,
                'frequency': form.frequency.data,
                'day_week': form.day_week.data,
                'interval_hours': form.interval_hours.data,
                'interval_minutes': form.interval_minutes.data,
                'interval_seconds': form.interval_seconds.data,
            }

            self._record_sched.time_based = form.frequency.data.lower() != "custom"
            self._record_sched.interval = (form.interval_hours.data, 
                                         form.interval_minutes.data, 
                                         form.interval_seconds.data)
            self._record_sched.schedule_time = form.time_sched.data
            self._record_sched.frequency = form.frequency.data.lower() if form.frequency.data.lower() != "custom" else self._record_sched.frequency
            self._record_sched.day_of_week = form.day_week.data

            self._record_sched.save_to_json("data/sched.json")
            self._record_sched.set_schedule(self.record_status)

            self._temp_format = form.temp_unit.data

            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            

            with open(file_path, 'w') as json_file:
                json.dump(settings, json_file, indent=4)
            
            return redirect(url_for('main.home'))
        
    def record_status(self):
        temperature = self._dht_device.temperature if self._dht_device else 0
        humidity = self._dht_device.humidity if self._dht_device else 0
        do_algal = self._serial_com.get_do_value() if self._serial_com else 0
        ph_value = self._serial_com.get_ph_value() if self._serial_com else 0
        new_status = Status(
            timestamp=datetime.now(),
            temperature=temperature,
            humidity=humidity,
            do_algal=do_algal,
            ph_value=ph_value
        )
        with self._app.app_context():
            self._database.session.add(new_status)
            self._database.session.commit()
        print("Status Recorded")
    
    def add_status(self):
        form = StatusForm()
        if form.validate_on_submit():
            new_status = Status(
                timestamp=datetime.now(),
                temperature=form.temperature.data,
                humidity=form.humidity.data,
                do_algal=form.do_algal.data,
                ph_value=form.ph_value.data
            )
            self._database.session.add(new_status)
            self._database.session.commit()
            return redirect(url_for('main.home'))

        return render_template('add_status.html', form=form)
    
    def export_excel(self):
        statuses = Status.query.all()

        data = [
            {"ID": i+1,
            "Temperature": status.temperature,
            "Humidity": status.humidity,
            "DO(mg/L)": status.do_algal,
            "pH": status.ph_value,
            "Date": status.timestamp.strftime("%Y-%m-%d"),
            "Time": status.timestamp.strftime("%I:%M:%S %p"),
            }
            for i, status in enumerate(statuses)
        ]

        df = pd.DataFrame(data)

        excel_file = pd.ExcelWriter('users.xlsx', engine='openpyxl')
        df.to_excel(excel_file, index=False, sheet_name='Users')
        excel_file.save()

        with open('users.xlsx', 'rb') as f:
            excel_data = f.read()

        response = Response(excel_data, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response.headers['Content-Disposition'] = 'attachment; filename=users.xlsx'
        return response
    
    def clear_table(self):
        Status.delete_all()
        return redirect(url_for('main.table'))
