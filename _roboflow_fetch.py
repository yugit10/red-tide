# -*- coding: utf-8 -*-
"""Roboflow Red Tide 数据集拉取: 先取项目元数据, 再下载最新版本 zip
key 从 _roboflow_key.txt 读取, 不做任何回显
"""
import urllib.request, urllib.parse, ssl, json, os, zipfile, sys

ctx = ssl.create_default_context()
KEY = open(r'D:\train\_roboflow_key.txt', encoding='utf-8').read().strip()
WORKSPACE = 'prowl-turdswerve-2024'
PROJECT = 'red-tide'
DL = r'D:\train\_roboflow_dl'
os.makedirs(DL, exist_ok=True)

def get(url, timeout=60):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read(), r.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers

out = []
# 1) 项目元数据
u = 'https://api.roboflow.com/%s/%s?api_key=%s' % (WORKSPACE, PROJECT, KEY)
st, body, hd = get(u)
out.append('项目元数据 HTTP %s' % st)
if st == 200:
    j = json.loads(body)
    out.append('  项目名: %s' % j.get('name'))
    out.append('  类型: %s | 公开: %s' % (j.get('type'), j.get('public')))
    vers = j.get('versions') or []
    out.append('  版本数: %d' % len(vers))
    for v in vers[:10]:
        out.append('    v%s | 图片%s | 标注%s | 创建 %s' % (
            v.get('id'), v.get('images'), v.get('num_annotations'), v.get('created_at', '?')))
else:
    out.append('  body: %s' % body[:300])

# 2) 最新版本下载(zip)
vers = json.loads(body).get('versions') if st == 200 else []
vid = None
if vers:
    vid = str(int(str(sorted(vers, key=lambda x: int(str(x.get('id', '0')).rstrip('/').split('/')[-1] or 0), reverse=True)[0].get('id')).rstrip('/').split('/')[-1]))
out.append('')
out.append('尝试下载版本 v%s' % vid)
if vid:
    u2 = 'https://api.roboflow.com/%s/%s/dataset/%s?api_key=%s' % (WORKSPACE, PROJECT, vid, KEY)
    st2, body2, hd2 = get(u2, timeout=180)
    out.append('  下载 HTTP %s | Content-Length: %s | Content-Type: %s' % (
        st2, hd2.get('Content-Length'), hd2.get('Content-Type')))
    if st2 == 200:
        zp = os.path.join(DL, 'red-tide.zip')
        with open(zp, 'wb') as f:
            f.write(body2)
        sz = os.path.getsize(zp) / 1e6
        out.append('  已保存 %s (%.1f MB)' % (zp, sz))
        # 解压
        try:
            with zipfile.ZipFile(zp) as z:
                z.extractall(os.path.join(DL, 'red-tide'))
            out.append('  解压完成, 顶层: %s' % os.listdir(os.path.join(DL, 'red-tide'))[:20])
        except Exception as e:
            out.append('  解压失败: %s (%s)' % (type(e).__name__, str(e)[:100]))
            # 可能是 JSON 错误信息
            out.append('  body 前300: %s' % body2[:300])
    else:
        out.append('  body 前500: %s' % body2[:500])

with open(r'D:\train\_rf_fetch.txt', 'w', encoding='utf-8') as f:
    f.write('\r\n'.join(out))
print('DONE')
