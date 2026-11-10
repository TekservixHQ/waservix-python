"""Python client for the WAservix WhatsApp API Gateway.

Docs: https://tekservix.com/waservix/docs/
"""

import hmac
import json
import urllib.error
import urllib.parse
import urllib.request

__all__ = ["WAservix", "WAservixError", "verify_webhook"]
__version__ = "1.0.0"

DEFAULT_BASE_URL = "https://tekservix.com/waservix/api"


class WAservixError(Exception):
    """Raised when the API answers with an error.

    Attributes: status (HTTP code), errors (field errors), body (parsed answer)
    and retry_after (seconds, on 429). A 503 means the device is reconnecting.
    """

    def __init__(self, message, status=None, errors=None, body=None, retry_after=None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.errors = errors
        self.body = body
        self.retry_after = retry_after


def _q(value):
    return urllib.parse.quote(str(value), safe="")


class WAservix:
    """Client for the WAservix WhatsApp API Gateway.

    >>> wa = WAservix(api_key="wpk_...")
    >>> wa.send_text("+15551234567", "Hello Aline, your order is ready")
    """

    def __init__(self, api_key, base_url=DEFAULT_BASE_URL, timeout=30):
        if not api_key:
            raise ValueError("WAservix: api_key is required (Devices -> API key in the WAservix dashboard)")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(self, method, path, body=None):
        """Call any documented endpoint, e.g. request("GET", "/groups"). Returns the `data` field."""
        headers = {
            "Authorization": "Bearer " + self.api_key,
            "Accept": "application/json",
            "User-Agent": "waservix-python/" + __version__,
        }
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                status, text, retry = res.status, res.read().decode("utf-8"), None
        except urllib.error.HTTPError as err:
            status, text = err.code, err.read().decode("utf-8", "replace")
            retry = err.headers.get("Retry-After") if err.headers else None
        try:
            parsed = json.loads(text) if text else None
        except ValueError:
            parsed = None
        failed = status >= 400 or (isinstance(parsed, dict) and parsed.get("success") is False)
        if failed:
            msg = parsed.get("message") if isinstance(parsed, dict) else None
            raise WAservixError(
                msg or "HTTP %d" % status,
                status=status,
                errors=parsed.get("errors") if isinstance(parsed, dict) else None,
                body=parsed if parsed is not None else text,
                retry_after=float(retry) if retry else None,
            )
        if isinstance(parsed, dict) and "data" in parsed:
            return parsed["data"]
        return parsed

    # Sending

    def send_message(self, to, **fields):
        """Send any message type to a number or group JID (...@g.us).

        Fields use the API names: text, imageUrl, videoUrl, audioUrl, documentUrl,
        fileName, stickerUrl, contact, location, poll, replyTo, mentions, viewOnce.
        Returns {"msgId": ..., "jid": ..., "status": "in_progress"}.
        """
        if not to:
            raise ValueError('send_message: "to" is required (international number or group JID)')
        body = {"to": to}
        body.update({k: v for k, v in fields.items() if v is not None})
        return self.request("POST", "/send-message", body)

    def send_text(self, to, text):
        return self.send_message(to, text=text)

    def send_image(self, to, image_url, caption=None):
        return self.send_message(to, imageUrl=image_url, text=caption)

    def send_document(self, to, document_url, file_name=None, caption=None):
        return self.send_message(to, documentUrl=document_url, fileName=file_name, text=caption)

    # Messages

    def get_message_info(self, msg_id):
        """Status: queued, sent, delivered, read, played or failed."""
        return self.request("GET", "/messages/%s/info" % _q(msg_id))

    def edit_message(self, msg_id, text):
        return self.request("PUT", "/messages/%s" % _q(msg_id), {"text": text})

    def delete_message(self, msg_id):
        return self.request("DELETE", "/messages/%s" % _q(msg_id))

    def resend_message(self, msg_id):
        return self.request("POST", "/messages/%s/resend" % _q(msg_id))

    # Account, contacts and groups

    def on_whatsapp(self, phone):
        """Is this number on WhatsApp? Returns {"exists": bool, "jid": ...}."""
        return self.request("GET", "/on-whatsapp/%s" % _q(phone))

    def get_status(self):
        """connected, connecting, need_scan, disconnected, logged_out or expired."""
        return self.request("GET", "/status")

    def get_user(self):
        return self.request("GET", "/user")

    def list_contacts(self):
        return self.request("GET", "/contacts")

    def get_contact(self, phone):
        return self.request("GET", "/contacts/%s" % _q(phone))

    def save_contact(self, phone, name):
        return self.request("PUT", "/contacts", {"phone": phone, "name": name})

    def list_groups(self):
        return self.request("GET", "/groups")

    def get_group_metadata(self, group_jid):
        return self.request("GET", "/groups/%s/metadata" % _q(group_jid))

    # Sessions (need a personal access token, not a device key)

    def list_sessions(self):
        return self.request("GET", "/whatsapp-sessions")

    def get_session(self, session_id):
        return self.request("GET", "/whatsapp-sessions/%s" % _q(session_id))

    def create_session(self, **params):
        return self.request("POST", "/whatsapp-sessions", params)

    def connect_session(self, session_id, method="qr", phone=None):
        body = {"method": method}
        if phone:
            body["phone"] = phone
        return self.request("POST", "/whatsapp-sessions/%s/connect" % _q(session_id), body)

    def get_session_qr_code(self, session_id):
        return self.request("GET", "/whatsapp-sessions/%s/qrcode" % _q(session_id))


def verify_webhook(signature, secret):
    """Constant-time check of the X-Webhook-Signature header against your device's webhook secret."""
    if not signature or not secret:
        return False
    return hmac.compare_digest(str(signature).encode("utf-8"), str(secret).encode("utf-8"))
