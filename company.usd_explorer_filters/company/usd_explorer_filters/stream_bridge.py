import carb
import omni.kit.livestream.core
from typing import Dict, Any, Optional
import json

from . import ui_panel

# ------------------------------------------------------------------------------
# Event Handling
# ------------------------------------------------------------------------------

class StreamBridge:
    """
    Handles communication with the WebRTC streaming client.
    Listens for custom events and dispatches them to the UI panel.
    """
    
    def __init__(self):
        self._livestream = omni.kit.livestream.core.get_livestream()
        self._event_subscription = None
        
    def startup(self) -> None:
        """
        Initializes the bridge and subscribes to livestream events.
        """
        if not self._livestream:
            carb.log_warn("[USD Explorer Filters] Livestream extension not available.")
            return

        carb.log_info("[USD Explorer Filters] Starting StreamBridge...")
        
        # Subscribe to the generic message event
        # Note: The actual API might vary slightly depending on the Kit version.
        # We assume a standard message event structure here.
        self._event_subscription = self._livestream.register_event_handler(
            "ToggleFilter", 
            self._on_toggle_filter
        )

    def shutdown(self) -> None:
        """
        Cleans up subscriptions.
        """
        if self._event_subscription:
            self._livestream.unregister_event_handler(self._event_subscription)
            self._event_subscription = None
        self._livestream = None

    def _on_toggle_filter(self, event_data: Any) -> None:
        """
        Callback for 'ToggleFilter' events from the client.
        
        Expected payload structure from client:
        {
            "event_type": "ToggleFilter",
            "payload": {
                "name": "Bosch Rexroth",
                "active": true
            }
        }
        
        Note: The 'event_data' passed here might be the full message object, 
        just the payload, or a string depending on the Kit version and transport.
        """
        # Log immediately to show receipt as requested
        carb.log_info(f"[USD Explorer Filters] Received 'ToggleFilter' event. Raw data: {event_data}")

        try:
            data = {}
            
            # 1. Normalize to dictionary
            if isinstance(event_data, dict):
                data = event_data
            elif isinstance(event_data, str):
                try:
                    data = json.loads(event_data)
                except json.JSONDecodeError:
                    carb.log_warn(f"[USD Explorer Filters] Failed to decode JSON string: {event_data}")
                    return
            elif hasattr(event_data, "payload"):
                # Handle carb.events.IEvent or similar objects
                # If it's an IEvent, the data might be in .payload
                raw_payload = event_data.payload
                if isinstance(raw_payload, dict):
                    data = raw_payload
                elif isinstance(raw_payload, str):
                     try:
                        data = json.loads(raw_payload)
                     except json.JSONDecodeError:
                        pass # Keep as is if not JSON

            # 2. Extract the actual payload
            # The client sends { "event_type": "...", "payload": { ... } }
            # If the livestream extension unwraps it, 'data' might be the inner payload.
            # If not, 'data' might be the outer object.
            
            target_payload = data
            if "payload" in data and isinstance(data["payload"], dict):
                target_payload = data["payload"]
            
            # 3. Extract fields from the target payload
            name = target_payload.get("name")
            active = target_payload.get("active")
            
            if name is None or active is None:
                carb.log_warn(f"[USD Explorer Filters] Invalid payload structure. Missing 'name' or 'active'. Processed data: {target_payload}")
                return
                
            carb.log_info(f"[USD Explorer Filters] Processing action: Set '{name}' to {active}")
            
            # Dispatch to UI panel
            ui_panel.set_filter_state(name, bool(active))
            
        except Exception as e:
            carb.log_error(f"[USD Explorer Filters] Error handling ToggleFilter event: {e}")

# Global instance
_bridge_instance: Optional[StreamBridge] = None

def startup() -> None:
    global _bridge_instance
    _bridge_instance = StreamBridge()
    _bridge_instance.startup()

def shutdown() -> None:
    global _bridge_instance
    if _bridge_instance:
        _bridge_instance.shutdown()
        _bridge_instance = None
