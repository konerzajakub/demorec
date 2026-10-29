"""Minimal DevTools client over a WebSocket, standard library only.

Playwright's sync API delivers events only while the main thread is inside a Playwright call,
so screencast frames waited, or were dropped, whenever the scene did anything else. capture.py
uses this client in its own process, on its own connection to the page."""
import base64, json, os, socket, struct, threading

OP_CLOSE, OP_PING, OP_PONG = 8, 9, 10


class CDP:
    def __init__(self, port, target_id, timeout=10):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=timeout)
        self.buf = bytearray(self._handshake(port, target_id))
        self.sock.settimeout(None)
        self.last_id = 0
        self.lock = threading.Lock()  # the reader acks while another thread stops the screencast

    def _handshake(self, port, target_id):
        """WebSocket upgrade. Returns the bytes that arrived after the response headers."""
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall(("GET /devtools/page/%s HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nUpgrade: websocket\r\n"
                           "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n"
                           % (target_id, port, key)).encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("DevTools closed the connection during the handshake")
            head += chunk
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            raise ConnectionError("DevTools refused the WebSocket: %r" % head[:200])
        return head.split(b"\r\n\r\n", 1)[1]

    def send(self, method, params=None):
        """Send a command without waiting for its reply. Replies arrive through recv()."""
        with self.lock:
            self.last_id += 1
            self._send_frame(json.dumps({"id": self.last_id, "method": method, "params": params or {}}).encode())

    def _send_frame(self, data):
        """One final text frame. Client frames must be masked."""
        mask = os.urandom(4)
        n = len(data)
        if n < 126: head = struct.pack("!BB", 0x81, 0x80 | n)
        elif n < 65536: head = struct.pack("!BBH", 0x81, 0x80 | 126, n)
        else: head = struct.pack("!BBQ", 0x81, 0x80 | 127, n)
        self.sock.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _read_exact(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(1 << 20)
            if not chunk:
                raise ConnectionError("DevTools connection closed")
            self.buf += chunk
        out = bytes(self.buf[:n])
        del self.buf[:n]
        return out

    def recv(self):
        """Next message as a dict. Raises ConnectionError when the page is gone."""
        parts = []
        while True:
            b0, b1 = self._read_exact(2)
            n = b1 & 0x7F
            if n == 126: n = struct.unpack("!H", self._read_exact(2))[0]
            elif n == 127: n = struct.unpack("!Q", self._read_exact(8))[0]
            payload = self._read_exact(n)  # the server never masks
            op = b0 & 0x0F
            if op == OP_CLOSE:
                raise ConnectionError("DevTools connection closed")
            if op in (OP_PING, OP_PONG):
                continue
            parts.append(payload)
            if b0 & 0x80:  # final frame of the message
                return json.loads(b"".join(parts))

    def close(self):
        try: self.sock.shutdown(socket.SHUT_RDWR)  # wakes the reader blocked in recv()
        except OSError: pass
        try: self.sock.close()
        except OSError: pass


def devtools_port(profile):
    """Port Chrome chose for --remote-debugging-port=0, from the profile folder."""
    with open(os.path.join(profile, "DevToolsActivePort"), encoding="utf-8") as f:
        return int(f.readline())
