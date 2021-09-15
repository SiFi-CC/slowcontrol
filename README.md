# Introduction

api.py uses the Python Flask package to format MariaDB data into REST JSON format. Data from various devices are stored in the `gccb` database. First they are registered under the `devices` table. 

Data coming into the `outputs` table depend on the frequency of the measurements set by `listen.py` for the 1wire temperature sensor and `C11204-02.cpp` for the C11204-02 SiPM voltage sensor. The MOTech power supply measured voltage is also reported.


# Database

Any new devices for long term monitoring can be registered in the `devices` table. After that, the generated `device_id` can be used to identify the device when inserting a new measurement point in the `outputs` table. Typically one would use the sql `WHERE` for filtering measurement values from a particular devices

# Web server

The Flask application runs on `Apache2` on wsgi. Several REST API endpoints are

- /home
- /temperature/<int:id>
- /voltage/<int:id>
- /motor
 
Plots for temperature and voltage are generated from `matplotlib` and updated on refresh.

The detector and devices are defined by an XML file. Devices can only be turned on if it is enabled in the XML.

Runs are also defined in the XML file, be it calibration or any other type. Currently only the calibration runs are properly defined. This requires the `<measurement position=x duration=y pause=z />` tag to be present. Each measurement tag contains information on the position of the calibration arm and the data acquisition time.

# Sample detector XML

A working XML is available under `files/current.xml`.

# Temperature measurement

This measurement is done with 1wire interface. Currently systemd is used to manage this `monkey.service`. `listen.py` measurement frequency depends on the `systemd` scripts `monkey.service` and the corresponding timer `monkey.timer`. Running `listen.py` with `python3` would only produce a single readout, so for persistence, use `systemctl start monkey` instead.

# TODO:

Find and kill zombie processes
