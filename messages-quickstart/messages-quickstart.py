import os

class MessagesQuickstart(object):
    print("Azure Communication Services - Advanced Messages Quickstart")
    # Advanced Messages SDK implementations goes in this section.
   
    connection_string = os.getenv("COMMUNICATION_SAMPLES_CONNECTION_STRING")
    phone_number = os.getenv("RECIPIENT_PHONE_NUMBER")
    channel_id = os.getenv("WHATSAPP_CHANNEL_ID")

    def send_template_send_message(self):
        from azure.communication.messages import NotificationMessagesClient
        from azure.communication.messages.models import ( TemplateNotificationContent , MessageTemplate )

        # client creation
        messaging_client = NotificationMessagesClient.from_connection_string(self.connection_string)
        input_template: MessageTemplate = MessageTemplate(
            name="gathering_invitation",
            language="ca")
        template_options = TemplateNotificationContent(
            channel_registration_id=self.channel_id,
            to=[self.phone_number],
            template=input_template
        )

        # calling send() with WhatsApp template details.
        message_responses = messaging_client.send(template_options)
        response = message_responses.receipts[0]
        
        if (response is not None):
            print("WhatsApp Templated Message with message id {} was successful sent to {}"
            .format(response.message_id, response.to))
        else:
            print("Message failed to send")

    def send_text_send_message(self):
        from azure.communication.messages import NotificationMessagesClient
        from azure.communication.messages.models import ( TextNotificationContent )

        # client creation
        messaging_client = NotificationMessagesClient.from_connection_string(self.connection_string)

        text_options = TextNotificationContent (
            channel_registration_id=self.channel_id,
            to= [self.phone_number],
            content="Thanks for your feedback.\n From Notification Messaging SDK",
        )
        
        # calling send() with WhatsApp message details
        message_responses = messaging_client.send(text_options)
        response = message_responses.receipts[0]
        
        if (response is not None):
            print("WhatsApp Text Message with message id {} was successful sent to {}"
            .format(response.message_id, response.to))
        else:
            print("Message failed to send")

    def send_image_message(self):
        from azure.communication.messages import NotificationMessagesClient
        from azure.communication.messages.models import ( ImageNotificationContent)

        # Create NotificationMessagesClient Client
        messaging_client = NotificationMessagesClient.from_connection_string(self.connection_string)
        input_media_uri: str = "https://aka.ms/acsicon1"
        image_message_options = ImageNotificationContent(
            channel_registration_id=self.channel_id,
            to=[self.phone_number],
            media_uri=input_media_uri
        )

        # calling send() with whatsapp image message
        message_responses = messaging_client.send(image_message_options)
        response = message_responses.receipts[0]
        
        if (response is not None):
            print("WhatsApp Image containing Message with message id {} was successfully sent to {}"
            .format(response.message_id, response.to))
        else:
            print("Message failed to send")

if __name__ == '__main__':
    messages = MessagesQuickstart()
    messages.send_template_send_message()
    messages.send_text_send_message()
    messages.send_image_message()