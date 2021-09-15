// notes: dialout group, dmesg | tail, usb-devices
// todo: add multiple devices, custom filename
// ftdi: vendor: 0x0403, product: 0x6001

// A/B Seite:
// T:  Bus=01 Lev=05 Prnt=124 Port=03 Cnt=02 Dev#=126 Spd=12  MxCh= 0
// D:  Ver= 2.00 Cls=00(>ifc ) Sub=00 Prot=00 MxPS= 8 #Cfgs=  1
// P:  Vendor=0403 ProdID=6001 Rev=06.00
// S:  Manufacturer=FTDI
// S:  Product=USB <-> Serial Converter
// S:  SerialNumber=FT1L0EZJ
// C:  #Ifs= 1 Cfg#= 1 Atr=80 MxPwr=100mA
// I:  If#= 0 Alt= 0 #EPs= 2 Cls=ff(vend.) Sub=ff Prot=ff Driver=ftdi_sio

// C/D Seite:
// Bus=01 Lev=05 Prnt=124 Port=02 Cnt=01 Dev#=125 Spd=12  MxCh= 0
// D:  Ver= 2.00 Cls=00(>ifc ) Sub=00 Prot=00 MxPS= 8 #Cfgs=  1
// P:  Vendor=0403 ProdID=6001 Rev=06.00
// S:  Manufacturer=FTDI
// S:  Product=FT232R USB UART
// S:  SerialNumber=A524YVP8
// C:  #Ifs= 1 Cfg#= 1 Atr=a0 MxPwr=90mA
// I:  If#= 0 Alt= 0 #EPs= 2 Cls=ff(vend.) Sub=ff Prot=ff Driver=ftdi_sio

#include <math.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <sstream>
#include <iostream>
#include <vector>
#include <unistd.h>
#include <cstdlib>
#include <fstream>
#include <time.h>
#include <iomanip>
#include <ctime>
#include <signal.h>
#include <usb.h>
#include "C11204-02.h"
#include "mysql.h"

volatile sig_atomic_t stop = 0;
/*
 * catch Ctrl+C and then exit while loop
 * so we can close the files nicely
 */
void exit_handler(int signum){
	stop = 1;
}
int main(int argc, char* argv[]) {
	MYSQL *conn;
	MYSQL_RES *res;
	MYSQL_ROW row;
	const char *server = "localhost";
	const char *user = "lab";
	const char *password = "protontherapy";
	const char *database = "gccb";
	conn = mysql_init(NULL);
	/* Connect to database */
	if (!mysql_real_connect(conn, server,
				user, password, database, 0, NULL, 0)) {
		fprintf(stderr, "%s\n", mysql_error(conn));
		exit(1);
	}
	double voltage, current, temperature = 0;
	const char* port = "/dev/ttyUSB0";
	float set_voltage = 53.2f;
	signal(SIGINT, exit_handler);
	if (argv[1] == (std::string)"--help") {
		printf("Usage: ./C11204-02 set_voltage\n");
		return 0;
	}
	else {
		if(argc == 2) {
			char *p;
			set_voltage = strtof(argv[1], &p);
			if (*p) {
				fprintf(stderr, "set_voltage is not a float or number\n");
				return 1;
			}
			if(set_voltage < 40) {
				fprintf(stderr, "set_voltage is not positive\n");
				return 1;
			}
			if(set_voltage > 54) {
				fprintf(stderr, "set_voltage is too high\n");
				return 1;
			}
		} else {
			fprintf(stderr, "user did not specify valid arguments\n");
		}
	}
	//set voltage
	SendHBV(std::to_string(set_voltage).c_str() );
	while(!stop) {
		voltage = SendCommand("HGV", "", port);
		current = SendCommand("HGC", "", port);
		temperature = SendCommand("HGT", "", port);
		// Execute a sql statement
		std::string query = "INSERT INTO outputs (device_id, value) VALUES ((SELECT id FROM devices WHERE name='C11204-02'), " + std::to_string(voltage) + ");";
		if (mysql_query(conn, query.c_str() ) ) {
			std::cerr << mysql_error(conn) << std::endl;
			return false;
		}
		//printf("v=%fV, i=%fA, t=%fC\n", voltage, current, temperature);
		//sleep 5min
		sleep(300);
	}
	if(stop) {
		voltage = 0.f;
		// Execute a sql statement
		std::string query = "INSERT INTO outputs (device_id, value) VALUES ((SELECT id FROM devices WHERE name='C11204-02'), " + std::to_string(voltage) + ");";
		if (mysql_query(conn, query.c_str() ) ) {
			std::cerr << mysql_error(conn) << std::endl;
			return false;
		}
	}
        // Close a MySQL connection
        mysql_close(conn);
	return 0;
}
