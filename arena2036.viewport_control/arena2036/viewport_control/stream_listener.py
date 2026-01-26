import carb
import omni.kit.livestream.core
import json
from typing import Any, Optional

class StreamListener:
    """
    Listens for 'CameraControl' events from the livestream and invokes the CameraController.
    """
    def __init__(self, controller):
        self._livestream = omni.kit.livestream.core.get_livestream()
        self._controller = controller
        self._event_subscription = None

    def startup(self):
        carb.log_info(f"[arena2036.viewport_control] omni.kit.livestream.core attributes: {dir(omni.kit.livestream.core)}")
        
        try:
            if hasattr(omni.kit.livestream.core, "get_livestream"):
                self._livestream = omni.kit.livestream.core.get_livestream()
            else:
                carb.log_warn("[arena2036.viewport_control] 'get_livestream' not found in omni.kit.livestream.core. Attempting fallback or logging structure.")
                # Fallback attempts or further inspection could go here
                self._livestream = None

        except Exception as e:
            carb.log_error(f"[arena2036.viewport_control] Error accessing livestream interface: {e}")
            self._livestream = None

        if not self._livestream:
            carb.log_warn("[arena2036.viewport_control] Livestream extension not available or interface not found.")
            return
            
        carb.log_info("[arena2036.viewport_control] StreamListener starting...")
        self._event_subscription = self._livestream.register_event_handler(
            "CameraControl",
            self._on_camera_control_event
        )

    def shutdown(self):
        if self._event_subscription and self._livestream:
            self._livestream.unregister_event_handler(self._event_subscription)
            self._event_subscription = None
        self._livestream = None

    def _on_camera_control_event(self, event_data: Any):
        """
        Handles the CameraControl event.
        Payload expected:
        {
            "command": "move_forward", 
            "value": 1.0 (optional)
        }
        """
        try:
            # Normalize data similar to stream_bridge pattern
            data = {}
            if isinstance(event_data, dict):
                data = event_data
            elif isinstance(event_data, str):
                try:
                    data = json.loads(event_data)
                except json.JSONDecodeError:
                    carb.log_warn(f"[arena2036.viewport_control] Invalid JSON: {event_data}")
                    return
            elif hasattr(event_data, "payload"):
                raw = event_data.payload
                if isinstance(raw, dict):
                    data = raw
                elif isinstance(raw, str):
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        pass

            # Extract inner payload if wrapped
            target_payload = data
            if "payload" in data and isinstance(data["payload"], dict):
                target_payload = data["payload"]

            command = target_payload.get("command")
            value = target_payload.get("value")

            if not command:
                carb.log_warn(f"[arena2036.viewport_control] Missing 'command' in payload: {target_payload}")
                return

            carb.log_info(f"[arena2036.viewport_control] Received command: {command}, value: {value}")
            
            # Map commands to controller methods
            if hasattr(self._controller, command):
                method = getattr(self._controller, command)
                if callable(method):
                    if value is not None:
                        method(float(value))
                    else:
                        method()
                else:
                    carb.log_warn(f"[arena2036.viewport_control] Command '{command}' is not callable.")
            else:
                carb.log_warn(f"[arena2036.viewport_control] Unknown command: {command}")

        except Exception as e:
            carb.log_error(f"[arena2036.viewport_control] Error handling event: {e}")
