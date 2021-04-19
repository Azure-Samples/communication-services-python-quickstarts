import os
from azure.communication.phonenumbers import PhoneNumbersClient,PhoneNumberCapabilityType, PhoneNumberAssignmentType, PhoneNumberType, PhoneNumberCapabilities

connection_string = 'https://<RESOURCE_NAME>.communication.azure.com/;accesskey=<YOUR_ACCESS_KEY>'
try:
    print('Azure Communication Services - Phone Numbers Quickstart')

    #Initializing phone number client
    phone_numbers_client = PhoneNumbersClient.from_connection_string(connection_string)

    capabilities = PhoneNumberCapabilities(
        calling = PhoneNumberCapabilityType.INBOUND,
        sms = PhoneNumberCapabilityType.INBOUND_OUTBOUND
    )

    #Search available phone numbers
    search_poller = phone_numbers_client.begin_search_available_phone_numbers(
        "US",
        PhoneNumberType.TOLL_FREE,
        PhoneNumberAssignmentType.APPLICATION,
        capabilities,
        polling = True
    )
    search_result = search_poller.result()
    print ('Search id: ' + search_result.search_id)

    phone_number_list = search_result.phone_numbers
    phone_number = phone_number_list[0:1]
    
    print('Reserved phone numbers:')
    for phone_number in phone_number_list:
        print(phone_number)

    #Purchase available phone number
    purchase_poller = phone_numbers_client.begin_purchase_phone_numbers(search_result.search_id, polling = True)
    purchase_poller.result()
    print("The status of the purchase operation was: " + purchase_poller.status())

    #Get purchased phone number
    purchased_phone_number_information = phone_numbers_client.get_phone_number(phone_number)
    print('Phone number: ' + purchased_phone_number_information.phone_number)
    print('Country code: ' + purchased_phone_number_information.country_code)

    #Get all purchased phone numbers
    purchased_phone_numbers = phone_numbers_client.list_acquired_phone_numbers()
    print('Purchased phone numbers:')
    for purchased_phone_number in purchased_phone_numbers:
        print(purchased_phone_number.phone_number)

    #Update the capabilities of the purchased phone number
    update_poller = phone_numbers_client.begin_update_phone_number_capabilities(
    phone_number,
    PhoneNumberCapabilityType.OUTBOUND,
    PhoneNumberCapabilityType.OUTBOUND,
    polling = True
    )
    update_poller.result()
    print('Status of the operation: ' + update_poller.status())

    #Release the purchased phone number
    release_poller = phone_numbers_client.begin_release_phone_number(phone_number)
    release_poller.result()
    print('Status of the operation: ' + release_poller.status())


except Exception as ex:
    print('Exception:')
    print(ex)