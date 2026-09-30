@tool
extends RefCounted

## Coverage heatmap overlay for the script editor.
##
## Reads per-file line/branch status from the ``.gd-tools/coverage/``
## machine-readable artifacts and applies CodeEdit line background
## colors (green covered / red uncovered / yellow partial branches).
## Implemented in Phase 3 of the editor plugin track.
