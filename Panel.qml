import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import qs.Ui
import qs.Commons

// Drawn keyboard icon: rounded body outline, two rows of keys, a spacebar
// flanked by modifier keys. Scales to the slot and follows the theme color.
component KeyboardGlyph: Canvas {
  id: glyph
  property color inkColor: "#ffffff"
  onInkColorChanged: requestPaint()
  onWidthChanged: requestPaint()
  onHeightChanged: requestPaint()

  onPaint: {
    var ctx = getContext("2d")
    ctx.reset()
    var u = Math.min(width / 24, height / 24)
    if (u <= 0) return
    var ink = String(inkColor)
    ctx.strokeStyle = ink
    ctx.fillStyle = ink
    ctx.lineWidth = Math.max(1.2, 1.6 * u)

    // Body outline: 22u x 10u, centered in the slot
    var kw = 22 * u, kh = 10 * u
    var x = (width - kw) / 2, y = (height - kh) / 2
    ctx.strokeRect(x, y, kw, kh)

    // Two rows of six keys
    var dashW = 2 * u, dashH = 1.3 * u, gap = 1.2 * u, pad = 1.8 * u
    var r1 = y + pad, r2 = y + pad + dashH + 1.2 * u
    for (var c = 0; c < 6; c++) {
      var kx = x + pad + c * (dashW + gap)
      ctx.fillRect(kx, r1, dashW, dashH)
      ctx.fillRect(kx, r2, dashW, dashH)
    }

    // Bottom row: two keys, wide spacebar, two keys
    var sy = y + pad + 2 * (dashH + 1.2 * u)
    var fW = 2.4 * u, sbW = 10 * u
    ctx.fillRect(x + pad, sy, fW, dashH)
    ctx.fillRect(x + (kw - sbW) / 2, sy, sbW, dashH)
    ctx.fillRect(x + kw - pad - fW, sy, fW, dashH)
  }
}

Panel {
  id: root
  moduleName: "sonic.apex"
  ipcTarget: "sonic.apex"
  manageIpc: true

  property var status: ({
    device: "Apex 7 TKL",
    rgb: { mode: "theme", brightness: 80, speed: 45, solid: "#89b4fa" },
    oled: { page: "clock" },
    wheel: { mode: "volume" },
    openrgb: false,
    daemon: false
  })

  readonly property var rgbModes: ["theme", "solid", "wave", "breathe", "rainbow", "reactive", "off"]
  readonly property var oledPages: ["clock", "now-playing", "workspace", "logo", "text", "clear"]
  readonly property var wheelModes: ["volume", "workspace", "brightness", "oled", "rgb"]

  readonly property string pluginDir: Qt.resolvedUrl(".").toString().replace("file://", "").replace(/\/$/, "")
  readonly property string scriptDir: pluginDir + "/bin"
  readonly property string apexctl: scriptDir + "/apexctl"

  property var queuedAction: null

  function apex(args) {
    if (actionProc.running) {
      // A previous command is still finishing; queue this one so no click is
      // ever dropped.
      root.queuedAction = args
      return
    }
    actionProc.command = [root.apexctl].concat(args)
    actionProc.running = true
  }

  function refresh() {
    if (!statusProc.running) statusProc.running = true
  }

  function pretty(value) {
    if (!value) return ""
    return String(value).replace(/-/g, " ")
  }

  Component.onCompleted: {
    if (!installProc.running) installProc.running = true
    root.refresh()
  }
  onOpenedChanged: if (opened) root.refresh()

  Timer {
    interval: 2500
    running: true
    repeat: true
    onTriggered: root.refresh()
  }

  Process {
    id: installProc
    command: ["bash", root.pluginDir + "/install", "--silent"]
    stdout: StdioCollector { waitForEnd: true }
  }

  Process {
    id: statusProc
    command: [root.apexctl, "status", "--json"]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        try {
          var data = JSON.parse(String(text || "{}"))
          if (data && data.rgb) root.status = data
        } catch (e) { /* ignore */ }
      }
    }
  }

  Process {
    id: actionProc
    stdout: StdioCollector { waitForEnd: true }
    onRunningChanged: {
      if (running) return
      if (root.queuedAction) {
        var args = root.queuedAction
        root.queuedAction = null
        root.apex(args)
      } else {
        root.refresh()
      }
    }
  }

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "󰌏"
    iconComponent: Component {
      KeyboardGlyph {
        anchors.fill: parent
        inkColor: button.foreground
      }
    }
    onPressed: function(b) { root.toggle() }
  }

  KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    contentWidth: panel.fittedContentWidth(Style.space(420))
    contentHeight: panel.fittedContentHeight(panelColumn.implicitHeight, Style.space(560))

    ScrollView {
      id: scrollArea
      anchors.fill: parent
      clip: true
      ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
      ScrollBar.vertical.policy: panelColumn.implicitHeight > height ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff

      Column {
        id: panelColumn
        width: scrollArea.availableWidth
        spacing: Style.space(14)

        Item {
          width: parent.width
          implicitHeight: heroIcon.implicitHeight
          KeyboardGlyph {
            id: heroIcon
            width: Style.font.display * 1.3
            height: Style.font.display * 1.3
            inkColor: root.bar.foreground
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
          }
          Column {
            anchors.left: heroIcon.right
            anchors.leftMargin: Style.space(14)
            anchors.verticalCenter: parent.verticalCenter
            spacing: 0
            Text {
              text: "Apex 7 TKL"
              color: root.bar.foreground
              font.family: root.bar.fontFamily
              font.pixelSize: Style.font.title
              font.bold: true
            }
            Text {
              text: root.status.daemon === false ? "daemon offline" : root.pretty(root.status.rgb && root.status.rgb.mode)
              color: root.bar.foreground
              opacity: 0.7
              font.family: root.bar.fontFamily
              font.pixelSize: Style.font.caption
            }
          }
        }

        PanelSeparator { foreground: root.bar.foreground }
        PanelSectionHeader { text: "RGB"; foreground: root.bar.foreground; fontFamily: root.bar.fontFamily }

        Flow {
          width: parent.width
          spacing: Style.spacing.xs
          Repeater {
            model: root.rgbModes
            Button {
              required property string modelData
              text: root.pretty(modelData)
              foreground: root.bar.foreground
              fontFamily: root.bar.fontFamily
              fontSize: Style.font.caption
              bordered: true
              active: root.status.rgb && root.status.rgb.mode === modelData
              onClicked: root.apex(["rgb", modelData])
            }
          }
        }

        Row {
          width: parent.width
          spacing: Style.spacing.xs
          Button {
            text: "Dim"
            foreground: root.bar.foreground
            fontFamily: root.bar.fontFamily
            fontSize: Style.font.caption
            bordered: true
            onClicked: root.apex(["rgb", "-b", String(Math.max(10, Number(root.status.rgb && root.status.rgb.brightness || 80) - 15))])
          }
          Button {
            text: "Bright"
            foreground: root.bar.foreground
            fontFamily: root.bar.fontFamily
            fontSize: Style.font.caption
            bordered: true
            onClicked: root.apex(["rgb", "-b", String(Math.min(100, Number(root.status.rgb && root.status.rgb.brightness || 80) + 15))])
          }
          Button {
            text: "Theme colors"
            foreground: root.bar.foreground
            fontFamily: root.bar.fontFamily
            fontSize: Style.font.caption
            bordered: true
            onClicked: root.apex(["rgb", "theme"])
          }
        }

        PanelSeparator { foreground: root.bar.foreground }
        PanelSectionHeader { text: "OLED"; foreground: root.bar.foreground; fontFamily: root.bar.fontFamily }

        Flow {
          width: parent.width
          spacing: Style.spacing.xs
          Repeater {
            model: root.oledPages
            Button {
              required property string modelData
              text: root.pretty(modelData)
              foreground: root.bar.foreground
              fontFamily: root.bar.fontFamily
              fontSize: Style.font.caption
              bordered: true
              active: root.status.oled && root.status.oled.page === modelData
              onClicked: root.apex(["oled", modelData])
            }
          }
        }

        PanelSeparator { foreground: root.bar.foreground }
        PanelSectionHeader { text: "WHEEL"; foreground: root.bar.foreground; fontFamily: root.bar.fontFamily }

        Flow {
          width: parent.width
          spacing: Style.spacing.xs
          Repeater {
            model: root.wheelModes
            Button {
              required property string modelData
              text: root.pretty(modelData)
              foreground: root.bar.foreground
              fontFamily: root.bar.fontFamily
              fontSize: Style.font.caption
              bordered: true
              active: root.status.wheel && root.status.wheel.mode === modelData
              onClicked: root.apex(["wheel", modelData])
            }
          }
        }

        Text {
          width: parent.width
          wrapMode: Text.WordWrap
          text: "Volume stays the default. Switch the wheel to workspaces, brightness, OLED pages, or RGB effects. Click the wheel to mute / cycle."
          color: root.bar.foreground
          opacity: 0.65
          font.family: root.bar.fontFamily
          font.pixelSize: Style.font.caption
        }
      }
    }
  }
}
