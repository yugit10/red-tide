const { analyzeSea } = require('../../utils/analyze');
const storage = require('../../utils/storage');

Page({
  data: {
    imgPath: '',
    busy: false,
    status: '',
    err: '',
  },

  choosePhoto() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['camera', 'album'],
      sizeType: ['compressed'],
      success: (res) => {
        this.setData({ imgPath: res.tempFiles[0].tempFilePath, err: '', status: '' });
      },
    });
  },

  async startAnalyze() {
    if (!this.data.imgPath || this.data.busy) return;
    this.setData({ busy: true, err: '', status: '开始分析…' });
    try {
      const r = await analyzeSea(this.data.imgPath, (s) => this.setData({ status: s }));
      this.setData({ busy: false, status: '' });
      if (r.rejected) {
        this.setData({ err: '这张照片看起来不像海面照片(海面概率约' + Math.round(r.seaProb * 100) + '%)。请对着海面拍照,或换一张。' });
        return;
      }
      const app = getApp();
      app.globalData.lastResult = {
        type: 'sea',
        imgPath: this.data.imgPath,
        rule: r.rule,
        res: {
          top: r.res.top, top_cn: r.res.top_cn, top_short: r.res.top_short,
          confidence: r.res.confidence, risk: r.res.risk, risk_note: r.res.risk_note,
          advice: r.res.advice, alert: r.res.alert, evidence: r.res.evidence,
          cnn_used: r.res.cnn_used,
        },
        plain: r.plain,
        seaProb: r.seaProb,
      };
      // 记录历史
      storage.add({
        ts: Date.now(),
        type: 'sea',
        summary: r.res.top_short + ' · ' + r.res.alert.color_cn + r.res.alert.level + '级',
        index: r.res.alert.index,
        imgPath: this.data.imgPath,
      });
      wx.navigateTo({ url: '/pages/result/result' });
    } catch (e) {
      this.setData({ busy: false, status: '', err: (e && e.message) || '分析失败,请重试' });
    }
  },

  // 示例图(可选):把示例图片放到 miniprogram/assets/ 后,在下方数组里填路径
  useSample(e) {
    const p = e.currentTarget.dataset.path;
    if (!p) { wx.showToast({ title: '示例图未配置', icon: 'none' }); return; }
    this.setData({ imgPath: p, err: '', status: '' });
  },
});
