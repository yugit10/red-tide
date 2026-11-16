// 模型管理:云存储下载 -> USER_DATA_PATH 缓存 -> wx.createInferenceSession 推理
// 模型文件:micro.onnx(7类) / macro.onnx(5类) / pre.onnx(2类)  输入 x[1,3,224,224] 输出 "232"
const MACRO_CLASSES = ['diatom', 'green_tide', 'noctiluca', 'none', 'toxic_dino'];
const MICRO_CLASSES = ['alexandrium', 'chaetoceros', 'karenia', 'noctiluca', 'prorocentrum', 'pseudonitzschia', 'skeletonema'];
const MICRO_CN = {
  alexandrium: '亚历山大藻属', chaetoceros: '角毛藻属', karenia: '凯伦藻属',
  noctiluca: '夜光藻', prorocentrum: '原甲藻属', pseudonitzschia: '拟菱形藻属', skeletonema: '骨条藻属',
};
const MICRO_RISK = {
  alexandrium: ['高', '可产麻痹性贝毒(PSP), 属重点产毒类群'],
  chaetoceros: ['中', '可能堵塞鱼鳃, 大量繁殖时影响养殖'],
  karenia: ['中—高', '部分种类产神经性毒素, 需警惕'],
  noctiluca: ['中—高', '高生物量耗氧致缺氧, 一般不产毒'],
  prorocentrum: ['高', '可产腹泻性贝毒(DSP)'],
  pseudonitzschia: ['高', '可产记忆缺失性贝毒(ASP)'],
  skeletonema: ['中', '常见硅藻水华, 耗氧/堵鳃'],
};

// 云存储 fileID 占位:上传模型后把下面的 cloud:// 换成真实 fileID
const MODELS = {
  pre: { fileID: 'cloud://PLACEHOLDER/pre.onnx', local: 'pre.onnx', classes: ['nonsea', 'sea'] },
  macro: { fileID: 'cloud://PLACEHOLDER/macro.onnx', local: 'macro.onnx', classes: MACRO_CLASSES },
  micro: { fileID: 'cloud://PLACEHOLDER/micro.onnx', local: 'micro.onnx', classes: MICRO_CLASSES },
};

const DIR = `${wx.env.USER_DATA_PATH}/models`;
const sessions = {};   // name -> session
const paths = {};      // name -> 本地路径

function ensureDir() {
  try { wx.getFileSystemManager().accessSync(DIR); } catch (e) {
    try { wx.getFileSystemManager().mkdirSync(DIR, true); } catch (e2) {}
  }
}

function localPath(name) { return `${DIR}/${MODELS[name].local}`; }

function exists(p) {
  try { wx.getFileSystemManager().accessSync(p); return true; } catch (e) { return false; }
}

// 下载模型(带进度回调)
async function ensureModel(name, onProgress) {
  ensureDir();
  const p = localPath(name);
  if (exists(p)) { paths[name] = p; return p; }
  const cfg = MODELS[name];
  if (!wx.cloud || cfg.fileID.indexOf('cloud://PLACEHOLDER') === 0) {
    throw new Error('模型云存储地址未配置(请上传模型并替换 MODELS.fileID)');
  }
  const res = await wx.cloud.downloadFile({ fileID: cfg.fileID, onProgressUpdate: onProgress });
  const fs = wx.getFileSystemManager();
  fs.copyFileSync(res.tempFilePath, p);
  paths[name] = p;
  return p;
}

// 创建推理 session
function createSession(name) {
  if (sessions[name]) return Promise.resolve(sessions[name]);
  const p = paths[name] || localPath(name);
  return new Promise((resolve, reject) => {
    if (!wx.createInferenceSession) {
      reject(new Error('当前基础库不支持 AI 推理(需 2.30.0+),请在开发者工具"详情-本地设置"调高基础库版本'));
      return;
    }
    const s = wx.createInferenceSession({
      model: p,
      precisionLevel: 0,
      allowQuantize: false,
      success: () => { sessions[name] = s; resolve(s); },
      fail: (e) => reject(new Error('模型加载失败(' + name + '): ' + JSON.stringify(e))),
    });
  });
}

function softmax(logits) {
  const mx = Math.max.apply(null, logits);
  const ex = logits.map(x => Math.exp(x - mx));
  const sum = ex.reduce((a, b) => a + b, 0) || 1;
  return ex.map(x => x / sum);
}

// 执行一次推理,返回概率数组
async function predict(name, input) {
  const session = await createSession(name);
  const out = await new Promise((resolve, reject) => {
    session.run({
      x: { data: input, shape: [1, 3, 224, 224] },
      success: resolve,
      fail: (e) => reject(new Error('推理失败(' + name + '): ' + JSON.stringify(e))),
    });
  });
  // 取第一个输出(输出名 "232")
  const key = Object.keys(out)[0];
  const arr = out[key] && out[key].data ? out[key].data : out[0] && out[0].data ? out[0].data : null;
  if (!arr) throw new Error('推理输出为空');
  const logits = Array.from(arr);
  return softmax(logits);
}

module.exports = {
  MODELS, MACRO_CLASSES, MICRO_CLASSES, MICRO_CN, MICRO_RISK,
  ensureModel, createSession, predict, softmax,
};
