from RsInstrument import *
import zmq, time, math
def monitor():
    print("starting RSHMP4040 monitor")
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind("tcp://172.16.32.214:2001")
    try:
        while True:
            instr = RsInstrument("TCPIP::172.16.32.113::5025::SOCKET", id_query=True, reset=False)
            instr.write_str('INST OUT3')
            ch3_c = instr.query_str('MEAS:CURR?')
            ch3_v = instr.query_str('MEAS:VOLT?')
            instr.write_str('INST OUT4')
            ch4_c = instr.query_str('MEAS:CURR?')
            ch4_v = instr.query_str('MEAS:VOLT?')
            instr.close()
            data = {'timestamp': math.floor(time.time() ), 'ch3_c': float(ch3_c), 'ch3_v': float(ch3_v), 'ch4_c': float(ch4_c), 'ch4_v': float(ch4_v) }
            socket.send_json(data)
            time.sleep(5) #5 seconds
    except KeyboardInterrupt:
        print("Keyboard interrupt")
if __name__ == '__main__':
    monitor()
