from RsInstrument import *
import time, sys
def on():
    instr = RsInstrument("TCPIP::172.16.32.113::5025::SOCKET", id_query=True, reset=True)
    # get device identifier
    idn = instr.query_str('*IDN?')
    print(idn)
    # reset device to factory settings
    instr.write_str('*RST')
    
    instr.visa_timeout = 10000
    instr.write_str('INST OUT3')
    instr.write_str('OUTP:SEL 1')
    instr.write_str('VOLT 12')
    instr.write_str('CURR 1.5')
    instr.write_str('OUTP 1')
    ch3 = instr.query_str('OUTP?')
    
    time.sleep(5)
    
    instr.write_str('INST OUT4')
    instr.write_str('OUTP:SEL 1')
    instr.write_str('VOLT 12')
    instr.write_str('OUTP 1')
    ch4 = instr.query_str('OUTP?')
    
    print(f"channel3 state: {ch3}, channel4 state: {ch4}")
    instr.close()
def off():
    instr = RsInstrument("TCPIP::172.16.32.113::5025::SOCKET", id_query=True, reset=True)
    instr.write_str('OUTP:GEN 0')
    instr.write_str('INST OUT3')
    ch3 = instr.query_str('OUTP?')
    instr.write_str('INST OUT4')
    ch4 = instr.query_str('OUTP?')
    print(f"channel3 state: {ch3}, channel4 state: {ch4}")
    instr.close()
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("usage: python3 main.py [on|off]")
        sys.exit()
    if sys.argv[1] == 'on':
        on()
    if sys.argv[1] == 'off':
        off()
