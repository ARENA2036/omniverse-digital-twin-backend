import omni.ui as ui
from .camera_controller import CameraController

def build_panel(controller: CameraController) -> None:
    """
    Builds the debug UI for the Viewport Control extension.
    
    Args:
        controller: The CameraController instance to invoke actions on.
    """
    with ui.VStack(spacing=10, height=0, style={"margin": 10}):
        ui.Label("Camera Navigation", style={"font_size": 18})
        
        # D-Pad for Movement (Forward/Back/Left/Right)
        with ui.VStack(alignment=ui.Alignment.CENTER, spacing=2):
            ui.Button("Forward", width=100, clicked_fn=lambda: controller.move_forward())
            with ui.HStack(spacing=2, width=0):
                ui.Button("Left", width=100, clicked_fn=lambda: controller.move_left())
                ui.Button("Right", width=100, clicked_fn=lambda: controller.move_right())
            ui.Button("Backward", width=100, clicked_fn=lambda: controller.move_backward())

        ui.Spacer(height=10)
        ui.Label("Rotation", style={"font_size": 14})
        with ui.HStack(alignment=ui.Alignment.CENTER, spacing=5, width=0):
            ui.Button("Rot Left", width=80, clicked_fn=lambda: controller.rotate_left())
            ui.Button("Rot Right", width=80, clicked_fn=lambda: controller.rotate_right())

        ui.Spacer(height=10)
        ui.Label("Zoom", style={"font_size": 14})
        with ui.HStack(alignment=ui.Alignment.CENTER, spacing=5, width=0):
            ui.Button("Zoom In", width=80, clicked_fn=lambda: controller.zoom_in())
            ui.Button("Zoom Out", width=80, clicked_fn=lambda: controller.zoom_out())

        ui.Spacer(height=10)
        ui.Label("Settings", style={"font_size": 14})
        with ui.VStack(spacing=5):
            # Translation Speed
            with ui.HStack(height=20):
                ui.Label("Translation Speed", width=120)
                trans_model = ui.SimpleFloatModel(controller.translation_speed)
                trans_model.add_value_changed_fn(lambda m: setattr(controller, "translation_speed", m.as_float))
                ui.FloatField(model=trans_model)

            # Rotation Speed
            with ui.HStack(height=20):
                ui.Label("Rotation Speed", width=120)
                rot_model = ui.SimpleFloatModel(controller.rotation_speed)
                rot_model.add_value_changed_fn(lambda m: setattr(controller, "rotation_speed", m.as_float))
                ui.FloatField(model=rot_model)
