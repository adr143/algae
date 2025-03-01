from flask import Flask
from flask_cors import CORS
from routes import Router
from models import db
from misc import CameraStream, Arduino_Serial, TaskScheduler
from serial import SerialException
import threading
import os

app = Flask(__name__)
serial_bus = "COM3"

CORS(app)

camera = CameraStream(0)
try:
    serial_command = Arduino_Serial(serial_bus)
except SerialException:
    print("Failed to connect")
    serial_command = None


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///track.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["UPLOAD_EXTENSIONS"] = [".jpg", ".png"]
app.config["UPLOAD_PATH"] = "image_uploads"
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

db.init_app(app)
# bcrypt.init_app(app)

router = Router(app, db, camera, serial_command)

if __name__ == '__main__':
    router.start_routing()