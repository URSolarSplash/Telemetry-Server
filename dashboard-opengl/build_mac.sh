#export PKG_CONFIG_PATH=$PKG_CONFIG_PATH:/usr/local/Cellar/raylib/2.0.0/lib/pkgconfig
clang -framework CoreVideo -framework IOKit -framework Cocoa -framework GLUT -framework OpenGL lib/libraylib_mac.a dashboard.c -o dashboard_mac
./dashboard_mac
