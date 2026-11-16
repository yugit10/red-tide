const { prepImage } = require('./image');
const { ensureModel, predict, MICRO_CLASSES, MICRO_CN, MICRO_RISK } = require('./infer');
const { colorLikelihood, seaRule } = require('./ruleflow');
const fusion = require('./fusion');

// 海面照完整分析:预检 -> 规则流 + 宏观CNN 保守融合
async function analyzeSea(tempPath, onProgress) {
  const say = (s) => onProgress && onProgress(s);
  say('正在准备图像…');
  const { input, d96 } = await prepImage(tempPath);

  say('正在加载预检模型(首次需下载)…');
  await ensureModel('pre');
  const preProbs = await predict('pre', input);   // [nonsea, sea]
  const seaProb = preProbs[1];

  let isSea = false, src = '';
  if (seaProb < 0.30) { isSea = false; src = 'cnn'; }
  else if (seaProb >= 0.60) { isSea = true; src = 'cnn'; }
  else {
    const r = seaRule(d96, 96, 96);
    isSea = r.isSea; src = 'tie';
  }
  if (!isSea) {
    return { rejected: true, seaProb, src };
  }

  say('正在分析水色…');
  const rule = colorLikelihood(d96, 96, 96);

  let cnnLik = null;
  try {
    say('正在加载宏观模型(首次需下载)…');
    await ensureModel('macro');
    const mp = await predict('macro', input);
    cnnLik = fusion.macroLikFromProbs(mp);
  } catch (e) {
    cnnLik = null;   // 宏观模型失败不阻塞, 退化为规则流单证据
  }

  const res = fusion.fuse(rule.lik, rule.meta, cnnLik);
  const plain = fusion.plainSentences(rule.meta, res);
  return { rejected: false, rule, res, plain, seaProb, src };
}

// 显微照分析
async function analyzeMicro(tempPath) {
  const { input } = await prepImage(tempPath);
  await ensureModel('micro');
  const probs = await predict('micro', input);
  const ranked = probs.map((p, i) => ({ cls: MICRO_CLASSES[i], cn: MICRO_CN[MICRO_CLASSES[i]], prob: p }))
    .sort((a, b) => b.prob - a.prob);
  const top = ranked[0];
  const risk = MICRO_RISK[top.cls] || ['中', ''];
  return { top, ranked: ranked.slice(0, 3), risk };
}

module.exports = { analyzeSea, analyzeMicro };
