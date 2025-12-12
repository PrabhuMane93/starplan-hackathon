import os
import json
from openai import OpenAI



def sla_check(state):
    print("\n📨 Detected DocuSign completion email — activating SLA AGENT...\n")
    client = OpenAI()
    email = state["email"]
    email_body   = email.get("body")

    print("🔍 Extracting property details from signing-completion email...")
    DELETING_PROMPT = """
You are a Contract Completion Agent for OneCorp Australia.

Your job:
You will receive:
1) A DocuSign system email that mentions a contract signing event.
2) A list of JSON filenames currently in the deadlines directory.

ANY signing event (buyer only or fully executed) means we should stop tracking the deadline for that property.

Your task:
From the email, identify which JSON file in the list corresponds to the property mentioned in the email.

Important details about filenames:
- Filenames are the property address with ".json" at the end.
- They usually do NOT include the word "Lot" or the lot number.
- Example:
- Email text: "Document: Contract of Sale – Lot 95 Fake Rise VIC 3336"
- Filename: "Fake Rise VIC 3336.json"

Matching rules (follow these carefully):
1. Find the line in the email that starts with or contains "Document:" or clearly names the contract.
Example: "Document: Contract of Sale – Lot 95 Fake Rise VIC 3336"

2. From that line, extract the **core property string** by:
- Removing leading labels like "Document:", "Contract of Sale –", "Contract of Sale -"
- Removing the "Lot <number>" prefix if present (e.g., "Lot 95 ")
- Trimming spaces
In the example above, the core property string becomes: "Fake Rise VIC 3336"

3. Normalise for comparison:
- Lowercase everything
- Ignore double spaces and punctuation like "–", "-", ":"
- Do NOT include ".json" during comparison

4. For each filename in the list:
- Remove the ".json" suffix
- Lowercase the remaining text
- Compare it to the core property string.
- If the core property string appears to clearly match the filename text (same street, state, and postcode), select that filename.

5. If there is a clear, single best match, return that filename.
6. If there is no good match, or more than one plausible match, return null.

Output format (always JSON):

{
"delete_filename": "<filename or null>"
}

Very important:
- Prefer an exact match on the full "Street Name + State + Postcode" segment.
- In this specific example:
- Email document: "Contract of Sale – Lot 95 Fake Rise VIC 3336"
- Filenames: "44 Pineview Crescent VIC 3977.json", "Fake Set VIC 3336.json", "12 Rivergum Road NSW 2259.json", "Fake Rise VIC 3336.json"
- The correct result MUST be:
{
    "delete_filename": "Fake Rise VIC 3336.json"
}

Now, using these rules, process the given email and filename list.
    """

    DEADLINES_DIR = "deadlines"

    email_prompt = "DocuSign System Email is as follows: \n" + email_body + "\n\n"
    # Get filenames
    filenames = [
        f for f in os.listdir(DEADLINES_DIR)
        if f.endswith(".json")
    ]

    filenames_string = "Filenames are as follows: \n"
    # Convert to: "file1.json", "file2.json", "file3.json"
    filenames_string = filenames_string + ", ".join(f'"{name}"' for name in filenames)


    response = client.chat.completions.create(
        model="gpt-4.1-mini",   # or your preferred model
        messages=[
            {"role": "system", "content": DELETING_PROMPT},
            {"role": "user", "content": email_prompt + filenames_string}
        ],
        temperature=0.2
    )

    filename = json.loads(response.choices[0].message.content)["delete_filename"]
    if filename!= None:
        path = os.path.join(DEADLINES_DIR, filename)
        print(f"🗑 Deleting: {filename}")
        print("CONTRACT PROCESSED SUCCESSFULLY!!!!!")
        os.remove(path)
    else:
        print("⭕ No matching deadline file identified — nothing to delete.")

    print("🎯 SLA AGENT complete.\n")
    return state