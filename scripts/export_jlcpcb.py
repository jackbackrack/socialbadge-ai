"""Import the dumped placements/board shape and export the JLCPCB packet.

Must be one process: layout import and jlcpcb export each do their own
`r.submit()`, and nothing persists across separate process invocations, so
chaining `import_layout.py` then `jitx design export jlcpcb` as two commands
does not carry the imported layout into the export.

Run after the main design has been built once, from the project root with
the venv active:

    python scripts/export_jlcpcb.py
"""

import jitx
import jitx.plugin
from socialbadge_ai.designs.badge_main import BadgeDesign

jitx.plugin.initialize()
exporter = jitx.plugin.Export.get("jlcpcb")

with jitx.runtime as r:
    d = r.submit(BadgeDesign, layout="jitx_export.json")
    d.capture()
    exporter.export(d, output="jlcpcb", overwrite=True)
