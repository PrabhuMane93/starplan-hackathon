import os
import json
import requests
from openai import OpenAI
from typing import Optional, List
from pydantic import BaseModel
from search_vs import search_vector_store
from vendor import add_vendor

class IncorrectField(BaseModel):
    Field: str
    EOI_Value: Optional[str]  # Some fields may be empty in the EOI
    Contract_Value: Optional[str]  # null allowed when missing from contract


class ContractValidationModel(BaseModel):
    Contract_Validation: bool
    Incorrect_Fields: List[IncorrectField]

def upload_file_to_openai(client, file_path: str):
    with open(file_path, "rb") as f:
        uploaded = client.files.create(
            file=f,
            purpose="assistants"   # required for responses API
        )
    return uploaded.id

def contract_checker(state):
    print("\n📌 Detected contract email — activating CONTRACT CHECKER agent...\n")

    email = state["email"]


    attachments  = email.get("attachments")
    email_body   = email.get("body")
    vendor_email = email.get("from")

    client = OpenAI()

    for attachment in attachments:
        pdf_path = attachment

    # 1️⃣ Upload file first → get file_id
    file_id = upload_file_to_openai(client, pdf_path)
    os.remove(pdf_path)

    CONTRACT_CHECKER_PROMPT = """
You are a Contract Validation AI Agent working for OneCorp Australia. Your job is to compare Contract of Sale values against the correct values extracted from an Expression of Interest (EOI).

The EOI JSON below contains authoritative values:
---
{eoi_json}
---

Important Validation Rules (follow EXACTLY):

1. A mismatch MUST be reported **only if BOTH of the following are true**:
    a. The EOI field has a real, non-empty value  
       (meaning: NOT null, NOT "", NOT " ", NOT missing)  
    b. The Contract contains a value for the same field AND it conflicts with the EOI value.

2. If the EOI value is empty (null, "", or whitespace), then:
    - EVEN IF the contract contains a value → **IGNORE this field completely**  
    - It must NOT be included in Incorrect_Fields.

3. If the contract does not mention a field at all:
    - DO NOT count it as a mismatch (missing contract fields are allowed).

4. Subtle contradictions MUST still be flagged.
   Example:
   EOI Finance_Terms = "Not Subject to Finance"
   Contract clause implies responsibility for securing finance approval.
   → Treat this as a mismatch in Finance_Terms.

5. Only detect mismatches for fields appearing in BOTH:
    - EOI has a real value
    - Contract explicitly states a different value

6. NEVER output mismatches where:
    - EOI value is empty/null  
    - EOI value is missing  
    - Contract has additional details not present in EOI  

### Extract from the contract:
- Purchaser Names
- Purchaser Emails
- Purchaser Mobiles
- Residential Address (if present)
- Lot Number
- Property Address
- Project Name
- Total Price
- Land Price
- Build Price
- Finance Terms
- Solicitor Name
- Solicitor Email
- Finance Provider (optional)

Then apply the rules above.

### OUTPUT FORMAT (strict)

Return ONLY this JSON:

{{
  "Contract_Validation": <true_or_false>,
  "Incorrect_Fields": [
      {{
        "Field": "<Field_Name>",
        "EOI_Value": "<Value_From_EOI>",
        "Contract_Value": "<Value_From_Contract>"
      }}
  ]
}}

Rules:
- If **no mismatches** exist → return:
{{
  "Contract_Validation": true,
  "Incorrect_Fields": []
}}

- Otherwise:
{{
  "Contract_Validation": false,
  "Incorrect_Fields": [...]
}}

- Do NOT include fields where EOI_Value was empty/null.
- Do NOT include fields missing in the contract.
- No explanations, no markdown, no comments.
    """


    eoi_json = search_vector_store(email_body)
    prompt = CONTRACT_CHECKER_PROMPT.format(eoi_json=eoi_json)

    print("🤖 Validating Contract of Sale against EOI values...")

    # Persisting Vendor
    add_vendor(eoi_json["Property_Address"],vendor_email)

    # 2️⃣ Reference the file via file_id in the input
    response = client.responses.parse(
        model="gpt-4.1",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_file", "file_id": file_id}
                ]
            }
        ],
        text_format=ContractValidationModel  # Pydantic automatic validation!
    )

    response = json.loads(response.output_text)
    print("📥 Contract validation complete.")

    purchasers = ""
    for i in eoi_json["Purchaser"]:
        purchasers += f"{i['First_Name']} {i['Last_Name']} & "
    purchasers = purchasers.rstrip(" & ")
    address = eoi_json["Property_Address"]

    if response["Contract_Validation"]:

        print("✅ Contract matches EOI — no discrepancies found.")
        print("📧 Sending approval email to solicitor...")

        # Generate solicitor email
        subject = f"Contract of Sale Validated Successfully for {purchasers} - {address}"
        body = f"""
Hi {eoi_json['Solicitor_Name']},

Please find attached the contract for {purchasers} for your review.

Let us know if you have any questions.

Kind regards,
OneCorp"""
        to_email = eoi_json["Solicitor_Email"]

        API_URL = "http://localhost:4000/send-email"

        payload = {
            "recipient": to_email,
            "subject": subject,
            "body": body
        }

        requests.post(API_URL, json=payload)
        print("📤 Solicitor notified successfully.\n")

    else:
        print("⚠️ Contains discrepancies, contract corrupted — preparing revision request email...")
        # Construct revision email to Vendor and internal team
        incorrect_fields = ""
        for field in response["Incorrect_Fields"]:
            incorrect_fields += f"- {field['Field']}: EOI Value = '{field['EOI_Value']}', Contract Value ='{field['Contract_Value']}'\n"
        subject = f"Contract of Sale Discrepancies for {purchasers} - {address}"
        body = f"""
Greetings,
We have reviewed the Contract of Sale for {purchasers} regarding the property at {address}. During validation, we identified the following discrepancies compared to the purchasers’ Expression of Interest: \n
{incorrect_fields}       
Could you please review and issue an updated contract addressing the items above?

Let us know once the corrected version is ready for validation.

Regards,
OneCorp Support Team"""
        to_email = vendor_email
        to_email_internal = "myvostro925@gmail.com"

        API_URL = "http://localhost:4000/send-email"

        payload_1 = {
            "recipient": to_email,
            "subject": subject,
            "body": body
        }

        payload_2 = {
            "recipient": to_email_internal,
            "subject": subject,
            "body": body
        }

        requests.post(API_URL, json=payload_1)
        print("📧 Sending discrepancy report to vendor:", vendor_email)
        requests.post(API_URL, json=payload_2)
        print("📧 Sending internal notification...")
    print("🎯 Contract Validator AGENT complete.\n")
    return state



