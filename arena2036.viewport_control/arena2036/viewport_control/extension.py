import omni.ext
from .stream_listener import StreamListener
from .camera_controller import CameraController

class ViewportControlExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        print("[arena2036.viewport_control] Viewport Control Extension starting up")
        self._camera_controller = CameraController()
        self._stream_listener = StreamListener(self._camera_controller)
        self._stream_listener.startup()

    def on_shutdown(self):
        print("[arena2036.viewport_control] Viewport Control Extension shutting down")
        if self._stream_listener:
            self._stream_listener.shutdown()
            self._stream_listener = None
        
        self._camera_controller = None
