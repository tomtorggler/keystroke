"""Swap Keystroke.qml's layer-shell PanelWindow for a plain Window, so the
palette runs under Quickshell's offscreen platform. The Window declares the
PanelWindow signals the palette connects to; tests emit them by hand.

Every edit must match once: a changed PanelWindow line fails here, by name,
instead of as a QML error or a silently unpatched window in some later check.
"""

WINDOW = "  Window {\n    transientParent: null\n    signal resourcesLost()\n    signal closed()\n"
LAYER_ONLY = [
    "    anchors { top: true; bottom: true; left: true; right: true }\n",
    "    margins { top: root.windowTop; bottom: root.windowBottom; left: root.windowLeft; right: root.windowRight }\n",
    "    screen: root.targetScreen\n",
    "    mask: root.inputMask\n",
]
LAYER_ONLY_PREFIXES = ["exclusionMode:", "WlrLayershell."]


def offscreen_window(qml, size="    width: 1000; height: 800\n", strict=True):
    """Return qml with the panel as an offscreen Window of the given size.
    strict=False tolerates older checkouts that lack some layer-only lines."""
    def check(ok, what):
        assert ok or not strict, "offscreen_window: Keystroke.qml no longer has " + what

    check(qml.count("  PanelWindow {") == 1, "exactly one '  PanelWindow {'")
    qml = qml.replace("  PanelWindow {\n", WINDOW + size, 1)
    for line in LAYER_ONLY:
        check(qml.count(line) == 1, repr(line.strip()))
        qml = qml.replace(line, "", 1)
    lines = qml.splitlines()
    for prefix in LAYER_ONLY_PREFIXES:
        check(any(prefix in line for line in lines), repr(prefix) + " lines")
    return "\n".join(line for line in lines if not any(prefix in line for prefix in LAYER_ONLY_PREFIXES))
