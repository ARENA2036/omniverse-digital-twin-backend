import omni.ext
import omni.ui as ui
import carb
from typing import Optional

from .tab_widgets import TabGroup, FilterTab, InfoTab
from .info_panel import InfoPanel
from .ui_panel import clear_all_highlights
from . import csv_bridge
from . import stream_bridge

class Extension(omni.ext.IExt):
    """
    Main entry point for the USD Explorer Filters extension.
    
    This class handles the extension lifecycle (startup, shutdown) and
    initializes the main UI window.
    """
    
    def on_startup(self, ext_id: str) -> None:
        """
        Called when the extension is loaded.
        
        Args:
            ext_id: The unique identifier for this extension instance.
        """
        # Load prim metadata from CSV
        csv_bridge.reload_csv()
        
        # Start the stream bridge to listen for WebRTC events
        stream_bridge.startup()

        carb.log_info("[USD Explorer Filters] Extension startup")

        self._window: Optional[ui.Window] = ui.Window(
            "USD Explorer Filters",
            width=420,
            height=600,
            dockPreference=ui.DockPreference.RIGHT_TOP,
            visible=True,
        )

        # One shared InfoPanel instance
        self._info_panel: Optional[InfoPanel] = InfoPanel()

        with self._window.frame:
            with ui.VStack():
                # Create the tab group with our two tabs.
                # Creating TabGroup automatically builds its UI into the current stack.
                TabGroup([
                    FilterTab(),
                    InfoTab(self._info_panel),
                ])

    def on_shutdown(self) -> None:
        """
        Called when the extension is unloaded.
        
        Responsible for cleaning up UI resources and restoring the USD stage state.
        """
        carb.log_info("[USD Explorer Filters] Extension shutdown")
        
        # Shutdown stream bridge
        stream_bridge.shutdown()
        
        # Restore original materials for any highlighted prims
        try:
            clear_all_highlights()
        except Exception as e:
            carb.log_warn(f"[USD Explorer Filters] Failed to clear highlights on shutdown: {e}")

        if getattr(self, "_info_panel", None):
            self._info_panel.destroy()
            self._info_panel = None

        if getattr(self, "_window", None):
            self._window.destroy()
            self._window = None
