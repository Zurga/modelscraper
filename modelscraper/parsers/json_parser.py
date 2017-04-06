

class JSONParser(BaseParser):
    def __init__(self, data=None, selector=None):
        self.data = json.loads(data)
        if selector:
            for key in selector:
                self.data = self.data[key]


    def sel_key(self, selector, key=''):
        return self.data.get(key)
