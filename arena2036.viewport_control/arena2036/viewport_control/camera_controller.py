import omni.kit.viewport.utility
from pxr import Gf, UsdGeom, Usd
import omni.usd
import omni.kit.commands
import carb

class CameraController:
    """
    Controls the active viewport camera.
    """
    def __init__(self):
        self.translation_speed = 1.0
        self.rotation_speed = 5.0

    def _get_active_camera_prim(self):
        # Use the utility helper which abstracts away API differences
        camera_path = omni.kit.viewport.utility.get_active_viewport_camera_path()
        carb.log_info(f"[Viewport Control] _get_active_camera_prim camera_path: {camera_path}")
        if not camera_path:
            carb.log_warn("[Viewport Control] Could not determine active viewport camera path.")
            return None
        
        stage = omni.usd.get_context().get_stage()
        if not stage:
            carb.log_warn("[Viewport Control] get_stage returned None.")
            return None

        prim = stage.GetPrimAtPath(camera_path)
        if not prim:
            carb.log_warn(f"[Viewport Control] GetPrimAtPath returned None for path: {camera_path}")
        return prim

    def move_forward(self, speed: float = None):
        self._move_local(Gf.Vec3d(0, 0, -1), speed)

    def move_backward(self, speed: float = None):
        self._move_local(Gf.Vec3d(0, 0, 1), speed)

    def move_left(self, speed: float = None):
        self._move_local(Gf.Vec3d(-1, 0, 0), speed)

    def move_right(self, speed: float = None):
        self._move_local(Gf.Vec3d(1, 0, 0), speed)
        
    def move_up(self, speed: float = None):
        self._move_local(Gf.Vec3d(0, 1, 0), speed)

    def move_down(self, speed: float = None):
        self._move_local(Gf.Vec3d(0, -1, 0), speed)
        
    def zoom_in(self, speed: float = None):
        self.move_forward(speed)

    def zoom_out(self, speed: float = None):
        self.move_backward(speed)

    def rotate_left(self, speed: float = None):
        self._rotate_y(speed if speed else self.rotation_speed)

    def rotate_right(self, speed: float = None):
        self._rotate_y(-(speed if speed else self.rotation_speed))

    def _move_local(self, direction: Gf.Vec3d, speed: float = None):
        prim = self._get_active_camera_prim()
        if not prim:
            carb.log_warn("[Viewport Control] No active camera prim found.")
            return
            
        xform = UsdGeom.Xformable(prim)
        world_transform = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        
        rotation = world_transform.ExtractRotation()
        move_vector = rotation.TransformDir(direction)
        
        move_amount = speed if speed else self.translation_speed
        
        # Local translation matrix
        local_translation = direction * move_amount
        local_transform = Gf.Matrix4d().SetTranslate(local_translation)
        
        new_world_transform = local_transform * world_transform
        
        self._set_world_transform(prim, new_world_transform)

    def _rotate_y(self, angle_degrees: float):
        prim = self._get_active_camera_prim()
        if not prim:
            carb.log_warn("[Viewport Control] No active camera prim found.")
            return

        xform = UsdGeom.Xformable(prim)
        current_world_transform = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        
        # Local Y rotation
        rotate_transform = Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0, 1, 0), angle_degrees))
        
        # New = Rotate * Old
        new_world_transform = rotate_transform * current_world_transform
        
        self._set_world_transform(prim, new_world_transform)

    def _set_world_transform(self, prim, new_transform_matrix):
        path_str = prim.GetPath().pathString
        carb.log_info(f"[Viewport Control] Moving camera '{path_str}'")
        omni.kit.commands.execute("TransformPrim", path=path_str, new_transform_matrix=new_transform_matrix)
