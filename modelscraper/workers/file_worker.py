from multiprocessing import Process, Queue


class FileWorker(Process):
    def __init__(self, parent, in_q, out_q, model, out_q=Queue):
        super(Worker, self).__init__()
        self.in_q = in_q
        self.out_q = out_q

    def run(self):
        while True:
            getter = self.in_q.get()
            if template is None:
                print('stopping')
                break
            with open(template.url) as fle:
                lines = fle.readlines()
                self.out_q.put((self.parser.parse(lines), db, col))
