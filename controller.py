from kinet import *
from threading import Lock, Thread
from time import monotonic, sleep

"""
Responsible for accepting control signals from wrappers and proxying them
to DMX controllers. It should be initialised on an independent thread.
"""
class LightStage:

    def __init__(self, addr='10.37.211.', render_interval=10, arc=12, lights_per_arc=14):
        if render_interval <= 0:
            raise ValueError("render_interval must be positive")
        self.render_interval = render_interval
        self.arc = arc
        self.lights_per_arc = lights_per_arc

        # Initialise DMX controls
        self._rgbc = [] # RGB controllers
        self._wc = []   # White controllers
        for i in range(arc):
            # Creates UDP socket to addr.(0-23)
            # Addresses alternate between RGB and White controllers
            # 1 RGB controller and 1 White controller per logical arc
            ps_RGB = PowerSupply(addr + str(2*i))
            ps_W = PowerSupply(addr + str(2*i + 1))
            # Each arc handles 14 logical lights, composed of 1 RGB + 1 W bulb
            # Each logical light has 12 channels, 6 for RGB and 6 for W
            # Each bulb's channels are (R, x, G, x, B, x)
            # Register them consecutively in the controllers' DMX universes
            for j in range(lights_per_arc):
                ps_RGB.append(FixtureRGB(3*j))
                ps_RGB.append(FixtureRGB(3*j))
                ps_W.append(FixtureRGB(3*j))
                ps_W.append(FixtureRGB(3*j))
            self._rgbc.append(ps_RGB)
            self._wc.append(ps_W)
        # Initialise locking mechanism
        self._rgb_lock = Lock()
        self._w_lock = Lock()
        # Initialise renderer thread
        Thread(
            target=self._mainloop,
            name="Renderer"
        ).start()

    def _render(self):
        # Render the current buffer to the DMX controllers
        # If the controllers are locked by another thread, give up this cycle
        acquired = self._rgb_lock.acquire(blocking=False)
        if acquired:
            try:
                for controller in self._rgbc:
                    controller.go()
            finally:
                self._rgb_lock.release()
        acquired = self._w_lock.acquire(blocking=False)
        if acquired:
            try:
                for controller in self._wc:
                    controller.go()
            finally:
                self._w_lock.release()

    def _mainloop(self):
        interval = self.render_interval / 1000
        next_render = monotonic()
        while True:
            self._render()
            next_render += interval

            delay = next_render - monotonic()
            if delay > 0:
                sleep(delay)
            else:
                next_render = monotonic()

    """
    Checks if control arguments are in range and valid.
    """
    def check_control_arguments(self, arc, light, r, g, b):
        assert light >= 0 and light < self.lights_per_arc, "light value is not between 0 and 13"
        assert arc >= 0 and arc < self.arc, "arc value is not between 0 and 11"
        assert min(r, g, b) >= 0.0 and max(
            r, g, b) <= 255.0, "intensity values are not between 0 and 255"

    """
    Controls 1 specific light on 1 specific arc. When w=True, white lights
    are controlled. When w=False, RGB lights are controlled.
    The main loop will hold the entire thread, so this should always be called
    from another thread.
    WARNING: it will wait for available locks before editing the buffers!
    """
    def set_light(self, arc, light, w=True, r=255, g=255, b=255):
        self.check_control_arguments(arc, light, r, g, b)
        if w:
            with self._w_lock:
                self._wc[arc][2*light].rgb = (r, 0, g)
                self._wc[arc][2*light+1].rgb = (0, b, 0)
        else:
            with self._rgb_lock:
                self._rgbc[arc][2*light].rgb = (r, 0, g)
                self._rgbc[arc][2*light+1].rgb = (0, b, 0)

if __name__ == '__main__':
    stage = LightStage()
    stage.set_light(0, 0)
    stage.set_light(0, 2)
    stage.set_light(0, 4)
    stage.set_light(0, 6)