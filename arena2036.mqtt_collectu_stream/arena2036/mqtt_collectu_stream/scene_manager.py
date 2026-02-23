import omni.usd
from pxr import Usd, UsdGeom, Gf, Sdf, UsdShade
from omni.kit.viewport.utility import get_active_viewport, frame_viewport_selection
import carb
import random
import string

class SceneManager:
    def __init__(self):
        self.usd_context = omni.usd.get_context()
        self.stage = self.usd_context.get_stage()

    def update_stage(self):
        self.usd_context = omni.usd.get_context()
        self.stage = self.usd_context.get_stage()
        carb.log_info("Stage updated in SceneManager")

    def zoom_to_prim(self, prim_path):
        if not self.stage:
            self.update_stage()
        
        prim = self.stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            carb.log_warn(f"No valid prim found at path {prim_path}")
            return False

        ctx = omni.usd.get_context()
        ctx.get_selection().set_selected_prim_paths([prim_path], True)
        active_viewport = get_active_viewport()
        frame_viewport_selection(active_viewport)
        return True

    def calculate_color(self, value, min_value, max_value, min_color_str, max_color_str):
        def parse_color(color_str):
            parts = color_str.split(",")
            return [int(p.strip()) for p in parts]

        min_color = parse_color(min_color_str)
        max_color = parse_color(max_color_str)

        if value < min_value:
            return tuple(min_color)
        elif value > max_value:
            return tuple(max_color)
        else:
            ratio = (value - min_value) / (max_value - min_value)
            r = int(min_color[0] + ratio * (max_color[0] - min_color[0]))
            g = int(min_color[1] + ratio * (max_color[1] - min_color[1]))
            b = int(min_color[2] + ratio * (max_color[2] - min_color[2]))
            return (r, g, b)

    def rgb_to_hex(self, rgb):
        r, g, b = rgb
        return f"0xFF{r:02X}{g:02X}{b:02X}"

    def change_color(self, prim_path, rgb_color):
        if not self.stage:
            self.update_stage()
        
        material_path = self._create_material_prim_path(prim_path)
        rgb_normalized = ((rgb_color[0] / 255.0), (rgb_color[1] / 255.0), (rgb_color[2] / 255.0))
        
        self._apply_material(prim_path, material_path, rgb_normalized)
        return rgb_normalized

    def _create_material_prim_path(self, prim_path):
        if not prim_path.startswith("/World/"):
             # Fallback if path doesn't start with World, though it should based on legacy code
             cleaned = prim_path.strip("/").replace("/", "-")
             return f"/World/Looks/{cleaned}"
        
        path_parts = prim_path[len("/World/"):].split("/")
        material_name = "-".join(path_parts)
        if len(material_name) > 20:
             material_name = ''.join(random.choices(string.ascii_lowercase, k=12))
        return f"/World/Looks/{material_name}"

    def _apply_material(self, prim_path, material_path, rgb_color):
        try:
            stage = self.stage
            
            # 1. Define Material
            material = UsdShade.Material.Define(stage, material_path)
            
            # 2. Define Shader
            shader_path = Sdf.Path(material_path).AppendPath("Shader")
            shader = UsdShade.Shader.Define(stage, shader_path)
            shader.CreateIdAttr("UsdPreviewSurface")
            shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgb_color))

            # 3. Connect Output
            shader_output = shader.CreateOutput("surface", Sdf.ValueTypeNames.Token)
            material_output = material.CreateOutput("surface", Sdf.ValueTypeNames.Token)
            material_output.ConnectToSource(shader_output)

            # 4. Bind to Prim
            prim = stage.GetPrimAtPath(prim_path)
            if prim.IsValid():
                UsdShade.MaterialBindingAPI(prim).Bind(material)
            else:
                carb.log_warn(f"Prim {prim_path} invalid during binding")

        except Exception as e:
            carb.log_error(f"Error applying material: {e}")

    def reset_materials(self, sensor_list):
        if not self.stage: return
        for item in sensor_list:
            try:
                prim = self.stage.GetPrimAtPath(item["prim_path"])
                if prim.IsValid():
                    binding = UsdShade.MaterialBindingAPI(prim)
                    binding.UnbindAllBindings()
            except Exception:
                pass
