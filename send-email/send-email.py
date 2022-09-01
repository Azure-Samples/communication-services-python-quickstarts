from azure.communication.email import EmailClient, EmailContent,EmailAddress,EmailMessage,EmailRecipients
import time
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
        if (response == None or response.message_id=='undfined' or response.message_id==''):
            print("Message Id not found.")
        else:  
            print("Send email succeed MessageId :"+ response.message_id)
            messageId = response.message_id
            counter = 0
            time.sleep(20) # wait max 20 seconds to check the send status for mail.
            while True:
                counter+=1
                sendStatus = client.get_send_status(messageId)

                if (sendStatus):
                   print("Email status for messageId %s is %s" %(messageId,sendStatus.status))
                if (sendStatus.status.lower() == "queued" and counter < 12):
                    continue
                else:
                    if(sendStatus.status.lower() == "outfordelivery" ):
                       print("Email is sucessfully delivered  for messageId %s" %(messageId))
                       break
                    else:
                        print("Looks like we timed out for email")
                        break
            time.sleep(20)
    except Exception as e:
        print(e)
main()
