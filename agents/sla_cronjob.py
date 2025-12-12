import os
import datetime
import requests
import json
from datetime import datetime
from zoneinfo import ZoneInfo

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def run_sla_check():
    """
    Runs daily at 9 AM AEDT via cron.
    For each JSON file, compare reminder date to today's date.
    If today's date matches, trigger an alert and delete the JSON file.
    """
    today = datetime.now(ZoneInfo("Australia/Melbourne")).strftime("%d-%m-%Y")
    DEADLINES_DIR = "deadlines"
    for file in os.listdir(DEADLINES_DIR):

        path = os.path.join(DEADLINES_DIR, file)
        data = load_json(path)
        reminder_full = data["reminder_datetime"]  
        reminder_date = reminder_full.split(" ")[0]  # Extract only dd-mm-yyyy

        if reminder_date == today:
            property_address = data.get("Property_Address")
            appointment_datetime = data.get("appointment_datetime")
            purchasers = ", ".join([f"{p['First_Name']} {p['Last_Name']}" for p in data.get("Purchaser")])

            subject = f"SLA Alert: Contract Not Signed by {reminder_date} for {purchasers} - {property_address}"
            email_body = f"""
Hi Team,

This is an automated SLA alert from the contract workflow.

The clients have not signed the Contract of Sale by the follow-up date.

Details:
- Purchasers: {purchasers}
- Property: {property_address}
- Signing Appointment: {appointment_datetime}
- Follow-up / SLA Date: {reminder_full}

Recommended actions:
1. Contact the solicitor to confirm the current signing status.
2. Follow up with the purchasers if needed.
3. Update the CRM / tracking system with any new information.

Please action this as soon as practical.

Regards,
OneCorp Contract Automation
support@onecorpaustralia.com.au
            """
            
            API_URL = "http://localhost:4000/send-email"

            payload = {
                "recipient": "dr.prabhumane@gmail.com",
                "subject": subject,
                "body": email_body
            }

            requests.post(API_URL, json=payload)

            # sending email logic would go here
            print(f"🗑 Deleting: {file}")
            os.remove(path)
