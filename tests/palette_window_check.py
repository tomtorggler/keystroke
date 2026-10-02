#!/usr/bin/env python3
"""Exercise surface geometry for both window modes. The offscreen Window mirrors
layer-shell anchor/margin sizing, so the palette's own bindings run unchanged.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from offscreen_window import offscreen_window

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="keystroke-palette-window-") as temp:
    work = Path(temp)
    project = work / "project"
    shutil.copytree(root, project, ignore=shutil.ignore_patterns(".git", ".claude", ".agents", ".codex", "tests", "__pycache__"))
    (work / "qs").symlink_to("/usr/share/omarchy/shell")
    source = project / "Keystroke.qml"
    qml = source.read_text().replace("  id: root\n", """  id: root
  property alias testPanel: panel
  property alias testCard: card
  property var testScreen: ({width: 2560, height: 1440})
""", 1)
    screen = "root.targetScreen || panel.screen || Quickshell.screens[0] || null"
    assert qml.count(screen) == 1, "paletteScreen expression changed"
    qml = qml.replace(screen, "root.testScreen")
    source.write_text(offscreen_window(qml, size="""    width: root.testScreen.width - root.windowLeft - root.windowRight
    height: root.testScreen.height - root.windowTop - root.windowBottom
"""))
    (work / "shell.qml").write_text('''import QtQuick
import Quickshell
import "project"
ShellRoot {
  id: test
  function check(ok, message) { if (!ok) { console.log("FAIL", message); Qt.quit(); throw Error(message) } }
  function configure(background, transition) {
    palette.applyConfigText(JSON.stringify({version:1, voice:{enabled:false}, matching:{mode:"off"},
      palette:{fullscreenBackground:background, animations:"fluid", windowTransition:transition || "instant"}}))
  }
  function fits() {
    test.check(palette.testPanel.width === palette.testCard.width, "surface fits the card horizontally")
    test.check(palette.testPanel.height === palette.frameHeight + palette.windowSlideMargin, "surface only reserves the tallest card and slide space")
    test.check(palette.testCard.y === palette.cardTop - palette.windowTop && palette.testCard.y >= 0, "card sits at its offset in the surface")
    test.check(palette.testCard.y + palette.testCard.height <= palette.frameHeight, "card stays inside the surface")
    test.check(palette.windowTop >= 0 && palette.windowBottom >= 0, "surface is within the display")
    test.check(palette.inputMask && palette.inputMask.item === palette.testCard, "only the card takes input")
  }
  // The card's place on the display, whichever surface holds it.
  function screenTop() { return palette.windowTop + palette.testCard.y }
  Keystroke { id: palette; omarchyPath: Quickshell.env("HOME") }
  Timer { interval:300; running:true; onTriggered: {
    test.check(palette.fullscreenBackground, "existing configs keep full-screen background")
    test.configure(true)
    palette.open('{}')
    test.check(palette.testPanel.width === 2560 && palette.testPanel.height === 1440, "default covers the display")
    test.check(palette.testCard.y > 0, "default card is offset within background")
    test.check(palette.inputMask === null, "the scrim takes clicks to close")
    var fullTop = test.screenTop()
    palette.cancel()

    test.configure(false)
    palette.open('{}')
    test.fits()
    test.check(palette.testPanel.width < 1000 && palette.testPanel.height < 800, "launcher uses a small surface")
    test.check(test.screenTop() === fullTop, "launcher sits where it does over the scrim")
    palette.cancel()
    test.check(!palette.opened && !palette.closing && !palette.testPanel.visible, "normal close unmaps")

    // Reconfigure while open, including fractional/odd viewport dimensions.
    palette.open('{}')
    test.configure(true)
    test.check(palette.testPanel.width === 2560, "full-screen can be restored live")
    test.configure(false)
    palette.testScreen = {width: 1281, height: 801}
    test.fits()
    palette.testScreen = {width: 480, height: 360}
    test.fits()
    test.check(palette.cardWidth <= 480 && palette.cardHeight <= 360, "small display clamps the card")
    palette.cancel()
    palette.testScreen = {width: 2560, height: 1440}

    // A slide transition reserves only its own travel distance.
    test.configure(false, "slide")
    palette.open('{}')
    test.check(palette.windowSlideMargin > 0, "slide has bounded extra space")
    palette.cancel()

    // Filtering a picker moves the card inside a surface that keeps its size;
    // on screen it moves exactly as it does over the full-screen scrim.
    var options = ["One", "Two", "Three", "Four", "Five", "Six"]
    var picker = JSON.stringify({mode:"select", width:600, options:options})
    var tops = {}
    ;[true, false].forEach(function(background) {
      test.configure(background)
      palette.open(picker)
      var surface = palette.testPanel.height, full = palette.testCard.height
      tops[background + "all"] = test.screenTop()
      palette.setQuery("Three"); palette.runQuery()
      test.check(palette.rows.length === 1 && palette.testCard.height < full, "filtering shrinks the card")
      test.check(palette.testPanel.height === surface, "filtering keeps the surface size")
      tops[background + "one"] = test.screenTop()
      palette.setQuery("nothing matches"); palette.runQuery()
      test.check(palette.rows.length === 0 && palette.testPanel.height === surface, "the empty state fits the surface")
      if (!background) test.fits()
      palette.cancel()
    })
    test.check(Math.abs(tops.trueall - tops.falseall) <= 1 && Math.abs(tops.trueone - tops.falseone) <= 1,
               "picker card positions match: " + JSON.stringify(tops))
    // One option still leaves room for the two-row empty state.
    palette.open(JSON.stringify({mode:"select", width:600, options:["Only"]}))
    palette.setQuery("nothing matches"); palette.runQuery()
    test.fits()
    palette.cancel()

    // The screen is chosen by the focused monitor's name; no match leaves it
    // to the compositor. Offscreen screens are unnamed, so stand-ins are used.
    var outputs = [{name:"DP-6"}, {name:"DP-9"}]
    test.check(palette.screenNamed("DP-9", outputs) === outputs[1], "a monitor name finds its screen")
    test.check(palette.screenNamed("", outputs) === null && palette.screenNamed("HDMI-A-1", outputs) === null, "no name, no screen")
    test.check(palette.targetScreen === null, "without Hyprland the compositor keeps choosing")

    finish.start()
  } }
  Timer { id: finish; interval:300; onTriggered: { console.log("PASS palette window"); Qt.quit() } }
  Timer { interval:10000; running:true; onTriggered: { console.log("FAIL timeout"); Qt.quit() } }
}
''')
    env = dict(os.environ, HOME=str(work), XDG_RUNTIME_DIR=str(work), QT_QPA_PLATFORM="offscreen", QT_QPA_PLATFORMTHEME="generic", QT_QUICK_BACKEND="software", QML_IMPORT_PATH=str(work), OMARCHY_PATH="/usr/share/omarchy")
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    result = subprocess.run(["quickshell", "-p", str(work / "shell.qml")], env=env, capture_output=True, text=True, timeout=20)
    output = result.stdout + result.stderr
    assert "PASS palette window" in output and "FAIL" not in output, output
    assert not any(error in output for error in ["TypeError", "ReferenceError", "Binding loop"]), output
    print("PASS palette window: bounded surface, fixed picker surface, input mask, screen choice, settings, small displays and animations")
