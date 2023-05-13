from direct.showbase.DirectObject import DirectObject
from direct.showbase.ShowBaseGlobal import aspect2d
from imgui.integrations.opengl import ProgrammablePipelineRenderer
from panda3d.core import GraphicsWindow, MouseButton, MouseWatcherParameter, PGItem


class Panda3DRenderer(ProgrammablePipelineRenderer):
    mouse_button_map = {MouseButton.button(i): i for i in range(5)}

    def __init__(self, window: GraphicsWindow) -> None:
        super().__init__()
        self.io.display_size = window.size
        self.window = window

        aspect_ratio = window.size.x / window.size.y
        self.suppressor = PGItem('suppressor')
        self.suppressor.set_frame(-aspect_ratio, aspect_ratio, -1, 1)
        self.suppressor.set_suppress_flags(0b101)
        aspect2d.attach_new_node(self.suppressor)

        self.acceptor = DirectObject()
        for button in self.mouse_button_map:
            press_event = self.suppressor.get_press_event(button)
            release_event = self.suppressor.get_release_event(button)
            self.acceptor.accept(press_event, self.on_mouse_press)
            self.acceptor.accept(release_event, self.on_mouse_release)
        self.acceptor.accept(window.window_event, self.on_window_changed)

    def render(self, draw_data) -> None:
        pointer = self.window.get_pointer(0)
        self.io.mouse_pos = pointer.x, pointer.y
        self.suppressor.set_active(self.io.want_capture_mouse)
        super().render(draw_data)

    def on_mouse_press(self, param: MouseWatcherParameter) -> None:
        index = self.mouse_button_map[param.get_button()]
        self.io.mouse_down[index] = True

    def on_mouse_release(self, param: MouseWatcherParameter) -> None:
        index = self.mouse_button_map[param.get_button()]
        self.io.mouse_down[index] = False

    def on_window_changed(self, window: GraphicsWindow) -> None:
        if window != self.window:
            return
        self.io.display_size = window.size
        aspect_ratio = window.size.x / window.size.y
        self.suppressor.set_frame(-aspect_ratio, aspect_ratio, -1, 1)
