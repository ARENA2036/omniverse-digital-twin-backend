import omni.ui as ui
import omni.kit.window.filepicker as filepicker
import pandas as pd
from functools import partial
import asyncio
from .constants import WINDOW_TITLE, WINDOW_WIDTH, BUTTON_HEIGHT, STATUS_STYLE_DISCONNECTED

class UiPanel:
    def __init__(self, callbacks):
        self._callbacks = callbacks # dict of functions like 'on_connect', 'on_zoom', etc.
        self._window = None
        self._sensor_rows = [] # stores UI widgets for each sensor
        self.status_label = None
        self.main_label = None

    def build_ui(self):
        self._window = ui.Window(WINDOW_TITLE, width=WINDOW_WIDTH)
        with self._window.frame:
            with ui.VStack(spacing=5):
                # Header
                ui.Button("Select Sensors File (.xlsx)", height=BUTTON_HEIGHT, clicked_fn=self._open_file_picker)
                
                # Dynamic Content
                self._sensor_container = ui.ScrollingFrame()
                with self._sensor_container:
                     self._sensor_list_vstack = ui.VStack(spacing=2)

    def _open_file_picker(self):
         def on_apply(filename, dirname):
            full_path = f"{dirname}/{filename}"
            self._callbacks['on_file_selected'](full_path)
            picker.hide()
            return True

         picker = filepicker.FilePickerDialog(
            title="Select Sensor Config",
            apply_button_label="Load",
            click_apply_handler=on_apply,
            click_file_handler=on_apply,
            file_extension_filters=["*.xlsx", "*.csv"],
            allow_multi_selection=False,
            hide_after_submit=True
        )

    def load_sensor_list(self, file_path):
        self._sensor_list_vstack.clear()
        self._sensor_rows = []
        
        try:
            df = pd.read_excel(file_path, engine='openpyxl')
        except Exception as e:
            with self._sensor_list_vstack:
                ui.Label(f"Error loading file: {e}")
            return []

        sensor_data = []
        
        with self._sensor_list_vstack:
             # Control Bar
             with ui.HStack(height=BUTTON_HEIGHT):
                 ui.Button("Connect", clicked_fn=self._callbacks['on_connect'])
                 ui.Button("Disconnect", clicked_fn=self._callbacks['on_disconnect'])
                 ui.Button("Simulate", clicked_fn=self._callbacks['on_simulate'])
                 self.status_label = ui.Label("Ready", width=200)

             ui.Separator(height=10)

             # Sensor List
             for index, row in df.iterrows():
                 # Handle missing columns safely
                 try:
                     s_name = str(row.iloc[0]) if pd.notna(row.iloc[0]) else "Unnamed"
                     s_unit = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
                     s_mqtt = str(row.iloc[2]) if pd.notna(row.iloc[2]) else ""
                     s_prim = str(row.iloc[3]) if pd.notna(row.iloc[3]) else ""
                     s_min = float(row.iloc[4]) if pd.notna(row.iloc[4]) else 0.0
                     s_max = float(row.iloc[5]) if pd.notna(row.iloc[5]) else 100.0
                     s_min_c = str(row.iloc[6]) if pd.notna(row.iloc[6]) else "0,0,0"
                     s_max_c = str(row.iloc[7]) if pd.notna(row.iloc[7]) else "255,255,255"

                     sensor_dict = {
                         "name": s_name, "unit": s_unit, "mqtt_id": s_mqtt,
                         "prim_path": s_prim, "min_value": s_min, "max_value": s_max,
                         "min_color": s_min_c, "max_color": s_max_c
                     }
                     sensor_data.append(sensor_dict)

                     # Build Row UI
                     with ui.HStack(height=BUTTON_HEIGHT):
                         indicator = ui.Circle(width=20, height=20, style=STATUS_STYLE_DISCONNECTED)
                         ui.Spacer(width=5)
                         ui.Button("Zoom", width=50, clicked_fn=partial(self._callbacks['on_zoom'], s_prim))
                         ui.Label(s_name, width=150)
                         val_label = ui.Label("-", width=50)
                         ui.Label(s_unit, width=50)
                     
                     self._sensor_rows.append({
                         "indicator": indicator,
                         "value_label": val_label,
                         "data": sensor_dict
                     })
                 except Exception:
                     continue
        
        return sensor_data, self._sensor_rows

    def update_sensor_row(self, index, value, color_hex):
        if 0 <= index < len(self._sensor_rows):
            row = self._sensor_rows[index]
            row["value_label"].text = str(value)
            row["indicator"].style = {"background_color": int(color_hex, 16)}

    def update_status(self, text):
        if self.status_label:
            self.status_label.text = text

    def destroy(self):
        if self._window:
            self._window.destroy()
            self._window = None
