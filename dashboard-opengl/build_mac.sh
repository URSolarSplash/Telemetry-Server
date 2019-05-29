#rm dashboard_mac
#export PKG_CONFIG_PATH=$PKG_CONFIG_PATH:/usr/local/Cellar/raylib/2.0.0/lib/pkgconfig
clang -framework CoreVideo -framework IOKit -framework Cocoa -framework GLUT -framework OpenGL lib/librequests_mac.a lib/libraylib_mac.a dashboard.c json.c -o dashboard_mac -L/opt/local/lib -lcurl -lssl -lcrypto -lssl -lcrypto -lz
./dashboard_mac
