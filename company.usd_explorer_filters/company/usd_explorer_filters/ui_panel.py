import omni.ui as ui
from pxr import Usd, UsdGeom, UsdShade, Sdf
import omni.usd
import carb
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

    prim = stage.GetPrimAtPath(info.prim_path)
    if not prim or not prim.IsValid():
        carb.log_warn(f"[USD Explorer Filters] Prim not found for CSV row: {info.prim_path}")
        return

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
        panel.set_override(info.prim_path, info)
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

    root_path = info.prim_path

    # Highlight / unhighlight
    _set_subtree_highlight_shader(root_path, value)

    # When turning ON, write CSV metadata into prim custom data (only if prim exists)
    if value:
        ctx = omni.usd.get_context()
        stage = ctx.get_stage()
        if not stage:
            carb.log_warn("[USD Explorer Filters] Cannot apply filter; no active USD stage.")
            _set_info_override(None, False)
            return

        prim = stage.GetPrimAtPath(root_path) if stage else None
        if not prim or not prim.IsValid():
            carb.log_warn(f"[USD Explorer Filters] Cannot apply filter; prim not found: {root_path}")
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
