from shlex import split

from controller import LightStage


class Command:

    def __init__(self, name, handler, usage, description, aliases=None):
        self.name = name
        self.handler = handler
        self.usage = usage
        self.description = description
        self.aliases = aliases or []


class LightCLI:

    def __init__(self, stage):
        self.stage = stage
        self.running = True
        self.commands = {}
        self._register_commands()

    def _register(self, command):
        self.commands[command.name] = command
        for alias in command.aliases:
            self.commands[alias] = command

    def _register_commands(self):
        self._register(Command(
            "help",
            self._help,
            "help",
            "show available commands",
            aliases=["?"],
        ))
        self._register(Command(
            "set",
            self._set_light,
            "set <arc> <light> [white|rgb] [r] [g] [b]",
            "set one light to a colour",
            aliases=["light"],
        ))
        self._register(Command(
            "off",
            self._turn_off,
            "off <arc> <light> [white|rgb|all]",
            "turn one light off",
        ))
        self._register(Command(
            "quit",
            self._quit,
            "quit",
            "stop rendering and exit",
            aliases=["exit"],
        ))

    def run(self):
        print("Type 'help' for commands. Type 'quit' to exit.")
        while self.running:
            try:
                line = input("lights> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            self._handle(line)

    def _handle(self, line):
        try:
            parts = split(line)
        except ValueError as error:
            print("error: %s" % error)
            return
        if not parts:
            return

        command = self.commands.get(parts[0])
        if command is None:
            print("unknown command: %s" % parts[0])
            print("type 'help' for commands")
            return

        try:
            command.handler(parts[1:])
        except ValueError as error:
            print("error: %s" % error)
            print("usage: %s" % command.usage)

    def _help(self, args):
        if args:
            raise ValueError("help does not take arguments")

        seen = set()
        for command in self.commands.values():
            if command.name in seen:
                continue
            seen.add(command.name)
            print("%-42s %s" % (command.usage, command.description))

    def _set_light(self, args):
        if len(args) < 2:
            raise ValueError("missing arc or light")
        if len(args) not in (2, 3, 5, 6):
            raise ValueError("expected 2, 3, 5, or 6 arguments")

        arc = self._parse_int(args[0], "arc")
        light = self._parse_int(args[1], "light")
        w = True
        colour_start = 2

        if len(args) in (3, 6):
            w = self._parse_mode(args[2])
            colour_start = 3

        r, g, b = 255, 255, 255
        if len(args) - colour_start == 3:
            r = self._parse_int(args[colour_start], "r")
            g = self._parse_int(args[colour_start + 1], "g")
            b = self._parse_int(args[colour_start + 2], "b")

        self.stage.set_light(arc, light, w=w, r=r, g=g, b=b)

    def _turn_off(self, args):
        if len(args) not in (2, 3):
            raise ValueError("expected arc, light, and optional mode")

        arc = self._parse_int(args[0], "arc")
        light = self._parse_int(args[1], "light")
        mode = args[2].lower() if len(args) == 3 else "all"

        if mode == "all":
            self.stage.set_light(arc, light, w=True, r=0, g=0, b=0)
            self.stage.set_light(arc, light, w=False, r=0, g=0, b=0)
            return

        self.stage.set_light(arc, light, w=self._parse_mode(mode), r=0, g=0, b=0)

    def _quit(self, args):
        if args:
            raise ValueError("quit does not take arguments")
        self.running = False

    def _parse_int(self, value, name):
        try:
            return int(value)
        except ValueError:
            raise ValueError("%s must be an integer" % name)

    def _parse_mode(self, value):
        value = value.lower()
        if value in ("white", "w"):
            return True
        if value in ("rgb", "r"):
            return False
        raise ValueError("mode must be white or rgb")


def main():
    with LightStage() as stage:
        LightCLI(stage).run()


if __name__ == "__main__":
    main()
