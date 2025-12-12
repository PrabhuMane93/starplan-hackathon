import json
import requests

from openai import OpenAI
from datetime import datetime
from pydantic import BaseModel
from search_vs import search_vector_store
from vendor import get_vendor

class SigningAppointment(BaseModel):
    appointment_datetime: str   # "dd-mm-yyyy HH:MM"
    reminder_datetime: str      # "dd-mm-yyyy HH:MM"

def signing_agent(state):
    print("\n🖊️ Detected signing-status email — activating SIGNING AGENT...\n")
    email = state["email"]
    # Extract appointment date and set reminder
    client = OpenAI()

    print("📩 Extracting appointment date and reminder from signing email...")
    APPOINTMENT_EXTRACTOR_PROMPT = """
    You are a date-reasoning AI assistant. You will receive an email from a solicitor regarding a signing appointment.

    Your tasks:

    1. Identify the signing appointment date AND time from the email.
    - The date may be described naturally (e.g., “Thursday at 11:30am”).
    - Use the CURRENT LOCAL DATE: {current_date}
    - The user is in the Australia/Melbourne timezone (AEDT/AEST).
    - Convert the appointment into a full datetime in AEDT/AEST.
    - Format the final appointment datetime as: dd-mm-yyyy HH:MM.
    - If the email does not specify a time, default to 09:00 local time.

    2. Compute a reminder datetime:
    - appointment date + 2 days
    - time = 09:00 local time
    - Format as dd-mm-yyyy HH:MM.

    3. Return ONLY this JSON:

    {{
    "appointment_datetime_aedt": "<dd-mm-yyyy HH:MM>",
    "reminder_datetime_aedt": "<dd-mm-yyyy HH:MM>"
    }}

    Rules:
    - No UTC conversion — all dates must remain in Melbourne local time.
    - No seconds.
    - No markdown or explanations.
    - Output ONLY valid JSON.

    Here is the email:
    ---
    {email_body}
    ---
    """

    current_date = datetime.now().strftime("%d-%m-%Y")
    prompt = APPOINTMENT_EXTRACTOR_PROMPT.format(
        current_date=current_date,
        email_body=email
    )

    response = client.responses.parse(
        model="gpt-4.1",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                ]
            }
        ],
        text_format=SigningAppointment  # Pydantic automatic validation!
    )

    print("📅 Appointment extracted successfully.")
    response = json.loads(response.output_text)
    eoi_json = search_vector_store(email)
    
    print("🔎 Retrieved EOI from vectorstore for appointment association...")

    response["Property_Address"] = eoi_json["Property_Address"]
    response["Purchaser"] = eoi_json["Purchaser"]

    filename = "deadlines/" + response["Property_Address"] + ".json"

    with open(filename, "w") as f:
        json.dump(response, f, indent=4)


    address = eoi_json["Property_Address"]
    purchasers = ""
    for i in eoi_json["Purchaser"]:
        purchasers += f"{i['First_Name']} {i['Last_Name']} & "
    purchasers = purchasers.rstrip(" & ")

    # Design Contract Release Email
    email = f"""
Hi,

The solicitor has approved the contract for {purchasers}.
Could you please release the contract via DocuSign for purchaser signing?

Thanks,
OneCorp
"""
    subject      = f"Contract Request: {address}"
    vendor_email = get_vendor(eoi_json["Property_Address"])

    API_URL = "http://localhost:4000/send-email"

    payload = {
        "recipient": vendor_email,
        "subject": subject,
        "body": email
    }

    requests.post(API_URL, json=payload)
    print("📤 Vendor notified to release contract via DocuSign.")
    return state

