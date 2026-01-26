from functools import partial
from typing import List, Dict, Any

import omni.ui as ui

# ------------------------------------------------------------------------------
# Styles
# ------------------------------------------------------------------------------

TAB_GROUP_STYLE: Dict[str, Dict[str, Any]] = {
    "TabGroupBorder": {
        "background_color": ui.color.transparent,
        "border_color": ui.color(25),
        "border_width": 1,
    },
    "Rectangle::TabGroupHeader": {
        "background_color": ui.color(20),
    },
    "ZStack::TabGroupHeader": {
        "margin_width": 1,
    },
}

TAB_STYLE: Dict[str, Dict[str, Any]] = {
    "": {
        "background_color": ui.color(31),
        "corner_flag": ui.CornerFlag.TOP,
        "border_radius": 4,
        "color": ui.color(127),
    },
    ":selected": {
        "background_color": ui.color(56),
        "color": ui.color(203),
    },
    "Label": {
        "margin_width": 5,
        "margin_height": 3,
    },
}


# ------------------------------------------------------------------------------
# Base Classes
# ------------------------------------------------------------------------------

class BaseTab:
    """
    Abstract base class for a tab in the TabGroup.
    """
    def __init__(self, name: str):
        self.name = name

    def build_fn(self) -> None:
        """
        Builds the UI content for this tab.
        Override this in child classes.
        """
        raise NotImplementedError("You must implement BaseTab.build_fn()")


class TabGroup:
    """
    A custom widget that manages a set of tabs and their content areas.
    
    It renders a header row with clickable tabs and switches the visible content
    area based on the selection.
    """
    def __init__(self, tabs: List[BaseTab]):
        if not tabs:
            raise ValueError("You must provide at least one BaseTab object.")
        self.tabs = tabs
        self.tab_containers: List[ui.Frame] = []
        self.tab_headers: List[ui.ZStack] = []

        # Creating the UI immediately
        self.frame = ui.Frame(build_fn=self._build_widget)

    def _build_widget(self) -> None:
        with ui.ZStack(style=TAB_GROUP_STYLE):
            ui.Rectangle(style_type_name_override="TabGroupBorder")
            with ui.VStack():
                ui.Spacer(height=1)
                # ---- header row with tab buttons ----
                with ui.ZStack(height=0, name="TabGroupHeader"):
                    ui.Rectangle(name="TabGroupHeader")
                    with ui.VStack():
                        ui.Spacer(height=2)
                        with ui.HStack(height=0, spacing=4):
                            for idx, tab in enumerate(self.tabs):
                                tab_header = ui.ZStack(width=0, style=TAB_STYLE)
                                self.tab_headers.append(tab_header)
                                with tab_header:
                                    rect = ui.Rectangle()
                                    rect.set_mouse_released_fn(
                                        partial(self._tab_clicked, idx)
                                    )
                                    ui.Label(tab.name)
                # ---- content area ----
                with ui.ZStack():
                    for idx, tab in enumerate(self.tabs):
                        container_frame = ui.Frame(build_fn=tab.build_fn)
                        self.tab_containers.append(container_frame)
                        container_frame.visible = False

        # show first tab by default
        self.select_tab(0)

    def select_tab(self, index: int) -> None:
        """
        Switches the visible content to the tab at the given index.
        
        Args:
            index: The index of the tab to select.
        """
        for i in range(len(self.tabs)):
            if i == index:
                self.tab_containers[i].visible = True
                self.tab_headers[i].selected = True
            else:
                self.tab_containers[i].visible = False
                self.tab_headers[i].selected = False

    def _tab_clicked(self, index: int, x: float, y: float, button: int, modifier: int) -> None:
        if button == 0:
            self.select_tab(index)

    def destroy(self) -> None:
        """Cleans up the UI resources."""
        if self.frame:
            self.frame.destroy()
            self.frame = None


# ------------------------------------------------------------------------------
# Concrete Implementations
# ------------------------------------------------------------------------------

from .ui_panel import build_panel
from .info_panel import InfoPanel


class FilterTab(BaseTab):
    """
    The main filter interface tab.
    """
    def __init__(self):
        super().__init__("Filter")

    def build_fn(self) -> None:
        # Filter tab content
        with ui.ScrollingFrame():
            with ui.VStack(spacing=4, height=0, style={"margin": 8}):
                build_panel()


class InfoTab(BaseTab):
    """
    The information display tab.
    """
    def __init__(self, info_panel: InfoPanel):
        super().__init__("Info")
        self._info_panel = info_panel

    def build_fn(self) -> None:
        # Info tab content
        with ui.ScrollingFrame():
            with ui.VStack(spacing=4, height=0, style={"margin": 8}):
                self._info_panel.build()
