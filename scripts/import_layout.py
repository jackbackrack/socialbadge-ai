"""Import the dumped placements and board shape into BadgeDesign.

Run after the main design has been built once (so refdes/placement state
exists), from the project root with the venv active:

    python scripts/import_layout.py
"""

import jitx
from socialbadge_ai.designs.badge_main import BadgeDesign

with jitx.runtime as r:
    d = r.submit(BadgeDesign, layout="jitx_export.json")
    print("board shape right after submit:", d.root.board.shape)
    d.capture()
    print("board shape after capture:", d.root.board.shape)
    print("mcu placement after capture:", d.root.circuit.mcu.mcu.transform)
