import os
from os import listdir
from os.path import isfile, join
from mysql.connector import connect, Error
from dotenv import load_dotenv

class Monkey(object):
    def __init__(self):
        self._cached_stamp = 0
        self.devices = []
        self.mysql_conn = ""
        self.path = '/mnt/1wire/'
        for f in listdir(self.path):
            if f[:3] == "28." and f not in self.devices:
                self.devices.append(f);
        self.mysql()
    def mysql(self):
        try:
            load_dotenv(os.path.join(os.path.dirname(__file__), '.env') )
            self.mysql_conn = connect(host=os.getenv("HOST"), database=os.getenv("DATABASE"), user=os.getenv("USER"), password=os.environ["PASSWORD"])
        except Error as e:
            print(e)
    def write_to_table(self, obj):
        cursor = self.mysql_conn.cursor()
        cursor.execute("INSERT INTO outputs (device_id, value) VALUES ((SELECT id FROM devices WHERE name=%s), %s);", (obj['name'], obj['value']) )
        self.mysql_conn.commit()
    def look(self):
        stamp = os.stat("%s/%s/temperature" % (self.path, self.devices[0]) ).st_mtime
        if self._cached_stamp != stamp:
            self._cached_stamp = stamp
            for d in self.devices:
                filename = "/%s/%s/temperature" % (self.path, d);
                f = open(filename)
                temperature = f.read()
                f.close()
                print(d, temperature)
                self.write_to_table({'name':d, 'value':temperature})
    def __del__(self):
        self.mysql_conn.close();
Monkey().look()
