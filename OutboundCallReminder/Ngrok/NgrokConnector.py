import requests
import json


class NgrokConnector:

    def __init__(self):
        self.ngrok_tunnel_url = "http://127.0.0.1:4040/api/tunnels"

    def get_all_tunnels(self):
        tunnel_url = requests.get(self.ngrok_tunnel_url).text
        tunnel_list = json.loads(tunnel_url)
        return tunnel_list
