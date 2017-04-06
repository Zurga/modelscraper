from .base_parser import BaseParser

class SliceParser(BaseParser):
    def __init__(self, **kwargs):
        super(BaseParser, self).__init__(**kwargs)

    def gen_objects(self, data, template):
        parsed = []
        for line in data:
            item = {}
            if len(line) < 240:
                return {}
            else:
                for k, v in self.model.items():
                    sl = v['slice']
                    if len(sl) == 2:
                        item[k] = line[sl[0]:sl[1]]

                    if len(sl) == 3:
                        item[k] = [line[i] for i in range(sl[0], sl[1], sl[2])]

                    if len(sl) == 4:
                        item[k] = [line[i:i+sl[3]] for
                                     i in range(sl[0], sl[1], sl[2])]
                parsed.append(item)
        yield parsed

    def source_from_object
