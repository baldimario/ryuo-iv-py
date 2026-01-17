from lib.cli import CLI

class Main():
    def __init__(self):
        self.app = CLI()

    def run(self):
        self.app.run()
    
if __name__ == "__main__":
    main_app = Main()
    main_app.run()