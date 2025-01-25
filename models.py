from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime

db = SQLAlchemy()
# bcrypt = Bcrypt()


class Status(db.Model):
    __tablename__ = 'parameter status'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.now()) 
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    do_algal = db.Column(db.Float)
    ph_value = db.Column(db.Float)

    def __init__(self, timestamp, temperature, humidity, ppm_algal, ph_value):
        self.timestamp = timestamp
        self.temperature = temperature
        self.humidity = humidity
        self.do_algal = ppm_algal
        self.ph_value = ph_value

    def __repr__(self):
        return f'<Status(timestamp={self.timestamp}, temperature={self.temperature}, humidity={self.humidity}, ppm_algal={self.do_algal}, ph_value={self.ph_value})>'
    
    def serialize(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'temperature': self.temperature,
            'humidity': self.humidity,
            'ppm_algal': self.do_algal,
            'ph_value': self.ph_value
        }
    
    @staticmethod
    def get_latest_status():
        return Status.query.order_by(Status.timestamp.desc()).first()
    
    @staticmethod
    def get_all_statuses():
        return Status.query.all()
    
    @staticmethod
    def get_status_by_id(status_id):
        return Status.query.get(status_id)
    
    