import http.server
import socketserver
import server.config as config
import threading

class Handler(http.server.SimpleHTTPRequestHandler):
    def send_response(self, *args, **kwargs):
        http.server.SimpleHTTPRequestHandler.send_response(self, *args, **kwargs)
        self.send_header('Access-Control-Allow-Origin', '*')

class DashboardManager(object):
    def __init__(self, interval=1):
        self.thread = threading.Thread(target=self.run, args=(self,))
        self.thread.start()
    def run(self,dashManager):
        print("[Dashboard] initializing dashboard HTTP server...")
        socketserver.TCPServer.allow_reuse_address = True
        dashManager.httpd = socketserver.TCPServer(("", config.dashboardHttpPort), Handler)
        dashManager.httpd.serve_forever()
    def shutdown(self):
        self.httpd.shutdown()
        self.thread.join()
