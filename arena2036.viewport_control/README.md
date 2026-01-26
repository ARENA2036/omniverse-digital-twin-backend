# Arena2036 Viewport Control

**Extension Name:** `arena2036.viewport_control`  
**Version:** 0.1.0  
**Category:** Simulation

## Overview

The **Viewport Control** extension enables remote camera manipulation within the NVIDIA Omniverse Viewport. It acts as a bridge between the digital twin frontend and the USD stage, allowing users to navigate the 3D environment using external controls (gamepads, web buttons, keyboard).

## Features

*   **Remote Navigation**: Commands for `move_forward`, `rotate_left`, `zoom_in`, etc.
*   **Livestream Integration**: Listens for `CameraControl` events via `omni.kit.livestream.core`.
*   **Smooth Control**: Maps discrete commands to camera primitives.

## Installation & Usage

1.  **Load the Extension**: Enable `arena2036.viewport_control`.
2.  **Connect Client**: Use a frontend that emits `CameraControl` events via Livestream.
3.  **Control**: The active viewport camera will respond to the commands.

## Dependencies

*   `omni.kit.livestream.core`
*   `omni.kit.viewport.utility`
*   `omni.usd`
