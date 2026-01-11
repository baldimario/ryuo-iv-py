from lib.app import App

class Main():
    def __init__(self):
        self.app = App()

    def run(self):
        self.app.run()
    
if __name__ == "__main__":
    main_app = Main()
    main_app.run()