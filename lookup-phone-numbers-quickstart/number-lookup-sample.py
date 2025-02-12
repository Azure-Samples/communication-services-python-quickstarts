import os
import sys
from azure.communication.phonenumbers import PhoneNumbersClient
    
try:
    print('Azure Communication Services - Number Lookup Quickstart')
    
    if len(sys.argv) < 2:
        sys.exit("Missing a phone number parameter")
    phoneNumber = sys.argv[1]
    
    # This code retrieves your connection string from an environment variable
    connection_string = os.getenv('COMMUNICATION_SERVICES_CONNECTION_STRING')
    try:
        phone_numbers_client = PhoneNumbersClient.from_connection_string(connection_string)
    except Exception as ex:
        print('Exception:')
        print(ex)

    # Use the free number lookup functionality to get number formatting information
    formatting_results = phone_numbers_client.search_operator_information(phoneNumber)
    formatting_info = formatting_results.values[0]
    print(str.format("{0} is formatted {1} internationally, and {2} nationally", formatting_info.phone_number, formatting_info.international_format, formatting_info.national_format))

    # Use the paid number lookup functionality to get operator specific details
    # IMPORTANT NOTE: Invoking the method below will incur a charge to your account
    options = { "include_additional_operator_details": True }
    operator_results = phone_numbers_client.search_operator_information([ phoneNumber ], options=options)
    operator_information = operator_results.values[0]

    number_type = operator_information.number_type if operator_information.number_type else "unknown"
    if operator_information.operator_details is None or operator_information.operator_details.name is None:
        operator_name = "an unknown operator"
    else:
        operator_name = operator_information.operator_details.name

    print(str.format("{0} is a {1} number, operated in {2} by {3}", operator_information.phone_number, number_type, operator_information.iso_country_code, operator_name))
except Exception as ex:
   print('Exception:')
   print(ex)
