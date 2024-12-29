import requests
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import webbrowser
import json
from datetime import datetime
import traceback

def run_test_server():
    class TestHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                self.path = '/index.html'
            return SimpleHTTPRequestHandler.do_GET(self)
        
        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()

    server = HTTPServer(('localhost', 5173), TestHandler)
    print("""
    ┌────────────────────────────────────────────┐
    │  AICFO Debug Frontend                      │
    │  Running at: http://localhost:5173         │
    │                                            │
    │  Press Ctrl+C to stop the server           │
    └────────────────────────────────────────────┘
    """)
    server.serve_forever()

if __name__ == "__main__":
    try:
        server_thread = threading.Thread(target=run_test_server)
        server_thread.daemon = True
        server_thread.start()
        
        # Open browser after a short delay to ensure server is running
        threading.Timer(1.5, lambda: webbrowser.open('http://localhost:5173')).start()
        
        while True:
            input()
    except KeyboardInterrupt:
        print("\nShutting down debug server...")
    except Exception as e:
        print(f"Error: {e}")
        print(traceback.format_exc())