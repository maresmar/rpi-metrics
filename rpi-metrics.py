import re
import os
import subprocess
import time
from wsgiref.simple_server import make_server

from dotenv import load_dotenv
from prometheus_client import Gauge, make_wsgi_app
from PyP100 import PyP110


load_dotenv()
P110_USERNAME = os.getenv("P110_USERNAME")
P110_PASSWORD = os.getenv("P110_PASSWORD")
P110_HOST = os.getenv("P110_HOST")


# Gauge for WiFi connected time
connected_time_metric = Gauge(
    'rpi_wifi_station_connected_time_seconds',
    'Connection time of connected WiFi stations',
    ['mac']
)

# ADC gauge without ID label, only name and type
adc_metric = Gauge(
    'rpi_adc_value',
    'Pi5 ADC voltage/current reading',
    ['name', 'type']  # type = current or volt
)

# Gauge for power
power_energy_metric = Gauge(
    'power_energy_kWhs',
    'kWh of energy consumed per month',
    ['ip']
)

power_current_metric = Gauge(
    'power_current_mWs',
    'mW of current currently drawn',
    ['ip']
)


def parse_iw_station_dump():
    try:
        output = subprocess.check_output(
            ['iw', 'dev', 'wlan0', 'station', 'dump'],
            text=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error calling iw: {e}")
        return []

    stations = []
    current_mac = None
    current_info = {}

    for line in output.strip().splitlines():
        line = line.strip()
        mac_match = re.match(r'^Station\s+([0-9a-f:]{17})', line)
        if mac_match:
            if current_mac and 'connected_time' in current_info:
                stations.append(current_info)
            current_mac = mac_match.group(1)
            current_info = {'mac': current_mac}
        elif line.startswith("connected time:") and current_mac:
            match = re.search(r'connected time:\s+(\d+)\s+seconds', line)
            if match:
                current_info['connected_time'] = int(match.group(1))

    if current_mac and 'connected_time' in current_info:
        stations.append(current_info)

    return stations


def update_p110_metrics():
    # Update WiFi connected time
    try:
        p110 = PyP110.P110(P110_HOST, P110_USERNAME, P110_PASSWORD)
        data = p110.getEnergyUsage()
        power_energy_metric.labels(ip=P110_HOST).set(data["month_energy"])
        power_current_metric.labels(ip=P110_HOST).set(data["current_power"])
    except e:
        print(f"p110 error {e}")


def update_metrics():
    # Update WiFi connected time
    stations = parse_iw_station_dump()
    for station in stations:
        connected_time_metric.labels(mac=station['mac']).set(
            station['connected_time'])

    # Update ADC metrics
    res = subprocess.run(["vcgencmd", "pmic_read_adc"], capture_output=True)
    lines = res.stdout.decode("utf-8").splitlines()
    for line in lines:
        m = re.search(
            r'([A-Z_0-9]+)_[VA] (current|volt)\([0-9]+\)=([0-9.]+)', line)
        if m:
            name = m.group(1)
            typ = m.group(2)
            val = float(m.group(3))
            adc_metric.labels(name=name, type=typ).set(val)

    # Updata Tapa metrics
    update_p110_metrics()


def main():
    # Create WSGI app for Prometheus metrics
    app = make_wsgi_app()

    # Start WSGI HTTP server on localhost only (127.0.0.1:8000)
    httpd = make_server('127.0.0.1', 8000, app)
    print("Serving metrics on http://127.0.0.1:8000/metrics")

    # Run the metrics update loop in background thread
    import threading

    def metrics_loop():
        while True:
            update_metrics()
            time.sleep(15)

    threading.Thread(target=metrics_loop, daemon=True).start()

    # Serve forever
    httpd.serve_forever()


if __name__ == "__main__":
    main()
