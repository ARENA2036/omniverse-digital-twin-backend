# Omniverse Digital Twin Backend

**Repository**: `omniverse-digital-twin-backend`  
**Focus**: Backend extensions for the ARENA2036 Digital Twin.

## Overview

This repository hosts a collection of **NVIDIA Omniverse extensions** that serve as the backend for the ARENA2036 Digital Twin. The core philosophy is to **decouple** the high-fidelity digital twin simulation from the frontend interfaces (web dashboards, mobile apps, kiosks).

By exposing control and feedback mechanisms through **interactive event streams**, we create a low-barrier entry point for clients, team members, and events to interact with the Digital Twin without needing deep knowledge of USD or Omniverse.

## Architecture

The backend operates as a set of modular extensions loaded into Omniverse Kit (e.g., USD Explorer). It communicates with external frontends via **Omniverse Livestreaming** and **Custom Events**.

- **Frontend**: Sends commands (e.g., "Show Filter X", "Move Camera Here") via WebRTC data channels or WebSocket.
- **Backend (This Repo)**: Listens for these events and manipulates the USD stage or Viewport in real-time.

## Extensions

### 1. `arena2036.usd_explorer_filters`
**Purpose**: Interactive filtering and highlighting of USD stage elements.
- **Function**: Listens for toggle commands to highlight specific partner sectors or asset groups (e.g., "Bosch Rexroth").
- **Features**: 
  - Dynamic material highlighting.
  - CSV-backed metadata mapping.
  - UI Panel for manual control.

### 2. `arena2036.viewport_control`
**Purpose**: Remote camera control for guided tours or interactive navigation.
- **Function**: Listens for navigation commands (`move_forward`, `rotate_left`, `zoom_in`).
- **Features**:
  - Smooth camera movement.
  - Livestream event integration (`CameraControl` event).

## Getting Started

1.  **Clone this repository** to your local machine.
2.  **Add to Omniverse**: In the Omniverse Extension Manager, add the path to this repository's root or specific extension folders.
3.  **Enable Extensions**: Toggle on `arena2036.usd_explorer_filters` and `arena2036.viewport_control`.
4.  **Connect Client**: Start a Livestream session and connect your web frontend to send commands.

## Contribution

- **New Extensions**: Create a new folder `arena2036.new_extension` and follow the standard extension structure.
- **Namespace**: All extensions use the `arena2036` namespace.
