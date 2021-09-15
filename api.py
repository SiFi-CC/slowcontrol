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

from extensions import MotorInterface

UPLOAD_FOLDER = '/scratch/gccb/mark/flask/files/'
popen = 0
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ['xml']
def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))
def create_figure(urls=[], title="", labels=[], xlabel="x", ylabel="y"):
    figure = Figure()
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
class Lemur(object):
    def __init__(self):
        self.processes = {}
    def start(self, label, process):
        self.processes[label] = subprocess.Popen(process)
    def stop(self, label):
        self.processes[label].send_signal(signal.SIGINT)

class Monkey(object):
    def __init__(self):
        self.mysql_conn = ""
        self.results = []
        self.current_run = 0
        self.mysql()
    def mysql(self):
        try:
            self.mysql_conn = connect(host="localhost", database=os.getenv("DATABASE"), user=os.getenv("USER"), password=os.getenv("PASSWORD"), auth_plugin='mysql_native_password')
        except Error as e:
            print(e)
    def read_from_table(self, device_id):
        cursor = self.mysql_conn.cursor()
        cursor.execute("SELECT value, created FROM outputs WHERE device_id=%s AND created >= CURDATE();", (device_id, ) )
        self.results = cursor.fetchall()
        return self.results
    def get_run(self):
        cursor = self.mysql_conn.cursor(dictionary=True)
        cursor.execute("SELECT id, start, stop FROM runs ORDER BY id DESC LIMIT 1;")
        self.results = cursor.fetchone()
        return self.results
    def start_run(self):
        cursor = self.mysql_conn.cursor()
        cursor.execute("INSERT INTO runs (detector_id) VALUES (1);")
        self.mysql_conn.commit()
        cursor.execute("SELECT LAST_INSERT_ID();")
        self.current_run = cursor.fetchone()[0]
        return self.results
    def stop_run(self):
        cursor = self.mysql_conn.cursor()
        cursor.execute("UPDATE runs SET state='calibration' WHERE id=%s;", (self.current_run, ) )
        self.mysql_conn.commit()
        print("UPDATE runs SET state='calibration' WHERE id=%s;", (self.current_run, ) )
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
@app.route('/voltage.png')
def voltage_png():
    fig = create_figure(["http://localhost/api/voltage/4", "http://localhost/api/voltage/5"], "SiPM", ["C11204-02", "MOTech"], "time", "V[V]")
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
    url_values = request.args
    motor = MotorInterface.MotorInterface()
    if url_values.get('cmd') == 'zero':
        motor.zero()
    if url_values.get('cmd') == 'move_x':
        x = url_values.get('x')
        motor.move_x(int(x) )
    status = motor.status
    return Response(json.dumps(status, default=json_serial), mimetype='text/json')
@app.route("/start_run", methods=['POST'])
def start_run():
    contents = ""
    with open(UPLOAD_FOLDER + 'current.xml', 'r') as f:
        contents = f.read()
    data = BeautifulSoup(contents, "lxml")
    monkey.start_run()
    #start devices
    ##if data.devices.find('device', attrs={"id":"C11204-02"})['state'] == "enable":
    ##    lemur.start('C11204-02', ["/scratch/gccb/mark/SiPMLogger/SiPMLogger", data.devices.find('device', attrs={"id":"C11204-02"})['voltage'] ] )
    ##if data.devices.find('device', attrs={"id":"MOTech"})['state'] == "enable":
    ##    lemur.start('MOTech', ["/scratch/gccb/mark/MOTech/MOTech", data.devices.find('device', attrs={"id":"MOTech"})['voltage'] ] )
    #start motor and data acquistion (desktop digitizer or twinpeaks)
    return redirect("/api/home")
@app.route("/stop_run", methods=['POST'])
def stop_run():
    monkey.stop_run()
    ##lemur.stop('C11204-02')
    ##lemur.stop('MOTech')
    return redirect("/api/home")

if __name__ == "__main__":
    app.run()
