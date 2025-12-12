# Azure Configuration Guide

## 1. Create App Registration
1. Go to https://portal.azure.com  
2. Search: **Microsoft Entra ID**  
3. Select **App registrations**  
4. Click **New registration**

### Registration Settings
- **Name:** WisyPlan Outlook Integration  
- **Supported account types:**  
  **Accounts in any organizational directory and personal Microsoft accounts**  
- **Redirect URI (Web):**  
http://localhost:3000/callback

- Click **Register**

---

## 2. Get App Credentials
1. Go to **Overview**  
2. Copy and Store **Application (client) ID**  

---

## 3. Create Client Secret
1. Go to **Certificates & secrets**  
2. Click **New client secret**  
3. Choose an expiry  
4. Click **Add**  
5. Copy and Store the **secret value**

---

## 4. Configure API Permissions
1. Go to **API permissions**  
2. Click **Add a permission**  
3. Select **Microsoft Graph**  
4. Choose **Delegated permissions**  
5. Add the following:
 - `openid`
 - `email`
 - `profile`
 - `offline_access`
 - `Mail.Read`
 - `IMAP.AccessAsUser.All`
6. Click **Grant admin consent**