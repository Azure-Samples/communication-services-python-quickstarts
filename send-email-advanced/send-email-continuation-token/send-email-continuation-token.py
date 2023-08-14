from azure.communication.email import EmailClient

connection_string = "<ACS_CONNECTION_STRING>"
sender_address = "<SENDER_EMAIL_ADDRESS>"
recipient_address = "<RECIPIENT_EMAIL_ADDRESS>"

POLLER_WAIT_TIME = 10
MAX_POLLS = 18

message = {
    "senderAddress": sender_address,
    "recipients":  {
        "to": [{"address": recipient_address}],
    },
    "content": {
        "subject": "Test email from Python Sample",
        "plainText": "This is plaintext body of test email.",
        "html": "<html><h1>This is the html body of test email.</h1></html>",
    }
}

try:
    client = EmailClient.from_connection_string(connection_string)
    poller = client.begin_send(message);

    # Pauses operation and saves state that can be used later to resume operation
    token = poller.continuation_token()

    # Additional processing can be done here between pausing and resuming the operation

    new_client = EmailClient.from_connection_string(connection_string);
    new_poller = new_client.begin_send(message, continuation_token=token);

    time_elapsed = 0
    while not new_poller.done():
        print("Email send poller status: " + new_poller.status())

        new_poller.wait(POLLER_WAIT_TIME)
        time_elapsed += POLLER_WAIT_TIME

        if time_elapsed > MAX_POLLS * POLLER_WAIT_TIME:
            raise RuntimeError("Polling timed out.")

    if new_poller.result()["status"] == "Succeeded":
        print(f"Successfully sent the email (operation id: {new_poller.result()['id']})")
    else:
        raise RuntimeError(str(new_poller.result()["error"]))
    
except Exception as ex:
    print(ex)
