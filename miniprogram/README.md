# 赤潮快查 · 微信小程序版

海面照片 → 赤潮风险三级研判;显微照片 → 7 类藻种识别。
**全部推理在手机端完成**(微信官方 AI 推理 `wx.createInferenceSession`),图片不上传服务器。

## 一、准备工作(一次性)

1. **注册小程序账号**:https://mp.weixin.qq.com → 立即注册 → 小程序 → 个人主体(身份证+人脸,免费)
2. **安装微信开发者工具**:https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html
3. 注册完成后,在开发者工具里用 **AppID** 导入本项目(`D:\train\miniprogram`)

## 二、开通云开发(只用于存放模型文件)

1. 开发者工具顶部点 **云开发** → 开通(选免费套餐)
2. 记下 **环境 ID**(形如 `xxx-1a2b3c`)
3. 打开 `miniprogram/app.js`,把 `env: 'YOUR_ENV_ID'` 改成你的环境 ID

## 三、上传模型到云存储

1. 开发者工具 → 云开发 → **存储** → 新建文件夹 `models`
2. 把 `models/` 目录下的三个文件上传:
   - `pre.onnx`(海面/非海面预检)
   - `macro.onnx`(宏观 5 类)
   - `micro.onnx`(显微 7 类)
3. 上传后,点击每个文件 → 复制 **File ID**(形如 `cloud://xxx/models/pre.onnx`)
4. 打开 `miniprogram/utils/infer.js`,把 `MODELS` 里三处 `cloud://PLACEHOLDER/xxx.onnx` 替换成真实 File ID

## 四、调基础库版本

1. 开发者工具 → 详情 → 本地设置 → **调试基础库** 选 **2.30.0 或更高**
   (AI 推理能力 `wx.createInferenceSession` 需要 2.30.0+)
2. 若下拉里没有更高版本,先在工具里检查更新

## 五、真机调试

- **模拟器可能不支持 AI 推理**,请用 **真机调试**(开发者工具右上角"真机调试")或"预览"扫码
- 首次选图后会下载模型(每个约 6MB),下载一次后缓存在本机

## 六、决赛演示建议

1. 提前在手机上下载好三个模型(各跑一次),避免现场等下载
2. 首页"拍一张 / 从相册选"→ 选提前拍好的海面图 → 开始看风险
3. 结果页:预警牌 + 三句话 + 复制上报话术
4. 显微页签演示一张显微图
5. 历史页展示查询记录

## 七、常见问题

- **"当前基础库不支持 AI 推理"**:调高基础库到 2.30.0+
- **"模型云存储地址未配置"**:没填 infer.js 的 fileID
- **模型加载失败**:确认云存储文件是 .onnx、fileID 正确、已开云开发
- **定位失败**:不影响主流程,只是上报话术不带地点(需在小程序后台配置隐私指引+接口权限)

## 八、目录结构

```
miniprogram/
├── project.config.json
├── models/                    # 三个 ONNX(不入 git,需上传云存储)
└── miniprogram/
    ├── app.js / app.json / app.wxss
    ├── utils/
    │   ├── image.js           # 图像预处理(224 归一化 + 96 规则流)
    │   ├── ruleflow.js        # 水色CV规则流(移植自 fusion.py)
    │   ├── fusion.js          # 保守融合 + 四级预警 + 三句大白话
    │   ├── infer.js           # 模型下载/缓存/推理
    │   ├── analyze.js         # 海面/显微完整分析流程
    │   └── storage.js         # 历史记录
    └── pages/
        ├── index/             # 海面拍照
        ├── result/            # 结果页(海面/显微共用)
        ├── micro/             # 显微识别
        └── history/           # 历史记录
```
