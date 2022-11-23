import psutil
import time
import zmq
def monitor():
    print("Starting LocalMachine monitor")
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind("tcp://172.16.32.214:2003")
    try:
        while True:
            r = {}
            r['diskusage'] = psutil.disk_usage('/').percent
            r['ioreadcount'] = psutil.disk_io_counters(perdisk=False).read_count
            r['iowritecount'] = psutil.disk_io_counters(perdisk=False).write_count
            r['timestamp'] = time.time()
            socket.send_json(r)
            time.sleep(5) # 5 seconds
    except KeyboardInterrupt:
        print("keyboard interrupt")
if __name__ == '__main__':
	monitor()

