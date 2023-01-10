from RsInstrument import *
import time, sys
def state():
    res = []
    try:
        instr = RsInstrument("TCPIP::172.16.32.115::5025::SOCKET", id_query=True, reset=True)
        for channel in range(1, 5):
            instr.write_str(f"INST OUT{channel}")
            res.append({'number':channel, 'state': instr.query_str('OUTP?') } ) #0 off, 1 on
        instr.close()
    except Exception as err:
        res.append({'error': err})
    return res
def on():
    try:
        instr = RsInstrument("TCPIP::172.16.32.115::5025::SOCKET", id_query=True, reset=True)
        # get device identifier
        idn = instr.query_str('*IDN?')
        print(idn)
        # reset device to factory settings
        instr.write_str('*RST')
        
        instr.visa_timeout = 10000
        instr.write_str('INST OUT3')
        instr.write_str('OUTP:SEL 1')
        instr.write_str('VOLT 12')
        instr.write_str('CURR 2')
        instr.write_str('OUTP 1')
        instr.query_opc()
        ch3 = instr.query_str('OUTP?')
        
        time.sleep(5)
        
        instr.write_str('INST OUT4')
        instr.write_str('OUTP:SEL 1')
        instr.write_str('VOLT 12')
        instr.write_str('OUTP 1')
        instr.query_opc()
        ch4 = instr.query_str('OUTP?')
        instr.close()
    except Exception as err:
        print(err)
def off():
    try:
        instr = RsInstrument("TCPIP::172.16.32.115::5025::SOCKET", id_query=True, reset=True)
        instr.write_str('OUTP:GEN 0')
        instr.write_str('INST OUT3')
        instr.query_opc()
        ch3 = instr.query_str('OUTP?')
        instr.write_str('INST OUT4')
        instr.query_opc()
        ch4 = instr.query_str('OUTP?')
        instr.close()
    except Exception as err:
        print(err)
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("usage: python3 RSHMP4040.py [on|off]")
        sys.exit()
    if sys.argv[1] == 'on':
        on()
    if sys.argv[1] == 'off':
        off()
