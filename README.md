# waservix

**WAservix WhatsApp API Gateway** - official Python client: send WhatsApp messages from your own number. By Tekservix.

Python client for the [WAservix WhatsApp API Gateway](https://tekservix.com/waservix/).

WAservix links your own WhatsApp number by QR code (the same way WhatsApp Web does) and gives you a REST API to send text, images, video, audio, documents, locations, polls and more, with webhooks for incoming messages and status updates.

- Zero dependencies (standard library only), Python 3.8+
- Works in Django, Flask, FastAPI, scripts and cron jobs
- Webhook check built in

## Install

```bash
pip install waservix
```

## Quick start

Copy your device's API key from the WAservix dashboard (Devices -> API key) and keep it on your server.

```python
import os
from waservix import WAservix

wa = WAservix(api_key=os.environ["WASERVIX_KEY"])

result = wa.send_text("+15551234567", "Hello Aline, your order is ready")
print(result["msgId"], result["status"])  # 58213 in_progress
```

## Sending

Messages are queued and sent one at a time per number, so each call returns right away with `status: "in_progress"` and a `msgId`.

```python
# Image with caption
wa.send_image("+15551234567", "https://example.com/product.jpg", caption="Back in stock")

# Document
wa.send_document("+15551234567", "https://example.com/inv-1042.pdf",
                 file_name="Invoice-1042.pdf", caption="Your invoice")

# Anything the API supports, including groups (JID ending in @g.us)
wa.send_message("120363040000000000@g.us", text="Team meeting at 3pm")
wa.send_message("+15551234567", location={"latitude": -1.9441, "longitude": 30.0619, "name": "Our shop"})
```

## Status, contacts and groups

```python
info = wa.get_message_info(58213)      # queued, sent, delivered, read, played or failed
check = wa.on_whatsapp("+15551234567")  # {"exists": True, "jid": "..."}
conn = wa.get_status()                  # {"status": "connected"}

wa.edit_message(58213, "Corrected text")  # own text messages, about 15 minutes
groups = wa.list_groups()
```

Anything else in the [API reference](https://tekservix.com/waservix/docs/) is one call away:

```python
wa.request("POST", "/messages/read", {"msgId": "3EB0X123456789"})
```

## Webhooks

Set a webhook URL and events for the number in the dashboard. Each request carries `X-Webhook-Signature`, which equals the device's webhook secret. Flask example:

```python
import os
from flask import Flask, request, abort
from waservix import verify_webhook

app = Flask(__name__)

@app.post("/wa/webhook")
def wa_webhook():
    if not verify_webhook(request.headers.get("X-Webhook-Signature"), os.environ["WASERVIX_WEBHOOK_SECRET"]):
        abort(401)
    payload = request.get_json()
    if payload["event"] == "messages.received":
        m = payload["data"]["messages"]
        print(m["key"]["cleanedSenderPn"], m["messageBody"])
    return "", 200  # acknowledge fast; queue slow work
```

## Errors

Failed calls raise `WAservixError` with `status`, `message`, field `errors` and, on 429, `retry_after` in seconds. A 503 means the device is reconnecting: retry shortly.

Never ship the key inside a browser or mobile app: anyone could read it. Call the API from your server.

## Migrating from WaSender

WAservix accepts the same `/send-message` body and webhook fields as WaSender, so most integrations switch by changing the base URL and key. See the [compatibility notes](https://tekservix.com/waservix/docs/).

## Use it responsibly

WAservix is not Meta's official WhatsApp Business Platform. There's no business verification and no per-conversation fee, but WhatsApp's spam rules apply to your number directly. Message people who expect to hear from you, warm up new numbers slowly and keep the built-in account protection on.

## More from Tekservix

- [SMS Gora SMS Gateway](https://tekservix.com/smsgora/): send SMS through your own Android phones (`pip install smsgora`)
- [AI Sales Agent](https://tekservix.com/ai-sales-agent): answers customers on WhatsApp and SMS using your website's content
- [Website to App](https://tekservix.com/mobile-apps): turn your website into Android and iOS apps
- Also on npm: `npm install waservix`

## License

MIT
