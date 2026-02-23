import paho.mqtt.client as mqtt
import ssl
import json
import threading
import time
import carb
from .constants import MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_USERNAME, MQTT_PASSWORD, MQTT_TOPICS

class MqttClient:
    def __init__(self, on_message_callback):
        self._client = mqtt.Client()
        self._client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self._client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)
        self._client.tls_insecure_set(False)
        self._on_message_callback = on_message_callback
        self._connected = False
        
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

    def connect(self):
        if not self._connected:
            try:
                carb.log_info(f"Connecting to MQTT Broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
                self._client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT)
                self._client.loop_start()
                return True
            except Exception as e:
                carb.log_error(f"Failed to connect to MQTT broker: {e}")
                return False
        return True

    def disconnect(self):
        if self._connected:
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False
            carb.log_info("Disconnected from MQTT Broker")

    def is_connected(self):
        return self._connected

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            carb.log_info("Connected to MQTT Broker successfully")
            for topic, qos in MQTT_TOPICS:
                client.subscribe((topic, qos))
                carb.log_info(f"Subscribed to topic: {topic}")
        else:
            carb.log_error(f"MQTT Connection failed with code {rc}")
            self._connected = False

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        carb.log_info(f"Disconnected with result code {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8")
            # We don't need to parse it here, just pass the raw string or parsed json to the callback
            # The original code parsed it in the process logic.
            # But let's verify it's valid string at least.
            self._on_message_callback(payload)
        except Exception as e:
            carb.log_error(f"Error processing message payload: {e}")
