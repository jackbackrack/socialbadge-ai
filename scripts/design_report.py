"""Thin shim: the real implementation moved to the shared `jitx-design-tools`
package (see /Users/jrb/jitx-design-tools), installed editable into this
project's venv (`pip install -e /Users/jrb/jitx-design-tools`), so this
project and its sibling jitx projects share one implementation instead of
copy-pasted, independently-drifting forks. Kept here so the existing
`python scripts/design_report.py <module.path.DesignClass> [output_stem]`
invocation keeps working unchanged.
"""

from jitx_design_tools.design_report import main

if __name__ == "__main__":
    main()
