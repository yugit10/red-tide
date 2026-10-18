# 海洋微藻智能识别与赤潮风险提示工具 —— 源码说明

## 项目简介
面向福建沿海的赤潮风险提示工具,双分支架构:
- **宏观分支(海面照片)**:水色 CV 检测 × 六问现场问卷 → 贝叶斯融合 → 四级预警(红/橙/黄/蓝),无需训练、秒级响应;
- **显微分支(显微照片)**:MindSpore + MindCV 训练 MobileNetV3-Small,对 7 类赤潮微藻识别确认(实验室人员使用),验证集准确率约 95.4%。

## 环境
- Python 3.10
- 依赖:`mindspore`、`mindcv`、`streamlit`、`pillow`、`openpyxl`、`numpy(<2)`、`matplotlib`、`python-pptx`、`python-docx`

## 目录 / 文件说明
| 文件 | 作用 |
|---|---|
| `app.py` | Streamlit 前端(双 Tab:渔民「拍海面查风险」+ 化验室「显微照片」),含语音播报/复制上报话术/定位 |
| `predict.py` | 显微分支推理:加载 best.ckpt + class_map.json,输出类别/置信度/Top-3/风险信息 |
| `fusion.py` | 宏观分支融合引擎:水色似然 × 问卷似然 → 贝叶斯后验 → 四级预警;保留 image_cnn_likelihood 扩展钩子 |
| `train.py` | 显微分支训练脚本(MindSpore + MindCV,迁移学习,支持 --epochs / --batch-size) |
| `prepare_data.py` | 由原始图像重建 train/val 目录(去重、划分) |
| `eval_and_charts.py` | 验证集评估 + 混淆矩阵/准确率曲线等图表 |
| `gbif_download2.py` | GBIF 公开影像下载器(带逐张溯源) |
| `make_kb.py` | 由藻种知识库源表生成 `藻种知识库.xlsx`(风险/预警/融合权重可审计) |
| `make_doc.py` / `make_ppt.py` | 生成设计文档 / 作品 PPT 的脚本 |
| `藻种知识库.xlsx` | 单一数据源:7 类藻种信息 + 宏观融合似然表 + 预警分级表(均可审计) |

## 快速开始
```bash
# 1. 启动 Web 应用(默认 D:\train\... 路径,或修改 app.py / predict.py 顶部路径常量)
streamlit run app.py

# 2. 浏览器访问 http://localhost:8501
#    - 「📷 拍海面查风险」:上传海面现状照片,回答六问(可跳过),得到渔民三句话结论 + 四级预警 + 给专家看的证据链
#    - 「🔬 显微照片」:上传显微照片(可多张),识别藻种 + 置信度 + 风险等级 + 科普信息

# 3. 命令行显微推理
python predict.py <图像或目录>

# 4. 宏观融合(命令行)
python -c "from PIL import Image; import fusion; print(fusion.fuse(fusion.image_color_likelihood(Image.open('<海面照>'))[1], {}))"
```

## 复现训练(显微分支)
```bash
python prepare_data.py           # 由 数据集/ 重建 train/val
python train.py --epochs 30      # 训练(详见 train_log.json,验证集约 95.4%)
```

## 数据真实性
- `数据集/provenance.csv` 逐张记录:类别、GBIF 采集记录号、记录学名、影像原始 URL、许可协议、权利人;
- 全部图像来自 GBIF 公开采集影像与 CNKI 学术显微图,真实可溯源;
- 宏观融合的问卷/水色似然权重(见 `藻种知识库.xlsx`「宏观融合似然表」)与四级预警阈值(「预警分级表」)均可审计。

## 免责声明
本工具用于科普与辅助研判,不构成专业监测结论;赤潮确认以当地海洋与渔业部门发布为准。
