from Utils.Logger import Logger


class EventAuthHandler:

    secret_value = 'h3llowW0rld'

    def authorize(self, query):
        if query == None:
            return False
        return ((query != None) and (query == self.secret_value))

    def get_secret_querystring(self):
        secretKey = "secret"
        return (secretKey + "=" + self.secret_value)
