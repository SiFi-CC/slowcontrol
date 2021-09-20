#include <iostream>
#include <vector>
#include <errno.h>
#include <fcntl.h> 
#include <string.h>
#include <termios.h>
#include <unistd.h>
#include <signal.h>
#include <mysql.h>
#include <math.h>
#include <sstream>

template <typename T>
std::string to_string_with_precision(const T a_value, const int n = 6)
{
    std::ostringstream out;
    out.precision(n);
    out << std::fixed << a_value;
    return out.str();
}
int set_interface_attribs (int fd, int speed, int parity) {
        struct termios tty;
        if (tcgetattr (fd, &tty) != 0) {
                fprintf(stderr, "error %d from tcgetattr", errno);
                return -1;
        }
        cfsetospeed (&tty, speed);
        cfsetispeed (&tty, speed);
        tty.c_cflag = (tty.c_cflag & ~CSIZE) | CS8;     // 8-bit chars
        // disable IGNBRK for mismatched speed tests; otherwise receive break
        // as \000 chars
        tty.c_iflag &= ~IGNBRK;         // disable break processing
        tty.c_lflag = 0;                // no signaling chars, no echo,
                                        // no canonical processing
        tty.c_oflag = 0;                // no remapping, no delays
        tty.c_cc[VMIN]  = 0;            // read doesn't block
        tty.c_cc[VTIME] = 5;            // 0.5 seconds read timeout
        tty.c_iflag &= ~(IXON | IXOFF | IXANY); // shut off xon/xoff ctrl
        tty.c_cflag |= (CLOCAL | CREAD);// ignore modem controls,
                                        // enable reading
        tty.c_cflag &= ~(PARENB | PARODD);      // shut off parity
        tty.c_cflag |= parity;
        tty.c_cflag &= ~CSTOPB;
        tty.c_cflag &= ~CRTSCTS;
        if (tcsetattr (fd, TCSANOW, &tty) != 0) {
                fprintf(stderr, "error %d from tcsetattr", errno);
                return -1;
        }
        return 0;
}
void set_blocking (int fd, int should_block) {
        struct termios tty;
        memset (&tty, 0, sizeof tty);
        if (tcgetattr (fd, &tty) != 0) {
                fprintf(stderr, "error %d from tggetattr", errno);
                return;
        }
        tty.c_cc[VMIN]  = should_block ? 1 : 0;
        tty.c_cc[VTIME] = 5;            // 0.5 seconds read timeout
        if (tcsetattr (fd, TCSANOW, &tty) != 0)
                fprintf(stderr, "error %d setting term attributes", errno);
}
volatile sig_atomic_t stop = 0;
int send_command(int fd, std::string command, unsigned char *buffer) {
	const char *cmd = std::string(command + "\n").c_str();
	write(fd, cmd, strlen(cmd) );
	sleep(1);             // sleep enough to transmit the 7 plus
	int n = read(fd, buffer, sizeof(buffer) - 1 );
	if(n > 0) {
		buffer[n] = 0;
	} else if (n < 0) {
		return errno;
	} else {  /* n == 0 */
		return -1;
	}
	return n;
}
void write_to_db(MYSQL *conn, int fd, unsigned char *voltBuf, unsigned char *currBuf) {
	/**
	 * Readout voltage and current from channel 1
	 */
	int s = send_command(fd, std::string("VOUT1?"), voltBuf);
	float voltage, current;
	if(s > 0) {
		voltage = std::atof(reinterpret_cast<const char *>(voltBuf) );
	}
	if(s > 0) {
		current = std::atof(reinterpret_cast<const char *>(currBuf) );
	}
	// Execute a sql statement
	std::string query = "INSERT INTO outputs (device_id, value) VALUES ((SELECT id FROM devices WHERE name='MOTech' AND unit='V'), " + std::to_string(voltage) + ");";
	if (mysql_query(conn, query.c_str() ) ) {
		std::cerr << mysql_error(conn) << std::endl;
	}
	// Execute a sql statement
	query = "INSERT INTO outputs (device_id, value) VALUES ((SELECT id FROM devices WHERE name='MOTech' AND unit='A'), " + std::to_string(current) + ");";
	if (mysql_query(conn, query.c_str() ) ) {
		std::cerr << mysql_error(conn) << std::endl;
	}
	printf("v=%f i=%f\n", voltage, current);
}
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
        const char *user = getenv("USER");
        const char *password = getenv("PASSWORD");
        const char *database = getenv("DATABASE");

        conn = mysql_init(NULL);

        /* Connect to database */
        if (!mysql_real_connect(conn, server,
                                user, password, database, 0, NULL, 0)) {
                fprintf(stderr, "%s\n", mysql_error(conn));
                exit(1);
        }

	signal(SIGINT, exit_handler);
	char *portname = (char*)"/dev/ttyS0";
	int fd = open (portname, O_RDWR | O_NOCTTY | O_SYNC);
	if (fd < 0) {
		fprintf(stderr, "Error %d opening %s: %s", errno, portname, strerror (errno));
		return 1;
	}
	set_interface_attribs (fd, B19200, 0);  // set speed to 19200 bps, 8n1 (no parity)
	set_blocking (fd, 0);                // set no blocking
	unsigned char state[32]; //to be deprecated
	unsigned char voltBuf[32];
	unsigned char currBuf[32];
	//defaults
	short rampInterval = 5;
	float set_voltage = 30.0f;
	/**
	 * Get arguments and setup voltage ramp up
	 */
	if (argv[1] == (std::string)"--help") {
		printf("Usage: ./MOTech set_voltage\n");
		return 0;
	} else {
		if(argc == 2) {
			char *p;
			set_voltage = strtof(argv[1], &p);
			if (*p) {
				fprintf(stderr, "set_voltage is not a float or number\n");
				return 1;
			}
			if(set_voltage < 0) {
				fprintf(stderr, "set_voltage is not positive\n");
				return 1;
			}
			if(set_voltage > 30.5) {
				fprintf(stderr, "set_voltage is too high\n");
				return 1;
			}
		} else {
			fprintf(stderr, "user did not specify valid arguments\n");
		}
		//printf("Voltage setting at: %f\n", set_voltage);
	}

	int s;
	float voltage = .0f, current = .0f;
	//printf("Start ramping up to  %2.2f\n", set_voltage);
	for(unsigned short i=0; i<=floor(set_voltage); i = i + rampInterval) {
		send_command(fd, std::string("VSET1 ") + std::to_string(i), state);
		write_to_db(conn, fd, voltBuf, currBuf);
		tcflush(fd,TCIOFLUSH);
	}
	send_command(fd, std::string("VSET1 ") + to_string_with_precision(set_voltage, 3), state);
	write_to_db(conn, fd, voltBuf, currBuf);
	tcflush(fd,TCIOFLUSH);
	//Ctrl+C to exit loop and start voltage rampdown
	while(!stop) {
		write_to_db(conn, fd, voltBuf, currBuf);
		tcflush(fd,TCIOFLUSH);
		//sleep for 5min
		sleep(300);
	}
	if(stop) {
		for(unsigned short i=floor(voltage); i > 0; i = i - rampInterval) {
			send_command(fd, std::string("VSET1 ") + std::to_string(i), state);
			write_to_db(conn, fd, voltBuf, currBuf);
			tcflush(fd,TCIOFLUSH);
		}
		send_command(fd, std::string("VSET1 0"), state);
		write_to_db(conn, fd, voltBuf, currBuf);
		tcflush(fd,TCIOFLUSH);
	}
	return 0;
}
