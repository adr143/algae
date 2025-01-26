document.addEventListener('DOMContentLoaded', function () {
    const frequencyField = document.getElementById('frequency');
    const timeSchedGroup = document.getElementById('time_sched_group');
    const dayWeekGroup = document.getElementById('day_week_group');
    const intervalGroup = document.getElementById('interval_group');
    const intervalHours = document.getElementById('interval_hours');
    const intervalMinutes = document.getElementById('interval_minutes');
    const intervalSeconds = document.getElementById('interval_seconds');

    function updateVisibility() {
        const frequency = frequencyField.value;

        // Show/Hide time schedule
        timeSchedGroup.classList.toggle('hidden', !['Daily', 'Weekly', 'Monthly'].includes(frequency));

        // Show/Hide day of the week
        dayWeekGroup.classList.toggle('hidden', frequency !== 'Weekly');

        // Show/Hide interval fields
        intervalGroup.classList.toggle('hidden', frequency !== 'Custom');
    }

    function validateInterval() {
        const hours = parseInt(intervalHours.value) || 0;
        const minutes = parseInt(intervalMinutes.value) || 0;
        const seconds = parseInt(intervalSeconds.value) || 0;

        if (hours === 0 && minutes === 0 && seconds < 10) {
            intervalSeconds.setCustomValidity('Seconds must not be less than 10 if hours and minutes are 0.');
        } else {
            intervalSeconds.setCustomValidity('');
        }
    }

    frequencyField.addEventListener('change', updateVisibility);
    intervalHours.addEventListener('input', validateInterval);
    intervalMinutes.addEventListener('input', validateInterval);
    intervalSeconds.addEventListener('input', validateInterval);

    updateVisibility();
});

function fetchDateTIme() {
    fetch('http://127.0.0.1:5000/data/datetime') // Flask endpoint
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        date_elem = document.getElementById('date')
        time_elem = document.getElementById('time')

        if (date_elem || time_elem) {
          document.getElementById('date').textContent = data.date;
          document.getElementById('time').textContent = data.time;
        }
      })
      .catch(error => {
        console.error('Error connecting to Flask:', error);
      });
  }

function fetchStatus() {
    fetch('http://127.0.0.1:5000/data/status') // Flask endpoint
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        const temp_format = () => {
          if (typeof data.temp_format === "string" && data.temp_format.toLowerCase() === "celsius") {
            return "C";
          }
          return "F";
        };

        ph_elem = document.getElementById('ph')
        do_elem = document.getElementById('do')
        temp_elem = document.getElementById('temp')
        humid_elem = document.getElementById('humid')
        
        if(ph_elem || temp_elem || humid_elem || do_elem) {
          document.getElementById('ph').textContent = `${data.ph_value} pH`;
          document.getElementById('do').textContent = `${data.do_value} mg/L`;
          document.getElementById('temp').textContent = `${data.temp} ${temp_format()}`;
          document.getElementById('humid').textContent = `${data.humid}%`;
        }
      })
      .catch(error => {
        console.error('Error connecting to Flask:', error);
      });
  }
  
  setInterval(fetchDateTIme, 1000);
  setInterval(fetchStatus, 1000);