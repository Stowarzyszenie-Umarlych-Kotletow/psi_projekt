from shell.controller import Controller
from shell.simple_shell import SimpleShell

def run():
    controller = Controller()
    controller.start()
    SimpleShell(controller).cmdloop()

if __name__ == "__main__":
    run()