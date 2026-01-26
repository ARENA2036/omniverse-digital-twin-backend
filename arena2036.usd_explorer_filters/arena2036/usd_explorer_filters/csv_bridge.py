import os
import csv
import carb
from typing import Optional, Dict, List
from collections import namedtuple

# ------------------------------------------------------------------------------
# Data Structures
# ------------------------------------------------------------------------------

# Define the structure for prim information
# Added 'category' to support dynamic UI grouping
PrimInfo = namedtuple("PrimInfo", ["name", "prim_path", "category", "type", "contact"])

# Global dictionary: "Bosch Rexroth" -> PrimInfo(...)
_PRIM_INFO_BY_NAME: Dict[str, PrimInfo] = {}


def _get_csv_path() -> str:
    """
    Returns the absolute path to the 'prim_info.csv' file.
    
    Returns:
        str: The absolute file path.
    """
    here = os.path.dirname(__file__)
    return os.path.join(here, "prim_info.csv")


def reload_csv() -> None:
    """
    Reads 'prim_info.csv' into memory and populates the global _PRIM_INFO_BY_NAME dictionary.
    
    This function should be called on extension startup. It handles missing files
    and malformed CSV rows gracefully, logging warnings where appropriate.
    """
    global _PRIM_INFO_BY_NAME
    _PRIM_INFO_BY_NAME = {}

    csv_path = _get_csv_path()
    if not os.path.exists(csv_path):
        carb.log_warn(f"[usd_explorer_filters] prim_info.csv not found at: {csv_path}")
        return

    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            
            # Check if the CSV is empty or headers are missing
            if not reader.fieldnames:
                 carb.log_warn(f"[usd_explorer_filters] prim_info.csv appears to be empty or invalid.")
                 return

            for row_idx, row in enumerate(reader, start=2): # Start at 2 for line number (header is 1)
                name = (row.get("name") or "").strip()
                prim_path = (row.get("path") or "").strip()
                category = (row.get("category") or "Uncategorized").strip()
                type_ = (row.get("type") or "").strip()
                contact = (row.get("contact") or "").strip()

                if not name or not prim_path:
                    # Skip incomplete rows but log a warning for visibility
                    carb.log_warn(f"[usd_explorer_filters] Skipping incomplete row {row_idx} in CSV: name='{name}', path='{prim_path}'")
                    continue

                _PRIM_INFO_BY_NAME[name] = PrimInfo(
                    name=name,
                    prim_path=prim_path,
                    category=category,
                    type=type_,
                    contact=contact,
                )

        carb.log_info(f"[usd_explorer_filters] Successfully loaded {len(_PRIM_INFO_BY_NAME)} prim rows from CSV")

    except csv.Error as e:
        carb.log_error(f"[usd_explorer_filters] CSV parsing error in {csv_path}: {e}")
    except Exception as e:
        carb.log_error(f"[usd_explorer_filters] Unexpected error reading prim_info.csv: {e}")


def get_prim_info(name: str) -> Optional[PrimInfo]:
    """
    Retrieves the PrimInfo object for a given display name.

    Args:
        name: The display name (e.g., 'Bosch Rexroth') to look up.

    Returns:
        The corresponding PrimInfo object, or None if not found.
    """
    return _PRIM_INFO_BY_NAME.get(name)


def get_all_prim_info() -> List[PrimInfo]:
    """
    Retrieves all loaded PrimInfo objects.

    Returns:
        List[PrimInfo]: A list of all loaded prim information.
    """
    return list(_PRIM_INFO_BY_NAME.values())


# Load immediately when the module is imported to ensure data is available
reload_csv()
