from .ryuo import Ryuo

class App():
    def __init__(self):
        self.ryuo = Ryuo()

    def run(self):
        self.ryuo.run()