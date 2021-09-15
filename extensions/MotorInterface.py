import os
import time
import fnmatch
import serial
class MotorInterface(object):
    def __init__(self):
        self.device = ''
        pattern = 'ttyACM*'
        for d in os.listdir('/dev/'):
            if fnmatch.fnmatch(d, pattern):
                self.device = '/dev/' + d
        self.stepPosition = 0
        self.setStepPosition = 0
        self.setPosition = 0
        self.ser = serial.Serial(self.device, 9600, timeout=1)
        self.status = {}
        #calibration constants
        self.m=0.01997
        self.b=0
    def move_steps(self,steps):
        movedsteps=0
        if not steps == 0: #Arduino is 16 bit therfore cant use steps above 2^15
            #self.status = "Trying to Go %d steps ..." % steps
            if(steps>32700):
                self.stepPosition += steps
                for i in range(steps/32700):
                    #print ("Go 32700 steps")
                    self.ser.write(("+%s " % 32700).encode() )
                    while True:
                        readout = self.ser.readline()
                        if readout.startswith("Ready".encode() ):
                            break
                steps= steps%32700
            elif(steps<-32700):
                self.stepPosition += steps
                for i in range(steps/-32700):
                    #print ("Go -32700 steps")
                    self.ser.write(("-%s " % 32700).encode() )
                    while True:
                        readout = self.ser.readline()
                        if readout.startswith("Ready".encode() ):
                            break
                steps= steps%-32700
            self.status = {'status':"moving"}
            self.ser.write(("%s" % steps).encode() )
            while True:
                readout = self.ser.readline()
                if readout.startswith("Ready".encode() ):
                    success=True
                    break
                elif readout.startswith("Reached".encode() ):
                    readout = self.ser.readline()
                    movedsteps=int(readout)
                    success=False
                    break
            if success:
                self.stepPosition += steps
                self.setStepPosition = self.stepPosition
                self.setPosition = self.stepPosition*self.m+self.b
                self.status = {'xpos': self.setPosition, 'status':'reached'}
            else:
                self.stepPosition+=movedsteps
                self.setStepPosition = self.stepPosition
                self.setPosition = self.stepPosition*self.m+self.b
                self.status = {'steps': movedsteps, 'status':'ready'}
    def move_x(self,x):
        self.move_steps(int(x*1./self.m) )
    def zero(self):
        self.ser.write("Default".encode() )
        while True:
            try:
                readout = self.ser.readline()
                self.status = {'status':"moving"}
                if readout.startswith("Ready".encode() ):
                    self.status = {'xpos':0, 'status':"reached"}
                    break
            except SerialException:
                self.status = {'status': 'SerialException'}
                break
        self.stepPosition=0
        self.setStepPosition = self.stepPosition
        self.setPosition = self.stepPosition*self.m+self.b
    def quit(self):
        self.destroy()
        quit()
