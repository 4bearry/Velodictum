"""
Velodictum - Mobile LAN Bridge Server (Security Hardened)
Allows smartphones or tablets on the same WiFi network to act as a wireless
dictation microphone for your Windows PC via an authenticated, DoS-protected web interface.
"""
import http.server
import socket
import threading
import io
import os
import json
import secrets
import time
import urllib.parse
from typing import Callable, Optional, Dict, List

from config import config

# Security Limits
DEFAULT_MAX_PAYLOAD_BYTES = 25 * 1024 * 1024  # 25 MB max payload
DEFAULT_RATE_LIMIT_PER_MIN = 30  # Max 30 requests / minute per remote IP


def get_local_ip() -> str:
    """Detect the local LAN IPv4 address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def generate_self_signed_cert(cert_path: str, key_path: str, hostname: str = "localhost") -> bool:
    """Generates an ad-hoc local self-signed TLS certificate for LAN HTTPS Secure Context."""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import datetime
        import ipaddress

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, hostname),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Velodictum Mobile Bridge"),
        ])

        san_list = [x509.DNSName("localhost"), x509.DNSName(hostname)]
        try:
            san_list.append(x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")))
            if hostname not in ("localhost", "127.0.0.1"):
                san_list.append(x509.IPAddress(ipaddress.IPv4Address(hostname)))
        except Exception:
            pass

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
            .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3650))
            .add_extension(x509.SubjectAlternativeName(san_list), critical=False)
            .sign(key, hashes.SHA256())
        )

        os.makedirs(os.path.dirname(os.path.abspath(cert_path)), exist_ok=True)
        with open(key_path, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        return True
    except Exception as e:
        print(f"[MobileBridge] Self-signed certificate generation notice: {e}")
        return False


MOBILE_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Velodictum Mobile Mic</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; -webkit-user-select: none; }
        body {
            background-color: #09090b;
            color: #f4f4f5;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: space-between;
            height: 100vh;
            padding: 32px 24px;
        }
        .header { text-align: center; }
        .header h1 { font-size: 20px; font-weight: 700; color: #fff; }
        .header p { font-size: 13px; color: #71717a; margin-top: 4px; }
        .status { font-size: 14px; font-weight: 600; color: #a1a1aa; height: 24px; text-align: center; }
        .btn-container { display: flex; flex-direction: column; align-items: center; }
        .record-btn {
            width: 140px;
            height: 140px;
            border-radius: 50%;
            background: linear-gradient(135deg, #18181b 0%, #27272a 100%);
            border: 2px solid rgba(255,255,255,0.1);
            color: #38bdf8;
            font-size: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            outline: none;
            -webkit-tap-highlight-color: transparent;
        }
        .record-btn.recording {
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            border-color: #f87171;
            color: #ffffff;
            transform: scale(1.08);
            box-shadow: 0 0 40px rgba(239, 68, 68, 0.4);
        }
        .token-bar {
            width: 100%;
            max-width: 280px;
            display: flex;
            gap: 8px;
            margin-top: 12px;
        }
        .token-bar input {
            flex: 1;
            background: #18181b;
            border: 1px solid #27272a;
            color: #f4f4f5;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 13px;
            font-family: monospace;
            text-align: center;
            outline: none;
        }
        .token-bar button {
            background: #27272a;
            border: 1px solid #3f3f46;
            color: #38bdf8;
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
        }
        .instructions {
            font-size: 12px;
            color: #52525b;
            text-align: center;
            max-width: 260px;
            line-height: 1.4;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Velodictum</h1>
        <p id="subHeader">Wireless Mobile Mic</p>
    </div>

    <div class="btn-container">
        <div class="status" id="statusText">Ready</div>
        <div style="height: 20px;"></div>
        <button class="record-btn" id="micBtn" onpointerdown="startRec(event)" onpointerup="stopRec(event)">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>
        </button>
        <div class="token-bar" id="tokenBar">
            <input type="password" id="tokenInput" placeholder="Pairing token..." />
            <button id="saveBtn" onclick="saveToken()">Save</button>
        </div>
    </div>

    <div class="instructions" id="instructText">
        Hold the button to dictate. Text will be inserted immediately into your active Windows window.
    </div>

    <script>
        const i18n = {
            en: {
                ready: "Ready",
                tokenSaved: "Token saved!",
                recording: "Recording...",
                processing: "Processing & Sending...",
                tokenInvalid: "Error: Invalid pairing token!",
                rateLimit: "Rate limit reached. Please wait.",
                injected: "Injected (",
                error: "Error: ",
                netError: "Network error: ",
                httpsRequired: "HTTPS required! Please open via https:// so the browser grants mic access.",
                micUnavailable: "Microphone access unavailable or blocked in browser.",
                tokenPlaceholder: "Enter pairing token...",
                save: "Save",
                instructions: "Hold the button to dictate. Text will be inserted immediately into your active Windows window.",
                subHeader: "Wireless Mobile Mic"
            },
            de: {
                ready: "Bereit",
                tokenSaved: "Token gespeichert!",
                recording: "Aufnahme...",
                processing: "Verarbeite & Sende...",
                tokenInvalid: "Fehler: Pairing-Code ungültig!",
                rateLimit: "Rate-Limit erreicht. Bitte warten.",
                injected: "Eingefügt (",
                error: "Fehler: ",
                netError: "Netzwerkfehler: ",
                httpsRequired: "HTTPS erforderlich! Bitte öffne die Seite mit https://, damit der Browser das Mikrofon freigibt.",
                micUnavailable: "Mikrofonzugriff nicht verfügbar oder im Browser blockiert.",
                tokenPlaceholder: "Pairing-Token eingeben...",
                save: "Speichern",
                instructions: "Halte den Button gedrückt, um zu diktieren. Der Text wird sofort in dein aktives Windows-Fenster eingefügt.",
                subHeader: "Kabelloses Mobil-Mikrofon"
            }
        };

        const userLang = (navigator.language || navigator.userLanguage || 'en').toLowerCase().startsWith('de') ? 'de' : 'en';
        const t = i18n[userLang] || i18n.en;

        let mediaRecorder;
        let audioChunks = [];
        const btn = document.getElementById('micBtn');
        const statusEl = document.getElementById('statusText');
        const tokenInput = document.getElementById('tokenInput');
        const saveBtn = document.getElementById('saveBtn');
        const instructEl = document.getElementById('instructText');
        const subHeaderEl = document.getElementById('subHeader');

        // Apply UI localization
        statusEl.textContent = t.ready;
        tokenInput.placeholder = t.tokenPlaceholder;
        saveBtn.textContent = t.save;
        instructEl.textContent = t.instructions;
        subHeaderEl.textContent = t.subHeader;

        // Check URL for token parameter ?token=...
        const urlParams = new URLSearchParams(window.location.search);
        const urlToken = urlParams.get('token');
        if (urlToken) {
            localStorage.setItem('velodictum_token', urlToken);
            tokenInput.value = urlToken;
        } else {
            const savedToken = localStorage.getItem('velodictum_token');
            if (savedToken) tokenInput.value = savedToken;
        }

        function saveToken() {
            const val = tokenInput.value.trim();
            localStorage.setItem('velodictum_token', val);
            statusEl.textContent = t.tokenSaved;
            statusEl.style.color = '#10b981';
            setTimeout(() => { statusEl.textContent = t.ready; statusEl.style.color = '#a1a1aa'; }, 2000);
        }

        function getToken() {
            return tokenInput.value.trim() || localStorage.getItem('velodictum_token') || '';
        }

        async function initAudio() {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                const isHttps = window.location.protocol === 'https:';
                if (!isHttps) {
                    throw new Error(t.httpsRequired);
                } else {
                    throw new Error(t.micUnavailable);
                }
            }
            if (!mediaRecorder) {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
                mediaRecorder.onstop = uploadAudio;
            }
        }

        async function startRec(e) {
            e.preventDefault();
            try {
                await initAudio();
                audioChunks = [];
                mediaRecorder.start();
                btn.classList.add('recording');
                statusEl.textContent = t.recording;
                statusEl.style.color = '#ef4444';
            } catch (err) {
                statusEl.textContent = t.error + err.message;
            }
        }

        function stopRec(e) {
            e.preventDefault();
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                mediaRecorder.stop();
                btn.classList.remove('recording');
                statusEl.textContent = t.processing;
                statusEl.style.color = '#38bdf8';
            }
        }

        async function uploadAudio() {
            const blob = new Blob(audioChunks, { type: 'audio/webm' });
            const formData = new FormData();
            formData.append('audio', blob, 'mobile_dictation.webm');

            const token = getToken();
            const headers = {};
            if (token) {
                headers['X-Velodictum-Token'] = token;
            }

            try {
                const res = await fetch('/api/dictate', { method: 'POST', body: formData, headers: headers });
                const data = await res.json();
                if (res.status === 401) {
                    statusEl.textContent = t.tokenInvalid;
                    statusEl.style.color = '#f43f5e';
                } else if (res.status === 429) {
                    statusEl.textContent = t.rateLimit;
                    statusEl.style.color = '#f59e0b';
                } else if (data.status === 'ok') {
                    statusEl.textContent = t.injected + (data.text ? data.text.substring(0, 18) + '...' : '') + ')';
                    statusEl.style.color = '#10b981';
                } else {
                    statusEl.textContent = t.error + (data.error || 'Unknown');
                    statusEl.style.color = '#f43f5e';
                }
            } catch (err) {
                statusEl.textContent = t.netError + err.message;
                statusEl.style.color = '#f43f5e';
            }
            setTimeout(() => {
                statusEl.textContent = t.ready;
                statusEl.style.color = '#a1a1aa';
            }, 3500);
        }
    </script>
</body>
</html>
"""


def extract_audio_payload(body: bytes) -> bytes:
    """Extract binary audio payload from browser multipart form-data."""
    if b"Content-Type:" in body:
        header_end = body.find(b"\r\n\r\n")
        if header_end != -1:
            data = body[header_end + 4:]
            tail = data.rfind(b"\r\n------")
            if tail != -1:
                return data[:tail]
            return data
    return body


class MobileBridgeHandler(http.server.BaseHTTPRequestHandler):
    transcriber_callback: Optional[Callable[[bytes], str]] = None
    auth_token: Optional[str] = None
    require_auth: bool = True
    max_payload_bytes: int = DEFAULT_MAX_PAYLOAD_BYTES
    rate_limit_per_minute: int = DEFAULT_RATE_LIMIT_PER_MIN

    # Thread-safe rate limiter & concurrency tracking
    _rate_limit_lock = threading.Lock()
    _ip_records: Dict[str, List[float]] = {}
    _transcription_lock = threading.Lock()

    def address_string(self) -> str:
        """Override to prevent blocking reverse DNS lookups on LAN IP addresses."""
        return self.client_address[0] if self.client_address else "127.0.0.1"

    @classmethod
    def _is_rate_limited(cls, client_ip: str) -> bool:
        """Sliding-window in-memory rate limiter."""
        now = time.time()
        with cls._rate_limit_lock:
            # Clean records older than 60s
            timestamps = cls._ip_records.get(client_ip, [])
            timestamps = [t for t in timestamps if now - t < 60.0]
            if len(timestamps) >= cls.rate_limit_per_minute:
                cls._ip_records[client_ip] = timestamps
                return True
            timestamps.append(now)
            cls._ip_records[client_ip] = timestamps
            return False

    def _is_authenticated(self) -> bool:
        """
        Validates pairing token strictly from headers (X-Velodictum-Token or Authorization: Bearer).
        URL query parameters (?token=...) are deprecated and rejected to prevent secret leaks in logs/history.
        """
        if not self.require_auth or not self.auth_token:
            return True

        # 1. Custom Header X-Velodictum-Token
        token = self.headers.get("X-Velodictum-Token", "").strip() if self.headers else ""
        if token and secrets.compare_digest(token, self.auth_token):
            return True

        # 2. Authorization: Bearer <token>
        auth_hdr = self.headers.get("Authorization", "").strip() if self.headers else ""
        if auth_hdr.startswith("Bearer "):
            bearer_token = auth_hdr[7:].strip()
            if secrets.compare_digest(bearer_token, self.auth_token):
                return True

        return False

    def _send_cors_headers(self, is_sensitive: bool = False):
        """Sends restricted CORS and security headers."""
        origin = self.headers.get("Origin", "") if hasattr(self, "headers") and self.headers else ""
        if not is_sensitive:
            self.send_header("Access-Control-Allow-Origin", origin if origin else "*")
        else:
            # Sensitive POST endpoints: Restrict origin to local LAN / host to prevent browser pivoting
            if origin:
                try:
                    parsed = urllib.parse.urlparse(origin)
                    host = parsed.hostname or ""
                    if host in ("localhost", "127.0.0.1", get_local_ip()):
                        self.send_header("Access-Control-Allow-Origin", origin)
                except Exception:
                    pass
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Velodictum-Token")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        client_ip = self.client_address[0]
        if self._is_rate_limited(client_ip):
            self.send_response(429)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "error": "Zu viele Anfragen. Bitte kurz warten."}).encode("utf-8"))
            return

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(MOBILE_HTML.encode("utf-8"))
        elif path == "/favicon.ico":
            self.send_response(204)
            self._send_cors_headers()
            self.end_headers()
        elif path == "/api/status":
            if not self._is_authenticated():
                self.send_response(401)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": "Unauthorized: Invalid or missing pairing token"}).encode("utf-8"))
                return

            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "app": "Velodictum"}).encode("utf-8"))
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()

    def do_POST(self):
        client_ip = self.client_address[0]
        if self._is_rate_limited(client_ip):
            self.send_response(429)
            self._send_cors_headers(is_sensitive=True)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "error": "Rate limit exceeded"}).encode("utf-8"))
            return

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/dictate":
            # 1. Authentication Check
            if not self._is_authenticated():
                self.send_response(401)
                self._send_cors_headers(is_sensitive=True)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": "Unauthorized: Invalid or missing pairing token"}).encode("utf-8"))
                return

            # 2. Content-Length & Payload Size Check (DoS / OOM Protection)
            try:
                content_length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                content_length = 0

            if content_length <= 0:
                self.send_response(400)
                self._send_cors_headers(is_sensitive=True)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": "Invalid Content-Length"}).encode("utf-8"))
                return

            if content_length > self.max_payload_bytes:
                self.send_response(413)
                self._send_cors_headers(is_sensitive=True)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": f"Payload exceeds maximum allowed size ({self.max_payload_bytes} bytes)"}).encode("utf-8"))
                return

            # 3. Read Body Safely in Chunks
            bytes_read = 0
            chunks = []
            chunk_size = 64 * 1024
            while bytes_read < content_length:
                to_read = min(chunk_size, content_length - bytes_read)
                chunk = self.rfile.read(to_read)
                if not chunk:
                    break
                chunks.append(chunk)
                bytes_read += len(chunk)
                if bytes_read > self.max_payload_bytes:
                    self.send_response(413)
                    self._send_cors_headers(is_sensitive=True)
                    self.end_headers()
                    return

            body = b"".join(chunks)

            # 4. Concurrency Guard: Ensure only one dictation is transcribed at a time
            if not self._transcription_lock.acquire(blocking=False):
                self.send_response(429)
                self._send_cors_headers(is_sensitive=True)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": "Transkription belegt. Bitte kurz warten."}).encode("utf-8"))
                return

            try:
                if MobileBridgeHandler.transcriber_callback and body:
                    try:
                        audio_payload = extract_audio_payload(body)
                        # Execute dictation callback with received audio bytes
                        result_text = MobileBridgeHandler.transcriber_callback(audio_payload)
                        self.send_response(200)
                        self._send_cors_headers(is_sensitive=True)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "ok", "text": str(result_text or "")}).encode("utf-8"))
                        return
                    except Exception as e:
                        self.send_response(500)
                        self._send_cors_headers(is_sensitive=True)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "error", "error": str(e)}).encode("utf-8"))
                        return

                self.send_response(400)
                self._send_cors_headers(is_sensitive=True)
                self.end_headers()
            finally:
                self._transcription_lock.release()
        else:
            self.send_response(404)
            self._send_cors_headers(is_sensitive=True)
            self.end_headers()

    def log_message(self, format, *args):
        # Silence default HTTP access logs for quiet operation
        pass


class MobileBridgeServer:
    def __init__(
        self,
        port: int = 8765,
        on_audio_received: Optional[Callable[[bytes], None]] = None,
        auth_token: Optional[str] = None,
        require_auth: bool = True,
        bind_address: str = "0.0.0.0",
    ):
        self.port = port
        self.bind_address = bind_address
        self.local_ip = get_local_ip()
        self.server: Optional[http.server.HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        
        # Load or generate authentication token
        self.auth_token = auth_token or getattr(config.mobile_bridge, "auth_token", None)
        if not self.auth_token:
            self.auth_token = secrets.token_hex(8)  # 16-character hex token
            config.mobile_bridge.auth_token = self.auth_token
            config.save()

        self.require_auth = require_auth
        
        self.is_https = False
        
        MobileBridgeHandler.transcriber_callback = on_audio_received
        MobileBridgeHandler.auth_token = self.auth_token
        MobileBridgeHandler.require_auth = self.require_auth
        MobileBridgeHandler.max_payload_bytes = getattr(config.mobile_bridge, "max_payload_bytes", DEFAULT_MAX_PAYLOAD_BYTES)
        MobileBridgeHandler.rate_limit_per_minute = getattr(config.mobile_bridge, "rate_limit_per_minute", DEFAULT_RATE_LIMIT_PER_MIN)

    def rotate_auth_token(self) -> str:
        """Regenerates the pairing token immediately, invalidating previous sessions."""
        new_token = secrets.token_hex(8)
        self.auth_token = new_token
        MobileBridgeHandler.auth_token = new_token
        config.mobile_bridge.auth_token = new_token
        config.save()
        print(f"[MobileBridge] Neues Pairing-Token generiert: {new_token}")
        return new_token

    def _setup_ssl(self):
        """Wraps the socket with a local TLS certificate to provide a Secure Context for mobile mic APIs."""
        try:
            import ssl
            app_data = os.getenv("APPDATA") or os.path.expanduser("~")
            cert_dir = os.path.join(app_data, "Velodictum", "ssl")
            cert_file = os.path.join(cert_dir, "mobile_bridge.crt")
            key_file = os.path.join(cert_dir, "mobile_bridge.key")

            if not (os.path.exists(cert_file) and os.path.exists(key_file)):
                generate_self_signed_cert(cert_file, key_file, self.local_ip)

            if os.path.exists(cert_file) and os.path.exists(key_file):
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ctx.load_cert_chain(certfile=cert_file, keyfile=key_file)
                self.server.socket = ctx.wrap_socket(self.server.socket, server_side=True)
                self.is_https = True
        except Exception as e:
            print(f"[MobileBridge] TLS/HTTPS Setup Notice (falling back to HTTP): {e}")
            self.is_https = False

    def start(self):
        """Starts the mobile bridge HTTP/HTTPS server on a daemon background thread."""
        if self.thread and self.thread.is_alive():
            return
        try:
            self.server = http.server.ThreadingHTTPServer((self.bind_address, self.port), MobileBridgeHandler)
            if getattr(config.mobile_bridge, "use_https", True):
                self._setup_ssl()
            proto = "https" if getattr(self, "is_https", False) else "http"
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            print(f"[MobileBridge] Aktiv unter {proto}://{self.local_ip}:{self.port}/ (Pairing Token: {self.auth_token})")
        except Exception as e:
            print(f"[MobileBridge] Could not start server on port {self.port}: {e}")

    def stop(self):
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass
            self.server = None
            self.thread = None