import omni.kit.viewport.utility
from pxr import Gf, UsdGeom

class CameraController:
    """
    Controls the active viewport camera.
    """
    def __init__(self):
        self._default_speed = 100.0
        self._default_rotation_speed = 5.0

    def _get_active_camera_prim(self):
        viewport_window = omni.kit.viewport.utility.get_active_viewport_window()
        if not viewport_window:
            return None
        
        stage = omni.usd.get_context().get_stage()
        if not stage:
            return None

        camera_path = viewport_window.get_active_camera()
        if not camera_path:
            return None
            
        return stage.GetPrimAtPath(camera_path)

    def move_forward(self, speed: float = None):
        self._move_local(Gf.Vec3d(0, 0, -1), speed)

    def move_backward(self, speed: float = None):
        self._move_local(Gf.Vec3d(0, 0, 1), speed)

    def move_left(self, speed: float = None):
        self._move_local(Gf.Vec3d(-1, 0, 0), speed)

    def move_right(self, speed: float = None):
        self._move_local(Gf.Vec3d(1, 0, 0), speed)
        
    def zoom_in(self, speed: float = None):
        # Zooming is often similar to moving forward, or changing focal length.
        # For simplicity, we'll treat it as moving forward.
        self.move_forward(speed)

    def zoom_out(self, speed: float = None):
        self.move_backward(speed)

    def rotate_left(self, speed: float = None):
        self._rotate_y(speed if speed else self._default_rotation_speed)

    def rotate_right(self, speed: float = None):
        self._rotate_y(-(speed if speed else self._default_rotation_speed))

    def _move_local(self, direction: Gf.Vec3d, speed: float = None):
        prim = self._get_active_camera_prim()
        if not prim:
            return
            
        xform = UsdGeom.Xformable(prim)
        world_transform = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        
        # Extract rotation from world transform to apply movement in local space direction
        rotation = world_transform.ExtractRotation()
        
        # Transform direction by rotation to get world space delta
        move_vector = rotation.TransformDir(direction)
        
        move_amount = speed if speed else self._default_speed
        move_delta = move_vector * move_amount
        
        # Apply translation
        # We need to find or create xformOp:translate
        # Ideally we should use the omni.kit.commands for undo support but 
        # direct USD manipulation is requested/implied for speed/direct control usually.
        # However, for an extension, let's try to be clean.
        
        # Actually, let's stick to direct manipulation for now as it's common for realtime control.
        # But we must be careful about existing ops.
        
        # Simplified approach: Get local transform, modify it, set it back.
        # Note: This might conflict if there are complex xform stacks.
        # A safer bet for camera control is often just updating the world transform if possible, 
        # but pure local translate op is most robust if available.
        
        # Let's try to find a translate op or add one.
        
        translate_op = None
        for op in xform.GetOrderedXformOps():
            if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
                translate_op = op
                break
        
        if not translate_op:
            translate_op = xform.AddTranslateOp()
            
        current_translate = translate_op.Get()
        if not current_translate:
            current_translate = Gf.Vec3d(0, 0, 0)
            
        # Wait, if we move in local direction (e.g. forward), we need to know the camera's orientation.
        # The logic above calculated `move_delta` in world coordinates.
        # So we should add `move_delta` to the current position (if distinct from translation).
        # CAUTION: If the camera has parent transforms, "world" move needs to be converted to local parent space.
        
        # Let's use omni.usd.utils to set world transform if possible?
        # Or just assume simple camera setup (root or simple hierarchy).
        
        # Let's Refine:
        # 1. Get World Transform
        # 2. Translate in World Space locally oriented
        # 3. Set World Transform
        
        # Better: use Gf.Matrix4d for everything.
        
        current_world_transform = world_transform
        
        # Local translation vector
        local_translation = direction * (speed if speed else self._default_speed)
        
        # Create a translation matrix
        # But we want to translate relative to the camera's current orientation
        # Camera Base (Rotation)
        
        # Matrix multiplication order: T * R or R * T depending on "move locally" or "move globally"
        # We want to move "forward" which is local -Z.
        
        # New World = Translation(local_translation) * Old World
        # Wait, usually:  New = Old * LocalDelta  (Post-multiply for local op)
        
        local_transform = Gf.Matrix4d().SetTranslate(local_translation)
        
        new_world_transform = local_transform * current_world_transform
        
        # Now set this back.
        self._set_world_transform(prim, new_world_transform)

    def _rotate_y(self, angle_degrees: float):
        prim = self._get_active_camera_prim()
        if not prim:
            return

        xform = UsdGeom.Xformable(prim)
        current_world_transform = xform.ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        
        # We want to rotate around the camera's "up" vector? Or the World Up?
        # Requirement: "rotate over the up vector of the camera viewport"
        # Usually checking "up" of the camera.
        
        # Local Y rotation
        rotate_transform = Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0, 1, 0), angle_degrees))
        
        # New = Rotate * Old (Pre-multiply?) No, Local rotation is usually Post-multiply?
        # If we want to strictly rotate around the LOCAL Y axis:
        new_world_transform = rotate_transform * current_world_transform
        
        self._set_world_transform(prim, new_world_transform)

    def _set_world_transform(self, prim, new_transform_matrix):
        # This helper from omni.usd is very useful
        import omni.usd
        
        # Note: This sets the local transform such that the world transform becomes `new_transform_matrix`
        # It handles parent transforms automatically.
        omni.kit.commands.execute("TransformPrim", path=prim.GetPath(), new_transform_matrix=new_transform_matrix)
