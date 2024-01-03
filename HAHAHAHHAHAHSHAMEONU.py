from PIL import Image
import datetime
import json

from http.server import BaseHTTPRequestHandler, HTTPServer
import os

class RedirectHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path2 = self.path.split("?")[0]
        print(path2)
        query_params = self.path.split("?")[1:] if "?" in self.path else []
        if path2 == '/':
            self.send_response(301)
            self.send_header('Location', 'site/index.html')
            self.end_headers()
        elif path2 == "/submit":
            with open('silly.json', 'r') as f:
                data = json.load(f)
            data.append({'name': str(datetime.datetime.now()), 'perc': query_params[0].split("=")[1]})
            print(data)
            with open('silly.json', 'w') as f:
                json.dump(data, f)
        elif path2 == "/submissions":
            with open("silly.json", "rb") as w:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(w.read())
        else:
            file_path = path2.strip('/')
            _, file_extension = os.path.splitext(file_path) 
            content_type = self.get_content_type(file_extension)
            if os.path.exists(file_path):
                if query_params and file_extension in ['.png', '.jpg', '.jpeg', '.gif']:
                    query_params = query_params[0].split("&")
                    size_param = [param for param in query_params if param.startswith("size=")]
                    if size_param:
                        print(file_path)
                        size = int(size_param[0].split("=")[1])
                        new_path = file_path + ".temp." + file_extension[1:]
                        file = Image.open(file_path)
                        file.thumbnail((size, file.size[1]))
                        file.save(new_path)
                        file_path = new_path
                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.end_headers()
                with open(file_path, 'rb') as file:
                    self.wfile.write(file.read())
                if query_params and file_extension in ['.png', '.jpg', '.jpeg', '.gif']:
                    os.remove(file_path)
            else:
                print(path2)
                #self.send_response(301)
                #self.send_header('Location', './404.html')
                #self.end_headers()

    def get_content_type(self, file_extension):
        if file_extension == '.html':
            return 'text/html'
        elif file_extension == '.css':
            return 'text/css'
        elif file_extension == '.js':
            return 'text/javascript'
        elif file_extension in ['.png', '.jpg', '.jpeg', '.gif']:
            return 'image/' + file_extension[1:]
        elif file_extension == '.ico':
            return 'image/png'
        else:
            return 'application/octet-stream'

def run(server_class, handler_class, port):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Server running on port {port}")
    httpd.serve_forever()

if __name__ == '__main__':
    try:
        server_port = 8080  # You can change this to any port you prefer
        run(HTTPServer, RedirectHandler, server_port)
    except KeyboardInterrupt:
        print('\nServer stopped.')