CC = clang
SOURCES = dashboard.c json.c
OBJECTS = $(SOURCES:.c=.o)
TARGET = dashboard

UNAME_S := $(shell uname -s)


CFLAGS = -O2 -Wall -I/usr/local/include -L/usr/local/lib
LIBS = -lcurl -lssl -lcrypto -lz -lm -lpthread


ifeq ($(UNAME_S),Darwin)
    TARGET := $(TARGET)_mac
    CFLAGS += -framework CoreVideo -framework IOKit -framework Cocoa -framework GLUT -framework OpenGL
    STATIC_LIBS = lib/librequests_mac.a lib/libraylib.a
endif


ifeq ($(UNAME_S),Linux)
    TARGET := $(TARGET)_linux
    # Disable PIE so non-PIC static libs (like librequests_linux.a) link fine
    CFLAGS += -I/usr/include -L/usr/lib -fno-pie -no-pie
    LIBS += -lGL -lGLU -lglut -lraylib
    STATIC_LIBS = lib/librequests_linux.a
endif


all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(CFLAGS) $(OBJECTS) $(STATIC_LIBS) -o $(TARGET) $(LIBS)
	rm -f $(OBJECTS)

%.o: %.c
	$(CC) -c $< -o $@

clean:
	rm -f $(OBJECTS) dashboard_mac dashboard_linux

