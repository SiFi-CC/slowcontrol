from petsys import daqd, fe_temperature, config
import time
import zmq
import signal
def monitor():
    print("Starting TOFPET2c temperature monitor")
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind("tcp://172.16.32.214:2002")
    connection = daqd.Connection()
    connection.initializeSystem()
    sensor_list = fe_temperature.get_sensor_list(connection)
    if sensor_list is []:
        print("WARNING: No sensors found. Check connections and power.")
    try:
        while True:
            r = {}
            for sensor in sensor_list:
                if sensor.get_location()[4] == "asic":
                    r[f"ch{sensor.get_location()[2]}_{sensor.get_location()[3]}_T"] = sensor.get_temperature()
            r['timestamp'] = time.time()
            socket.send_json(r)
            time.sleep(5) # 5 seconds
    except KeyboardInterrupt:
        del connection
        print("Keyboard interrupt")
if __name__ == '__main__':
    monitor()
