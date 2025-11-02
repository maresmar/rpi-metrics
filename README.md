# RPi metrics for Prometheus

This is a simple script that collect stats about power usage and connected clients and publish them for Prometheus to scrape.

```bash
python3 rpi-metrics.py
```

Prometheus metrics are are available on http://127.0.0.1:8000/metrics, see example:

```prometheus
rpi_adc_value{name="3V7_WL_SW",type="current"} 0.05562801
rpi_adc_value{name="3V3_SYS",type="current"} 0.1366302
...
rpi_adc_value{name="3V7_WL_SW",type="volt"} 3.671938
rpi_adc_value{name="3V3_SYS",type="volt"} 3.296114
...
rpi_wifi_station_connected_time_seconds{mac="ab:cd:ef:12:34:56"} 2161.0
...
power_energy_kWhs{ip="192.168.1.5"} 2042.0
```

## Sources

### Power

The script is using `vcgencmd pmic_read_adc` to generate stats to Prometheus, you cannot see full power consumption however, it can be useful to monitor things like the core voltage, check [full docs](https://github.com/raspberrypi/documentation/blob/develop/documentation/asciidoc/computers/raspberry-pi/power-supplies.adoc).

### Wifi AP

The script is parsing `iw` list of connected devices, so you could track devices on your WiFi

### Tapa P110

The script is collecting power consumption data from Tapa P110 using [Python library P100](https://github.com/almottier/TapoP100).