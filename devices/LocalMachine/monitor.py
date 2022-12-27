import psutil
import time
import zmq
def findProcessIdByName(processName):
    '''
    Get a list of all the PIDs of a all the running process whose name contains
    the given string processName
    '''
    listOfProcessObjects = []
    #Iterate over the all the running process
    for proc in psutil.process_iter():
       try:
           pinfo = proc.as_dict(attrs=['pid', 'name', 'create_time'])
           # Check if process name contains the given name string.
           if processName.lower() in pinfo['name'].lower():
               listOfProcessObjects.append(pinfo)
       except (psutil.NoSuchProcess, psutil.AccessDenied , psutil.ZombieProcess):
           pass
    return listOfProcessObjects
def monitor():
    print("Starting LocalMachine monitor")
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind("tcp://172.16.32.214:2003")
    listOfProcessIds = findProcessIdByName('daqd')
    print(listOfProcessIds)
    try:
        while True:
            r = {}
            r['diskusage'] = psutil.disk_usage('/').percent
            # Assuming only one instance of daqd is created.
            r['ioreadcount'] = psutil.Process(listOfProcessIds[0]['pid']).io_counters()[0]
            r['iowritecount'] = psutil.Process(listOfProcessIds[0]['pid']).io_counters()[1]
            r['timestamp'] = time.time()
            socket.send_json(r)
            time.sleep(5) # 5 seconds
    except KeyboardInterrupt:
        print("keyboard interrupt")
if __name__ == '__main__':
	monitor()

