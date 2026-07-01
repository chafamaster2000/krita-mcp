"""Tests for the kri CLI against a fake kritamcp plugin server.

The fake server records every request body in `FakePlugin.requests_log` and
answers from `FakePlugin.responses` (action -> dict, or list of dicts served
in order for polling tests). Tests invoke the real CLI via subprocess with
KRITA_URL pointed at the fake server."""
import base64
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KRI = os.path.join(REPO, "cli", "kri")


class FakePlugin(BaseHTTPRequestHandler):
    requests_log = []
    responses = {}

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        self._reply({"status": "ok", "plugin": "kritamcp"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        cmd = json.loads(self.rfile.read(n))
        FakePlugin.requests_log.append(cmd)
        r = FakePlugin.responses.get(cmd["action"], {"status": "ok"})
        if isinstance(r, list):
            r = r.pop(0) if len(r) > 1 else r[0]
        self._reply(r, 500 if r.get("error") else 200)

    def _reply(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)


class KriTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("localhost", 0), FakePlugin)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        FakePlugin.requests_log.clear()
        FakePlugin.responses = {}

    def kri(self, *args, stdin=None):
        env = dict(os.environ, KRITA_URL=f"http://localhost:{self.port}")
        return subprocess.run(
            [sys.executable, KRI, *args],
            capture_output=True, text=True, env=env, input=stdin, timeout=30,
        )

    def last_request(self):
        return FakePlugin.requests_log[-1]

    # ----- Task 1 -----

    def test_health_ok(self):
        r = self.kri("health")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("kritamcp", r.stdout)

    def test_connection_error_exits_1(self):
        env = dict(os.environ, KRITA_URL="http://localhost:1")  # nothing there
        r = subprocess.run([sys.executable, KRI, "undo"],
                           capture_output=True, text=True, env=env, timeout=30)
        self.assertEqual(r.returncode, 1)
        self.assertIn("Cannot connect", r.stderr)

    # ----- Task 3 -----

    def test_status_merges_doc_and_ai_in_one_roundtrip(self):
        FakePlugin.responses["batch"] = {
            "status": "ok", "count": 2,
            "results": [
                {"status": "ok", "document": {"name": "x.kra", "width": 800,
                                              "height": 600, "layers": []}},
                {"status": "ok", "ai": {"workspace": "generation"},
                 "regions": [], "styles": []},
            ],
        }
        r = self.kri("status")
        self.assertEqual(r.returncode, 0, r.stderr)
        merged = json.loads(r.stdout)
        self.assertEqual(merged["doc"]["name"], "x.kra")
        self.assertEqual(merged["ai"]["workspace"], "generation")
        # exactly ONE round-trip
        self.assertEqual(len(FakePlugin.requests_log), 1)
        req = self.last_request()
        self.assertEqual(req["action"], "batch")
        self.assertEqual([c["action"] for c in req["params"]["commands"]],
                         ["doc_info", "ai_overview"])

    def test_status_tolerates_missing_ai_plugin(self):
        FakePlugin.responses["batch"] = {
            "status": "ok", "count": 2,
            "results": [
                {"status": "ok", "document": None},
                {"error": "AI Diffusion plugin not loaded: ..."},
            ],
        }
        r = self.kri("status")
        self.assertEqual(r.returncode, 0, r.stderr)
        merged = json.loads(r.stdout)
        self.assertIn("error", merged["ai"])

    # ----- Task 4 -----

    def test_paint_command_mappings(self):
        """Each CLI invocation maps to the right action + params."""
        cases = [
            (["canvas", "800", "600", "--bg", "#ffffff"],
             "new_canvas", {"width": 800, "height": 600,
                            "name": "New Canvas", "background": "#ffffff"}),
            (["color", "#ff0000"], "set_color", {"color": "#ff0000"}),
            (["brush", "--size", "12"], "set_brush", {"size": 12}),
            (["stroke", "10,10", "50,60", "--size", "8"],
             "stroke", {"points": [[10, 10], [50, 60]], "size": 8,
                        "feather": 0.0, "opacity": 1.0}),
            (["fill", "100", "120", "30"],
             "fill", {"x": 100, "y": 120, "radius": 30, "feather": 0.0}),
            (["shape", "ellipse", "10", "20", "100", "50"],
             "draw_shape", {"shape": "ellipse", "x": 10, "y": 20,
                            "width": 100, "height": 50, "fill": True,
                            "stroke": False, "feather": 0.0}),
            (["redo"], "redo", {}),
            (["clear", "#000000"], "clear", {"color": "#000000"}),
            (["color-at", "5", "6"], "get_color_at", {"x": 5, "y": 6}),
            (["brushes", "soft", "--limit", "5"],
             "list_brushes", {"filter": "soft", "limit": 5}),
        ]
        for argv, action, params in cases:
            with self.subTest(argv=argv):
                FakePlugin.requests_log.clear()
                r = self.kri(*argv)
                self.assertEqual(r.returncode, 0, f"{argv}: {r.stderr}")
                req = self.last_request()
                self.assertEqual(req["action"], action)
                self.assertEqual(req["params"], params)

    def test_stroke_rejects_bad_point(self):
        r = self.kri("stroke", "10,10", "banana")
        self.assertEqual(r.returncode, 2)
        self.assertIn("invalid point", r.stderr)

    def test_save_uses_absolute_path(self):
        r = self.kri("save", "out.png")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isabs(self.last_request()["params"]["path"]))

    # ----- Task 5 -----

    def _canvas_payload(self, fmt="jpeg"):
        return {"status": "ok", "mode": "fast", "format": fmt,
                "data_b64": base64.b64encode(b"fakeimagebytes").decode(),
                "width": 640, "height": 480}

    def test_look_writes_image_and_prints_path(self):
        FakePlugin.responses["get_canvas"] = self._canvas_payload()
        with tempfile.TemporaryDirectory() as d:
            dest = os.path.join(d, "c.jpg")
            r = self.kri("look", "-o", dest)
            self.assertEqual(r.returncode, 0, r.stderr)
            info = json.loads(r.stdout)
            self.assertEqual(info["path"], dest)
            with open(dest, "rb") as f:
                self.assertEqual(f.read(), b"fakeimagebytes")
        self.assertEqual(self.last_request()["params"]["mode"], "fast")

    def test_look_full_mode(self):
        FakePlugin.responses["get_canvas"] = self._canvas_payload(fmt="png")
        with tempfile.TemporaryDirectory() as d:
            dest = os.path.join(d, "c.png")
            r = self.kri("look", "--full", "-o", dest)
            self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.last_request()["params"]["mode"], "full")

    def test_batch_from_stdin_sets_stop_on_error(self):
        FakePlugin.responses["batch"] = {"status": "ok", "count": 2,
                                         "results": [{"status": "ok"}] * 2}
        script = json.dumps([
            {"action": "set_color", "params": {"color": "#fff"}},
            {"action": "fill", "params": {"x": 1, "y": 2, "radius": 3}},
        ])
        r = self.kri("batch", stdin=script)
        self.assertEqual(r.returncode, 0, r.stderr)
        req = self.last_request()
        self.assertEqual(req["action"], "batch")
        self.assertTrue(req["params"]["stop_on_error"])
        self.assertEqual(len(req["params"]["commands"]), 2)

    def test_batch_stopped_at_exits_1(self):
        FakePlugin.responses["batch"] = {
            "status": "ok", "count": 2, "stopped_at": 1,
            "results": [{"status": "ok"}, {"error": "boom"}],
        }
        r = self.kri("batch", stdin='[{"action":"undo"},{"action":"undo"}]')
        self.assertEqual(r.returncode, 1)
        self.assertIn("stopped at command 1", r.stderr)

    def test_batch_look_writes_canvas(self):
        FakePlugin.responses["batch"] = {
            "status": "ok", "count": 1, "results": [{"status": "ok"}],
            "canvas": self._canvas_payload(),
        }
        with tempfile.TemporaryDirectory() as d:
            dest = os.path.join(d, "after.jpg")
            r = self.kri("batch", "--look", "fast", "-o", dest,
                         stdin='[{"action":"undo"}]')
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(os.path.exists(dest))
            res = json.loads(r.stdout)
            self.assertEqual(res["canvas"]["path"], dest)
        self.assertEqual(self.last_request()["params"]["review"], "fast")

    def test_batch_invalid_json_exits_2(self):
        r = self.kri("batch", stdin="not json")
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
