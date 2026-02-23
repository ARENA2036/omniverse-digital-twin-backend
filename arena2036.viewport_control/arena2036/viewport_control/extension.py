import omni.ext
import omni.ui as ui
from .stream_listener import StreamListener
from .camera_controller import CameraController
from . import ui_panel

class ViewportControlExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        print("[arena2036.viewport_control] Viewport Control Extension starting up")
        self._camera_controller = CameraController()
        self._stream_listener = StreamListener(self._camera_controller)
        self._stream_listener.startup()

        # Create the UI Window for testing
        self._window = ui.Window("Viewport Control", width=300, height=400)
        with self._window.frame:
            ui_panel.build_panel(self._camera_controller)

    def on_shutdown(self):
        print("[arena2036.viewport_control] Viewport Control Extension shutting down")
        if self._stream_listener:
            self._stream_listener.shutdown()
            self._stream_listener = None
        
        if self._window:
            self._window.destroy()
            self._window = None

        self._camera_controller = None
