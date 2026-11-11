"""app.py: Task Tracker 1.5.0, which also shows metrics for Prometheus."""
import html  # makes user text safe to show on a web page
import json  # converts Python data into JSON text
import os  # reads environment variables and builds file paths
import socket  # finds the name of the computer or container that answers
import time  # measures how long each request takes
from http.server import BaseHTTPRequestHandler, HTTPServer  # built-in web server
from urllib.parse import parse_qs, urlparse  # reads ?task=... from the address

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest  # /metrics page
from prometheus_client import Counter, Gauge, Histogram  # the metric types

VERSION = "1.5.0"
PORT = int(os.environ.get("APP_PORT", "8080"))  # port to listen on
APP_ENV = os.environ.get("APP_ENV", "local")  # where this copy runs
DATA_DIR = os.environ.get("DATA_DIR", "data")  # folder that keeps the tasks
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")
KNOWN_PATHS = {"/", "/add", "/health", "/fail", "/metrics"}  # others: "other"

# Metrics that Prometheus reads from the /metrics page
REQUESTS = Counter("http_requests", "Total HTTP requests.", ["path", "status"])
LATENCY = Histogram("http_request_duration_seconds", "Request time.", ["path"])
TASKS = Gauge("tasks_total", "Number of saved tasks.")


def load_tasks():  # reads the saved tasks, or starts with an empty list
    """Return the list of tasks saved in DATA_DIR."""
    if not os.path.exists(TASKS_FILE):
        return []
    with open(TASKS_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_task(task):  # adds one task and writes the list back to the file
    """Append a task to the saved list."""
    os.makedirs(DATA_DIR, exist_ok=True)  # create the folder if it is missing
    tasks = load_tasks() + [task]
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f)


def health_payload():  # builds the data for the /health page
    """Return the data for the /health endpoint."""
    return {"status": "ok", "version": VERSION, "environment": APP_ENV}


def render_page(tasks):  # builds the HTML home page
    """Return the HTML home page."""
    items = "".join(f"<li>{html.escape(t)}</li>" for t in tasks)
    items = items or "<li>No tasks yet</li>"
    return (f"<h1>Task Tracker ({APP_ENV})</h1><p>Version {VERSION}</p>"
            f"<p>Served by: {socket.gethostname()}</p><ul>{items}</ul>")


class Handler(BaseHTTPRequestHandler):  # decides how to answer each web request
    def do_GET(self):  # runs every time a browser or curl asks for a page
        start = time.perf_counter()  # start the stopwatch for this request
        url = urlparse(self.path)  # splits /add?task=x into path and query
        status = 200  # status 200 means OK
        if url.path == "/metrics":  # the page Prometheus scrapes
            TASKS.set(len(load_tasks()))
            body, content_type = generate_latest(), CONTENT_TYPE_LATEST
        elif url.path == "/health":
            body, content_type = json.dumps(health_payload()), "application/json"
        elif url.path == "/add":  # /add?task=Buy+milk saves a new task
            task = parse_qs(url.query).get("task", [""])[0].strip()
            if task:
                save_task(task)
            body, content_type = f"Added: {task}\n", "text/plain"
        elif url.path == "/fail":  # a practice error, to see errors in Prometheus
            status = 500  # status 500 means server error
            body, content_type = "Practice error\n", "text/plain"
        else:  # any other address returns the home page
            body, content_type = render_page(load_tasks()), "text/html"
        if isinstance(body, str):
            body = body.encode()  # the web server sends bytes
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(body)
        path = url.path if url.path in KNOWN_PATHS else "other"
        REQUESTS.labels(path=path, status=str(status)).inc()  # count the request
        LATENCY.labels(path=path).observe(time.perf_counter() - start)  # its time


if __name__ == "__main__":  # true only when you run: python app.py
    print(f"Task Tracker {VERSION} ({APP_ENV}) on port {PORT}", flush=True)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()  # keep running
