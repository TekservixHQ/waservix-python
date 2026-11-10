import json, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from waservix import WAservix, WAservixError, verify_webhook

CALLS = []


class Handler(BaseHTTPRequestHandler):
    def _go(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n)) if n else None
        CALLS.append((self.command, self.path, {k.lower(): v for k, v in self.headers.items()}, body))
        if self.path.startswith("/down"):
            self.send_response(503); self.end_headers()
            self.wfile.write(b'{"success":false,"message":"Device reconnecting"}'); return
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(json.dumps({"success": True, "data": {"msgId": 1, "status": "in_progress"}}).encode())
    do_GET = do_POST = do_DELETE = do_PUT = _go
    def log_message(self, *a): pass


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.c = WAservix("wpk_test", base_url="http://127.0.0.1:%d" % cls.srv.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def last(self):
        return CALLS[-1]

    def test_send_text(self):
        self.assertEqual(self.c.send_text("+1555", "hi")["msgId"], 1)
        m, p, h, b = self.last()
        self.assertEqual((m, p, b), ("POST", "/send-message", {"to": "+1555", "text": "hi"}))
        self.assertEqual(h["authorization"], "Bearer wpk_test")

    def test_media(self):
        self.c.send_image("+1", "https://x/y.jpg")
        self.assertEqual(self.last()[3], {"to": "+1", "imageUrl": "https://x/y.jpg"})
        self.c.send_document("+1", "https://x/a.pdf", file_name="a.pdf", caption="c")
        self.assertEqual(self.last()[3], {"to": "+1", "documentUrl": "https://x/a.pdf", "fileName": "a.pdf", "text": "c"})

    def test_paths(self):
        self.c.get_message_info(5); self.assertEqual(self.last()[1], "/messages/5/info")
        self.c.edit_message(5, "t"); self.assertEqual(self.last()[:2], ("PUT", "/messages/5"))
        self.c.on_whatsapp("+1555"); self.assertEqual(self.last()[1], "/on-whatsapp/%2B1555")
        self.c.get_group_metadata("1203@g.us"); self.assertEqual(self.last()[1], "/groups/1203%40g.us/metadata")
        self.c.save_contact("+1", "A"); self.assertEqual(self.last()[3], {"phone": "+1", "name": "A"})
        self.c.connect_session(3); self.assertEqual(self.last()[3], {"method": "qr"})

    def test_error(self):
        c = WAservix("k", base_url="http://127.0.0.1:%d/down" % self.srv.server_port)
        with self.assertRaises(WAservixError) as e:
            c.get_status()
        self.assertEqual(e.exception.status, 503)

    def test_webhook(self):
        self.assertTrue(verify_webhook("abc", "abc"))
        self.assertFalse(verify_webhook("abc", "abd"))
        self.assertFalse(verify_webhook(None, "abc"))

    def test_requires(self):
        with self.assertRaises(ValueError):
            WAservix("")
        with self.assertRaises(ValueError):
            self.c.send_message("", text="x")


if __name__ == "__main__":
    unittest.main()
