CC = clang
CFLAGS = -framework CoreVideo -framework IOKit -framework Cocoa -framework GLUT -framework OpenGL -L/usr/local/lib
LIBS = -lcurl -lssl -lcrypto -lz -Wl
SOURCES = dashboard.c json.c
OBJECTS = $(SOURCES:.c=.o)
TARGET = dashboard_mac

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(CFLAGS) lib/librequests_mac.a lib/libraylib.a $(OBJECTS) -o $(TARGET) $(LIBS)
	rm -f $(OBJECTS)

%.o: %.c
	$(CC) -c $< -o $@

clean:
	rm -f $(OBJECTS) $(TARGET)

rpi: dashboard.c json.c
	gcc -o dashboard_rpi dashboard.c json.c -O1 -s -Wall -std=c99 -D_DEFAULT_SOURCE -Wno-missing-braces -std=gnu99 -I. -I/home/pi/raylib/src -I/home/pi/raylib/src/external -I/opt/vc/include -I/opt/vc/include/interface/vmcs_host/linux -I/opt/vc/include/interface/vcos/pthreads -L. -L./lib -L/home/pi/raylib/src -L/opt/vc/lib -lraylib -lrequests_rpi -lbrcmGLESv2 -lbrcmEGL -lpthread -lrt -lm -lbcm_host -ldl -lcurl -DPLATFORM_RPI

.PHONY: all clean