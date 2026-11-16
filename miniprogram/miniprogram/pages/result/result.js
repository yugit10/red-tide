const app = getApp();

Page({
  data: {
    r: null,          // 结果对象
    isMicro: false,
    location: '',
    showEvidence: false,
    copied: false,
  },

  onLoad() {
    const r = app.globalData.lastResult || null;
    this.setData({ r, isMicro: !!(r && r.type === 'micro') });
    this.tryLocation();
  },

  // 定位:失败不阻塞(只影响"上报话术是否带地点")
  tryLocation() {
    wx.getLocation({
      type: 'wgs84',
      success: (res) => {
        this.setData({ location: res.latitude.toFixed(4) + ',' + res.longitude.toFixed(4) });
      },
      fail: () => { /* 未授权/未开通: 静默 */ },
    });
  },

  toggleEvidence() {
    this.setData({ showEvidence: !this.data.showEvidence });
  },

  copyReport() {
    const r = this.data.r;
    if (!r) return;
    let text = '';
    if (r.type === 'sea') {
      const a = r.res.alert;
      text = '【赤潮快查】' + new Date().toLocaleString() + '\n'
        + '研判: ' + r.res.top_cn + '(把握约' + Math.round(r.res.confidence * 100) + '成)\n'
        + '预警: ' + a.color_cn + a.level + '级 · 指数' + a.index + '\n'
        + '建议: ' + r.res.advice + '\n'
        + (this.data.location ? '位置: ' + this.data.location + '\n' : '')
        + '（照片由本工具自动识别，仅供上报参考）';
    } else {
      text = '【赤潮快查·显微】' + new Date().toLocaleString() + '\n'
        + '识别: ' + r.micro.top.cn + '(置信度' + Math.round(r.micro.top.prob * 100) + '%)\n'
        + '风险: ' + r.micro.risk[0] + ' · ' + r.micro.risk[1];
    }
    wx.setClipboardData({
      data: text,
      success: () => { this.setData({ copied: true }); wx.showToast({ title: '已复制, 去群里粘贴', icon: 'none' }); },
      fail: () => { wx.showToast({ title: '复制失败, 请长按选择', icon: 'none' }); },
    });
  },

  back() { wx.navigateBack({ delta: 1 }); },
});
