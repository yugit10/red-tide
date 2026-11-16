// 图像预处理:临时图片路径 -> 模型输入(1x3x224x224 NCHW 归一化) + 规则流 96x96 像素
const MEAN = [123.675, 116.28, 103.53];   // ImageNet mean*255
const STD = [58.395, 57.12, 57.375];      // ImageNet std*255

function makeCanvas(w, h) {
  const c = wx.createOffscreenCanvas({ type: '2d', width: w, height: h });
  return { c, ctx: c.getContext('2d') };
}

function loadImage(canvas, src) {
  return new Promise((resolve, reject) => {
    const img = canvas.createImage();
    img.onload = () => resolve(img);
    img.onerror = (e) => reject(new Error('图片加载失败: ' + JSON.stringify(e)));
    img.src = src;
  });
}

async function prepImage(tempPath) {
  // 224x224 -> 模型输入
  const a = makeCanvas(224, 224);
  const img = await loadImage(a.c, tempPath);
  a.ctx.drawImage(img, 0, 0, 224, 224);
  const d224 = a.ctx.getImageData(0, 0, 224, 224).data;

  // 96x96 -> 规则流
  const b = makeCanvas(96, 96);
  b.ctx.drawImage(img, 0, 0, 96, 96);
  const d96 = b.ctx.getImageData(0, 0, 96, 96).data;

  const N = 224 * 224;
  const input = new Float32Array(3 * N);
  for (let i = 0; i < N; i++) {
    input[i] = (d224[i * 4] - MEAN[0]) / STD[0];
    input[N + i] = (d224[i * 4 + 1] - MEAN[1]) / STD[1];
    input[2 * N + i] = (d224[i * 4 + 2] - MEAN[2]) / STD[2];
  }
  return { input, d96, size: 224 };
}

module.exports = { prepImage };
