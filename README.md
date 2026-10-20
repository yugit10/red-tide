# 赤潮快查 · 海洋微藻智能识别与赤潮风险提示工具

拍一张海面照片，判断有没有赤潮风险、该找谁；拍一张显微照片，判断是哪类微藻。

面向养殖户和岸边人员的轻量工具：不需要专业设备，手机拍一张就能得到一个可解释的预警；化验室拿到显微照片，可以进一步确认藻种。

---

## 两个分支

| 分支 | 输入 | 方案 | 使用者 |
| --- | --- | --- | --- |
| 宏观（主） | 海面照片 | HSV 水色规则流 × 宏观 CNN（保守融合）→ 四级预警 | 渔民、岸边人员 |
| 显微（次） | 显微照片 | MindSpore + MobileNetV3-Small 迁移学习，7 类识别 | 化验室 |

7 类：夜光藻、原甲藻、角毛藻、拟菱形藻、骨条藻、亚历山大藻、凯伦藻。

设计原则：**宁可保守，不可误报**。宏观分支以规则流为主，CNN 只作为辅助证据，融合结果会随证据强弱给出不同的置信区间。

## 实测指标

| 分支 | 指标 | 出处 |
| --- | --- | --- |
| 显微 7 类 | val acc **95.39%**（30 epoch，607/152 划分） | `model/train_log.json` |
| 宏观 25 张精选海面 | 规则流 **92%**（23/25）、宏观 CNN **80%**（20/25） | `model_macro/real_eval.json` |
| 逐类准确率 | 夜光藻 100%、原甲藻 95%、骨条藻 87.5%、凯伦藻 80% | `materials/eval_results.json` |

宏观分支不训 CNN 是一个**有意的决策**：公开来源的海面实拍图极少（正常海面仅 3 张），数据墙下训练只会得到过拟合的模型。规则流的阈值可审计、可回归，见 `materials/宏观数据墙与路线决策.md`。

## 快速开始

```bash
pip install streamlit mindspore mindcv numpy pillow requests openpyxl python-docx python-pptx matplotlib
streamlit run tools/app.py
```

几点说明：

- `tools/app.py` 里的模型路径默认指向 `D:\train\model` 等目录，换机器时需要改这三个常量。
- 模型权重（`*.ckpt`）和数据集图像按规范不入库，仓库里保留了 `train_log.json`、`class_map.json`、`eval_results.json` 和逐张溯源 CSV。
- 没有权重也能跑通界面，只是显微分支会提示模型缺失。

## 目录结构

```
tools/            源码
  app.py            Streamlit 界面
  fusion.py         贝叶斯融合引擎（宏观）
  predict.py        显微推理封装
  train.py          显微训练
  prepare_data.py   数据预处理
  package.py        组装提交包（内容匿名）
  make_doc.py       设计文档生成
  make_ppt.py       作品 PPT 生成
model/            显微模型（best.ckpt + train_log.json）
model_macro/      宏观模型（class_map.json + real_eval.json）
model_precheck/   海面/非海面预检模型
materials/        设计文档、作品 PPT、图表、评测结果
dataset_raw/      数据溯源（GBIF / CNKI），图像不入库
algae_dataset/    处理后数据集的 class_map
```

## 数据与合规

- 训练影像全部来自 GBIF / CNKI 公开来源，逐张记录采集号、学名、原始 URL、许可协议与权利人，见 `dataset_raw/*/provenance*.csv`。
- 提交包由 `tools/package.py` 组装，并自带匿名扫描：打包前检查包内文本是否残留学校名、姓名或手机号。
- 身份信息（学校名、队长姓名、手机号）**不写在代码里**，从本地 `.identity.local` 读取（已 gitignore）；仓库中用占位符。

## 版本

见 [CHANGELOG.md](CHANGELOG.md)。四个版本的关键变化：v2 确认宏观数据墙、决定规则流优先；v3 按渔民视角做可用性整改；v4 删除现场问卷、改为纯图像判定，并加入海面/非海面预检。
