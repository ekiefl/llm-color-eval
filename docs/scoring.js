function hsbToRgb(h, s, b) {
  s /= 100; b /= 100;
  const c = b * s, x = c * (1 - Math.abs((h / 60) % 2 - 1)), m = b - c;
  let r = 0, g = 0, bl = 0;
  if (h < 60) { r = c; g = x; } else if (h < 120) { r = x; g = c; }
  else if (h < 180) { g = c; bl = x; } else if (h < 240) { g = x; bl = c; }
  else if (h < 300) { r = x; bl = c; } else { r = c; bl = x; }
  return [Math.round((r + m) * 255), Math.round((g + m) * 255), Math.round((bl + m) * 255)];
}

function hexToRgb(hex) {
  return [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
}

function rgbToHsb(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min;
  let h = 0;
  if (d > 0) {
    if (max === r) h = 60 * (((g - b) / d) % 6);
    else if (max === g) h = 60 * ((b - r) / d + 2);
    else h = 60 * ((r - g) / d + 4);
  }
  return [(h + 360) % 360, max === 0 ? 0 : (d / max) * 100, max * 100];
}

function rgbToLab(r, g, b) {
  const lin = c => { c /= 255; return c > 0.04045 ? Math.pow((c + 0.055) / 1.055, 2.4) : c / 12.92; };
  const rl = lin(r), gl = lin(g), bl = lin(b);
  const x = (0.4124564 * rl + 0.3575761 * gl + 0.1804375 * bl) / 0.95047;
  const y = 0.2126729 * rl + 0.7151522 * gl + 0.0721750 * bl;
  const z = (0.0193339 * rl + 0.1191920 * gl + 0.9503041 * bl) / 1.08883;
  const f = t => t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116;
  return [116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))];
}

function deltaE2000(lab1, lab2) {
  const [l1, a1, b1] = lab1, [l2, a2, b2] = lab2;
  const lBar = (l1 + l2) / 2;
  const cBar = (Math.hypot(a1, b1) + Math.hypot(a2, b2)) / 2;
  const g = 0.5 * (1 - Math.sqrt(Math.pow(cBar, 7) / (Math.pow(cBar, 7) + Math.pow(25, 7))));
  const ap1 = a1 * (1 + g), ap2 = a2 * (1 + g);
  const cp1 = Math.hypot(ap1, b1), cp2 = Math.hypot(ap2, b2);
  const cpBar = (cp1 + cp2) / 2, dcp = cp2 - cp1;
  const hp1 = (Math.atan2(b1, ap1) * 180 / Math.PI + 360) % 360;
  const hp2 = (Math.atan2(b2, ap2) * 180 / Math.PI + 360) % 360;
  let dhp, hpBar;
  if (Math.abs(hp1 - hp2) <= 180) {
    dhp = hp2 - hp1;
    hpBar = (hp1 + hp2) / 2;
  } else {
    dhp = hp2 <= hp1 ? hp2 - hp1 + 360 : hp2 - hp1 - 360;
    hpBar = hp1 + hp2 < 360 ? (hp1 + hp2 + 360) / 2 : (hp1 + hp2 - 360) / 2;
  }
  const rad = d => d * Math.PI / 180;
  const dhpTerm = 2 * Math.sqrt(cp1 * cp2) * Math.sin(rad(dhp) / 2);
  const t = 1 - 0.17 * Math.cos(rad(hpBar - 30)) + 0.24 * Math.cos(rad(2 * hpBar))
    + 0.32 * Math.cos(rad(3 * hpBar + 6)) - 0.20 * Math.cos(rad(4 * hpBar - 63));
  const sl = 1 + 0.015 * Math.pow(lBar - 50, 2) / Math.sqrt(20 + Math.pow(lBar - 50, 2));
  const sc = 1 + 0.045 * cpBar, sh = 1 + 0.015 * cpBar * t;
  const rt = -2 * Math.sqrt(Math.pow(cpBar, 7) / (Math.pow(cpBar, 7) + Math.pow(25, 7)))
    * Math.sin(rad(60 * Math.exp(-Math.pow((hpBar - 275) / 25, 2))));
  return Math.sqrt(
    Math.pow((l2 - l1) / sl, 2) + Math.pow(dcp / sc, 2) + Math.pow(dhpTerm / sh, 2)
    + (dcp / sc) * rt * (dhpTerm / sh)
  );
}

function dialedScore(guessHsb, truthHex) {
  const guessRgb = hsbToRgb(...guessHsb);
  const truthRgb = hexToRgb(truthHex);
  const distance = deltaE2000(rgbToLab(...guessRgb), rgbToLab(...truthRgb));
  const base = 10 / (1 + Math.pow(distance / 25.25, 1.55));
  const truthHsb = rgbToHsb(...truthRgb);
  const dh = Math.min(Math.abs(guessHsb[0] - truthHsb[0]), 360 - Math.abs(guessHsb[0] - truthHsb[0]));
  const meanSat = (guessHsb[1] + truthHsb[1]) / 2;
  const adjusted = base
    + (10 - base) * Math.max(0, 1 - Math.pow(dh / 25, 1.5)) * Math.min(1, meanSat / 30) * 0.25
    - base * Math.max(0, (dh - 30) / 150) * Math.min(1, meanSat / 40) * 0.15;
  return Math.max(0, Math.min(10, Math.round(adjusted * 100) / 100));
}

if (typeof module !== "undefined") {
  module.exports = { hsbToRgb, hexToRgb, rgbToHsb, rgbToLab, deltaE2000, dialedScore };
}
