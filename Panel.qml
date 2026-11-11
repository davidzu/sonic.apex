import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import qs.Ui
import qs.Commons

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

  // Overwritten from `apexctl modes` so the panel never drifts from the CLI.
  property var rgbModes: ["theme", "solid", "gradient", "wave", "breathe", "rainbow", "reactive", "off"]
  property var rgbProfiles: ["sunset", "ocean", "fire", "matrix", "cyberpunk", "aurora", "candy", "ice", "vaporwave", "gold"]
  property var oledPages: ["clock", "now-playing", "workspace", "logo", "text", "clear"]
  property var wheelModes: ["volume", "workspace", "brightness", "oled", "rgb"]

  readonly property string pluginDir: Qt.resolvedUrl(".").toString().replace("file://", "").replace(/\/$/, "")
  readonly property string scriptDir: pluginDir + "/bin"
  readonly property string apexctl: scriptDir + "/apexctl"

  property var actionQueue: []
  property string lastError: ""

  function apex(args) {
    if (actionProc.running) {
      // A previous command is still finishing; queue this one so no click is
      // ever dropped.
      var next = root.actionQueue.slice()
      next.push(args)
      root.actionQueue = next
      return
    }
    root.lastError = ""
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
    if (!modesProc.running) modesProc.running = true
    root.refresh()
  }
  onOpenedChanged: if (opened) root.refresh()

  // Only poll while the panel is visible: a closed panel does not need a
  // Python process every 2.5s.
  Timer {
    interval: 2500
    running: root.opened
    repeat: true
    onTriggered: root.refresh()
  }

  Process {
    id: installProc
    command: ["bash", root.pluginDir + "/install", "--silent"]
    stdout: StdioCollector { waitForEnd: true }
  }

  Process {
    id: modesProc
    command: [root.apexctl, "modes"]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        try {
          var data = JSON.parse(String(text || "{}"))
          if (data.rgbModes && data.rgbModes.length) root.rgbModes = data.rgbModes
          if (data.profiles && data.profiles.length) root.rgbProfiles = data.profiles
          if (data.oledPages && data.oledPages.length) root.oledPages = data.oledPages
          if (data.wheelModes && data.wheelModes.length) root.wheelModes = data.wheelModes
        } catch (e) { /* keep the built-in defaults */ }
      }
    }
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
    stderr: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.lastError = String(text || "").trim()
    }
    onRunningChanged: {
      if (running) return
      if (root.actionQueue.length > 0) {
        var queue = root.actionQueue.slice()
        var args = queue.shift()
        root.actionQueue = queue
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
        ink: button.foreground
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
            ink: root.bar.foreground
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

        Text {
          width: parent.width
          visible: root.lastError.length > 0
          wrapMode: Text.WordWrap
          text: root.lastError
          color: root.bar.foreground
          opacity: 0.9
          font.family: root.bar.fontFamily
          font.pixelSize: Style.font.caption
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
        PanelSectionHeader { text: "GRADIENT PROFILES"; foreground: root.bar.foreground; fontFamily: root.bar.fontFamily }

        Flow {
          width: parent.width
          spacing: Style.spacing.xs
          Repeater {
            model: root.rgbProfiles
            Button {
              required property string modelData
              text: root.pretty(modelData)
              foreground: root.bar.foreground
              fontFamily: root.bar.fontFamily
              fontSize: Style.font.caption
              bordered: true
              active: root.status.rgb && root.status.rgb.mode === "gradient" && root.status.rgb.profile === modelData
              onClicked: root.apex(["rgb", "gradient", "-p", modelData])
            }
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
