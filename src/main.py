from controller import Controller
from simple_shell import SimpleShell

if __name__ == "__main__":
    controller = Controller()
    controller.start()
    SimpleShell(controller).cmdloop()
