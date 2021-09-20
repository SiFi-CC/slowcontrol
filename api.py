import io
import os
import json
import requests
from flask import Flask, flash, Response, render_template, request, redirect
from werkzeug.utils import secure_filename
from mysql.connector import connect, Error
from datetime import date, datetime
from matplotlib.dates import AutoDateLocator, DateFormatter
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from PIL import Image, ImageFont, ImageDraw
from bs4 import BeautifulSoup
import subprocess
import signal
import threading
import time

from extensions import MotorInterface
from serial import SerialException

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'files/')
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ['xml']
def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))
def create_figure(urls=[], title="", labels=[], xlabel="x", ylabel="y"):
    figure = Figure(figsize=(15, 2) )
    ax = figure.add_subplot(1, 1, 1)
    k = 0
    for url in urls:
        r = requests.get(url)
        data = r.json()
        x = []
        y = []
        for d in data:
            x.append(datetime.fromisoformat(d[1]) )
            y.append(d[0])
        ax.plot(x, y, label=labels[k])
        k = k + 1
    locator = AutoDateLocator()
    ax.set_title(title)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M") )
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend(loc="best")
    return figure
def create_two_axes_figure(urls=[], title="", labels=[], xlabel="x", ylabel=["y0", "y1"]):
    figure = Figure(figsize=(15, 2) )
    ax0 = figure.add_subplot(1, 1, 1)
    r0 = requests.get(urls[0])
    data = r0.json()
    x = []
    y0 = []
    for d in data:
        x.append(datetime.fromisoformat(d[1]) )
        y0.append(d[0])
    ax0.plot(x, y0, label=labels[0])
    locator = AutoDateLocator()
    ax0.set_title(title)
    ax0.xaxis.set_major_locator(locator)
    ax0.xaxis.set_major_formatter(DateFormatter("%H:%M") )
    ax0.set_xlabel(xlabel)
    ax0.set_ylabel(ylabel[0])

    ax1 = ax0.twinx()
    color = 'tab:orange'
    r1 = requests.get(urls[1])
    data = r1.json()
    x = []
    y1 = []
    for d in data:
        x.append(datetime.fromisoformat(d[1]) )
        y1.append(d[0])
    ax1.plot(x, y1, label=labels[1], color=color)
    ax1.set_title(title)
    ax1.xaxis.set_major_locator(locator)
    ax1.xaxis.set_major_formatter(DateFormatter("%H:%M") )
    ax1.set_xlabel(xlabel)
    ax1.set_ylabel(ylabel[1], color=color)
    ax1.tick_params(axis='y', labelcolor=color)
    handles,labels = [],[]

    for ax in figure.axes:
        for h,l in zip(*ax.get_legend_handles_labels()):
            handles.append(h)
            labels.append(l)
    ax.legend(handles, labels)
    return figure
def create_detector():
    contents = ""
    with open(UPLOAD_FOLDER + 'current.xml', 'r') as f:
        contents = f.read()
    data = BeautifulSoup(contents, "lxml")
    #print(data.run.find_all("measurement") )
    board3 = data.detector.find("board", attrs={"number":"3"}).find_all("sipm")
    board4 = data.detector.find("board", attrs={"number":"4"}).find_all("sipm")
    # size of image
    canvas = (800, 115)
    width=20
    height=20
    space=5
    frames = ([], [])
    for i in range(0, 16):
        # rectangles (width, height, left position, top position)
        frames[0].append((width, height, i*width+space, space, (i+1)+3*16) );
        frames[0].append((width, height, i*width+2*space, height+space, (i+1)+2*16) );
        frames[0].append((width, height, i*width+space, 2*height+space, (i+1)+16) );
        frames[0].append((width, height, i*width+2*space, 3*height+space, (i+1) ) );

        frames[1].append((width, height, 17*width + i*width+space, space, (i+1)+3*16) );
        frames[1].append((width, height, 17*width + i*width+2*space, height+space, (i+1)+2*16) );
        frames[1].append((width, height, 17*width + i*width+space, 2*height+space, (i+1)+16) );
        frames[1].append((width, height, 17*width + i*width+2*space, 3*height+space, (i+1) ) );
    # init canvas
    im = Image.new('RGBA', canvas, (255, 255, 255, 255))
    draw = ImageDraw.Draw(im)
    # draw rectangles
    fill = (255, 255, 255, 255)
    draw.text((space, 90), "Board 3", "black")
    for frame in frames[0]:
        x1, y1 = frame[2], frame[3]
        x2, y2 = frame[2] + frame[0], frame[3] + frame[1]
        for s in board3:
            if str(frame[4]) == s["id"]:
                fill = (0, 0, 0, 100)
        draw.rectangle([x1, y1, x2, y2], outline=(0, 0, 0, 255), fill=fill)
        draw.text((frame[2], frame[3]), " " + str(frame[4]), fill="black")
        fill = (255, 255, 255, 255)
    draw.text((space + 17*width, 90), "Board 4", "black")
    for frame in frames[1]:
        x1, y1 = frame[2], frame[3]
        x2, y2 = frame[2] + frame[0], frame[3] + frame[1]
        for s in board4:
            if str(frame[4]) == s["id"]:
                fill = (0, 0, 0, 100)
        draw.rectangle([x1, y1, x2, y2], outline=(0, 0, 0, 255), fill=fill)
        draw.text((frame[2], frame[3]), " " + str(frame[4]), fill="black")
        fill = (255, 255, 255, 255)
    draw.text((space, 100), "Coupling: " + data.detector['coupling'] + "mm, raster: " + data.detector['raster'], "black")
    return im
def interval(measurements):
    #lemur.zero()
    for measurement in measurements:
        #lemur.move_x(measurement['position'])
        print("Motor position moved by %s mm" % measurement['position'])
        time.sleep(int(measurement['pause']) )
        lemur.wavedump() #does not block, also updated the DB with run start/stop times
        time.sleep(int(measurement['duration']) )
        time.sleep(int(measurement['pause']) )
class Lemur(object):
    def __init__(self):
        self.processes = {}
        self.motor = MotorInterface.MotorInterface()
        self.status = self.motor.status
    def start(self, label, process):
        self.processes[label] = subprocess.Popen(process)
    def stop(self, label):
        self.processes[label].send_signal(signal.SIGINT)
    def zero(self):
        self.motor.zero()
        self.status = self.motor.status
    def move_x(self, x):
        try:
            val = int(x)
        except ValueError:
            print("calibration motor x-value not a valid number")
            return
        self.motor.move_x(int(x) )
        self.status = self.motor.status
    def wavedump(self):
        subprocess.Popen([os.path.join(os.path.dirname(__file__), "devices/CAENDigitizer/wavedump-3.10.2_mod/src/wavedump") ] )

class Monkey(object):
    def __init__(self):
        self.mysql_conn = ""
        self.results = []
        self.mysql()
    def mysql(self):
        try:
            self.mysql_conn = connect(host="localhost", database=os.getenv("DATABASE"), user=os.getenv("USER"), password=os.getenv("PASSWORD"), auth_plugin='mysql_native_password', autocommit='True')
        except Error as e:
            print(e)
    def read_from_table(self, device_id):
        cursor = self.mysql_conn.cursor()
        #cursor.execute("SELECT value, created FROM outputs WHERE device_id=%s AND created >= CURDATE() - INTERVAL 1 DAY;", (device_id, ) )
        cursor.execute("SELECT value, created FROM outputs WHERE device_id=%s AND created >= CURDATE();", (device_id, ) )
        self.results = cursor.fetchall()
        return self.results
    def get_run(self):
        cursor = self.mysql_conn.cursor(dictionary=True)
        cursor.execute("SELECT id, start, stop FROM runs ORDER BY id DESC LIMIT 1;")
        self.results = cursor.fetchone()
        return self.results
    def __del__(self):
        self.mysql_conn.close();

os.environ['MPLCONFIGDIR'] = '/tmp/'
app = Flask(__name__, static_folder='static')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 #max 16mb
lemur = Lemur()
monkey = Monkey()
@app.route("/home")
def home():
    contents = ""
    with open(UPLOAD_FOLDER + 'current.xml', 'r') as f:
        contents = f.read()
    data = BeautifulSoup(contents, "lxml")
    rundata = monkey.get_run()
    return render_template("home.html", data={'xml':data, 'sql':rundata} )
@app.route("/upload_xml", methods=['GET', 'POST'])
def upload_xml():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'detector_xml' not in request.files:
            flash('No file part')
            return redirect("/api/home")
        file = request.files['detector_xml']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect("/api/home")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'current.xml') );
            flash(filename + ' uploaded successfully')
            detector_png()
            return redirect("/api/home")
    return redirect("/api/home")

@app.route('/temperature.png')
def temperature_png():
    fig = create_figure(["http://localhost/api/temperature/1", "http://localhost/api/temperature/2", "http://localhost/api/temperature/3"], "Temperature", ["28.A953460B0000", "28.2D28440B0000", "28.8B08470B0000"], "time", "T[C]")
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')
@app.route('/rate.png')
def rate_png():
    fig = create_figure(["http://localhost/api/rate"], "Rate", ["CAENDigitizer"], "time", "f[Hz]")
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')
@app.route('/voltage.png')
def voltage_png():
    #fig = create_figure(["http://localhost/api/voltage/4", "http://localhost/api/voltage/5"], "SiPM", ["C11204-02", "MOTech"], "time", "V[V]")
    fig = create_two_axes_figure(["http://localhost/api/voltage/4", "http://localhost/api/voltage/5"], "SiPM", ["C11204-02", "MOTech"], "time", ["V[V]", "V[V]"])
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')
@app.route('/detector.png')
def detector_png():
    fig=create_detector()
    output = io.BytesIO()
    fig.save(output, 'PNG')
    output.seek(0)
    return Response(output, mimetype='image/png')

@app.route("/rate")
def rate():
    results = Monkey().read_from_table(6) #CAENDigitizer
    return Response(json.dumps(results, default=json_serial), mimetype='text/json')
@app.route("/temperature/<int:id>")
def temperature(id):
    results = Monkey().read_from_table(id) #28.A953460B0000
    return Response(json.dumps(results, default=json_serial), mimetype='text/json')
@app.route("/voltage/<int:id>") # 4 or 5
def voltage(id):
    results = Monkey().read_from_table(id) #C11204-02
    return Response(json.dumps(results, default=json_serial), mimetype='text/json')
@app.route("/motor")
def motor():
    return Response(json.dumps(lemur.status, default=json_serial), mimetype='text/json')
@app.route("/start_devices", methods=['POST'])
def start_devices():
    contents = ""
    with open(UPLOAD_FOLDER + 'current.xml', 'r') as f:
        contents = f.read()
    data = BeautifulSoup(contents, "lxml")
    #start devices
    if data.devices.find('device', attrs={"name":"C11204-02"})['state'] == "enable":
        lemur.start('C11204-02', [os.path.join(os.path.dirname(__file__), "devices/C11204-02/C11204-02"), data.devices.find('device', attrs={"name":"C11204-02"})['voltage'] ] )
    if data.devices.find('device', attrs={"name":"MOTech"})['state'] == "enable":
        lemur.start('MOTech', [os.path.join(os.path.dirname(__file__), "devices/MOTech/MOTech"), data.devices.find('device', attrs={"name":"MOTech"})['voltage'] ] )
    return redirect("/api/home")
@app.route("/stop_devices", methods=['POST'])
def stop_devices():
    lemur.stop('C11204-02')
    lemur.stop('MOTech')
    return redirect("/api/home")
@app.route("/start_run", methods=['POST'])
def start_run():
    contents = ""
    with open(UPLOAD_FOLDER + 'current.xml', 'r') as f:
        contents = f.read()
    data = BeautifulSoup(contents, "lxml")
    #start motor
    if data.run['type'] == "calibration":
        measurements = data.run.find_all('measurement')
        thread = threading.Thread(target=interval, args=(measurements,) )
        thread.setDaemon(True)
        thread.start()
        #data acquistion (desktop digitizer or twinpeaks) in the daemon interval method
    return redirect("/api/home")
@app.route("/stop_run", methods=['POST'])
def stop_run():
    return redirect("/api/home")

if __name__ == "__main__":
    app.run()
