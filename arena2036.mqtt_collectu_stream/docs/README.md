# ARENA2036 MQTT Collectu Stream Extension

**Extension ID:** `arena2036.mqtt_collectu_stream`  
**Version:** 1.1.0  
**Authors:** digitales bauen GmbH - Tim Schumann, Michael Hernandez

## Overview

The `arena2036.mqtt_collectu_stream` extension is a specialized plugin for the ARENA2036 Digital Twin in NVIDIA Omniverse. It facilitates real-time data streaming and continuous monitoring of sensor data via MQTT. The extension allows users to visualize sensor data directly within the 3D environment, mapping live values to visual properties of US D Prims.

## Features

- **MQTT Connectivity**: Connects to the Collectu MQTT broker to receive real-time sensor data.
- **Data Visualization**: Maps sensor values (e.g., temperature, humidity) to color gradients on 3D objects.
- **Excel/CSV Configuration**: Easily map MQTT topics to USD Prims using an external configuration file.
- **Zoom & Focus**: Quickly locate and zoom into specific sensors within the massive digital twin.
- **Simulation Mode**: Includes a simulation mode to test data flow and visualization without a live connection.
- **Material Management**: Automatically manages and binds materials to Prims based on data states.

## Installation

1.  Ensure you have NVIDIA Omniverse Kit installed.
2.  Add the folder containing this extension to your Omniverse Extension path.
3.  Open the **Extensions** window (`Window ` -> `Extensions`).
4.  Search for "ARENA2036 MQTT Collectu Stream".
5.  Enable the extension.

## Usage

1.  **Open the UI**: Upon enabling, the "Arena2036 MQTT Stream" window will appear.
2.  **Load Configuration**:
    - Click "Select Sensors File (.xlsx)".
    - Choose your sensor mapping Excel file.
    - The UI will populate with a list of configured sensors.
3.  **Connect**:
    - Click "Connect to Sensors" to establish a connection to the MQTT broker.
    - The status indicators will update as data is received.
4.  **Simulate**:
    - If no live data is available, use "Simulate Sensor Messages" or "Simulate MQTT Access" to verify visual feedback.
5.  **Navigation**:
    - Click the "Zoom" button next to any sensor to frame it in the viewport.

## Configuration File Format

The extension accepts `.xlsx` files with the following columns:
1.  **Name**: Display name of the sensor.
2.  **Unit**: Unit of measurement (e.g., "°C").
3.  **MQTT ID**: The unique identifier in the MQTT payload.
4.  **Prim Path**: Full USD path to the 3D object representation.
5.  **Min Value**: Lower bound for color interpolation.
6.  **Max Value**: Upper bound for color interpolation.
7.  **Min Color**: RGB code (e.g., "0, 0, 255") for minimum value.
8.  **Max Color**: RGB code (e.g., "255, 0, 0") for maximum value.

## Troubleshooting

- **Connection Failed**: Check your internet connection and ensure the MQTT broker credentials are up to date in the source code if hardcoded, or accessible.
- **No Color Change**: Verify the `Prim Path` in your Excel file matches exactly with the USD stage hierarchy. Ensure the Prims are visible and have valid geometry.

## License

Copyright (c) 2026 ARENA2036. All rights reserved.
