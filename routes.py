from flask import Blueprint, render_template, Response, jsonify, redirect, url_for, request
from misc import CameraStream, Arduino_Serial
from werkzeug.utils import secure_filename
from forms import Settings, StatusForm
from datetime import datetime
from models import Status
import pandas as pd
import threading
import openpyxl
import json
import cv2
import os

class Router:
    def __init__(self, app, database, stream, serial_com, router_name:str='main', templates_path:str='templates', static_path:str='static'):
        self.app = app
        self.database = database
        self.stream = stream
        self.serial_com = serial_com
        self.router_name = router_name
        self.templates_path = templates_path
        self.static_path = static_path
        self.main_bp = Blueprint(self.router_name, __name__, template_folder=self.templates_path, static_folder=self.static_path)

        self.main_bp.add_url_rule('/', 'home', self.home)
        self.main_bp.add_url_rule('/video_feed', 'video_feed', self.video_feed)
        self.main_bp.add_url_rule('/table', 'table', self.table)
        self.main_bp.add_url_rule('/data/datetime', 'datetime', self.get_datetime, methods=['GET'])
        self.main_bp.add_url_rule('/data/status', 'status', self.get_status, methods=['GET'])
        self.main_bp.add_url_rule('/settings', 'settings', self.settings, methods=['GET', 'POST'])
        self.main_bp.add_url_rule('/add_status', 'add_status', self.add_status, methods=['GET', 'POST'])
        self.main_bp.add_url_rule('/export-excel', 'export_excel', self.export_excel, methods=['POST'])
        self.main_bp.add_url_rule('/clear-table', 'clear_table', self.clear_table, methods=['POST'])

        with app.app_context():
            self.database.create_all()

    def start_routing(self, host_ip="0.0.0.0", port_num=5000):
        self.app.register_blueprint(self.main_bp)
        self.app.run(host=host_ip, port=port_num)

    def home(self):
        return render_template('home.html')
    
    def get_status(self):
        ph_data = self.serial_com.get_ph_value
        do_data = self.serial_com.get_do_algal()
        return jsonify({"ph_value":ph_data, "do_value": do_data})
    
    def video_feed(self):
        return Response(self.stream.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    
    def get_datetime(self):
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M:%S")
        return jsonify({"date": current_date, "time": current_time})
    
    def table(self):
        statuses = Status.get_all_statuses()
        return render_template('table.html', statuses=statuses)

    def settings(self):
        form = Settings()
        if form.validate_on_submit():
            settings = {
                'time_sched': form.time_sched.data.strftime('%H:%M:%S'),
                'temp_unit': form.temp_unit.data
            }
            file_path = os.path.join('data', 'output.json')

            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            

            with open(file_path, 'w') as json_file:
                json.dump(settings, json_file, indent=4)
            
            return redirect(url_for('main.home'))
        return render_template('settings.html', form=form)
    
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
            self.database.session.add(new_status)
            self.database.session.commit()
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
        Status.query.delete()
        self.database.session.commit()
        return redirect(url_for('main.table'))
