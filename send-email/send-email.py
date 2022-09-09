import time
from azure.communication.email import EmailClient, EmailContent, EmailAddress, EmailMessage, EmailRecipients

def main():
    try:
        connection_string = "<ACS_CONNECTION_STRING>"
        client = EmailClient.from_connection_string(connection_string)
        sender = "<SENDER_EMAIL>"
        content = EmailContent(
            subject="Test email from Python",
            plain_text="This is plaintext body of test email.",
            html= "<html><h1>This is the html body of test email.</h1></html>",
        )

        recipient = EmailAddress(email="<RECIPIENT_EMAIL>", display_name="<RECIPIENT_DISPLAY_NAME>")

        message = EmailMessage(
            sender=sender,
            content=content,
            recipients=EmailRecipients(to=[recipient])
        )

        response = client.send(message)
        if (not response or response.message_id=='undefined' or response.message_id==''):
            print("Message Id not found.")
        else:
            print("Send email succeeded for message_id :"+ response.message_id)
            message_id = response.message_id
            counter = 0
            while True:
                counter+=1
                send_status = client.get_send_status(message_id)

                if (send_status):
                    print(f"Email status for message_id {message_id} is {send_status.status}.")
                if (send_status.status.lower() == "queued" and counter < 12):
                    time.sleep(10)  # wait for 10 seconds before checking next time.
                    counter +=1
                else:
                    if(send_status.status.lower() == "outfordelivery"):
                        print(f"Email delivered for message_id {message_id}.")
                        break
                    else:
                        print("Looks like we timed out for checking email send status.")
                        break

    except Exception as ex:
        print(ex)
main()
