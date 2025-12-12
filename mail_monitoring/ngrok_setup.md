# Ngrok Setup Instructions

## 1. Install Ngrok

### **macOS**
```bash
brew install ngrok/ngrok/ngrok
```
### **Windows**
- Download ZIP from: https://ngrok.com/download
- Extract ZIP
- Move ngrok.exe in this directory

## 2. Authenticate Ngrok
- Go to: https://dashboard.ngrok.com/get-started/your-authtoken
- Copy your Auth Token
- Run the following command:
```bash
ngrok config add-authtoken YOUR_AUTHTOKEN_HERE
```

## 3. Start an HTTP Tunnel- Run the following command:
```bash
ngrok http 3000
```

## 4. Copy the Assigned Public URL
Copy and Store the HTTPS URL shown under Forwarding, for example: **https://xxxxx.ngrok-free.dev** and stop the ngrok HTTP Tunnel on 3000.