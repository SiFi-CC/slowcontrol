from multiprocessing import Process, active_children
import subprocess
import sys
import os
import time
import secrets
import zmq
import requests
from dotenv import load_dotenv
from devices.RSHMP4040.monitor import monitor as rshmp4040_monitor
from devices.RSHMP4040 import RSHMP4040 as rshmp4040_state
from devices.LocalMachine.monitor import monitor as localmachine
from devices.DS1490F.monitor import monitor as temperature
from flask import Flask, request, redirect, render_template, session, jsonify
app = Flask(__name__, static_folder='static')
app.secret_key = secrets.token_hex(16)
tp = []
@app.route("/remaining")
def remaining():
    if not session.get('startTime') or not session.get('acquisitionTime'):
        return jsonify(success=False)
    remaining = (time.time() - float(session['startTime']) ) / float(session['acquisitionTime'] )
    if remaining > 1:
        return jsonify(100)
    return jsonify(int(remaining*100) )
@app.route("/start_daq", methods=['GET', 'POST'])
def start_daq():
    if request.method == 'POST':
        if not request.form['acquisitionTime']:
            return {"status": "alert-warning", "message": "No value entered for acquisition time."}, 200
        if not request.form['acquisitionTime'].isnumeric():
            return {"status": "alert-warning", "message": "Acquisition time value is non-numeric."}, 200
        if float(request.form['acquisitionTime']) < 1:
            return {"status": "alert-warning", "message": "Acquisition time value is less than one second."}, 200
        acquisitionTime = request.form['acquisitionTime']
        session['startTime'] = time.time()
        session['acquisitionTime'] = acquisitionTime
        os.chdir("/home/lab/Desktop/DAQ/build/")
        proc = subprocess.Popen(["python3", "-u", "./acquire_sipm_data", "--config", "/home/lab/Desktop/DAQ/sandbox/config.ini", "-o", "run99999", "--mode", "qdc", "--time", "--enable-hw-trigger", acquisitionTime], stdout=subprocess.PIPE)
    return {"status": "alert-success", "message": "DAQ started."}, 200
    # TODO: do we want to check if the DAQ acquire process is really gone?
@app.route("/start_devices", methods=['GET', 'POST'])
def start_devices():
    if request.method == 'POST':
        # start power supply monitor
        rs = rshmp4040_state.state()
        r = Process(name="rshmp4040", target=rshmp4040_monitor)
        r.start()
        print("Started RSHMP4040 monitor.")
        time.sleep(5)
        subprocess.call(["mv", "/tmp/d.sock", "/tmp/old.d.sock"], stdout=subprocess.PIPE)
        subprocess.call(["killall", "daqd"], stdout=subprocess.PIPE)
        print("Cleaning up possible remnants from improper program termination. Usually should report warnings or errors.")
        p = subprocess.Popen(["/home/lab/Desktop/DAQ/build/./daqd", "--daq-type=PFP_KX7"], stdout=subprocess.PIPE)
        print("Initialising daqd from TOFPET2.")
        time.sleep(5)
        # start disk space monitor
        l = Process(name="localmachine", target=localmachine)
        l.start()
        print("Started disk space monitor.")
        time.sleep(5)
        # start temperature monitor
        m = Process(name="temperature", target=temperature)
        m.start()
        print("Started temperature monitor.")
        if p:
            print("Started daqd.")
            tp[0] = {"name": "FEBD", "state": 1}
            subprocess.Popen(["python3", "-u", "/home/lab/Desktop/slowcontrol/devices/TOFPET2c/monitor.py"], stdout=subprocess.PIPE)
            print("Started TOFPET2c ASIC temperature monitor.")
        else:
            return {"status": "alert-warning", "message": "Problem starting the daqd process."}, 200
        snapshotType = request.form['snapshotType']
        snapshotInterval = request.form['snapshotInterval']
        subprocess.Popen(["/home/lab/Desktop/DAQ/monitoring/./online", "-t", snapshotType, "-i", snapshotInterval], stdout=subprocess.PIPE)
        return {"status": "alert-success", "message": "All devices started.", "rshmp4040": rs, "tofpet": tp}, 200
@app.route("/stop_devices", methods=['GET', 'POST'])
def stop_devices():
    if request.method == 'POST':
        try:
            pid = subprocess.check_output(["pgrep", "-f", "python3 -u /home/lab/Desktop/slowcontrol/devices/TOFPET2c/monitor.py"])
            print(f"Found pid of TOFPET2c temperature monitor, pid={pid.decode().strip()}")
            subprocess.call(["kill", "-INT", pid.decode().strip() ] )
            print("Terminating TOFPET2c temperature monitor.")
        except subprocess.CalledProcessError:
            print("TOFPET2 temperature monitor process does not exist.")
        subprocess.call(["killall", "daqd"], stdout=subprocess.PIPE)
        tp[0] = {"name": "FEBD", "state": 0}
        print("Terminating TOFPET2c daqd process")
        for p in active_children():
            print(f"Terminating {p.name} monitor process.")
            p.terminate()
        try:
            snapshotType = request.form['snapshotType']
            snapshotInterval = request.form['snapshotInterval']
            pid = subprocess.check_output(["pgrep", "-f", f"/home/lab/Desktop/DAQ/monitoring/./online -t {snapshotType} -i {snapshotInterval}"])
            print(f"Found pid of online data quality monitor, pid={pid.decode().strip()}")
            subprocess.call(["kill", "-INT", pid.decode().strip() ] )
            print("Terminating online data quality monitor.")
        except subprocess.CalledProcessError:
            print("Online data quality monitor process does not exist.")
        return {"status": "alert-success", "message": "All devices stopped."}, 200
@app.route("/", methods=['GET', 'POST'])
def home():
    load_dotenv()
    endpoint = "https://bragg.if.uj.edu.pl/SiFiCCData/Prototype/api/measurements?q=last_inserted_id"
    runs = requests.get(url = endpoint, auth=requests.auth.HTTPBasicAuth(os.getenv('DB_USER'), os.getenv('DB_PASS') ) )
    ps = rshmp4040_state.state()
    ps = 0
    tp = 0
    return render_template("app.html", data={'run': runs.json()[0]} )
if __name__ == "__main__":
    app.run(host="0.0.0.0")
