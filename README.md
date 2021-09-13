# Introduction

api.py uses the Python Flask package to format MariaDB data into REST JSON format. Data from various devices are stored in the `gccb` database. First they are registered under the `devices` table. 

Data coming into the `outputs` table depend on the frequency of the measurements set by `listen.py` for the 1wire temperature sensor and `SiPMLogger.cpp` for the C11204-02 SiPM voltage sensor.

`listen.py` measurement frequency depends on the `systemd` scripts `monkey.service` and the corresponding timer `monkey.timer`. Running `listen.py` with `python3` would only produce a single readout, so for persistence, use `systemctl start monkey` instead. `SiPMLogger.cpp` still runs the old way.

# Database

Any new devices for long term monitoring can be registered in the `devices` table. After that, the generated `device_id` can be used to identify the device when inserting a new measurement point in the `outputs` table. Typically one would use the sql `WHERE` for filtering measurement values from a particular devices

# Web server

The Flask application runs on `Apache2` on wsgi. Several REST API endpoints are

- /home
- /temperature/<int:id>
- /voltage
 
Plots for temperature and voltage are generated from `matplotlib` and updated on refresh.
