import omni.ext
import omni.kit.app
import queue
import json
import random
import time
from threading import Thread
import carb

from .constants import SIMULATION_INTERVAL
from .mqtt_client import MqttClient
from .scene_manager import SceneManager
from .ui_panel import UiPanel

class MqttCollectuStreamExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        carb.log_info("[MqttCollectuStreamExtension] Startup")
        
        # Core Components
        self.scene_manager = SceneManager()
        self.ui_panel = UiPanel(callbacks={
            'on_file_selected': self.load_config,
            'on_connect': self.connect_mqtt,
            'on_disconnect': self.disconnect_mqtt,
            'on_simulate': self.start_simulation,
            'on_zoom': self.scene_manager.zoom_to_prim
        })
        self.mqtt_client = MqttClient(on_message_callback=self.enqueue_message)
        
        # State
        self.task_queue = queue.Queue()
        self.sensor_data_list = [] # List of dicts from config
        self.ui_rows = []          # List of UI row objects
        self.simulation_active = False
        self.update_sub = None

        # Build UI
        self.ui_panel.build_ui()

    def on_shutdown(self):
        carb.log_info("[MqttCollectuStreamExtension] Shutdown")
        self.disconnect_mqtt()
        self.stop_simulation()
        if self.ui_panel:
            self.ui_panel.destroy()
            self.ui_panel = None

    # --- Logic ---

    def load_config(self, file_path):
        self.sensor_data_list, self.ui_rows = self.ui_panel.load_sensor_list(file_path)
        self.ui_panel.update_status(f"Loaded {len(self.sensor_data_list)} sensors.")

    def connect_mqtt(self):
        if self.mqtt_client.connect():
            self.ui_panel.update_status("Connected to MQTT Broker.")
            self._start_update_loop()
        else:
            self.ui_panel.update_status("Connection Failed.")

    def disconnect_mqtt(self):
        self.mqtt_client.disconnect()
        self.stop_simulation()
        self.ui_panel.update_status("Disconnected.")
        self._stop_update_loop()
        # Reset colors
        self.scene_manager.reset_materials(self.sensor_data_list)

    def enqueue_message(self, payload):
        self.task_queue.put(payload)

    def _start_update_loop(self):
        if not self.update_sub:
            self.update_sub = omni.kit.app.get_app().get_update_event_stream().create_subscription_to_pop(
                self.on_update
            )

    def _stop_update_loop(self):
        self.update_sub = None

    def on_update(self, e):
        # Process all queued messages
        while not self.task_queue.empty():
            try:
                payload = self.task_queue.get_nowait()
                self.process_payload(payload)
            except queue.Empty:
                break
            except Exception as ex:
                carb.log_error(f"Error processing payload: {ex}")

    def process_payload(self, payload_str):
        # Determine if payload is JSON or just string (simulation vs real)
        try:
            if isinstance(payload_str, dict):
                 data = payload_str
            else:
                 data = json.loads(payload_str)
        except json.JSONDecodeError:
            return

        # Flatten logic if needed, but assuming simple structure or parsing
        # Original code had complex parsing for "0.value" etc. Simplified here
        # to match sensor list.
        
        search_str = str(data) # Quick check against raw string first for performance

        for i, sensor in enumerate(self.sensor_data_list):
            mqtt_id = sensor["mqtt_id"]
            if mqtt_id in search_str:
                # Extract value. This is highly specific to the payload format.
                # Adapting the logic from original extension roughly:
                # It looked for the ID in keys or values. 
                # Let's assume standard format: { "pointId": "ID", "value": VAL }
                
                value = None
                if isinstance(data, dict):
                    if data.get("pointId") == mqtt_id:
                        value = data.get("value")
                    # Fallback for complex nested keys mentioned in legacy code:
                    elif any(mqtt_id in k for k in data.keys()):
                         # Legacy fuzzy match logic
                         for k, v in data.items():
                             if mqtt_id in k:
                                 # If key is like "0.value", maybe value is sibling?
                                 # Or value is v?
                                 # Original was: value = self.data["0.value"] if "0" in matching_keys[0]
                                 # This is very specific. Let's try to get 'value' from the dict if present.
                                 value = data.get("value", data.get(k)) 
                                 break
                
                if value is not None:
                    try:
                        f_value = float(value)
                        rgb = self.scene_manager.calculate_color(
                            f_value, 
                            sensor["min_value"], sensor["max_value"],
                            sensor["min_color"], sensor["max_color"]
                        )
                        hex_color = self.scene_manager.rgb_to_hex(rgb)
                        
                        # Update Scene
                        self.scene_manager.change_color(sensor["prim_path"], rgb)
                        
                        # Update UI
                        self.ui_panel.update_sensor_row(i, f_value, hex_color)
                        
                    except ValueError:
                        pass

    # --- Simulation ---
    
    def start_simulation(self):
        if self.simulation_active: return
        self.simulation_active = True
        self.ui_panel.update_status("Simulation Started.")
        self._start_update_loop() # Ensure loop is running to process sim messages
        
        self.sim_thread = Thread(target=self._sim_loop, daemon=True)
        self.sim_thread.start()

    def stop_simulation(self):
        self.simulation_active = False

    def _sim_loop(self):
        while self.simulation_active:
            if not self.sensor_data_list: 
                time.sleep(1)
                continue

            # Pick a random sensor and simulate a value
            sensor = random.choice(self.sensor_data_list)
            val = random.uniform(sensor["min_value"], sensor["max_value"])
            
            payload = {
                "pointId": sensor["mqtt_id"],
                "value": val
            }
            
            self.task_queue.put(payload)
            time.sleep(SIMULATION_INTERVAL / 10.0) # Faster simulation for visual effect