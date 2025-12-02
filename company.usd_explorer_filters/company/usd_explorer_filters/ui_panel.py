import omni.ui as ui
from pxr import Usd, UsdGeom, UsdShade, Sdf
import omni.usd
import carb
import omni.kit.viewport.utility as vp_utils
import omni.kit.commands as kit_commands
from typing import Dict, Optional, Any, List
from collections import defaultdict
from . import csv_bridge

# ------------------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------------------

# Path to the highlight material in the USD stage.
# This material must exist for highlighting to work.
HIGHLIGHT_MAT_PATH = "/World/Looks/Highlight_Mat"

# ------------------------------------------------------------------------------
# State Management
# ------------------------------------------------------------------------------

# Store original material bindings per prim to allow restoration.
# Mapping: prim_path (str) -> original_material_path (Sdf.Path) or None
_ORIGINAL_MATERIALS: Dict[str, Optional[Sdf.Path]] = {}

# Registry of filter checkbox models to allow programmatic control
# Mapping: label (str) -> ui.SimpleBoolModel
_FILTER_MODELS: Dict[str, ui.SimpleBoolModel] = {}
# Track which filter currently owns the Info tab override
_ACTIVE_INFO_LABEL: Optional[str] = None


def _set_subtree_highlight_shader(root_path: str, highlighted: bool) -> None:
    """
    Applies or removes the highlight material on the given prim and all its children.

    This function recursively traverses the stage from `root_path`. It uses
    `UsdShade.MaterialBindingAPI` to bind the highlight material. Original bindings
    are cached in `_ORIGINAL_MATERIALS` to be restored later.

    Args:
        root_path: The absolute USD path to the root prim of the subtree.
        highlighted: True to apply highlight, False to restore original materials.
    """
    ctx = omni.usd.get_context()
    stage = ctx.get_stage()
    if not stage:
        carb.log_warn("[USD Explorer Filters] No active stage found.")
        return

    root_prim = stage.GetPrimAtPath(root_path)
    if not root_prim or not root_prim.IsValid():
        carb.log_warn(f"[USD Explorer Filters] Root prim not found or invalid: {root_path}")
        return

    # Get highlight material when turning ON
    highlight_mat = None
    if highlighted:
        mat_prim = stage.GetPrimAtPath(HIGHLIGHT_MAT_PATH)
        if not mat_prim or not mat_prim.IsValid():
            carb.log_warn(f"[USD Explorer Filters] Highlight material not found at {HIGHLIGHT_MAT_PATH}")
            return
        highlight_mat = UsdShade.Material(mat_prim)

    # Walk root and children
    for prim in Usd.PrimRange(root_prim):
        if not prim.IsA(UsdGeom.Imageable):
            continue

        prim_path = prim.GetPath().pathString
        binding_api = UsdShade.MaterialBindingAPI(prim)

        if highlighted:
            # Remember original direct binding once
            if prim_path not in _ORIGINAL_MATERIALS:
                bound = binding_api.GetDirectBinding().GetMaterial()
                _ORIGINAL_MATERIALS[prim_path] = bound.GetPath() if bound else None

            # Bind highlight material
            if highlight_mat:
                binding_api.Bind(highlight_mat)

        else:
            # Restore original material if we have it
            if prim_path not in _ORIGINAL_MATERIALS:
                continue  # we never changed this one

            original_path = _ORIGINAL_MATERIALS[prim_path]

            if original_path is None:
                # No original → remove our direct binding
                binding_api.UnbindDirectBinding()
            else:
                orig_prim = stage.GetPrimAtPath(original_path)
                if not orig_prim or not orig_prim.IsValid():
                    # Original material gone? best effort: unbind
                    binding_api.UnbindDirectBinding()
                    continue

                original_mat = UsdShade.Material(orig_prim)
                binding_api.Bind(original_mat)


def clear_all_highlights() -> None:
    """
    Restores all original material bindings for any prims that have been highlighted.

    This should be called on extension shutdown to ensure no temporary highlight
    materials are left in the USD stage.
    """
    ctx = omni.usd.get_context()
    stage = ctx.get_stage()
    if not stage:
        return

    for prim_path, original_path in list(_ORIGINAL_MATERIALS.items()):
        prim = stage.GetPrimAtPath(prim_path)
        if not prim or not prim.IsValid():
            continue

        binding_api = UsdShade.MaterialBindingAPI(prim)

        if original_path is None:
            # No original material → remove our direct binding
            binding_api.UnbindDirectBinding()
        else:
            orig_prim = stage.GetPrimAtPath(original_path)
            if not orig_prim or not orig_prim.IsValid():
                # Original material gone → best effort: unbind
                binding_api.UnbindDirectBinding()
            else:
                original_mat = UsdShade.Material(orig_prim)
                binding_api.Bind(original_mat)

    _ORIGINAL_MATERIALS.clear()


def _apply_csv_metadata(info: csv_bridge.PrimInfo) -> None:
    """
    Writes metadata from a PrimInfo object into the prim's customData.

    This allows the InfoPanel to read the data directly from the prim.

    Args:
        info: The PrimInfo object containing metadata.
    """
    ctx = omni.usd.get_context()
    stage = ctx.get_stage()
    if not stage:
        return

    for path in info.prim_paths:
        prim = stage.GetPrimAtPath(path)
        if not prim or not prim.IsValid():
            carb.log_warn(f"[USD Explorer Filters] Prim not found for CSV row: {path}")
            continue

        # Only write if present in CSV
        if info.contact:
            prim.SetCustomDataByKey("company:contact", info.contact)
        if info.type:
            prim.SetCustomDataByKey("company:type", info.type)


def _set_info_override(info: Optional[csv_bridge.PrimInfo], active: bool) -> None:
    """
    Update the Info tab override so it mirrors the currently toggled filter.

    Args:
        info: PrimInfo for the active filter.
        active: True to show this filter in the Info tab, False to clear.
    """
    from .info_panel import info_panel_instance  # local import to avoid circulars

    global _ACTIVE_INFO_LABEL
    panel = info_panel_instance
    if not panel:
        carb.log_warn("[USD Explorer Filters] InfoPanel not available to show CSV data.")
        return

    if active and info:
        _ACTIVE_INFO_LABEL = info.name
        panel.set_override(info.prim_paths[0] if info.prim_paths else None, info)
    elif not active:
        # Only clear if we are turning off the entry that currently owns the override
        if _ACTIVE_INFO_LABEL is None or (info and _ACTIVE_INFO_LABEL == info.name):
            _ACTIVE_INFO_LABEL = None
            panel.set_override(None, None)

def _on_checkbox_changed(label: str, model: ui.SimpleBoolModel) -> None:
    """
    Callback for when a filter checkbox is toggled.

    Args:
        label: The label of the checkbox (e.g., "Bosch Rexroth").
        model: The UI model holding the checkbox state.
    """
    value = model.get_value_as_bool()
    carb.log_info(f"[USD Explorer Filters] Filter '{label}' changed to: {value}")

    # Look up this label in the CSV
    info = csv_bridge.get_prim_info(label)
    if not info:
        carb.log_warn(f"[USD Explorer Filters] No CSV entry found for '{label}'")
        return

    prim_paths = info.prim_paths

    # Highlight / unhighlight
    for path in prim_paths:
        _set_subtree_highlight_shader(path, value)

    # When turning ON, write CSV metadata into prim custom data (only if prim exists)
    if value:
        ctx = omni.usd.get_context()
        stage = ctx.get_stage()
        if not stage:
            carb.log_warn("[USD Explorer Filters] Cannot apply filter; no active USD stage.")
            _set_info_override(None, False)
            return

        prim = stage.GetPrimAtPath(prim_paths[0]) if stage and prim_paths else None
        if not prim or not prim.IsValid():
            carb.log_warn(f"[USD Explorer Filters] Cannot apply filter; prim not found: {prim_paths[0] if prim_paths else 'None'}")
            _set_info_override(None, False)
            return

        _apply_csv_metadata(info)
        _set_info_override(info, True)
    else:
        _set_info_override(info, False)


def set_filter_state(label: str, active: bool) -> None:
    """
    Programmatically sets the state of a filter.
    
    This is used by external modules (like stream_bridge) to toggle filters.
    Setting the model value will automatically trigger _on_checkbox_changed.
    
    Args:
        label: The label of the filter (e.g., "Bosch Rexroth").
        active: True to enable, False to disable.
    """
    model = _FILTER_MODELS.get(label)
    if model:
        # Avoid redundant updates if value is already correct
        if model.get_value_as_bool() != active:
            model.set_value(active)
    else:
        carb.log_warn(f"[USD Explorer Filters] Cannot set state for unknown filter: '{label}'")


def _focus_prim(label: str) -> None:
    """
    Frames the viewport on the prim associated with the given label.

    Args:
        label: The filter label whose prim should be focused.
    """
    info = csv_bridge.get_prim_info(label)
    if not info:
        carb.log_warn(f"[USD Explorer Filters] Cannot focus; no CSV entry for '{label}'")
        return

    ctx = omni.usd.get_context()
    stage = ctx.get_stage()
    if not stage:
        carb.log_warn("[USD Explorer Filters] Cannot focus; no active USD stage.")
        return

    focus_path = info.prim_paths[0] if getattr(info, "prim_paths", None) else info.prim_path
    prim = stage.GetPrimAtPath(focus_path)
    if not prim or not prim.IsValid():
        carb.log_warn(f"[USD Explorer Filters] Cannot focus; prim not found: {focus_path}")
        return

    # Preselect the prim so frame_selection fallbacks work across API versions.
    try:
        selection = ctx.get_selection()
        if selection:
            selection.clear_selected_prim_paths()
            selection.set_prim_path_selected(focus_path, True, False, False, False)
            # Also set the main selection (covers older APIs)
            try:
                ctx.get_selection().set_selected_prim_paths([focus_path], False)
            except Exception:
                pass
    except Exception:
        pass

    try:
        # Try the active viewport API first; fall back to the window helper if needed.
        viewport_win = None
        viewport_api = None

        try:
            viewport_win = vp_utils.get_active_viewport_window()
            viewport_api = getattr(viewport_win, "viewport_api", None)
        except Exception:
            viewport_win = None

        success = False
        controller = None

        # Newer APIs expose frame_prim on the viewport API; older ones expose it on the window.
        if viewport_api and hasattr(viewport_api, "frame_prim"):
            viewport_api.frame_prim(focus_path)
            success = True
        elif viewport_win and hasattr(viewport_win, "frame_prim"):
            viewport_win.frame_prim(focus_path)
            success = True
        elif viewport_api and hasattr(viewport_api, "get_viewport_camera_controller"):
            controller = viewport_api.get_viewport_camera_controller()
            if controller and hasattr(controller, "frame_paths"):
                controller.frame_paths(info.prim_paths if getattr(info, "prim_paths", None) else [focus_path])
                success = True
            elif controller and hasattr(controller, "frame_selection"):
                controller.frame_selection()
                success = True
        elif viewport_api and hasattr(viewport_api, "frame_selection"):
            viewport_api.frame_selection()
            success = True
        elif viewport_win and hasattr(viewport_win, "frame_selection"):
            viewport_win.frame_selection()
            success = True
        elif viewport_api and hasattr(viewport_api, "get_viewport_camera_controller"):
            controller = viewport_api.get_viewport_camera_controller()
            if controller and hasattr(controller, "frame_selection"):
                controller.frame_selection()
                success = True
        elif viewport_win and hasattr(viewport_win, "get_viewport_camera_controller"):
            controller = viewport_win.get_viewport_camera_controller()
            if controller and hasattr(controller, "frame_selection"):
                controller.frame_selection()
                success = True
        elif hasattr(vp_utils, "get_active_viewport"):
            try:
                viewport = vp_utils.get_active_viewport()
                if viewport and hasattr(viewport, "frame_selection"):
                    viewport.frame_selection()
                    success = True
            except Exception:
                pass
        elif hasattr(vp_utils, "frame_prim"):
            vp_utils.frame_prim(focus_path)
            success = True

        if not success:
            # Use FramePrimsCommand with active viewport data or a temporary camera.
            try:
                active_viewport = vp_utils.get_active_viewport() if hasattr(vp_utils, "get_active_viewport") else None
                time_code = Usd.TimeCode.Default()
                resolution = (1, 1)
                camera_path = None

                if active_viewport:
                    time_code = getattr(active_viewport, "time", time_code)
                    res = getattr(active_viewport, "resolution", None)
                    if res and len(res) >= 2 and res[0] and res[1]:
                        resolution = res
                    camera_path = getattr(active_viewport, "camera_path", None)

                if not camera_path:
                    camera_path = "/World/TempFocusCamera"
                    UsdGeom.Camera.Define(stage, camera_path)

                aspect_ratio = resolution[0] / resolution[1] if resolution[1] else 1.0

                kit_commands.execute(
                    "FramePrimsCommand",
                    prim_to_move=camera_path,
                    prims_to_frame=info.prim_paths if getattr(info, "prim_paths", None) else [focus_path],
                    time_code=time_code,
                    aspect_ratio=aspect_ratio,
                    zoom=0.3,
                )
                success = True
            except Exception:
                pass

        if not success:
            # Try a set of known command names, some take paths, others use current selection.
            command_attempts = [
                ("FramePrims", {"paths": info.prim_paths if getattr(info, "prim_paths", None) else [focus_path]}),
                ("FrameSelected", {}),
                ("FrameSelectedCommand", {}),
                ("FrameSelection", {}),
                ("FrameViewportSelection", {}),
                ("SelectAndFrame", {"paths": info.prim_paths if getattr(info, "prim_paths", None) else [focus_path]}),
            ]
            for cmd_name, kwargs in command_attempts:
                try:
                    command_dict = getattr(kit_commands, "get_command_dict", None)
                    if command_dict:
                        available = command_dict()
                        if cmd_name not in available:
                            continue
                    kit_commands.execute(cmd_name, **kwargs)
                    success = True
                    break
                except Exception:
                    continue

        if success:
            carb.log_info(f"[USD Explorer Filters] Focused prim: {focus_path}")
        else:
            carb.log_error("[USD Explorer Filters] No viewport API available to focus prim.")
    except Exception as e:
        carb.log_error(f"[USD Explorer Filters] Failed to focus prim '{focus_path}': {e}")
    finally:
        # Clear selection so the UI does not leave the prim selected after focusing.
        try:
            selection = ctx.get_selection()
            if selection:
                selection.clear_selected_prim_paths()
                selection.set_selected_prim_paths([], False)
        except Exception:
            pass


# ------------------------------------------------------------------------------
# UI Construction
# ------------------------------------------------------------------------------

def _checkbox(label: str, default: bool = False) -> ui.SimpleBoolModel:
    """
    Creates a checkbox with a label and returns its model.
    
    Args:
        label: The text label for the checkbox.
        default: Initial state.
        
    Returns:
        ui.SimpleBoolModel: The model controlling the checkbox state.
    """
    model = ui.SimpleBoolModel(default)
    _FILTER_MODELS[label] = model  # Register model
    
    ui.CheckBox(model=model)
    ui.Spacer(width=6)
    ui.Label(label, alignment=ui.Alignment.LEFT_CENTER)
    ui.Spacer(width=4)
    ui.Button(
        "Focus",
        height=0,
        width=60,
        clicked_fn=lambda l=label: _focus_prim(l),
        tooltip="Frame the viewport on this prim",
    )
    model.add_value_changed_fn(lambda m: _on_checkbox_changed(label, m))
    return model


def build_panel() -> None:
    """
    Builds the main content of the Filter tab.
    
    Dynamically generates collapsible groups and checkboxes based on the 
    data loaded in `csv_bridge`.
    """
    # Clear old models when rebuilding UI to avoid leaks or stale references
    _FILTER_MODELS.clear()
    
    # Reload CSV to ensure we have the latest data
    csv_bridge.reload_csv()
    
    # Get all data and group by category
    all_info = csv_bridge.get_all_prim_info()
    grouped_info = defaultdict(list)
    for info in all_info:
        grouped_info[info.category].append(info)

    # Wrap everything in a nice padded column
    with ui.VStack(spacing=10, height=0, style={"margin": 10}):
        # Header
        ui.Label(
            "Filter",
            style={
                "font_size": 20,
                "color": 0xFF202020,
                "margin": 0,
            },
        )
        ui.Spacer(height=6)

        # Iterate over categories and create collapsible frames
        for category, items in grouped_info.items():
            with ui.CollapsableFrame(title=category, collapsed=False):
                with ui.VStack(spacing=4, height=0, style={"margin": 4}):
                    for item in items:
                        with ui.HStack(spacing=4, height=0):
                            _checkbox(item.name, default=False)
            
            ui.Spacer(height=4)

        ui.Line()
        ui.Spacer(height=4)

        # Help text
        ui.Label(
            "Use these filters to highlight \npartners in the Arena2036.",
            word_wrap=True,
            style={
                "font_size": 12,
                "color": 0xFF707070,
            },
        )
