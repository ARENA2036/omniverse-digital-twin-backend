# Requirements Elicitation

## 1. Introduction
This document outlines the functional and non-functional requirements for the **USD Explorer Filters** extension (`company.usd_explorer_filters`). The extension is designed to enhance the NVIDIA Omniverse user experience by providing a dedicated interface for filtering and visualizing specific assets within a USD stage.

## 2. Functional Requirements

### 2.1 Filter Panel UI
*   **FR-01**: The system shall provide a dockable UI panel named "USD Explorer Filters".
*   **FR-02**: The panel shall contain collapsible groups for filter categories (e.g., "Shop Floor Sectors", "Classification").
*   **FR-03**: The panel shall provide checkboxes for individual filter items (e.g., "Bosch Rexroth", "Start-up").
*   **FR-04**: The UI shall be built using the `omni.ui` framework to ensure consistency with the Omniverse environment.

### 2.2 Filtering & Highlighting
*   **FR-05**: When a filter checkbox is **checked**, the system shall:
    *   Identify the corresponding USD prim path from the configuration.
    *   Apply a specific highlight material (`/World/Looks/Highlight_Mat`) to the target prim and its descendants.
    *   Store the original material bindings for all affected prims.
*   **FR-06**: When a filter checkbox is **unchecked**, the system shall:
    *   Remove the highlight material.
    *   Restore the original material bindings to their previous state.
*   **FR-07**: The system must support multiple active filters simultaneously (though visual overlap behavior depends on USD resolution order).

### 2.3 Information Display
*   **FR-08**: The system shall provide an "Info" tab separate from the "Filter" tab.
*   **FR-09**: When a filter is active, the Info panel shall display metadata for the associated object, including:
    *   **Type** (e.g., "Partner")
    *   **Contact** (e.g., email address)
*   **FR-10**: The metadata shall be injected into the USD prim's `customData` upon activation to ensure accessibility.

### 2.4 Data Management
*   **FR-11**: The system shall load filter definitions and metadata from a CSV file (`prim_info.csv`) at startup.
*   **FR-12**: The CSV configuration must support the following fields: `name`, `path`, `type`, `contact`.
*   **FR-13**: The system shall gracefully handle missing or malformed CSV rows by logging a warning and skipping the invalid entry.

### 2.5 Lifecycle Management
*   **FR-14**: On extension **shutdown**, the system must automatically clear all active highlights and restore original materials to prevent scene corruption.

## 3. Non-Functional Requirements

### 3.1 Integration
*   **NFR-01**: The extension must be compatible with NVIDIA Omniverse Kit.
*   **NFR-02**: The extension must declare dependencies on `omni.usd`, `omni.ui`, and `omni.kit.uiapp`.

### 3.2 Performance
*   **NFR-03**: The highlighting operation should be efficient enough to handle standard scene hierarchies without causing significant UI freezing.
*   **NFR-04**: Material restoration must be reliable to ensure the stage is returned to its exact original state.

### 3.3 Usability
*   **NFR-05**: The UI should follow standard Omniverse styling guidelines (colors, spacing, fonts).
*   **NFR-06**: The extension should provide visual feedback (logging) for errors such as missing paths or materials.
