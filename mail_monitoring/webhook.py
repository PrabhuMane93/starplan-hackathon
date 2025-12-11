import os
import re
import requests
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response
from typing import Optional, List
from pydantic import BaseModel
from dotenv import load_dotenv, set_key
import uvicorn
from cachetools import TTLCache
from convert_document import save_pdf_from_content_bytes

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

NGROK_URL = os.getenv("NGROK_URL")
WEBHOOK_URL = "https://valarie-keratoplastic-fissiparously.ngrok-free.dev/webhook"

app = FastAPI()
processed_messages = TTLCache(maxsize=1000, ttl=600)  # store for 10 minutes

# -----------------------------------
# REFRESH TOKENS
# -----------------------------------
def refresh_tokens():
    global ACCESS_TOKEN, REFRESH_TOKEN

    url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid email profile offline_access Mail.Read Mail.Send IMAP.AccessAsUser.All",
    }

    resp = requests.post(url, data=data).json()
    # print("REFRESH:", resp)

    if "access_token" not in resp:
        print("❌ Refresh failed")
        return False

    ACCESS_TOKEN = resp["access_token"]
    REFRESH_TOKEN = resp["refresh_token"]

    set_key(".env", "ACCESS_TOKEN", ACCESS_TOKEN)
    set_key(".env", "REFRESH_TOKEN", REFRESH_TOKEN)

    print("🔄 Tokens refreshed")
    return True

# -----------------------------------
# SUBSCRIBE
# -----------------------------------
@app.get("/subscribe")
def subscribe():
    expiration = (datetime.utcnow() + timedelta(minutes=4210)).isoformat() + "Z"

    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    payload = {
        "changeType": "created",
        "notificationUrl": WEBHOOK_URL,
        "resource": "me/mailFolders('inbox')/messages",
        "expirationDateTime": expiration,
        "clientState": "secret123",
    }

    url = "https://graph.microsoft.com/v1.0/subscriptions"
    r = requests.post(url, json=payload, headers=headers)
    data = r.json()
    print("SUB RESPONSE:", data)

    if data.get("error"):
        if refresh_tokens():
            headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
            r2 = requests.post(url, json=payload, headers=headers)
            print("SUB AFTER REFRESH:", r2.json())
            return r2.json()

    return data

# -----------------------------------
# WEBHOOK
# -----------------------------------
@app.api_route("/webhook", methods=["GET", "POST"])
async def webhook(request: Request):

    # --- VALIDATION HANDLING ---
    validation = request.query_params.get("validationToken")
    if validation:
        print("🔵 VALIDATION (GET):", validation)
        return Response(content=validation, media_type="text/plain")

    try:
        body = await request.json()
    except:
        body = {}

    # JSON validation token case
    if "validationToken" in body:
        return Response(content=body["validationToken"], media_type="text/plain")

    print("\n📩 EVENT:", body)

    # --- PROCESS NOTIFICATIONS ---
    try:
        message_id = body["value"][0]["resourceData"]["id"]

        # 🛑 DEDUPE: skip if already processed
        if message_id in processed_messages:
            print(f"⚠️ Duplicate notification ignored: {message_id}")
            return {"status": "duplicate"}

        processed_messages[message_id] = True  # mark as processed

        # --- FETCH EMAIL CONTENT ---
        email = fetch_email(message_id)
        payload = {
            "body": email['body'],
            "subject": email['subject'],
            "to_email": email['recipient_email'],
            "from_email": email['sender_email'],
            "attachments": email['attachments']
        }
        resp = requests.post("http://localhost:2000/incoming-email", json=payload)

  
        # send_email(
        #     access_token=ACCESS_TOKEN,
        #     recipient=email['sender_email'],
        #     subject="RE: " + email['subject'],
        #     body=reply
        # )

    except Exception as e:
        print("⚠️ Parsing error:", e)

    return {"status": "ok"}


# -----------------------------------
# FETCH EMAIL
# -----------------------------------
def fetch_email(message_id):
    url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

    r = requests.get(url, headers=headers)
    data = r.json()
    # Extract fields safely
    subject = data.get("subject", "")
    body_html = data.get("body", {}).get("content", "")
    sender_email = data.get("from", {}).get("emailAddress", {}).get("address", "")
    recipient_email = (
        data.get("toRecipients", [{}])[0]
        .get("emailAddress", {})
        .get("address", "")
    )
    received_time = data.get("receivedDateTime", "")

    # Strip HTML from the body (optional)
    body_text = re.sub(r"<.*?>", "", body_html).strip()

    # Handle attachments if needed
    attachments_list = []
    if data.get("hasAttachments"):
        url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}/attachments"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        attachments = data.get("value")
        for attachment in attachments:
            save_pdf_from_content_bytes(attachment['name'], attachment['contentBytes'])
            attachments_list.append(f"data/{attachment['name']}")


    summary = {
        "subject": subject,
        "body": body_text,
        "sender_email": sender_email,
        "recipient_email": recipient_email,
        "received_time": received_time,
        "attachments": attachments_list
    }
    # print(attachments)
    print("\n📨 CLEAN EMAIL DATA:", summary)
    return summary



# -----------------------------------
# SEND EMAIL
# -----------------------------------
class SendEmailRequest(BaseModel):
    recipient: str
    cc: Optional[List[str]] = None
    subject: str
    body: str

@app.post("/send-email")
def send_email_route(payload: SendEmailRequest):
    url = "https://graph.microsoft.com/v1.0/me/sendMail"

    # Convert text newlines to HTML <br>
    html_body = payload.body.replace("\n", "<br>")

    # Build message
    email_msg = {
        "message": {
            "subject": payload.subject,
            "body": {
                "contentType": "HTML",
                "content": html_body
            },
            "toRecipients": [
                {"emailAddress": {"address": payload.recipient}}
            ]
        },
        "saveToSentItems": "true"
    }

    # --------------------------------------------
    # Add CC recipients only if provided
    # --------------------------------------------
    if payload.cc:
        email_msg["message"]["ccRecipients"] = [
            {"emailAddress": {"address": cc_addr}}
            for cc_addr in payload.cc
        ]

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    r = requests.post(url, headers=headers, json=email_msg)

    if r.status_code == 202:
        return {"status": "success", "detail": "Email sent successfully."}

    raise HTTPException(
        status_code=r.status_code,
        detail={"error": "Failed to send email", "response": r.text}
    )


if __name__ == "__main__":
    print("Backend service running at http://localhost:4000")
    uvicorn.run(app, host="0.0.0.0", port=4000)
