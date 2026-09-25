import jitx
from jitx.component import Component
from jitx.feature import Courtyard
from jitx.inspect import visit
from jitxlib.parts import Capacitor, Resistor
from socialbadge_ai.designs.badge_main import BadgeDesign

with jitx.runtime as r:
    d = r.submit(BadgeDesign)

for trace, comp in visit(d.root, Component):
    if not isinstance(comp, (Capacitor, Resistor)):
        continue
    mpn = getattr(comp, "mpn", None)
    courtyards = list(visit(comp, Courtyard))
    if not courtyards:
        print(f"{trace.path!s:35s} mpn={mpn!r:25s} NO COURTYARD")
        continue
    _, feature = courtyards[0]
    bounds = feature.shape.geometry.to_shapely().bounds
    w = round(bounds[2] - bounds[0], 2)
    h = round(bounds[3] - bounds[1], 2)
    flag = "" if (w, h) in ((0.9, 1.4), (1.4, 0.9)) else "  <-- NOT 0402"
    print(f"{trace.path!s:35s} mpn={mpn!r:25s} size={w}x{h}{flag}")
