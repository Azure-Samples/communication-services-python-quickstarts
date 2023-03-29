import base64
from azure.communication.email import EmailClient

with open("./attachment.pdf", "rb") as file:
    pdf_b64encoded = base64.b64encode(file.read())

with open("./attachment.txt", "rb") as file:
    txt_b64encoded = base64.b64encode(file.read())

connection_string = "<ACS_CONNECTION_STRING>"
sender_address = "<SENDER_EMAIL_ADDRESS>"
recipient_address = "<RECIPIENT_EMAIL_ADDRESS>"

POLLER_WAIT_TIME = 10

message = {
    "senderAddress": sender_address,
    "recipients":  {
        "to": [{ "address": recipient_address }]
    },
    "content": {
        "subject": "Test email from Python Sample",
        "plainText": "This is plaintext body of test email.",
        "html": "<html><h1>This is the html body of test email.</h1></html>"
    },
    "attachments": [
        {
            "name": "attachment.pdf",
            "contentType": "application/pdf",
            "contentInBase64": pdf_b64encoded.decode()
        },
        {
            "name": "attachment.txt",
            "contentType": "text/plain",
            "contentInBase64": txt_b64encoded.decode()
        }
    ]
}

try:
    client = EmailClient.from_connection_string(connection_string)

    poller = client.begin_send(message);

    time_elapsed = 0
    while not poller.done():
        print("Email send poller status: " + poller.status())

        poller.wait(POLLER_WAIT_TIME)
        time_elapsed += POLLER_WAIT_TIME

        if time_elapsed > 18 * POLLER_WAIT_TIME:
            raise RuntimeError("Polling timed out.")

    if poller.result()["status"] == "Succeeded":
        print(f"Successfully sent the email (operation id: {poller.result()['id']})")
    else:
        raise RuntimeError(str(poller.result()["error"]))
    
except Exception as ex:
    print(ex)
