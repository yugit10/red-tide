App({
  globalData: {
    lastResult: null,   // 结果页数据(海面/显微)
  },
  onLaunch() {
    if (wx.cloud) {
      // 云开发环境 ID:在微信开发者工具"云开发"控制台可以看到,形如 xxx-1a2b3c
      wx.cloud.init({
        env: 'YOUR_ENV_ID',
        traceUser: true,
      });
    }
  },
});
