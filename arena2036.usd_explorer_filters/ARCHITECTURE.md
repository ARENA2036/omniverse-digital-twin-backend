# Architecture: USD Explorer Filters

## Overview
The `company.usd_explorer_filters` extension provides a UI panel in NVIDIA Omniverse to filter and highlight specific USD prims based on metadata. It is designed to be data-driven, loading filter definitions from a CSV file, and supports external control via WebRTC events.

## Components

### 1. Data Layer (`csv_bridge.py`, `prim_info.csv`)
-   **Responsibility**: Loads and validates filter definitions and metadata.
-   **Source**: `prim_info.csv` contains the mapping between display names, USD paths, categories, and metadata (type, contact).
-   **Interface**: Provides `get_prim_info(name)` and `reload_csv()` functions.

### 2. UI Layer (`ui_panel.py`, `tab_widgets.py`, `info_panel.py`)
-   **Responsibility**: Renders the user interface and handles user interactions.
-   **`ui_panel.py`**: Dynamically builds the filter list based on categories defined in the Data Layer. Handles the highlighting logic (`_set_subtree_highlight_shader`).
-   **`tab_widgets.py`**: Provides reusable tab components (`TabGroup`, `FilterTab`, `InfoTab`).
-   **`info_panel.py`**: Displays detailed metadata for the selected or active prim. It observes the stage selection and supports overrides from the filter panel.

### 3. Logic & State (`ui_panel.py`)
-   **Highlighting**: Uses `UsdShade.MaterialBindingAPI` to apply a highlight material to prims.
-   **Restoration**: Caches original material bindings to restore them when filters are disabled or the extension shuts down.
-   **State**: Maintains the state of active filters and cached materials.

### 4. Bridge Layer (`stream_bridge.py`)
-   **Responsibility**: Enables external control of the filters.
-   **Mechanism**: Listens for `ToggleFilter` events from the `omni.kit.livestream.core` extension.
-   **Protocol**: Expects JSON payloads with `name` and `active` fields.

## Data Flow

1.  **Startup**: `Extension.on_startup` initializes `csv_bridge` (loads data) and `stream_bridge` (starts listening).
2.  **UI Construction**: `ui_panel.build_panel` requests data from `csv_bridge` and generates collapsible groups and checkboxes.
3.  **User Interaction**:
    *   User toggles a checkbox.
    *   `ui_panel._on_checkbox_changed` is called.
    *   `_set_subtree_highlight_shader` applies/removes material.
    *   `_set_info_override` updates the Info Panel.
4.  **External Event**:
    *   `stream_bridge` receives `ToggleFilter`.
    *   Calls `ui_panel.set_filter_state`.
    *   Updates UI model, triggering the standard `_on_checkbox_changed` flow.

## Dependencies
-   `omni.usd`: For stage access and prim manipulation.
-   `omni.ui`: For UI construction.
-   `omni.kit.livestream.core`: For WebRTC event handling.
