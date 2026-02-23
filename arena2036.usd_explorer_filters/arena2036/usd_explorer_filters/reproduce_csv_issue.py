
import os
import csv
import sys

# Mock carb to avoid import errors
import types

# Create a mock carb module with required logging functions
mock_carb = types.SimpleNamespace(
    log_warn=lambda msg: print(f"WARN: {msg}"),
    log_info=lambda msg: print(f"INFO: {msg}"),
    log_error=lambda msg: print(f"ERROR: {msg}")
)

# Insert the mock into sys.modules so that imports receive it
sys.modules["carb"] = mock_carb


# Import the module to test
import csv_bridge

print("Testing csv_bridge...")
csv_bridge.reload_csv()
data = csv_bridge.get_all_prim_info()
print(f"Loaded {len(data)} items.")
for item in data:
    print(item)
