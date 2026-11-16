// 保守融合 + 四级预警 + 三句大白话:与 D:\train\tools\fusion.py / app.py 等价

const HYP = ['noctiluca', 'toxic_dino', 'diatom', 'green_tide', 'none'];

const HYP_CN = {
  noctiluca: '夜光藻型水华(缺氧致害)',
  toxic_dino: '有毒甲藻型(可能产毒)',
  diatom: '硅藻型水华(缺氧/堵鳃)',
  green_tide: '绿潮/绿藻水华',
  none: '无明显赤潮(正常海水)',
};
const HYP_SHORT = {
  noctiluca: '夜光藻型', toxic_dino: '有毒甲藻型', diatom: '硅藻型',
  green_tide: '绿潮', none: '无明显赤潮',
};
const HYP_RISK = {
  noctiluca: ['中—高', '高生物量耗氧致鱼虾窒息, 一般不产毒'],
  toxic_dino: ['高', '可产麻痹性/神经性贝毒, 严禁采食贝类, 避免接触'],
  diatom: ['中', '堵塞鱼鳃/耗氧, 养殖区需增氧防损失'],
  green_tide: ['低—中', '主要影响景观与局部溶氧, 毒性低'],
  none: ['无', '未见赤潮征象'],
};
const HYP_ADVICE = {
  noctiluca: '建议上报当地海洋渔业部门; 养殖区夜间注意增氧; 避免直接接触水华。',
  toxic_dino: '立即上报; 严禁采捕/食用该海域贝类; 避免皮肤接触; 关注官方贝毒通报。',
  diatom: '上报并加密监测; 养殖区启动增氧; 关注鱼虾摄食与鳃部状况。',
  green_tide: '可上报城管/海洋部门清理; 避免在聚集区接触。',
  none: '无需处置; 若后续出现变色/死鱼请重新拍照查询。',
};
const RISK_WEIGHT = { '高': 1.0, '中—高': 0.8, '中': 0.6, '低—中': 0.4, '低': 0.25, '无': 0.0 };

const ALERT_LEVELS = [
  { level: 'Ⅰ', color_cn: '红色', color_hex: '#C00000', min: 70, name: '红色预警(Ⅰ级·特别严重)',
    meaning: '高置信命中高危/产毒类群, 赤潮危害风险很高。' },
  { level: 'Ⅱ', color_cn: '橙色', color_hex: '#ED7D31', min: 50, name: '橙色预警(Ⅱ级·严重)',
    meaning: '较高置信命中致灾类群, 需尽快核实与防范。' },
  { level: 'Ⅲ', color_cn: '黄色', color_hex: '#FFC000', min: 30, name: '黄色预警(Ⅲ级·较重)',
    meaning: '中等置信或中低危类群, 存在赤潮苗头, 需加强观察。' },
  { level: 'Ⅳ', color_cn: '蓝色', color_hex: '#2E75B6', min: 0, name: '蓝色预警(Ⅳ级·一般/观察)',
    meaning: '未见明显赤潮征象, 维持常规关注即可。' },
];

function alertFrom(risk, confidence) {
  const w = RISK_WEIGHT[risk] !== undefined ? RISK_WEIGHT[risk] : 0;
  const index = Math.round(confidence * w * 100);
  let lv = ALERT_LEVELS[ALERT_LEVELS.length - 1];
  for (const a of ALERT_LEVELS) { if (index >= a.min) { lv = a; break; } }
  return {
    index, level: lv.level, color_cn: lv.color_cn, color_hex: lv.color_hex,
    name: lv.name, meaning: lv.meaning, risk_weight: w,
    trigger: `预警指数 ${index} = 置信度${Math.round(confidence * 100)}% × 风险权重${w.toFixed(2)} × 100 → ${lv.color_cn}(${lv.level}级)`,
  };
}

// 宏观 CNN 的 5 类输出(顺序=model_macro/class_map.json: diatom, green_tide, noctiluca, none, toxic_dino)
const MACRO_CLASSES = ['diatom', 'green_tide', 'noctiluca', 'none', 'toxic_dino'];

function macroLikFromProbs(probs) {
  const lik = { noctiluca: 1, toxic_dino: 1, diatom: 1, green_tide: 1, none: 1 };
  for (let i = 0; i < MACRO_CLASSES.length; i++) lik[MACRO_CLASSES[i]] = probs[i] + 0.01;
  return lik;
}

// 保守融合(agree):规则流为主;CNN 仅在顶类与规则流一致时增强置信
function fuse(ruleLik, ruleMeta, cnnLik) {
  const post = {}; HYP.forEach(h => post[h] = 1.0);
  if (ruleLik) HYP.forEach(h => post[h] *= Math.pow(ruleLik[h], 2.0));
  let ruleTop = 'none', best = -1;
  if (ruleLik) HYP.forEach(h => { if (ruleLik[h] > best) { best = ruleLik[h]; ruleTop = h; } });
  const evidence = ['图像·水色CV(主)'];
  let cnnUsed = false, cnnTop = null;
  if (cnnLik) {
    cnnTop = HYP.reduce((a, b) => (cnnLik[a] >= cnnLik[b] ? a : b), HYP[0]);
    if (cnnTop === ruleTop) {
      HYP.forEach(h => post[h] *= cnnLik[h]);
      cnnUsed = true;
      evidence.push('图像·宏观CNN(辅助, 与规则流一致)');
    } else {
      evidence.push('图像·宏观CNN(提示不一致, 未计入)');
    }
  }
  let tot = 0; HYP.forEach(h => tot += post[h]); if (!tot) tot = 1;
  HYP.forEach(h => post[h] = post[h] / tot);
  const top = HYP.reduce((a, b) => (post[a] >= post[b] ? a : b), HYP[0]);
  const risk = HYP_RISK[top][0];
  const alert = alertFrom(risk, post[top]);
  return {
    posterior: post, top, top_cn: HYP_CN[top], top_short: HYP_SHORT[top],
    confidence: post[top], risk, risk_note: HYP_RISK[top][1], advice: HYP_ADVICE[top],
    alert, evidence, cnn_used: cnnUsed, cnn_top: cnnTop,
  };
}

// 三句大白话
function plainSentences(ruleMeta, res) {
  const conf = Math.round(res.confidence * 100);
  const colorCn = (ruleMeta && ruleMeta.color_cn) || '海面';
  let s1;
  if (res.top === 'none') s1 = `照片里的海是${colorCn}, 没看出赤潮, 眼下基本放心。`;
  else s1 = `照片里的海是${colorCn}, 大概是${res.top_short}, 十成里把握约${conf}成; 预警牌:${res.alert.color_cn}${res.alert.level}级。`;
  const s2 = res.advice.split(';')[0] + '。';
  const s3 = res.top === 'none'
    ? '不用上报; 哪天水变色、见死鱼, 再拍一张来查。'
    : '要上报: 打12345或找镇里渔业技术员; 也可点「复制上报话术」发到渔业微信群。';
  return { s1, s2, s3 };
}

module.exports = { HYP, HYP_CN, HYP_SHORT, HYP_RISK, HYP_ADVICE, ALERT_LEVELS, alertFrom, fuse, plainSentences, macroLikFromProbs, MACRO_CLASSES };
