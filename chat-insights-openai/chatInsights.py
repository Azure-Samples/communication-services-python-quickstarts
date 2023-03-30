from azure.communication.chat import ChatClient, CommunicationTokenCredential, ChatMessageType,ChatParticipant
from azure.communication.identity import CommunicationIdentityClient, CommunicationUserIdentifier
from datetime import datetime

connection_string = "INSERT AZURE COMMUNICATION SERVICES CONNECTION STRING"
endpoint = "INSERT AZURE COMMUNICATION SERVICES ENDPOINT"
client = CommunicationIdentityClient.from_connection_string(connection_string)
identity1 = client.create_user()
token_result1 = client.get_token(identity1, ["chat"])
identity2 = client.create_user()
token_result2 = client.get_token(identity2, ["chat"])

Agent  = ChatParticipant(identifier=identity1, display_name="Agent", share_history_time=datetime.utcnow()) 
Customer  = ChatParticipant(identifier=identity2, display_name="Customer", share_history_time=datetime.utcnow())
participants = [Agent, Customer ]

chat_client1 = ChatClient(endpoint, CommunicationTokenCredential(token_result1.token))
chat_client2 = ChatClient(endpoint, CommunicationTokenCredential(token_result2.token))
topic="Support conversation"
create_chat_thread_result = chat_client1.create_chat_thread(topic, thread_participants=participants)
chat_thread_client1 = chat_client1.get_chat_thread_client(create_chat_thread_result.chat_thread.id)
chat_thread_client2 = chat_client2.get_chat_thread_client(create_chat_thread_result.chat_thread.id)

agentText = [    
    "Thank you for calling our customer service hotline. How may I assist you today?",    
    "I'm sorry to hear that. Can you provide me with your name and account number, so I can look up your account and assist you better?",    
    "Thank you. Can you please tell me a little more about the problem you're having with your dishwasher?",
    "I see. That can be frustrating. Can you please check if the dishwasher is getting enough water supply? Also, please check if the spray arms inside the dishwasher are properly attached and not clogged.",    
    "Alright. Please check the spray arms and see if they're clogged or damaged in any way. Also, make sure they're attached properly.",
    "That could be the reason why the dishes aren't getting cleaned properly. Can you please try to reattach the spray arm and run the dishwasher again?",    
    "Great to hear that! Is there anything else I can help you with?",    
    "You're welcome. Don't hesitate to call us back if you have any more issues. Have a nice day!"
]

customerText = [    
    "Hi, I'm having trouble with my dishwasher. It doesn't seem to be cleaning the dishes properly.",    
    "Yes, my name is Lisa and my account number is 12345.",    
    "Well, it seems like the dishwasher isn't spraying enough water to clean the dishes properly. Some of the dishes are coming out dirty even after I run the dishwasher.",    
    "I've checked the water supply and it seems to be okay. But I haven't checked the spray arms yet.",    
    "Okay, let me check. Yes, it seems like one of the spray arms is loose and not attached properly.",    
    "Sure, let me try that. Okay, I reattached the spray arm and ran the dishwasher again. It seems to be working fine now. The dishes are coming out clean.",   
    "No, that's all. Thank you for your help.",
    "Bye."
]

for x in range(len(agentText)):
    chat_thread_client1.send_message(content= agentText[x], sender_display_name="Agent", chat_message_type=ChatMessageType.TEXT)
    chat_thread_client2.send_message(content= customerText[x], sender_display_name="Customer", chat_message_type=ChatMessageType.TEXT)

from datetime import datetime, timedelta

start_time = datetime.utcnow() - timedelta(days=1)
messages = []

chat_messages = chat_thread_client1.list_messages(results_per_page=1, start_time=start_time)
for chat_message_page in chat_messages.by_page():
    for chat_message in chat_message_page:
        if(chat_message.type == ChatMessageType.TEXT):
            messages.append(chat_message)

# didn't know I had to filter out other messages

prompt = ""
for m in range(len(messages)-1, -1, -1):
    prompt = prompt + messages[m].sender_display_name + ": " + messages[m].content.message + "\n"
print(prompt)

import os
import requests
import json
import openai

openai.api_key = "INSERT YOUR AZURE OPENAI API KEY"
openai.api_base =  "INSERT YOUR AZURE OPENAI ENDPOINT" # your endpoint should look like the following https://YOUR_RESOURCE_NAME.openai.azure.com/
openai.api_type = 'azure'
openai.api_version = '2022-12-01' # this may change in the future
deployment_name='INSERT YOUR DEPLOyMENT NAME' #This will correspond to the custom name you chose for your deployment when you deployed a model. 

# Send a completion call to generate an answer
start_phrase = 'For the following conversation, extract a topic, summary, highlights (1-3 bullet points of key information) and the sentiment of both of the users.\n\n' + prompt
response = openai.Completion.create(engine=deployment_name, prompt=start_phrase, max_tokens=500)
text = response['choices'][0]['text'].replace('\n', '').replace(' .', '.').strip()
print(start_phrase + '\n' + text)

