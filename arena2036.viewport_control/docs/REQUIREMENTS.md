# Requirements Specification: Viewport Control

## Functional Requirements

1.  **Command Reception**:
    - MUST accept `CameraControl` events from `omni.kit.livestream.core`.
    - MUST support commands: `move_forward`, `move_backward`, `move_left`, `move_right`, `rotate_left`, `rotate_right`, `zoom_in`, `zoom_out`.
2.  **Camera Manipulation**:
    - MUST act on the *currently active* viewport camera.
    - Movement MUST be relative to the camera's local orientation (e.g., "forward" is along the camera's negative Z axis).
    - Rotation MUST be around the camera's local Y axis (pan) or X axis (tilt - if implemented).
3.  **Concurrency**:
    - MUST handle rapid fire events without crashing (thread safety check implicit in Kit's main thread event handling).

## Non-Functional Requirements

1.  **Latency**: Processing of a command to USD update should be < 16ms (1 frame @ 60fps) to ensure responsive feel.
2.  **Safety**: Invalid commands or missing values should be logged but ignored.
3.  **Compatibility**: Must work with standard UsdGeom.Camera primitives.
