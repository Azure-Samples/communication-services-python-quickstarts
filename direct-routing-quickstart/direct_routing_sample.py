import os
from azure.communication.phonenumbers.siprouting import SipRoutingClient, SipTrunk, SipTrunkRoute

# You can find your connection string from your resource in the Azure portal
connection_string = 'endpoint=https://<RESOURCE_NAME>.communication.azure.com/;accesskey=<ACCESS_KEY>'
try:
    print('Azure Communication Services - Direct Routing Quickstart')
    sip_routing_client = SipRoutingClient.from_connection_string(connection_string)

    print('Set Trunks')
    new_trunks = [SipTrunk(fqdn="sbc.us.contoso.com", sip_signaling_port=1234), SipTrunk(fqdn="sbc.eu.contoso.com", sip_signaling_port=1234)]
    sip_routing_client.set_trunks(new_trunks)
    
    print('Set Routes')
    us_route = SipTrunkRoute(name="UsRoute", description="Handle US numbers '+1'", number_pattern="^\\+1(\\d{10})$", trunks=["sbc.us.contoso.com"])
    def_route = SipTrunkRoute(name="DefaultRoute", description="Handle all numbers", number_pattern="^\\+\\d+$", trunks=["sbc.us.contoso.com","sbc.eu.contoso.com"])
    new_routes = [us_route, def_route]
    sip_routing_client.set_routes(new_routes)

    print('Finish')

except Exception as ex:
    print('Exception:')
    print(ex)
