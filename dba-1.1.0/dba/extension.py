import omni.ext
import omni.ui as ui
from pxr import Usd, UsdGeom, Gf, Sdf, UsdShade
import omni.usd
import omni.kit
import paho.mqtt.client as mqtt
import json
import carb.events
import json
import os
from omni.kit.app import get_app
import pathlib
from threading import Thread
import ssl
from omni.usd import get_context
from pathlib import Path
import queue
import omni.kit.window.filepicker as filepicker
import pandas as pd
import openpyxl
from omni.kit.viewport.utility import get_active_viewport, frame_viewport_selection
from functools import partial
import time
import datetime
import logging
import time
import paho.mqtt.publish as publish
from threading import Thread
import random
import string


# region initialize 

# Configuration
MQTT_BROKER_HOST = 'mqtt.collectu.de'
MQTT_BROKER_PORT = 8883 
MQTT_USERNAME = 'eyJhbGciOiJSUzI1NiIsImtpZCI6IjhlN2NiZDczNzNkZmJiMzhkMTUzYzZmNjJmZTVlZWJmNGUzZjQ3NDgwYjJiYzY2MzIwOGZhOTI1ZDljMDg4OTMiLCJ0eXAiOiJKV1QifQ.eyJ1c2VyX2lkIjoiZjU2NTFjMDEtMTNmNS00OWMzLTgyYzItYjkyNjQ4ZjUwZjA3IiwidG9rZW5faWQiOiI2ODRlMTI0OS1lM2U4LTQ0MTQtODRiNy05ZmUzMDJiNTNkZTYiLCJpc3MiOiJDb2xsZWN0dSBBUEkiLCJqdGkiOiI1Y2ZiNzAwMy1iZDNiLTRjMTQtYmExNi02ZGRmN2NkZTM0NWIiLCJpYXQiOjE3NDcwNjM0MjMsIm5iZiI6MTc0NzA2MzQyM30.q_RYnCCUfpfMAt9r6_DiOSlbHphE04_K8S8gvOcffV7EbzPdapLApM8BW_I2ydU5crdHSimHSIHqHkey3l9H8cKcXRr9xTv56vQt5JUHcKyIDWwU50RVuNoMcJTqdSN-PcQWppQECHwDvrFCsAAZ9UpnuCxCg1xZU2VhJlOA3i4LbLBlW76pIkvpnIiXVnlm68PM8N2eAJpfDkdZxDZe-mM1srd_8I1DXn8UmKd4guJB6-J60pXXWf3Pv-4Y9Dp-4RV-6KWXlUBPym2G18UH39nGyJrv4o4GeMQVvFnnJHWhSmRWtzMZSLuCjPYH5c2YTXQ8n_LI3yNFppG8-ZaVQQ'
MQTT_PASSWORD = '0'
MQTT_TOPICS = [('Arena2036/omniverse/spie/disruptive_technologies', 0), ('Arena2036/omniverse/spie/demonstrator', 1), ('Arena2036/omniverse/spie/', 2)]

task_queue = queue.Queue()

script_dir = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(script_dir, "log")
with open(OUT_PATH, 'w') as file:
    file.write("Logger Started\n")


# endregion

# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
class DbaExtension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.

    # region user interface
    def __init__(self):
        super().__init__()
        self.data_table = []
        self.sensor_status_list = []
        self.sensor_value_list = []
        self.zoom_button_list = []
        self.data = None
        self.connection = False	
        self.config_path = False
        self.real_data = True
        self.active_file = False

    def on_startup(self, ext_id):
        self._build_ui()

    def _build_ui(self):
        self._window = ui.Window("Arena2036 Sensors by DBA", width=800)
        with self._window.frame:
            with ui.VStack(spacing=0):
                ui.Button("Select Sensors File (.xslx)",  height = 30, clicked_fn=self.open_file_picker_dba)
                self._button_container = ui.ScrollingFrame()#height=400)
                with self._button_container:
                    self._vstack = ui.VStack(spacing=0)

    def _load_excel_and_generate_buttons(self, path):
        self._vstack.clear()

        self._count = 0
        self.lock_bool = False
        self.usd_context = omni.usd.get_context()
        self.stage = self.usd_context.get_stage()
        

        if not os.path.exists(path):
            with self._vstack:
                ui.Label(f"File not found: {path}")
            return

        try:
            wb = openpyxl.load_workbook(path)
            sheet = wb.active
            self.active_file = True

            with self._vstack:
                
                self.label = ui.Label("")
                self.status_label = ui.Label("")
                self.status_style = {"background_color": 0xFFC9C9C9}
                with ui.HStack():
                    ui.Button("Connect to Sensors",  height = 30, clicked_fn=self.on_connection)
                    ui.Button("Disconnect",  height = 30, clicked_fn=self.on_reset)
                    ui.Button("Simulate Sensor Messages", height=30, clicked_fn=lambda: self.simulate_incoming_messages())
                    ui.Button("Simulate MQTT Access", height=30, clicked_fn=lambda: self.simulate_mqtt())
                    ui.Button("Update Stage", height=30, clicked_fn=lambda: self.update_stage())

            
                for index, row in enumerate(sheet.iter_rows(values_only=True)):
                    if any(cell is not None for cell in row) and index != 0:  # skip empty rows
                        dict_row = {}
                        dict_row["name"] = row[0] if row[0] is not None else "Unnamed Sensor"
                        dict_row["unit"]  = row[1] if row[1] is not None else "Unknown Unit"
                        dict_row["mqtt_id"]  = row[2] if row[2] is not None else "Unknown MQTT ID"
                        dict_row["prim_path"] = row[3] if row[3] is not None else "/World/Unknown"
                        dict_row["min_value"] = row[4] if row[4] is not None else "0"
                        dict_row["max_value"] = row[5] if row[5] is not None else "100"
                        dict_row["min_color"] = row[6] if row[6] is not None else "0, 0, 0"
                        dict_row["max_color"] = row[7] if row[7] is not None else "255, 255, 255"
                        self.data_table.append(dict_row)
                        ui.Line(style={"padding": 0, "margin_height": 0})
                        with ui.HStack(style={"margin": 0, "margin_height": 3}):
                            with ui.HStack(style={"margin": 0, "margin_height": 3}):
                                ui.Spacer(width=5)
                                self.sensor_status_list.append(ui.Circle(height=30, width=30, style=self.status_style))
                                ui.Spacer(width=10)
                                ui.Button(" Zoom ",  height = 30, width = 30, clicked_fn=partial(self.zoom_to_prim, dict_row["prim_path"]))
                                ui.Spacer(width=10)
                                ui.Label(dict_row["name"], height = 30, width = 100)
                                ui.Spacer(width=10)
                                ui.Rectangle(height=30, width=1)
                                ui.Spacer(width=10)
                            with ui.HStack(style={"margin": 0, "margin_height": 3}):
                                self.sensor_value_list.append(ui.Label("-", height = 30, width = 100))
                                ui.Label(dict_row["unit"], height = 30, width = 100)
                
                for i in range(3):  # Example: 50 buttons
                    ui.Label(f".")

        except Exception as e:
            with self._vstack:
                ui.Label(f"Error initializing: {str(e)}")
      
    def update_stage(self):
        self.usd_context = omni.usd.get_context()
        self.stage = self.usd_context.get_stage()
        self.status_label.text = " Stage updated."     
          
    def on_connection(self):
        self._update_sub = omni.kit.app.get_app().get_update_event_stream().create_subscription_to_pop(
                self._on_update
            )
        self.append_to_file(OUT_PATH, f"Update Loop started at {datetime.datetime.now()}")
        self.create_mqtt_client()

        if not self.connection: 
            self.client.loop_start()
            #self.client.enable_logger() #
            self.label.text = " connected"
            self.connection = True
        else:
            self.label.text = " already connected"
                
    def on_reset(self):
        if self.connection:
            if self.client.is_connected():
                self.client.disconnect()
                self.client.loop_stop()
                self.status_label.text = " Disconnected"
                self.connection = False
            else:
                self.status_label.text = " Service already disconnected"
        else:
            self.status_label.text = " Service already disconnected"
        for sensor_status in self.sensor_status_list:
            sensor_status.style = {"background_color": 0xFFC9C9C9}
        for item in self.data_table:
            try:
                prim = self.stage.GetPrimAtPath(item["prim_path"])
                material_binding = UsdShade.MaterialBindingAPI(prim)
                if material_binding:
                    material_binding.UnbindDirectBinding()
                    material_binding.UnbindAllBindings()
            except Exception as e:
                self.append_to_file(OUT_PATH, f"Error unbinding material: {e}")

    def zoom_to_prim(self, prim_path):
        #prim_path = "/World/Cone"  # Change to your prim's path
        prim = self.stage.GetPrimAtPath(prim_path)

        if not prim.IsValid():
            self.label.text = f" Error: No valid prim found at path {prim_path}"
            return

        ctx = omni.usd.get_context()
        ctx.get_selection().set_selected_prim_paths([prim_path], True)
        active_viewport = get_active_viewport()
        frame_viewport_selection(active_viewport)
        self.label.text = f" Framed prim at path: {prim_path}"

    def open_file_picker_dba(self):
        if not self.active_file:
            def on_apply(filename, dirname):
                full_path = dirname + "/" + filename
                self._load_excel_and_generate_buttons(full_path)
                # Explicitly close the file picker window
                picker.hide()
                #picker.destroy()
                return True  # Ensures hide_after_submit works

            # Create the picker instance so we can reference it
            picker = filepicker.FilePickerDialog(
                title="Select a Sensor Mapping Excel Workbook",
                apply_button_label="Open",
                click_apply_handler=on_apply,
                click_file_handler=on_apply, 
                file_extension_filters=["*.xlsx", "*.csv"],
                hide_after_submit=True,
                allow_multi_selection=False
            )

        else:
            self.status_label.text = (
                " File already selected. Please reload the extension to select a new file."
            )

    def on_file_selected(self, filepath):
        self.label.text = " No file selected"
        if not filepath:
            return
        
        self.label.text = f"Selected: {filepath}"

        try:
            # Read the Excel file using pandas
            df = pd.read_excel(filepath, engine='openpyxl')
            print("Excel DataFrame:")
            print(df)
            self.label.text = f" Dataframe initialized"

        except Exception as e:
            print(f"Error reading Excel file: {e}")
            self.label.text = f"Error: {e}"

    def open_file_picker(self):
        file_picker = filepicker.get_file_picker()
        file_picker.show_open_file_dialog(
            title="Select Excel File",
            apply_button_label="Open",
            file_filter="Excel Files (*.xlsx)",
            multi_select=False,
            callback= self.on_file_selected
        )


    def reload_extension(self):
        omni.ext.unload_extension(self.ext_id)
        omni.ext.reload_extension(self.ext_id)
            
    # endregion

    # region mqtt

    def simulate_incoming_messages(self, count=10, interval=2):
        def _simulate():
            for i in range(count):
                if i % 2 == 0:
                    simulated_payload = json.dumps({
                        "pointId": "TEST_xxxxx_xxxxx_V01",
                        "value": round(i * 10)
                    })
                else: 
                    simulated_payload = json.dumps({
                        "pointId": "TEST_xxxxx_xxxxx_PRD01",
                        "value": round(i * 5)
                    })
                try:
                    if self.real_data:
                        publish.single(
                            topic="Arena2036/omniverse/spie/demonstrator",
                            payload=simulated_payload,
                            hostname=MQTT_BROKER_HOST,
                            port=MQTT_BROKER_PORT,
                            auth={
                                'username': MQTT_USERNAME,
                                'password': MQTT_PASSWORD
                            },
                            tls={
                                'tls_version': ssl.PROTOCOL_TLS_CLIENT
                            }
                        )
                    else:
                        publish.single(
                            topic="test/topic",
                            payload=simulated_payload,
                            hostname="localhost",
                            port=1883
                        )
                    print(f"[SIM] Sent message {i+1}: {simulated_payload}")
                except Exception as e:
                    print(f"[SIM] Failed to send message {i+1}: {e}")
                time.sleep(interval)
        # Run in a separate thread
        sim_thread = Thread(target=_simulate, daemon=True)
        sim_thread.start()
#

    def on_shutdown(self):
        if self._window:
            self._window.destroy()
            self._window = None
        #self.client.loop_stop()


    def parse_json_string(self, input_str):
        try:
            # Safely evaluate the input string to a Python dict
            data = json.loads(input_str)
            return data
        except json.JSONDecodeError as e:
            print("Invalid JSON string:", e)
            return None


    def process_message(self, message_str):
        self.append_to_file(OUT_PATH, message_str)


    # Callback when connected
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.status_label.text = " Connected successfully."
            print("Connected successfully.")
            for topic, qos in MQTT_TOPICS:
                client.subscribe((topic, qos))
            #client.subscribe(MQTT_TOPIC)
        else:
            print(f"Connection failed with code {rc}")
            self.status_label.text = f" Connection failed with code {rc}"


    # Callback when a message is received
    def on_message(self, client, userdata, msg):

        if not self.data_table or not self.sensor_value_list or not self.sensor_status_list:
            self.status_label.text = f"[Warning] UI lists or data table not initialized yet."
            self.append_to_file(OUT_PATH, f"[Warning] UI lists or data table not initialized yet.")
            return

        message_str = msg.payload.decode("utf-8")
        task_queue.put(lambda: self.process_message(message_str))

        try:
            self.data = json.loads(message_str)
        except Exception as e:
            self.update_status(f"Failed to json load message:\n{e}")

        for index, sensor_item in enumerate(self.data_table):
            if sensor_item["mqtt_id"] in message_str:
                try:
                    matching_keys = [key for key, value in self.data.items() if sensor_item["mqtt_id"] in key or sensor_item["mqtt_id"] in str(value)]
                    
                    if not matching_keys:
                        # Fallback: check json string representation to handle unicode escapes (e.g. \u00b0)
                        matching_keys = [key for key, value in self.data.items() if sensor_item["mqtt_id"] in json.dumps(key) or sensor_item["mqtt_id"] in json.dumps(value)]
                        
                    self.append_to_file(OUT_PATH, f"Matching keys: {matching_keys}")
                except Exception as e:
                    matching_keys = False
                    self.append_to_file(OUT_PATH, f"An error occurred: {e}")
                    self.append_to_file(OUT_PATH, str(self.data))

                if matching_keys:
                    self.append_to_file(OUT_PATH, f"Matching Json entr found: {matching_keys[0]}")
                    try:
                        matched_key = matching_keys[0]
                        if sensor_item["mqtt_id"] in matched_key or sensor_item["mqtt_id"] in json.dumps(matched_key):
                             value = self.data[matched_key]
                        elif "0" in matched_key:
                            value = self.data["0.value"]
                        elif "1" in matched_key:
                            value =self.data["1.value"]
                        else:
                            value = self.data["value"]

                        rgb_color = self.calculate_color(float(value), float(sensor_item["min_value"]), float(sensor_item["max_value"]), sensor_item["min_color"], sensor_item["max_color"])
                        self.sensor_value_list[index].text = str(value)
                        self.status_style["background_color"] = int(self.rgb_to_hex(rgb_color), 16)
                        self.sensor_status_list[index].style = self.status_style
                        self.append_to_file(OUT_PATH, f"color {self.rgb_to_hex(rgb_color)}")
                        material_path = self.create_material_prim_path(sensor_item["prim_path"])
                        # recolor element in omniverse
                        self.change_color(sensor_item["prim_path"], rgb_color, material_path)
                    except Exception as e:
                        self.append_to_file(OUT_PATH, f"An error occurred (04): {e}")    
                name = sensor_item["name"]
                self.append_to_file(OUT_PATH, f"sensor {name} identified")

        userdata.append(msg.payload)

        if len(userdata) >= 10000:
            for topic, qos in MQTT_TOPICS:
                client.unsubscribe(topic)
                self.status_label.text = " Unsubscribed from all topics due to userdata limit reached."

    def simulate_mqtt(self):
        self.append_to_file(OUT_PATH, "Start Simulation")

        self.sim_index = 0
        self.sim_last_time = time.time()

        # Subscribe to per-frame update
        self._update_sub = omni.kit.app.get_app().get_update_event_stream().create_subscription_to_pop(
            self._on_simulate_update
        )
                
        self._update_sub2 = omni.kit.app.get_app().get_update_event_stream().create_subscription_to_pop(
            self._on_update
        )

    def _on_simulate_update(self, _):

        # Wait 2 seconds between messages
        if time.time() - self.sim_last_time < 2.0:
            return

        self.sim_last_time = time.time()


        if self.sim_index >= 20:
            self._update_sub = None  # Stop updates
            self.append_to_file(OUT_PATH, "Simulation finished.")
            return

        simple_data = False

        if simple_data:
            # Simulated data
            self.data = {
                "pointId": "_TEST_xxxxx_xxxxx_V01",
                "value": f"{random.uniform(20.0, 30.0):.2f}"
            }
        else:
            selected_index = random.randint(0, len(self.data_table) - 1)
            item = self.data_table[selected_index]
            min_value = float(item["min_value"])
            max_value = float(item["max_value"])
            self.data = {
                "pointId": item["mqtt_id"],
                "value": f"{random.uniform(min_value, max_value):.2f}"
            }



        #self.append_to_file(OUT_PATH, f"Message {self.sim_index + 1}: {self.data[0]['pointId']}")

        self.status_label.text = f" Simulating MQTT message [{self.sim_index + 1}]"
        task_queue.put(lambda: self.process_message(self.data))

        # Process the message   
        for index, sensor_item in enumerate(self.data_table):
            sensor_name = sensor_item["mqtt_id"]
            if sensor_item["mqtt_id"] in self.data or sensor_item["mqtt_id"] in str(self.data):
                self.append_to_file(OUT_PATH, f"indentified: {sensor_name}")
                try:
                    matching_keys = [key for key, value in self.data.items() if sensor_item["mqtt_id"] in str(value)]
                    self.append_to_file(OUT_PATH, str(matching_keys))
                except Exception as e:
                    matching_keys = False
                    self.append_to_file(OUT_PATH, f"An error occurred: {e}")
                    self.append_to_file(OUT_PATH, str(self.data))

                if matching_keys:
                    self.append_to_file(OUT_PATH, f"Matching Json entr found: {matching_keys[0]}")
                    try:
                        if "0" in matching_keys[0]:
                            value = float(self.data["0.value"])
                        elif "1" in matching_keys[0]:
                            value =float(self.data["1.value"])
                        else:
                            value = float(self.data["value"])

                        rgb_color = self.calculate_color(int(value), int(sensor_item["min_value"]), int(sensor_item["max_value"]), sensor_item["min_color"], sensor_item["max_color"])
                        self.sensor_value_list[index].text = str(value)
                        self.status_style["background_color"] = int(self.rgb_to_hex(rgb_color), 16)
                        self.sensor_status_list[index].style = self.status_style
                        self.append_to_file(OUT_PATH, f"color {self.rgb_to_hex(rgb_color)}")
                        material_path = self.create_material_prim_path(sensor_item["prim_path"])
                        # recolor element in omniverse
                        rgb_simple = ((rgb_color[0] / 255), (rgb_color[1] / 255), (rgb_color[2] / 255))
                        self.change_color(sensor_item["prim_path"], rgb_simple, material_path)
                    except Exception as e:
                        self.append_to_file(OUT_PATH, f"An error occurred (04): {e}")    
                name = sensor_item["name"]
                self.append_to_file(OUT_PATH, f"sensor {name} identified")

        self.sim_index += 1


    def create_mqtt_client(self):
        '''
        logger = logging.getLogger("mqtt_logger")
        logger.setLevel(logging.DEBUG)

        # Create a file handler that logs to your OUT_PATH
        handler = logging.FileHandler(OUT_PATH)
        handler.setLevel(logging.DEBUG)

        # Optional: Set format
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        # Add handler to logger
        logger.addHandler(handler)

        # Enable Paho MQTT client logging to this logger
        mqtt_logger = logging.getLogger("paho")
        mqtt_logger.setLevel(logging.DEBUG)
        mqtt_logger.addHandler(handler)
        '''

        # Create MQTT client and set callbacks
        self.client = mqtt.Client()
        self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

        self.append_to_file(OUT_PATH, f"MQTT Client created")

        # Enable TLS
        self.client.tls_set(
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS_CLIENT
        )

        self.client.tls_insecure_set(False)  # Set to True if using self-signed certs

        # Assign callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # Connect to the broker
        self.client.user_data_set([])
        self.client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT)

        # Start the loop to process network traffic and dispatch callbacks
        #self.client.loop_forever()
        
        self.update_sub = get_app().get_update_event_stream().create_subscription_to_push(
            self.on_update, name="CollectuUpdate"
        )

        self.append_to_file(OUT_PATH, f"MQTT Client created and connected to {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")

    def on_update(self, event):
        if self.data is not None:
            output_string = self.shorten_string(str(self.data), 70)
            self.label.text = (f" Received the following message: {output_string}")

    # endregion

    # region utility
    
    def rgb_to_hex(self, rgb):
        if not (isinstance(rgb, tuple) and len(rgb) == 3 and all(0 <= x <= 255 for x in rgb)):
            raise ValueError("Input must be a tuple of 3 integers between 0 and 255.")

        b, g, r = rgb
        #return f"0xFF{r:02X}{g:02X}{b:02X}"
        return f"0xFF{r:02X}{g:02X}{b:02X}"


    def calculate_color(self, value, min_value, max_value, min_color, max_color):
        min_color = min_color.split(",")
        for i in range(len(min_color)):
            min_color[i] = int(min_color[i].strip())
        max_color = max_color.split(",")
        for i in range(len(max_color)):
            max_color[i] = int(max_color[i].strip())    
        """
        Calculate a color based on the value's position between min_value and max_value.
        min_color and max_color should be tuples of (R, G, B).
        """
        if value < min_value:
            return min_color
        elif value > max_value:
            return max_color
        else:
            ratio = (value - min_value) / (max_value - min_value)
            r = int(min_color[0] + ratio * (max_color[0] - min_color[0]))
            g = int(min_color[1] + ratio * (max_color[1] - min_color[1]))
            b = int(min_color[2] + ratio * (max_color[2] - min_color[2]))
            return (r, g, b)


    def append_to_file(self, file_path, text_to_append):
        try:
            with open(file_path, 'a', encoding='utf-8') as file:
                file.write(text_to_append + '\n')
            #self.status_label.text = f"Successfully appended {text_to_append} to {file_path}"
        except Exception as e:
            pass
            #self.status_label.text = f"An error occurred: {e}"

    def create_material_prim_path(self, prim_path: str) -> str:
        """
        Given a Prim path like "/World/Sensors/Test/SEN_Vent",
        returns a Material Prim path like "/World/Looks/Sensors-Test-SEN_Vent".
        """
        if not prim_path.startswith("/World/"):
            raise ValueError("Prim path must start with '/World/'")

        # Remove the "/World/" prefix and split the rest by "/"
        path_parts = prim_path[len("/World/"):].split("/")

        if len(path_parts) < 1:
            raise ValueError("Prim path must contain at least one subpath after '/World/'")

        # Join path parts with "-" and prepend "/World/Looks/"
        material_name = "-".join(path_parts)
        material_name = self.maybe_replace_string(material_name, 20)
        self.append_to_file(OUT_PATH, f"Creating material path {material_name}")
        return f"/World/Looks/{material_name}"
    
    def string_to_usd_path(self, input_str: str) -> Sdf.Path:
        # Replace invalid characters and normalize
        cleaned = input_str.strip().replace(" ", "_").replace("\\", "/")
        
        # Ensure it starts with a slash
        if not cleaned.startswith("/"):
            cleaned = "/" + cleaned

        # Return an Sdf.Path object
        return Sdf.Path(cleaned)
    
    def shorten_string(self, input_str: str, max_length: int) -> str:
        if len(input_str) <= max_length:
            return input_str

        if max_length <= 3:
            return '.' * max_length

        # Reserve space for "..."
        part_length = (max_length - 3) // 2
        extra_char = (max_length - 3) % 2  # Handle odd max_length

        start = input_str[:part_length + extra_char]
        end = input_str[-part_length:]

        return f"{start}...{end}"

    def maybe_replace_string(self, input_str, max_length):
        """
        Replace input_str with a 12-character random string if its length exceeds max_length.
        
        Args:
            input_str (str): The original string to evaluate.
            max_length (int): The threshold length.

        Returns:
            str: Either the original string or a 12-character random string.
        """
        if len(input_str) > max_length:
            return ''.join(random.choices(string.ascii_lowercase, k=12))
        return input_str

    # region model coloring


    def change_color(self, prim_path: str, rgb_color, material_path: str):
        self.append_to_file(OUT_PATH, "Material Binding started")

        def do_binding():
            prim_usd_path = self.string_to_usd_path(prim_path)
            material_usd_path = self.string_to_usd_path(material_path)

            self.append_to_file(OUT_PATH, "Function do_binding started")
            try:
                stage = omni.usd.get_context().get_stage()
                if not stage:
                    self.append_to_file(OUT_PATH, "[MaterialChanger] No USD stage open.")
                    return

                # Define or get the material prim
                material_prim = stage.GetPrimAtPath(material_path)
                if not material_prim.IsValid():
                    self.append_to_file(OUT_PATH, "MatCreation started")
                    material_prim = stage.DefinePrim(material_path, "Material")
                    if not material_prim.IsValid():
                        self.append_to_file(OUT_PATH, f"Failed to define material prim at {material_path}")
                        return
                else:
                    self.append_to_file(OUT_PATH, "MatRecycling started")

                material = UsdShade.Material.Define(stage, material_path)
                if not material.GetPrim().IsValid():
                    self.append_to_file(OUT_PATH, f"Failed to define UsdShade.Material at {material_path}")
                    return

                # Define or get the shader
                shader_path = material_usd_path.AppendPath("Shader")
                shader = UsdShade.Shader.Get(stage, shader_path)
                if not shader or not shader.GetPrim().IsValid():
                    shader = UsdShade.Shader.Define(stage, shader_path)
                    if not shader.GetPrim().IsValid():
                        self.append_to_file(OUT_PATH, f"Failed to define shader at {shader_path}")
                        return
                    shader.CreateIdAttr("UsdPreviewSurface")

                # Set the shader color
                shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgb_color))

                # Create and connect shader output
                shader_output = shader.GetOutput("surface")
                if not shader_output:
                    shader_output = shader.CreateOutput("surface", Sdf.ValueTypeNames.Token)

                material_output = material.CreateOutput("surface", Sdf.ValueTypeNames.Token)
                if not material_output or not shader_output:
                    self.append_to_file(OUT_PATH, "Failed to create outputs for material-shader connection.")
                    return

                material_output.ConnectToSource(shader_output)

                if material_prim.IsValid():
                    self.append_to_file(OUT_PATH, "MatRecycling finished")

                # Get the target prim
                prim = stage.GetPrimAtPath(prim_path)
                if not prim.IsValid():
                    self.append_to_file(OUT_PATH, f"Error: Prim at path {prim_path} does not exist.")
                    return

                # Bind material
                material_binding = UsdShade.MaterialBindingAPI(prim)
                if material_binding:
                    material_binding.UnbindDirectBinding()
                    material_binding.UnbindAllBindings()

                UsdShade.MaterialBindingAPI(prim).Bind(material)
                self.append_to_file(
                    OUT_PATH,
                    f"Material '{material_path}' bound to prim '{prim_path}' with color {rgb_color}"
                )

            except Exception as e:
                self.append_to_file(OUT_PATH, f"Error at Material Assignment: {e}")

        # Enqueue function to be safely run on main thread
        task_queue.put(do_binding)


    def _on_update(self, e):
        while not task_queue.empty():
            try:
                fn = task_queue.get_nowait()
                fn()  # Execute the queued main-thread-safe function
            except Exception as ex:
                print("[MaterialChangerExtension] Error during task execution:", ex)


    # endregion