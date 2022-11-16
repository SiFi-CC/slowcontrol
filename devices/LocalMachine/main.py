import psutil
import time
import zmq
import signal

context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://172.16.32.214:2003")
class SignalListener:
    terminate = False
    def __init__(self):
        signal.signal(signal.SIGINT, self.exit)
        signal.signal(signal.SIGTERM, self.exit)
    def exit(self, *args):
        self.terminate = True
def main():
    listener = SignalListener()
    while not listener.terminate:
        r = {}
        r['diskusage'] = psutil.disk_usage('/').percent
        r['ioreadcount'] = psutil.disk_io_counters(perdisk=False).read_count
        r['iowritecount'] = psutil.disk_io_counters(perdisk=False).write_count
        r['timestamp'] = time.time()
        socket.send_json(r)
        time.sleep(5) # 5 seconds
    return 0

if __name__ == '__main__':
	main()

