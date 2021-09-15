#include <sys/select.h>
#include <ctype.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
#include <unistd.h>
#include <time.h>
#include <termios.h>
#include <poll.h>

const char *time0() {
  time_t t = time(NULL);

  struct tm *tmp = gmtime(&t);
  if (tmp == NULL)
    return "0000-00-00 --:--:--";

  static char buf[1024];
  if (strftime(buf, 1023, "%F %H:%M:%S", tmp)==0)
    return "0000-00-00 --:--:--";

  return buf;
}

const char *DecToStr(const unsigned char v) {
  const char b0 = (v>>(0*4))&0xf;
  const char b1 = (v>>(1*4))&0xf;

  static char buf[3];

  buf[0] = (b1>9 ? '7' : '0') + b1;     // 7[0x37] 0[0x30]
  buf[1] = (b0>9 ? '7' : '0') + b0;     // 7[0x37] 0[0x30]
  buf[2] = 0;

  return buf;
}

const char *ShortToStr(const unsigned short val) {
  const unsigned char *v = (const unsigned char*)(&val);

  static char buf[5];
//     printf(".%c%c%c%c%c\n",buf[0],buf[1],buf[2],buf[3],buf[4]);
  strncpy(buf,   DecToStr(v[1]), 2);
//     printf(".%c%c%c%c%c\n",buf[0],buf[1],buf[2],buf[3],buf[4]);
  strncpy(buf+2, DecToStr(v[0]), 2);
//     printf(".%c%c%c%c%c\n",buf[0],buf[1],buf[2],buf[3],buf[4]);
  buf[4] = 0;
  return buf;
}

unsigned short StrToDec8(const char *v) {
  const char v0 = v[0] - (v[0]>'9'?'7':'0');
  const char v1 = v[1] - (v[1]>'9'?'7':'0');

  return (v1&0xf) | ((v0&0xf)<<4);
}

unsigned short StrToDec16(const char *v) {
  return StrToDec8(v+2) | (StrToDec8(v)<<8);
}


// int SendCommand(const char *cmd, const char *data)
double SendCommand(const char *cmd, const char *data, const char *port = "/dev/ttyUSB0") {

  // const char *port = "/dev/ttyUSB0";
  // const char *port = "/dev/SDA1";

  // Open the serial port.
  //FILE *usb = fopen("/dev/usb0", "rw");
  //const int usb = open("/dev/ttyUSB0", O_CLOEXEC|O_NONBLOCK);
  const int usb = open(port, O_RDWR | O_NOCTTY | O_SYNC);
  if (usb==-1) {
    printf("E%s: open failed [%s]: %s\n", time0(), port, strerror(errno));
    return 3;
  }

  // Create new termios struc, we call it 'tty' for convention
  struct termios tty;
  memset(&tty, 0, sizeof(tty));

  // Read in existing settings, and handle any error
  if (tcgetattr (usb, &tty) != 0) {
    printf("E%s: tcgetattr failed: %s\n", time0(), strerror(errno));
    return 4;
  }

  // example settings
  tty.c_cflag &= ~PARENB; // Clear parity bit, disabling parity (most common)
  tty.c_cflag &= ~CSTOPB; // Clear stop field, only one stop bit used in communication (most common)
  tty.c_cflag |= CS8; // 8 bits per byte (most common)
  tty.c_cflag &= ~CRTSCTS; // Disable RTS/CTS hardware flow control (most common)
  tty.c_cflag |= CREAD | CLOCAL; // Turn on READ & ignore ctrl lines (CLOCAL = 1)

  tty.c_lflag &= ~ICANON;
  tty.c_lflag &= ~ECHO; // Disable echo
  tty.c_lflag &= ~ECHOE; // Disable erasure
  tty.c_lflag &= ~ECHONL; // Disable new-line echo
  tty.c_lflag &= ~ISIG; // Disable interpretation of INTR, QUIT and SUSP
  tty.c_iflag &= ~(IXON | IXOFF | IXANY); // Turn off s/w flow ctrl
  tty.c_iflag &= ~(IGNBRK|BRKINT|PARMRK|ISTRIP|INLCR|IGNCR|ICRNL); // Disable any special handling of received bytes

  tty.c_oflag &= ~OPOST; // Prevent special interpretation of output bytes (e.g. newline chars)
  tty.c_oflag &= ~ONLCR; // Prevent conversion of newline to carriage return/line feed
  // tty.c_oflag &= ~OXTABS; // Prevent conversion of tabs to spaces (NOT PRESENT ON LINUX)
  // tty.c_oflag &= ~ONOEOT; // Prevent removal of C-d chars (0x004) in output (NOT PRESENT ON LINUX)


  // default settings
  tty.c_cc[VMIN]  = 0;                // read doesn't block
  tty.c_cc[VTIME] = 5;                // 0.5 seconds read timeout

  tty.c_iflag = IGNBRK; // disable special handling of received bytes
  tty.c_cflag = CS8|CLOCAL|CREAD|PARENB|HUPCL; // 8 bits per byte
    //, Turn on READ & ignore ctrl lines (CLOCAL = 1)
    // , Clear parity bit, disabling parity (most common)

  // cout << tty.c_cflag << endl;
  // printf("%d\n", tty.c_cflag);

  cfsetospeed(&tty, B38400);
  cfsetispeed(&tty, B38400);

  if (tcsetattr(usb, TCSANOW, &tty) != 0) {
    printf("E%s: tcsetattr failed: %s\n", time0(), strerror(errno));
    return 5;
  }

  // printf("USB ready.\n");

  // -------------------------------------------------------------

  char chk[1024];
  const int l = snprintf(chk, 1023, "\x02%s%s\x03", cmd, data);

  unsigned char sum = 0;
  for (char *ptr=chk; ptr<chk+l; ptr++)
    sum += *ptr;

  char buf[1024];
  const int len = snprintf(buf, 1023, "%s%s\r", chk, DecToStr(sum));

  //for (int i=0; i<len; i++)
  //    printf("%02x [%c]\n", buf[i], buf[i]>30&buf[i]<127?buf[i]:' ');

  if (write(usb, buf, len)!=len) {
    printf("E%s: write failed: %s\n", time0(), strerror(errno));
    return 6;
  }

    //usleep ((7 + 25) * 100);             // sleep enough to transmit the 7 plus

    // -------------------------------------------------------------

  fd_set rdfs;
  FD_ZERO(&rdfs);
  FD_SET(usb, &rdfs);

  time_t now = time(0);
  for (char *ptr=buf; ptr<buf+1024; ) {
	// timeout 5s
    if (time(0) - now > 5) {
      printf("E%s: read timeout [5s]\n", time0());
      return 7;
    }

    struct pollfd pfd = { usb, POLLIN, 0 };
    const int timeout = 10; // milliseconds

    switch (poll(&pfd, 1, timeout)) {
      case -1 :
        printf("E%s: poll failed: %s\n", time0(),  strerror(errno));
        return 8;

      case 0:
        continue;

      default:
        //if (pfd.reevents&POLLIN) pfd.revents = 0;
      {
        unsigned char c;
        const ssize_t sz = read(usb, &c, 1);
        if (sz==-1) {
          printf("E%s: read failed: %s\n", time0(), strerror(errno));
          return 9;
        }
        if (sz==0) {
          printf("E%s: read returned no bytes.\n", time0());
          return 10;
        }

        if (c=='\r') {
          *ptr = 0;
          ptr=buf+1024;
          break;
        }

        *ptr++ = c;
      }
    }
  }

  if (close(usb)!=0)
    printf("W%s: close failed: %s\n", time0(), strerror(errno));

  //for (char *ptr=buf; *ptr && ptr<buf+1024; ptr++)
  //    printf("%02x [%c]\n", *ptr, *ptr>30&*ptr<127?*ptr:' ');

  // -------------------------------------------------------------

  const char ret[3] = {
    (char) tolower(cmd[0]),
    (char) tolower(cmd[1]),
    (char) tolower(cmd[2])
  };

  const int L = strlen(buf);
  if (L<7) {
    printf("E%s: Unexpected length of answer [%d]\n", time0(), L);
    return 11;
  }

  if (buf[0]!=0x02 || buf[L-3]!=0x03) {
    printf("E%s: STX/EXR error\n", time0());
    return 12;
  }

  sum = 0;
  for (char *ptr=buf; ptr<buf+L-2; ptr++)
    sum += *ptr;

  if (strncmp(buf+L-2, DecToStr(sum), 2)) {
    printf("E%s: Checksum error\n", time0());
    return 13;
  }

  if (strncmp(buf+1, ret, 3) && strncmp(buf+1, "hxx", 3))
    printf("W%s: Answer [%c%c%c] does not fit request [%s]\n",
     time0(), buf[1], buf[2], buf[3], cmd);

  // -------- Return without data -------

  if (strncmp(buf+1, "hst", 3)==0 ||
    strncmp(buf+1, "hof", 3)==0 ||
    strncmp(buf+1, "hon", 3)==0 ||
    strncmp(buf+1, "hcm", 3)==0 ||
    strncmp(buf+1, "hre", 3)==0 ||
    strncmp(buf+1, "hbv", 3)==0 ||
    strncmp(buf+1, "hsc", 3)==0) {
    if (L!=7)
      printf("W%s: Received %d bytes, expected 8 [%c%c%c]\n",
       time0(), L+1, buf[1], buf[2], buf[3]);

    printf("R%s: %c%c%c\n", time0(), buf[1], buf[2], buf[3]);
    return 0;
  }

  // -------- Return with one double -------

  // Temp
  if (strncmp(buf+1, "hgt", 3)==0) {
    if (L!=11)
      printf("W%s: Received %d bytes, expected 11 [%c%c%c]\n",
       time0(), L+1, buf[1], buf[2], buf[3]);

    // printf("R%s: hgt %lf\n", time0(), -(StrToDec16(buf+4)*1.907e-5-1.035)/5.5e-3);
    return -(StrToDec16(buf+4)*1.907e-5-1.035)/5.5e-3;
    // return 0;
  }

  // Volt
  if (strncmp(buf+1, "hgv", 3)==0) {
    if (L!=11)
      printf("W%s: Received %d bytes, expected 11 [%c%c%c]\n",
       time0(), L+1, buf[1], buf[2], buf[3]);

    // printf("R%s: hgv %lf\n", time0(), StrToDec16(buf+4)*1.812e-3);
    return StrToDec16(buf+4)*1.812e-3;
    // return 0;
  }

  // Current
  if (strncmp(buf+1, "hgc", 3)==0) {
    if (L!=11)
      printf("W%s: Received %d bytes, expected 11 [%c%c%c]\n",
       time0(), L+1, buf[1], buf[2], buf[3]);

    //printf("R%s: hgc %lf\n", time0(), StrToDec16(buf+4)*4.980e-3);
    //printf("R%s: hgc %lf\n", time0(), StrToDec16(buf+4)*5.194e-3); // Rev.C
    return StrToDec16(buf+4)*5.194e-3;
    // return 0;
  }

  // Status
  if (strncmp(buf+1, "hgs", 3)==0) {
    if (L!=11)
      printf("W%s: Received %d bytes, expected 11 [%c%c%c]\n",
       time0(), L+1, buf[1], buf[2], buf[3]);

    printf("R%s: hgs 0x%02x\n", time0(), StrToDec16(buf+4));
    return 0;
  }

  // Power function
  if (strncmp(buf+1, "hrc", 3)==0) {
    if (L!=11)
      printf("W%s: Received %d bytes, expected 11 [%c%c%c]\n",
       time0(), L+1, buf[1], buf[2], buf[3]);

    printf("R%s: hrc 0x%x\n", time0(), StrToDec16(buf+4));
    return 0;
  }

    // ------ Return with all data -----------

  if (strncmp(buf+1, "hpo", 3)==0) {
    if (L!=27)
      printf("W%s: Received %d bytes, expected 28 [%c%c%c]\n",
       time0(), L+1, buf[1], buf[2], buf[3]);

    printf("R%s: hpo 0x%x %lf %lf %lf %lf\n", time0(),
           StrToDec16(buf+ 4),                           // status
           StrToDec16(buf+ 8)*1.812e-3,                  // U out [Reserve in Rev.C]
           StrToDec16(buf+12)*1.812e-3,                  // U mon
           //StrToDec16(buf+16)*4.980e-3,                  // I mon
           StrToDec16(buf+16)*5.194e-3,                  // I mon [Rev.C]
           (1.035-StrToDec16(buf+20)*1.907e-5)/5.5e-3); // Temp

    return 0;
  }

  if (strncmp(buf+1, "hrt", 3)==0) {
    if (L!=31)
      printf("W%s: Received %d bytes, expected 32 [%c%c%c]\n",
       time0(), L+1, buf[1], buf[2], buf[3]);

    printf("R%s: hrt %lf %lf %lf %lf %lf %lf\n", time0(),
           StrToDec16(buf+ 4)*1.507e-3,
           StrToDec16(buf+ 8)*1.507e-3,
           StrToDec16(buf+12)*5.225e-2,
           StrToDec16(buf+16)*5.225e-2,
           StrToDec16(buf+20)*1.812e-3,
           (1.035-StrToDec16(buf+24)*1.907e-5)/5.5e-3);

    return 0;
  }

  // ------------- Error returned -----------

  if (strncmp(buf+1, "hxx", 3)==0) {
    if (L!=11)
      printf("W%s: Received %d bytes, expected 12 [%c%c%c]\n",
       time0(), L+1, buf[1], buf[2], buf[3]);

    const unsigned short err = StrToDec16(buf+4);

    const char *msg = "";
    switch (err) {
      case 1:  msg = "Communication";  break;
      case 2:  msg = "Timeout";        break;
      case 3:  msg = "Syntax";         break;
      case 4:  msg = "Checksum";       break;
      case 5:  msg = "Command";        break;
      case 6:  msg = "Parameter";      break;
      case 7:  msg = "Parameter size"; break;
      default: msg = "Unknown";        break;
    }
    printf("R%s: hxx %d [%s error]\n", time0(), err, msg);
    return 1;
  }

  printf("E%s: returned id unknown [%c%c%c]\n", time0(), buf[1], buf[2], buf[3]);
  return 2;
}

int SendHST(const char *argv[]) {
  double v[6];
  for (int i=0; i<6; i++)
    if (sscanf(argv[i+2], "%lf", v+i)!=1)
      return 1;

  unsigned short s[6] = {
    (unsigned short) (v[0] / 1.507e-3),  // tp1
    (unsigned short) (v[1] / 1.507e-3),  // tp2
    (unsigned short) (v[2] / 5.225e-2),  // t1
    (unsigned short) (v[3] / 5.225e-2),  // t2
    (unsigned short) (v[4] / 1.812e-3),  // vb
    (unsigned short) ((1.035-v[5]*5.5e-3)/1.907e-5)
  };

  char buf[6*4+1];

  for (int i=0; i<6; i++)
    strncpy(buf+4*i, ShortToStr(s[i]), 4);
  buf[6*4] = 0;

  return SendCommand("HST", buf);
}

int SendHBV(const char *argv)
{
  double v;
  if (sscanf(argv, "%lf", &v)!=1)
    return 1;
  printf("%f\n",v);
  const unsigned short s = v / 1.812e-3;
  printf("%d\n",s);
  char buf[5];
  sprintf(&buf[0], "%04x", s);
  buf[4] = 0;

  printf("%c%c%c%c%c\n",buf[0],buf[1],buf[2],buf[3],buf[4]);

  return SendCommand("HBV", buf);
}

int PrintHelp() {
  printf("\n"
    "Command:\n"
    "   psuctrl2 --help\n"
    "   psuctrl2 CMD [args...]\n"
    "\n"
    "Possible commands are:\n"
    "\n"
    "  Reading:\n"
    "    HPO     Get the values [stat Uset Umon Imon Tmon]\n"
    "    HGV     Get the output voltage [Umon]\n"
    "    HGC     Get the output current [Imon]\n"
    "    HGS     Get the status [stat]\n"
    "    HRC     Get power function [pf]\n"
    "    HGT     Get sensor temperature [Tmon]\n"
    "    HRT     Get the temperature correction factors [dT1' dT2' dT1 dT2 Ub Tb]\n"
    "\n"
    "  Control:\n"
    "    HOF     Voltage output off\n"
    "    HON     Voltage output on\n"
    "    HRE     Power supply reset\n"
    "\n"
    "  Setting:\n"
    "    HCM N   Switch temperature compensation mode [N=0|1]\n"
    "    HBV U   Temporary setting for the reference voltage\n"
    "    HSC pf  Set power function mode\n"
    "\n"
    "    HST dT1' dT2' dT1 dT2 Ub Tb\n"
    "            Set the temperture correction factor\n"
    "\n");
  return 0;
}
