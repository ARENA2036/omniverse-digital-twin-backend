# USD Explorer Filters

**Extension Name:** `company.usd_explorer_filters`  
**Version:** 1.0.0  
**Category:** UI

## Overview

The **USD Explorer Filters** extension adds a custom "USD Explorer Filters" panel to the NVIDIA Omniverse UI. It provides a streamlined way to locate, highlight, and inspect specific objects (prims) within a complex USD stage based on pre-defined categories.

This tool is particularly useful for visualizing shop floor sectors, partner classifications, or any other grouped assets in a digital twin environment.

## Features

*   **Interactive Filter Panel**: A dedicated UI panel (dockable) with checkboxes for various categories (e.g., "Bosch Rexroth", "Start-up").
*   **Visual Highlighting**: 
    *   Automatically applies a highlight material (`/World/Looks/Highlight_Mat`) to selected objects and their entire hierarchy.
    *   Smartly preserves original material bindings and restores them when the filter is disabled or the extension shuts down.
*   **Info Panel**: Displays context-specific metadata (Type, Contact info) for the currently active filter/object.
*   **Data-Driven Configuration**: Filter categories and their corresponding USD paths are defined in a simple CSV file, making it easy to update without changing code.

## Installation & Usage

1.  **Load the Extension**: Enable `company.usd_explorer_filters` in the Omniverse Extension Manager.
2.  **Open the Panel**: The "USD Explorer Filters" window will appear automatically on startup (defaulting to the top-right dock).
3.  **Filter Objects**:
    *   Navigate to the **Filter** tab.
    *   Check the boxes (e.g., "Bosch Rexroth") to highlight those objects in the viewport.
    *   Uncheck to restore original materials.
4.  **View Info**:
    *   Switch to the **Info** tab to see details about the highlighted object.

## Configuration

The extension uses a CSV file to map UI labels to USD prim paths.

**File Location:** `company/usd_explorer_filters/prim_info.csv`

**Format:**
```csv
name,path,type,contact
Bosch Rexroth,/World/ShopFloor/BoschRexroth,Partner,info@bosch.com
```

*   **name**: The label displayed in the UI.
*   **path**: The absolute USD path to the root prim of the object/group.
*   **type**: Metadata displayed in the Info panel.
*   **contact**: Metadata displayed in the Info panel.

## Dependencies

This extension requires the following Omniverse Kit extensions (defined in `extension.toml`):
*   `omni.kit.uiapp`
*   `omni.usd`
*   `omni.ui`

## File Structure

*   **`extension.toml`**: Extension configuration and dependencies.
*   **`company/usd_explorer_filters/`**: Source code.
    *   `__init__.py`: Entry point and main window setup.
    *   `ui_panel.py`: Core logic for the filter UI and material highlighting.
    *   `tab_widgets.py`: Custom tab UI components.
    *   `csv_bridge.py`: Handles loading data from `prim_info.csv`.
    *   `info_panel.py`: Displays metadata.
