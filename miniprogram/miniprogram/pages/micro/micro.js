const { analyzeMicro } = require('../../utils/analyze');
const storage = require('../../utils/storage');
const app = getApp();

Page({
  data: { imgPath: '', busy: false, status: '', err: '' },

  choosePhoto() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['camera', 'album'],
      sizeType: ['compressed'],
      success: (res) => this.setData({ imgPath: res.tempFiles[0].tempFilePath, err: '', status: '' }),
    });
  },

  async startAnalyze() {
    if (!this.data.imgPath || this.data.busy) return;
    this.setData({ busy: true, err: '', status: '正在识别…' });
    try {
      const r = await analyzeMicro(this.data.imgPath);
      this.setData({ busy: false, status: '' });
      app.globalData.lastResult = { type: 'micro', imgPath: this.data.imgPath, micro: r };
      storage.add({
        ts: Date.now(),
        type: 'micro',
        summary: r.top.cn + ' · 置信' + Math.round(r.top.prob * 100) + '%',
        imgPath: this.data.imgPath,
      });
      wx.navigateTo({ url: '/pages/result/result' });
    } catch (e) {
      this.setData({ busy: false, status: '', err: (e && e.message) || '识别失败,请重试' });
    }
  },
});
