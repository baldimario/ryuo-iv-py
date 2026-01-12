#from lib.app import App
from lib.tui import TUI
#from lib.cli import CLI
#from lib.api import API

class Main():
    def __init__(self):
        self.app = TUI()

    def run(self):
        self.app.run()
    
if __name__ == "__main__":
    main_app = Main()
    main_app.run()