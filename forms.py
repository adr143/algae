from flask_wtf import FlaskForm
from wtforms import TimeField, SelectField, IntegerField, SubmitField, FloatField
from wtforms.validators import DataRequired, NumberRange
import datetime

class Settings(FlaskForm):
    frequency = SelectField('Frequency', choices=["Daily", "Weekly", "Monthly", "Custom"], validators=[DataRequired()])
    time_sched = TimeField('Time Sched', default= datetime.time(10, 0, 0))
    day_week = SelectField('Dayweek', choices=["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"], default="Sunday")
    interval_hours = IntegerField('Interval Hours', validators=[NumberRange(min=0, max=23, message="Must be between 0 and 23 inclusive")], default=0)
    interval_minutes = IntegerField('Interval Minutes', validators=[NumberRange(min=0, max=59, message="Must be between 0 and 59 inclusive")], default=0)
    interval_seconds = IntegerField('Interval Seconds', validators=[NumberRange(min=0, max=59, message="Must be between 0 and 59 inclusive")], default=10)
    temp_unit = SelectField('Temperature Units', choices=["Celsius", "Fahrenheit"], validators=[DataRequired()])
    submit = SubmitField('Save Settings')

class StatusForm(FlaskForm):
    temperature = FloatField('Temperature', validators=[DataRequired()])
    humidity = FloatField('Humidity', validators=[DataRequired()])
    ppm_algal = FloatField('PPM Algal', validators=[DataRequired()])
    ph_value = FloatField('pH Value', validators=[DataRequired()])
    submit = SubmitField('Submit')
