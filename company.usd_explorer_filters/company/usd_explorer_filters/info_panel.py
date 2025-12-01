from pxr import Usd, UsdGeom, Gf
import omni.usd
import omni.ui as ui
import carb
import omni.kit.app
from typing import Optional, Tuple, Dict, Any

# Global reference so other modules can reach the active panel
info_panel_instance: Optional["InfoPanel"] = None


# Keys we’ll read from Prim Custom Data (Metadata)
CUSTOM_KEYS: Dict[str, str] = {
    "contact": "company:contact",
    "type":    "company:type",
    "area":    "info:area_sqm",
}

class InfoPanel:
    """
    A UI panel that displays metadata for the currently selected or overridden prim.
    """

    def __init__(self):
        global info_panel_instance
        info_panel_instance = self
        
        # UI models
        self._path = ui.SimpleStringModel("")
        self._type = ui.SimpleStringModel("-")
        self._contact = ui.SimpleStringModel("-")
        self._area = ui.SimpleStringModel("-")

        # State
        self._meters_per_unit: float = 1.0
        self._last_selection: Tuple[str, ...] = tuple()
        self._update_sub: Optional[Any] = None  # Subscription to update event
        self._override_path: Optional[str] = None

        # Cache metersPerUnit if a stage is open
        ctx = omni.usd.get_context()
        stage = ctx.get_stage()
        if stage:
            self._meters_per_unit = UsdGeom.GetStageMetersPerUnit(stage) or 1.0

    def set_override_prim(self, prim_path: Optional[str]) -> None:
        """
        Sets a specific prim to display, ignoring the current stage selection.
        
        Args:
            prim_path: The path of the prim to show, or None to revert to selection.
        """
        self._override_path = prim_path
        # Force an immediate update
        self._poll_selection()

    def destroy(self) -> None:
        """Cleans up resources and subscriptions."""
        if hasattr(self, "_update_sub") and self._update_sub:
            self._update_sub = None
        
        global info_panel_instance
        if info_panel_instance == self:
            info_panel_instance = None

    # ---------- UI ----------

    def build(self) -> None:
        """Builds the UI widgets for the info panel."""
        with ui.VStack(spacing=8, height=0, style={"margin": 10}):
            ui.Label("Selected Prim", style={"font_size": 18})
            self._line("Path", self._path)
            self._line("Type", self._type)
            self._line("Contact", self._contact)
            self._line("Area (m²)", self._area)

            ui.Spacer(height=8)
            ui.Label(
                "Add Prim Custom Data in this format:\n"
                "  company:contact = \"Name, phone\"\n"
                "  company:type = \"Produktion\" / \"Robotik\"\n"
                "  info:area_sqm = 1234.5",
                word_wrap=True,
                style={"color": 0xFF777777, "font_size": 12},
            )
            
        # Subscribe to update events (runs every frame)
        app = omni.kit.app.get_app()
        self._update_sub = app.get_update_event_stream().create_subscription_to_pop(
            self._on_update,
            name="info_panel_update"
        )

    def _on_update(self, e: Any) -> None:
        """Called every frame to poll for selection changes."""
        self._poll_selection()

    def _line(self, label: str, model: ui.SimpleStringModel) -> None:
        """Helper to create a labeled text field."""
        with ui.HStack(height=0):
            ui.Label(label, width=110, alignment=ui.Alignment.RIGHT_CENTER)
            ui.Spacer(width=6)
            ui.StringField(model=model, read_only=True)

    # ---------- Selection polling ----------

    def _poll_selection(self) -> None:
        """Checks for changes in selection or override path."""
        ctx = omni.usd.get_context()

        # If there is an override prim, use that instead of selection
        if self._override_path:
            paths = (self._override_path,)
        else:
            sel = ctx.get_selection()
            paths = tuple(sel.get_selected_prim_paths() or ())

        if paths != self._last_selection:
            self._last_selection = paths
            self._on_selection_changed(paths)

    # ---------- Selection handling ----------

    def _on_selection_changed(self, paths: Tuple[str, ...]) -> None:
        """Updates the UI when the selection changes."""
        if not paths:
            self._path.set_value("")
            self._type.set_value("-")
            self._contact.set_value("-")
            self._area.set_value("-")
            return

        prim_path = paths[0]
        self._path.set_value(prim_path)

        prim = self._get_prim(prim_path)
        if not prim or not prim.IsValid():
            self._type.set_value("-")
            self._contact.set_value("-")
            self._area.set_value("-")
            return

        # Read metadata (walk up to parent if missing)
        c_type = self._find_custom_data(prim, CUSTOM_KEYS["type"]) or "-"
        c_contact = self._find_custom_data(prim, CUSTOM_KEYS["contact"]) or "-"

        area_est = self._estimate_area_sqm(prim)
        area_str = f"{area_est:,.2f}" if area_est is not None else "-"

        self._type.set_value(str(c_type))
        self._contact.set_value(str(c_contact))
        self._area.set_value(area_str)

    # ---------- Helpers ----------

    def _get_prim(self, path: str) -> Optional[Usd.Prim]:
        """Retrieves a prim from the current stage."""
        stage = omni.usd.get_context().get_stage()
        return stage.GetPrimAtPath(path) if stage else None

    def _find_custom_data(self, prim: Usd.Prim, key: str) -> Any:
        """
        Recursively searches for custom data on the prim and its ancestors.
        """
        cur = prim
        while cur and cur.IsValid():
            try:
                data = cur.GetCustomData()  # returns a dict-like
            except Exception:
                data = {}

            if data and key in data:
                return data[key]

            cur = cur.GetParent()

        return None

    def _estimate_area_sqm(self, prim: Usd.Prim) -> Optional[float]:
        """
        Estimates the footprint area (X * Y) of the prim's bounding box.
        """
        try:
            cache = UsdGeom.BBoxCache(
                Usd.TimeCode.Default(),
                includedPurposes=[UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy],
                useExtentsHint=True,
            )
            bbox = cache.ComputeWorldBound(prim)
            size = bbox.ComputeAlignedRange().GetSize()  # X,Y,Z in stage units
            to_m = self._meters_per_unit  # meters per 1 stage unit
            width_m = size[0] * to_m
            depth_m = size[1] * to_m
            return max(0.0, width_m) * max(0.0, depth_m)
        except Exception as e:
            carb.log_warn(f"[USD Explorer Filters] Area estimate failed: {e}")
            return None
