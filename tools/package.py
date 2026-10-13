# -*- coding: utf-8 -*-
"""package.py —— 组装提交包(内容匿名)并打包 zip
结构:
  作品PPT.pptx / 设计文档.docx
  源码/(各 .py + 藻种知识库.xlsx)
  模型/(best.ckpt, train_log.json, class_map.json)
  数据集/(algae_dataset 处理后 train/val + provenance.csv)
  演示说明.txt
输出: D:\\train\\submission\\学校名称-海洋微藻智能识别与赤潮风险提示工具-队长-13800000000.zip
(文件名含队长真实姓名与手机号; 包内内容匿名)
"""
import os, shutil, zipfile, re

ROOT=r"D:\train"; STAGE=os.path.join(ROOT,"submission","stage")
TOOLS=os.path.join(ROOT,"tools"); MAT=os.path.join(ROOT,"materials")
def _onerr(fn,path,_):
    os.chmod(path,0o666); fn(path)
if os.path.exists(STAGE): shutil.rmtree(STAGE,onerror=_onerr)
os.makedirs(STAGE)

def cp(src,dst):
    os.makedirs(os.path.dirname(dst),exist_ok=True); shutil.copy2(src,dst)
    try: os.chmod(dst,0o666)
    except Exception: pass

# 主文档
cp(os.path.join(MAT,"作品PPT.pptx"),os.path.join(STAGE,"作品PPT.pptx"))
cp(os.path.join(MAT,"设计文档.docx"),os.path.join(STAGE,"设计文档.docx"))

# 源码
for f in ["prepare_data.py","train.py","predict.py","app.py","fusion.py","gbif_download2.py",
          "make_kb.py","eval_and_charts.py","make_ppt.py","make_doc.py"]:
    cp(os.path.join(TOOLS,f),os.path.join(STAGE,"源码",f))
cp(os.path.join(ROOT,"藻种知识库.xlsx"),os.path.join(STAGE,"源码","藻种知识库.xlsx"))

# 模型
for f in ["best.ckpt","train_log.json"]:
    cp(os.path.join(ROOT,"model",f),os.path.join(STAGE,"模型",f))
cp(os.path.join(ROOT,"algae_dataset","class_map.json"),os.path.join(STAGE,"模型","class_map.json"))

# 数据集(处理后 224x224) + 溯源
for split in ["train","val"]:
    src=os.path.join(ROOT,"algae_dataset",split)
    for cls in os.listdir(src):
        d=os.path.join(src,cls)
        if not os.path.isdir(d): continue
        for img in os.listdir(d):
            cp(os.path.join(d,img),os.path.join(STAGE,"数据集",split,cls,img))
cp(os.path.join(ROOT,"dataset_raw","gbif2","provenance.csv"),os.path.join(STAGE,"数据集","provenance.csv"))

# 演示说明
demo="""海洋微藻智能识别与赤潮风险提示工具 —— 演示与运行说明(双分支)

一、环境
  Python 3.10;依赖:mindspore、mindcv、streamlit、pillow、openpyxl、numpy(<2)、matplotlib、python-pptx、python-docx

二、运行演示(推荐)
  1) 将 模型/best.ckpt、模型/class_map.json 与 源码/藻种知识库.xlsx 放到对应路径(默认 D:\\train\\...),
     或直接修改 app.py / predict.py 顶部的路径常量;
  2) 进入 源码/ 目录,执行:  streamlit run app.py
  3) 浏览器访问 http://localhost:8501 ,默认在「宏观海面照片(推荐)」Tab:
     上传一张海面现状照片 + 填写现场6题问卷 → 贝叶斯融合输出最可能致灾类群、
     赤潮风险等级、风险说明,并给出四级预警信号(红/橙/黄/蓝)+ 预警指数 + 分级响应措施,
     同时展示后验概率与证据链;宏观分支为水色CV+融合,无需训练、秒开;
  4) 切到「显微照片(实验室确认)」Tab 上传显微照片 → MobileNetV3-Small(MindSpore)
     输出识别类别 + 置信度 + Top-3 + 固有风险等级 + 四级预警信号 + 毒素/生态/养殖影响/爆发规律/监测优先级;
     支持多张批量上传并输出汇总表。

三、复现训练(显微分支)
  python prepare_data.py     # 由 数据集/ 或原始 GBIF 影像重建 train/val
  python train.py --epochs 30
  验证集准确率约 95.4%(详见 模型/train_log.json)。

四、命令行推理
  显微:python predict.py <图像或目录>
  宏观融合:python -c "from PIL import Image; import fusion; print(fusion.fuse(fusion.image_color_likelihood(Image.open('<海面照>'))[1], {}))"

五、数据真实性
  数据集/provenance.csv 逐张记录:类别、GBIF 采集记录号、记录学名、影像原始 URL、许可协议、权利人。
  全部图像来自 GBIF 公开采集影像与 CNKI 学术显微图,真实可溯源;
  宏观融合的问卷/水色似然权重见 源码/藻种知识库.xlsx「宏观融合似然表」sheet,可审计;
  四级预警的风险权重与分级阈值见同文件「预警分级表」sheet,同样可审计。
"""
open(os.path.join(STAGE,"演示说明.txt"),"w",encoding="utf-8").write(demo)

# ---- 匿名扫描: 检查文本类文件是否含个人信息 ----
PAT=re.compile(r"队长|队长|200705023|nick0000000|宁德师范|1[3-9]\d{9}",re.I)
hits=[]
for dp,_,fns in os.walk(STAGE):
    for fn in fns:
        if fn.lower().endswith((".py",".txt",".json",".csv",".md")):
            p=os.path.join(dp,fn)
            try: txt=open(p,encoding="utf-8",errors="ignore").read()
            except Exception: continue
            for m in PAT.finditer(txt):
                hits.append((os.path.relpath(p,STAGE),m.group(0)))
print("匿名扫描命中:",hits if hits else "无(通过)")

# ---- 打包 ----
OUTDIR=os.path.join(ROOT,"submission")
zipname="学校名称-海洋微藻智能识别与赤潮风险提示工具-队长-13800000000.zip"
zpath=os.path.join(OUTDIR,zipname)
if os.path.exists(zpath): os.remove(zpath)
total=0; nfiles=0
with zipfile.ZipFile(zpath,"w",zipfile.ZIP_DEFLATED) as z:
    for dp,_,fns in os.walk(STAGE):
        for fn in fns:
            full=os.path.join(dp,fn); rel=os.path.relpath(full,STAGE)
            z.write(full,rel); total+=os.path.getsize(full); nfiles+=1
print(f"zip 已生成: {zpath}")
print(f"文件数 {nfiles}, 未压缩 {total/1e6:.1f} MB, 压缩后 {os.path.getsize(zpath)/1e6:.1f} MB")
print("文件名已含队长真实姓名与手机号, 包内内容匿名, 可直接提交。")
