import carb
import carb.events
from carb.eventdispatcher import get_eventdispatcher
import json
import omni.kit.app
from typing import Any, Optional

class StreamListener:
    """
    Listens for 'CameraControl' events from the livestream and invokes the CameraController.
    """
    def __init__(self, controller):
        self._controller = controller
        self._event_subscription = None

    def startup(self):
        carb.log_info("[arena2036.viewport_control] StreamListener starting...")
        
        event_type = "CameraControl"
        
        # Register the alias so the bridging layer knows to forward it
        omni.kit.app.register_event_alias(
            carb.events.type_from_string(event_type),
            event_type,
        )
        
        # Subscribe to the event
        ed = get_eventdispatcher()
        self._event_subscription = ed.observe_event(
            observer_name=f"ViewportControl:{event_type}",
            event_name=event_type,
            on_event=self._on_camera_control_event,
        )

    def shutdown(self):
        if self._event_subscription:
            ed = get_eventdispatcher()
            # In some versions, observe_event returns a subscription object that we must keep alive.
            # When the object is garbage collected, it unsubscribes. Or we can clear it.
            self._event_subscription = None
        carb.log_info("[arena2036.viewport_control] StreamListener shut down.")

    def _on_camera_control_event(self, event_data: Any):
        """
        Handles the CameraControl event.
        Payload expected:
        {
            "command": "move_forward", 
            "value": 1.0 (optional)
        }
        """
        carb.log_info(f"[arena2036.viewport_control] Received 'CameraControl' event. Raw data: {event_data}")
        try:
            # Normalize data similar to stream_bridge pattern in usd_explorer_filters
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
                if hasattr(raw, "get_dict"):
                    data = raw.get_dict()
                elif isinstance(raw, dict):
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
