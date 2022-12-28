from onewire import Onewire
import time
import zmq
def monitor():
    print("Starting Temperature monitor")
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind("tcp://172.16.32.214:2004")
    try:
        while True:
            r = {}
            with Onewire('u') as o:
                r['timestamp'] = time.time()
                for s in o.find(has_all=['temperature']):
                    try:
                        r[f"{s.family}.{s.id}"] = s.read_float('temperature')
                    except TypeError:
                        continue
            socket.send_json(r)
            time.sleep(5) # 5 seconds
    except KeyboardInterrupt:
        print("keyboard interrupt")
if __name__ == '__main__':
	monitor()

