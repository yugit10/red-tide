// 水色CV规则流:与 D:\train\tools\fusion.py 的 image_color_likelihood / sea_precheck 等价移植
// 输入均为 RGBA Uint8ClampedArray(来自 canvas getImageData)

const COLOR_LIK = {
  pink_red:    { noctiluca: 4.0, toxic_dino: 2.0, diatom: 1.0, green_tide: 0.3, none: 0.2 },
  brown_gold:  { noctiluca: 1.0, toxic_dino: 3.0, diatom: 3.0, green_tide: 0.3, none: 0.2 },
  green:       { noctiluca: 0.3, toxic_dino: 0.5, diatom: 1.5, green_tide: 4.0, none: 0.3 },
  foam_white:  { noctiluca: 2.0, toxic_dino: 1.0, diatom: 2.0, green_tide: 0.5, none: 0.5 },
  normal_blue: { noctiluca: 0.3, toxic_dino: 0.3, diatom: 0.3, green_tide: 0.3, none: 4.0 },
};
const COLOR_CN = {
  pink_red: '粉红/砖红', brown_gold: '褐黄/酱色', green: '翠绿/墨绿',
  foam_white: '乳白/泡沫', normal_blue: '灰蓝/正常',
};

// RGBA -> HSV 数组(逐像素)
function toHSV(rgba, w, h) {
  const n = w * h;
  const hue = new Float32Array(n);
  const s = new Float32Array(n);
  const v = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const r = rgba[i * 4] / 255, g = rgba[i * 4 + 1] / 255, b = rgba[i * 4 + 2] / 255;
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b);
    const df = mx - mn + 1e-8;
    v[i] = mx;
    s[i] = mx > 0 ? df / (mx + 1e-8) : 0;
    let hh = 0;
    if (mx === r) hh = ((g - b) / df) % 6;
    else if (mx === g) hh = (b - r) / df + 2;
    else hh = (r - g) / df + 4;
    hh *= 60;
    if (hh < 0) hh += 360;
    hue[i] = hh;
  }
  return { hue, s, v };
}

// 水色似然:对应 fusion.py image_color_likelihood(取下方 80% 区域,去天空)
// rgba 尺寸 w x h(建议 96x96 或 224x224 均可,内部按比例取中下带)
function colorLikelihood(rgba, w, h) {
  const y0 = Math.floor(h * 0.20);
  const bandW = w, bandH = h - y0;
  const n = bandW * bandH;
  const crop = new Uint8ClampedArray(n * 4);
  for (let y = y0; y < h; y++) {
    crop.set(rgba.subarray(y * w * 4, (y + 1) * w * 4), (y - y0) * w * 4);
  }
  const { hue, s, v } = toHSV(crop, bandW, bandH);
  let pink = 0, brown = 0, green = 0, foam = 0, sumS = 0, sumV = 0;
  for (let i = 0; i < n; i++) {
    const hh = hue[i], ss = s[i], vv = v[i];
    sumS += ss; sumV += vv;
    if (((hh >= 330) || (hh < 20)) && ss > 0.30 && vv > 0.15) pink++;
    if (hh >= 20 && hh < 50 && ss > 0.30 && vv > 0.20 && vv < 0.85) brown++;
    if (hh >= 50 && hh < 170 && ss > 0.30) green++;
    if (ss < 0.10 && vv > 0.80) foam++;
  }
  const fPink = pink / n, fBrown = brown / n, fGreen = green / n, fFoam = foam / n;
  let label = 'normal_blue';
  if (fPink > 0.02) label = 'pink_red';
  else if (fGreen > 0.05) label = 'green';
  else if (fBrown > 0.08) label = 'brown_gold';
  else if (fFoam > 0.30) label = 'foam_white';
  const meta = {
    f_pink: +fPink.toFixed(3), f_brown: +fBrown.toFixed(3),
    f_green: +fGreen.toFixed(3), f_foam: +fFoam.toFixed(3),
    sat: +(sumS / n).toFixed(3), val: +(sumV / n).toFixed(3),
    color_cn: COLOR_CN[label], color_key: label,
  };
  return { label, lik: Object.assign({}, COLOR_LIK[label]), meta };
}

// 海面规则兜底:对应 fusion.py sea_precheck 的规则部分(96x96 输入的 RGBA)
// water: hue 150-270 或 50-150, s>0.08, v>0.10;需要 f_water>=0.45 且 sat>0.08 且 ncol>=12
function seaRule(rgba96, w, h) {
  const { hue, s, v } = toHSV(rgba96, w, h);
  const n = w * h;
  let water = 0, sumS = 0;
  for (let i = 0; i < n; i++) {
    const hh = hue[i], ss = s[i], vv = v[i];
    sumS += ss;
    const m = ((hh >= 150 && hh <= 270) || (hh >= 50 && hh < 150)) && ss > 0.08 && vv > 0.10;
    if (m) water++;
  }
  const fWater = water / n;
  const meanS = sumS / n;
  // 颜色多样性:48x48 量化到 8 级(>>5)统计唯一色
  const qw = 48, qh = 48;
  const seen = new Set();
  for (let y = 0; y < qh; y++) {
    const sy = Math.floor(y * h / qh);
    for (let x = 0; x < qw; x++) {
      const sx = Math.floor(x * w / qw);
      const i = sy * w + sx;
      seen.add(((rgba96[i * 4] >> 5) << 6) | ((rgba96[i * 4 + 1] >> 5) << 3) | (rgba96[i * 4 + 2] >> 5));
    }
  }
  const ncol = seen.size;
  return {
    isSea: fWater >= 0.45 && meanS > 0.08 && ncol >= 12,
    fWater: +fWater.toFixed(3), sat: +meanS.toFixed(3), ncol,
  };
}

module.exports = { colorLikelihood, seaRule, COLOR_LIK, COLOR_CN };
