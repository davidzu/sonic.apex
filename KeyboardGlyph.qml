import QtQuick

// Drawn keyboard icon: rounded body outline, two rows of keys, a spacebar
// flanked by two keys. Scales to its slot and follows the theme via `ink`.
Canvas {
  id: glyph

  property color ink: "#ffffff"
  onInkChanged: requestPaint()
  onWidthChanged: requestPaint()
  onHeightChanged: requestPaint()

  onPaint: {
    var ctx = getContext("2d")
    ctx.reset()
    var u = Math.min(width / 24, height / 24)
    if (u <= 0) return
    var ink = String(glyph.ink)
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
    var fW = 2.4 * u, sbW = 11.2 * u
    ctx.fillRect(x + pad, sy, fW, dashH)
    ctx.fillRect(x + (kw - sbW) / 2, sy, sbW, dashH)
    ctx.fillRect(x + kw - pad - fW, sy, fW, dashH)
  }
}
