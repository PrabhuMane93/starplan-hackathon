# 🚀 Setup Instructions

## 1. Configure Azure App
Refer to **azure_app_setup.md** and obtain:
- `CLIENT_ID`
- `CLIENT_SECRET`

## 2. Configure Ngrok
Refer to **ngrok_setup.md** and obtain:
- Assigned **Ngrok Public URL**

## 3. Create `.env` File
Run the following command (replace placeholders):

```bash
echo "CLIENT_ID=YOUR_CLIENT_ID_HERE
CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE
SECRET_KEY=supersecret
REDIRECT_URI=http://localhost:3000/callback
NGROK_URL=YOUR_NGROK_URL_HERE/webhook" > .env
```


## 4. Start OAuth Login App
```bash
uvicorn login_app:app --reload --port 3000
```

## 5. Start Webhook Listener Service
```bash
uvicorn webhook:app --reload --port 4000
```

## 6. Bind Webhook to Ngrok
```bash
ngrok http 4000
```

# 🧪 Test Instructions
1. Visit:
```bash
http://localhost:3000
```
2. Sign in with any Outlook (Microsoft) account.

3. Send a test email to the **signed-in account**.

4. Check the webhook server terminal — the email event should appear there.

**🎉 Setup complete! Your email automation service is now live.**