const storage = require('../../utils/storage');

Page({
  data: { list: [] },

  onShow() {
    this.refresh();
  },

  refresh() {
    this.setData({ list: storage.list() });
  },

  onItemTap(e) {
    const i = e.currentTarget.dataset.index;
    const rec = this.data.list[i];
    if (rec && rec.imgPath) {
      // 重看历史: 用当时图片重新走一次分析,或直接提示
      wx.showModal({
        title: '历史记录',
        content: '时间: ' + new Date(rec.ts).toLocaleString() + '\n结论: ' + rec.summary,
        showCancel: false,
      });
    }
  },

  onClear() {
    wx.showModal({
      title: '清空历史',
      content: '确定清空全部查询记录吗?',
      success: (res) => {
        if (res.confirm) { storage.clear(); this.refresh(); }
      },
    });
  },
});
