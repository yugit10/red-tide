// 历史记录(本地 Storage,最近 20 条)
const KEY = 'chk_history';
const MAX = 20;

function list() {
  try { return wx.getStorageSync(KEY) || []; } catch (e) { return []; }
}

function add(rec) {
  const arr = list();
  arr.unshift(rec);
  try { wx.setStorageSync(KEY, arr.slice(0, MAX)); } catch (e) {}
}

function clear() {
  try { wx.removeStorageSync(KEY); } catch (e) {}
}

module.exports = { list, add, clear };
