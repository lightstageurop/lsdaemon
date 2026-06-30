from kinet import *
from threading import Lock
from time import monotonic, sleep

"""
Responsible for accepting control signals from wrappers and proxying them
to DMX controllers. It should be run on an independent thread.
To prevent frame split, it utilised vertical synchronisation.
"""
class LightStage:

    def __init__(self, addr='10.37.211.', render_interval=10):
        if render_interval <= 0:
            raise ValueError("render_interval must be positive")
        self.render_interval = render_interval

        # Initialise DMX controls
        self.rgbc = [] # RGB controllers
        self.wc = []   # White controllers
        for i in range(12):
            # Creates UDP socket to addr.(0-23)
            # Addresses alternate between RGB and White controllers
            # 1 RGB controller and 1 White controller per logical arc
            ps_RGB = PowerSupply(addr + str(2*i))
            ps_W = PowerSupply(addr + str(2*i + 1))
            # Each arc handles 14 logical lights, composed of 1 RGB + 1 W bulb
            # Each logical light has 12 channels, 6 for RGB and 6 for W
            # Each bulb's channels are (R, x, G, x, B, x)
            # Register them consecutively in the controllers' DMX universes
            for j in range(2 * 14):
                ps_RGB.append(FixtureRGB(3*j))
                ps_W.append(FixtureRGB(3*j))
            self.rgbc.append(ps_RGB)
            self.wc.append(ps_W)
        # Initialise double buffer
        self.buf = []
        self.buf_lock = Lock()

    def render(self):
        # Render the current buffer to the DMX controllers
        for light in range(12):
            self.buf[light].go()
            self.buf[light].go()

    def mainloop(self):
        interval = self.render_interval / 1000
        next_render = monotonic()
        while True:
            self.render()
            next_render += interval

            delay = next_render - monotonic()
            if delay > 0:
                sleep(delay)
            else:
                next_render = monotonic()
