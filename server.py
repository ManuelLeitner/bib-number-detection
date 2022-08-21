import json
import os
import re
import socketserver
from http.server import BaseHTTPRequestHandler, HTTPServer
from os.path import exists

from client import ApiClient
from detection.BibNumberDetector import BibNumberDetector
from file_system_watcher import FileSystemWatcher
from result_collector import ResultCollector, ResultType

hostName = "localhost"
serverPort = 8081


# noinspection PyPep8Naming
class Server(BaseHTTPRequestHandler):
    results: ResultCollector
    post_regex = re.compile('/image/([^/]+)')

    def __init__(self, request: bytes, client_address: (str, int), server: socketserver.BaseServer,
                 results: ResultCollector):
        self.results = results
        super().__init__(request, client_address, server)

    def do_GET(self):
        file = "index.html"
        response_type = "text/html"
        if self.path == '/image':
            response_type = "image/jpeg"
            file = self.results.get_manual_pending()

        if file is not None and exists(file):
            self.send_response(200)
            self.send_header("Content-type", response_type)
            if self.path == '/image':
                self.send_header("Content-Disposition", f'attachment; filename="{os.path.split(file)[1]}"')
            self.end_headers()
            with open(file, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, "Aktuell gibt es keine Bilder")

    def do_POST(self):
        match = Server.post_regex.match(self.path)
        if match is not None:
            content_length = int(self.headers['Content-Length'])
            content_str = self.rfile.read(content_length)
            nums = json.loads(content_str)
            self.results.add_manually(nums, str(match.groups()[0]))
        else:
            self.send_error(400, f"path ({self.path}) doesn't match required format: {Server.post_regex.pattern}")

    @staticmethod
    def construct(results: ResultCollector, ):
        def __b(request: bytes, client_address: (str, int), server: socketserver.BaseServer):
            return Server(request, client_address, server, results)

        return __b


def main():
    img_dir = "D:/LaufendHelfen/ai/res/test/imgs/imgdirectory"
    api_client = ApiClient("https://api.laufendhelfen.org/timecapture/tag_id", "AI", "aVsp4Lhita1A+")
    results = ResultCollector(api_client, ResultType.FINISH, "buffer.csv", img_dir)
    watcher = FileSystemWatcher(img_dir, results)

    number_detector = BibNumberDetector("temp/ai", 1)

    def detect(f):
        results.detection_started(f)
        results.add_ai(number_detector.detect_bib_numbers(f))

    watcher.add_listener(detect)

    web_server = HTTPServer((hostName, serverPort), Server.construct(results))
    print(f"Server started http://{hostName}:{serverPort}")

    try:
        web_server.serve_forever()
    except KeyboardInterrupt:
        pass

    watcher.stop()
    web_server.server_close()
    print("Server stopped.")


if __name__ == '__main__':
    main()
