# -*- coding: utf-8 -*-
"""贝叶斯融合引擎: 宏观海面图像双证据(规则流水色CV × 宏观CNN) → 后验(致灾类群/风险/建议).
纯图像判定, 无需现场问卷; 规则流为主(可解释), 宏观CNN为辅(第三路证据).
透明可解释: 各证据对假设集的似然权重显式声明, 可写入设计文档."""
import os
import colorsys
import numpy as np
from PIL import Image

# 宏观 CNN 懒加载(首次调用时载入, 避免非宏观场景引入 MindSpore 依赖)
_CNN = {"net": None, "cmap": None, "ok": False}


def _load_macro_cnn():
    """载入宏观5类CNN(MobileNetV3-Small). 失败返回 None(整套融合退化为纯规则流)."""
    if _CNN["net"] is not None:
        return _CNN["net"], _CNN["cmap"]
    try:
        import json
        import mindspore as ms
        from mindcv import create_model
        cmap = json.load(open(r"D:\train\model_macro\class_map.json", encoding="utf-8"))
        classes = cmap["classes"]; N = len(classes)
        net = create_model("mobilenet_v3_small_100", num_classes=N, pretrained=False, in_channels=3)
        ck = r"D:\train\model_macro\best.ckpt"
        if os.path.exists(ck):
            ms.load_param_into_net(net, ms.load_checkpoint(ck))
            _CNN["net"] = net; _CNN["cmap"] = cmap; _CNN["ok"] = True
            return net, cmap
    except Exception:
        pass
    return None, None


def image_cnn_likelihood(pil_img):
    """宏观CNN第三路图像证据: softmax(5类) → HYP顺序似然向量.
    返回 (ok, lik): ok=False 表示CNN未就绪(调用方应退化为纯规则流)."""
    net, cmap = _load_macro_cnn()
    if net is None:
        return False, None
    try:
        import mindspore as ms
        from mindspore import Tensor
        MEAN = [0.485 * 255, 0.456 * 255, 0.406 * 255]
        STD = [0.229 * 255, 0.224 * 255, 0.225 * 255]
        SIZE = 224
        img = pil_img.convert("RGB").resize((SIZE, SIZE), Image.BILINEAR)
        a = np.asarray(img).astype(np.float32)
        for i in range(3):
            a[..., i] = (a[..., i] - MEAN[i]) / STD[i]
        x = Tensor(a.transpose(2, 0, 1)[None])
        logits = net(x).asnumpy()[0]
        e = np.exp(logits - logits.max())
        soft = e / e.sum()
        classes = cmap["classes"]
        lik = {h: 0.01 for h in HYP}
        for c, p in zip(classes, soft):
            lik[c] = float(p) + 0.01  # 平滑下限, 避免0似然
        return True, lik
    except Exception:
        return False, None


# ===== 海面/非海面预检 =====
_PC = {"net": None, "ok": False}
_PC_PATH = r"D:\train\model_precheck\best.ckpt"


def _load_precheck():
    """载入海面预检二分类CNN. 失败返回 None(回退规则流预检)."""
    if _PC["net"] is not None:
        return _PC["net"]
    try:
        import mindspore as ms
        from mindcv import create_model
        net = create_model("mobilenet_v3_small_100", num_classes=2, pretrained=False, in_channels=3)
        if os.path.exists(_PC_PATH):
            ms.load_param_into_net(net, ms.load_checkpoint(_PC_PATH))
            _PC["net"] = net; _PC["ok"] = True
            return net
    except Exception:
        pass
    return None


def sea_precheck(pil_img):
    """海面/非海面预检(分层: CNN 为主, 规则流救回临界).

    分层判定(CNN 输出海面概率 sea_prob):
      - sea_prob < 0.30        -> 非海面(坚决拒绝, 规则流无权翻案)
      - 0.30 <= sea_prob < 0.60 -> 模棱两可 -> 由规则流决定(救回真实海面近景/浪花)
      - sea_prob >= 0.60       -> 海面(放行)
    规则流兜底信号: 青蓝绿占比 f_water + 饱和度 + 颜色多样性(纯色块/低多样性 -> 非海面).

    返回 (is_sea: bool, source: str, score: float, detail: str)
      source: "cnn" / "rule" / "tie", score = 依据一方的置信(0-1).
    """
    sea_prob = None
    try:
        net = _load_precheck()
        if net is not None:
            import mindspore as ms
            from mindspore import Tensor
            MEAN = [0.485 * 255, 0.456 * 255, 0.406 * 255]
            STD = [0.229 * 255, 0.224 * 255, 0.225 * 255]
            img = pil_img.convert("RGB").resize((224, 224), Image.BILINEAR)
            a = np.asarray(img).astype(np.float32)
            for i in range(3):
                a[..., i] = (a[..., i] - MEAN[i]) / STD[i]
            logits = net(Tensor(a.transpose(2, 0, 1)[None])).asnumpy()[0]
            p = np.exp(logits - logits.max()); p = p / p.sum()
            sea_prob = float(p[1])  # 类1 = sea (目录字母序 nonsea=0, sea=1)
    except Exception:
        sea_prob = None
    # ---- 规则流兜底 ----
    img2 = pil_img.convert("RGB")
    arr = np.asarray(img2.resize((96, 96))).astype(np.float32) / 255.0
    tot = arr.shape[0] * arr.shape[1]
    mx = arr.max(2); mn = arr.min(2); df = mx - mn + 1e-8
    s = np.where(mx > 0, df / (mx + 1e-8), 0)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    hue = np.zeros_like(mx)
    m = (mx == r); hue[m] = ((g - b)[m] / df[m]) % 6
    m = (mx == g) & (mx != r); hue[m] = ((b - r)[m] / df[m]) + 2
    m = (mx == b) & (mx != r) & (mx != g); hue[m] = ((r - g)[m] / df[m]) + 4
    hue = hue * 60.0
    water_m = (((hue >= 150) & (hue <= 270)) | ((hue >= 50) & (hue < 150)))
    s_water = water_m & (s > 0.08) & (mx > 0.10)
    f_water = float(s_water.sum()) / tot
    mean_s = float(s.mean())
    q = np.asarray(img2.resize((48, 48))).astype(np.uint8) >> 5
    ncol = len(np.unique(q.reshape(-1, 3), axis=0))
    rule_is_sea = (f_water >= 0.45 and mean_s > 0.08 and ncol >= 12)
    rule_detail = f"f_water={f_water:.2f} sat={mean_s:.2f} ncol={ncol}"

    if sea_prob is None:
        # 模型未就绪 -> 纯规则流
        return rule_is_sea, "rule", round(min(1.0, f_water), 3), rule_detail
    if sea_prob < 0.30:
        return False, "cnn", round(sea_prob, 3), f"预检模型(海面概率{sea_prob:.0%}, 坚决拒绝)"
    if sea_prob >= 0.60:
        return True, "cnn", round(sea_prob, 3), f"预检模型(海面概率{sea_prob:.0%})"
    # 模棱两可 0.30-0.60 -> 规则流决定
    if rule_is_sea:
        return True, "tie", round(sea_prob, 3), f"模型临界({sea_prob:.0%})+规则流水色(放行)"
    return False, "tie", round(sea_prob, 3), f"模型临界({sea_prob:.0%})+规则流({rule_detail}, 拒绝)"



# 假设集 H
HYP = ["noctiluca", "toxic_dino", "diatom", "green_tide", "none"]
HYP_CN = {
    "noctiluca":  "夜光藻型水华(缺氧致害)",
    "toxic_dino": "有毒甲藻型(亚历山大藻/短裸藻/原甲藻, 产毒)",
    "diatom":     "硅藻型水华(骨条藻/角毛藻, 缺氧/堵塞鳃)",
    "green_tide": "绿潮/绿藻水华(浒苔/石莼)",
    "none":       "无明显赤潮(正常海水)",
}
HYP_RISK = {
    "noctiluca":  ("中—高", "高生物量耗氧致鱼虾窒息, 一般不产毒"),
    "toxic_dino": ("高",    "可产麻痹性/神经性贝毒, 严禁采食贝类, 避免接触"),
    "diatom":     ("中",    "堵塞鱼鳃/耗氧, 养殖区需增氧防损失"),
    "green_tide": ("低—中", "主要影响景观与局部溶氧, 毒性低"),
    "none":       ("无",    "未见赤潮征象"),
}
HYP_ADVICE = {
    "noctiluca":  "建议上报当地海洋渔业部门; 养殖区夜间注意增氧; 无需恐慌性禁食贝类但避免直接接触水华。",
    "toxic_dino": "立即上报; 严禁采捕/食用该海域贝类; 避免皮肤接触与气溶胶吸入; 关注官方贝毒通报。",
    "diatom":     "上报并加密监测; 养殖区启动增氧; 关注鱼虾摄食与鳃部状况。",
    "green_tide": "可上报城管/海洋部门清理; 对游泳影响小, 避免大量聚集区接触。",
    "none":       "无需处置; 若后续出现变色/死鱼请重新上报。",
}

# ===== 四级预警分级 (显式、可审计) =====
# 类群固有风险等级 → 权重 (与 HYP_RISK 的风险字符串对应)
RISK_WEIGHT = {"高": 1.0, "中—高": 0.8, "中": 0.6, "低—中": 0.4, "低": 0.25, "无": 0.0}
# 预警指数 = round(后验置信度 × 风险权重 × 100), 综合"研判有多确定"与"命中类群有多危险"

# 四级预警: 指数区间(下限含、上限不含) / 色标 / 名称 / 含义 / 响应措施
ALERT_LEVELS = [
    {"level": "Ⅰ", "color_cn": "红色", "color_hex": "#C00000", "min": 70,
     "name": "红色预警(Ⅰ级·特别严重)",
     "meaning": "高置信命中高危/产毒类群, 或已现死鱼死贝等致灾征兆, 赤潮危害风险很高。",
     "measures": "立即上报海洋渔业主管部门并启动应急; 受影响海域暂停贝类采捕与上市、待官方贝毒检测合格方可恢复; 加密至每日监测水色与藻密度; 核查麻痹性/腹泻性/失忆性贝毒及鱼毒素; 养殖区应急增氧、必要时转移网箱; 人员避免接触水华与吸入气溶胶。"},
    {"level": "Ⅱ", "color_cn": "橙色", "color_hex": "#ED7D31", "min": 50,
     "name": "橙色预警(Ⅱ级·严重)",
     "meaning": "较高置信命中致灾类群, 赤潮危害风险较高, 需尽快核实与防范。",
     "measures": "48小时内复核研判; 暂停该点位贝类采捕并送检; 每日监测水色、夜间荧光与死鱼死虾情况; 养殖区提前增氧, 关注鱼虾摄食与鳃部状况; 做好上报准备。"},
    {"level": "Ⅲ", "color_cn": "黄色", "color_hex": "#FFC000", "min": 30,
     "name": "黄色预警(Ⅲ级·较重)",
     "meaning": "中等置信或中低危类群, 存在赤潮发生苗头, 需加强观察。",
     "measures": "加强巡查(每2—3天一次); 采集水样镜检确认类群与细胞密度; 留意水色变化、腥味与夜间荧光; 向主管部门通报发展趋势。"},
    {"level": "Ⅳ", "color_cn": "蓝色", "color_hex": "#2E75B6", "min": 0,
     "name": "蓝色预警(Ⅳ级·一般/观察)",
     "meaning": "未见明显赤潮征象, 或仅低风险提示, 维持常规关注即可。",
     "measures": "维持常规监测; 若出现升温、暴雨径流、盐度骤降或水色突变等情况, 请重新研判并上报。"},
]


def alert_from(risk, confidence):
    """由命中类群固有风险(risk字符串)与后验置信度(0—1)计算四级预警. 返回 alert dict."""
    w = RISK_WEIGHT.get(risk, 0.0)
    index = int(round(float(confidence) * w * 100))
    lv = next((a for a in ALERT_LEVELS if index >= a["min"]), ALERT_LEVELS[-1])
    return {
        "index": index, "level": lv["level"], "color_cn": lv["color_cn"],
        "color_hex": lv["color_hex"], "name": lv["name"], "meaning": lv["meaning"],
        "measures": lv["measures"], "risk_weight": w,
        "trigger": "预警指数 %d = 置信度%.0f%% × 风险权重%.2f × 100 → %s(≥%d)"
                   % (index, confidence * 100, w, lv["color_cn"], lv["min"]),
    }


# 水色标签 → 似然 (与Q1选项共用)
COLOR_LIK = {
    "pink_red":   {"noctiluca": 4.0, "toxic_dino": 2.0, "diatom": 1.0, "green_tide": 0.3, "none": 0.2},
    "brown_gold": {"noctiluca": 1.0, "toxic_dino": 3.0, "diatom": 3.0, "green_tide": 0.3, "none": 0.2},
    "green":      {"noctiluca": 0.3, "toxic_dino": 0.5, "diatom": 1.5, "green_tide": 4.0, "none": 0.3},
    "foam_white": {"noctiluca": 2.0, "toxic_dino": 1.0, "diatom": 2.0, "green_tide": 0.5, "none": 0.5},
    "normal_blue":{"noctiluca": 0.3, "toxic_dino": 0.3, "diatom": 0.3, "green_tide": 0.3, "none": 4.0},
}
COLOR_CN = {"pink_red": "粉红/砖红", "brown_gold": "褐黄/酱色", "green": "翠绿/墨绿",
            "foam_white": "乳白/泡沫", "normal_blue": "灰蓝/正常"}

# 6题问卷: 每题选项带似然权重
QUESTIONS = [
    {"id": "color", "text": "1. 海水整体颜色更接近?", "options": [
        {"label": "粉红/砖红",   "lik": COLOR_LIK["pink_red"]},
        {"label": "褐黄/酱色",   "lik": COLOR_LIK["brown_gold"]},
        {"label": "翠绿/墨绿",   "lik": COLOR_LIK["green"]},
        {"label": "乳白/泡沫多", "lik": COLOR_LIK["foam_white"]},
        {"label": "灰蓝/清澈正常","lik": COLOR_LIK["normal_blue"]}]},
    {"id": "glow", "text": "2. 夜间或搅动水面时是否发蓝绿光?", "options": [
        {"label": "是",   "lik": {"noctiluca": 5.0, "toxic_dino": 0.5, "diatom": 0.5, "green_tide": 0.5, "none": 0.2}},
        {"label": "否",   "lik": {"noctiluca": 0.6, "toxic_dino": 1.0, "diatom": 1.0, "green_tide": 1.0, "none": 1.0}},
        {"label": "不确定","lik": {h: 1.0 for h in HYP}}]},
    {"id": "mortality", "text": "3. 是否见死鱼/死虾蟹/贝类开口异常?", "options": [
        {"label": "有", "lik": {"noctiluca": 3.0, "toxic_dino": 4.0, "diatom": 3.0, "green_tide": 1.0, "none": 0.2}},
        {"label": "无", "lik": {"noctiluca": 0.8, "toxic_dino": 0.8, "diatom": 0.8, "green_tide": 1.0, "none": 1.2}}]},
    {"id": "floating", "text": "4. 水面漂浮物情况?", "options": [
        {"label": "绿色藻团/菜叶状", "lik": {"noctiluca": 0.3, "toxic_dino": 0.3, "diatom": 0.3, "green_tide": 5.0, "none": 0.3}},
        {"label": "褐色膜/泡沫",     "lik": {"noctiluca": 1.5, "toxic_dino": 2.0, "diatom": 2.5, "green_tide": 0.5, "none": 0.4}},
        {"label": "油污感(非藻类)",  "lik": {"noctiluca": 0.3, "toxic_dino": 0.3, "diatom": 0.3, "green_tide": 0.3, "none": 2.0}},
        {"label": "无明显漂浮物",    "lik": {h: 1.0 for h in HYP}}]},
    {"id": "smell", "text": "5. 现场气味?", "options": [
        {"label": "明显腥臭", "lik": {"noctiluca": 2.5, "toxic_dino": 2.0, "diatom": 2.5, "green_tide": 1.5, "none": 0.2}},
        {"label": "轻微气味", "lik": {h: 1.0 for h in HYP}},
        {"label": "无明显气味","lik": {"noctiluca": 0.8, "toxic_dino": 0.8, "diatom": 0.8, "green_tide": 0.8, "none": 1.5}}]},
    {"id": "env", "text": "6. 近期环境背景?", "options": [
        {"label": "内湾/养殖区+高温晴朗", "lik": {"noctiluca": 2.0, "toxic_dino": 2.5, "diatom": 2.0, "green_tide": 1.0, "none": 0.5}},
        {"label": "大雨后/河口附近",     "lik": {"noctiluca": 1.0, "toxic_dino": 1.5, "diatom": 2.5, "green_tide": 2.0, "none": 0.6}},
        {"label": "开阔近岸+降温大风",   "lik": {"noctiluca": 0.7, "toxic_dino": 0.7, "diatom": 0.7, "green_tide": 0.7, "none": 2.0}},
        {"label": "不确定",             "lik": {h: 1.0 for h in HYP}}]},
]


def image_color_likelihood(pil_img):
    """经典CV: 取下部水体区域HSV统计→水色标签→似然. 返回(label, lik, meta)."""
    img = pil_img.convert("RGB")
    w, h = img.size
    # 水体区域: 取中段水平带, 避开天空(上)与前景沙滩/船体(下)
    crop = img.crop((0, int(h * 0.20), w, h))  # 去天空
    arr = np.asarray(crop).astype(np.float32) / 255.0
    tot_px = arr.shape[0] * arr.shape[1]
    # 向量化 RGB->HSV
    mx = arr.max(axis=2); mn = arr.min(axis=2); df = mx - mn + 1e-8
    v = mx
    s = np.where(mx > 0, df / (mx + 1e-8), 0)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    hue = np.zeros_like(mx)
    m = (mx == r); hue[m] = ((g - b)[m] / df[m]) % 6
    m = (mx == g) & (mx != r); hue[m] = ((b - r)[m] / df[m]) + 2
    m = (mx == b) & (mx != r) & (mx != g); hue[m] = ((r - g)[m] / df[m]) + 4
    hue = hue * 60.0
    mean_s = float(s.mean()); mean_v = float(v.mean())
    # 水华色块存在性: 各色系饱和像素占比
    pink_m  = ((hue >= 330) | (hue < 20)) & (s > 0.30) & (v > 0.15)
    brown_m = (hue >= 20) & (hue < 50) & (s > 0.30) & (v > 0.20) & (v < 0.85)
    green_m = (hue >= 50) & (hue < 170) & (s > 0.30)
    foam_m  = (s < 0.10) & (v > 0.80)
    f_pink  = float(pink_m.sum()) / tot_px
    f_brown = float(brown_m.sum()) / tot_px
    f_green = float(green_m.sum()) / tot_px
    f_foam  = float(foam_m.sum()) / tot_px
    if f_pink > 0.02:
        label = "pink_red"
    elif f_green > 0.05:
        label = "green"
    elif f_brown > 0.08:
        label = "brown_gold"
    elif f_foam > 0.30:
        label = "foam_white"
    else:
        label = "normal_blue"
    meta = {"f_pink": round(f_pink, 3), "f_brown": round(f_brown, 3),
            "f_green": round(f_green, 3), "f_foam": round(f_foam, 3),
            "sat": round(mean_s, 3), "val": round(mean_v, 3),
            "color_cn": COLOR_CN[label]}
    return label, dict(COLOR_LIK[label]), meta


def fuse(image_lik=None, answers=None, image_weight=2.0, cnn_lik=None, cnn_weight=1.0,
         cnn_mode="agree"):
    """图像双证据贝叶斯融合(纯图像判定, 问卷可选).
    image_lik: 规则流水色CV似然(主); cnn_lik: 宏观CNN似然(辅);
    cnn_mode: "agree"=保守融合(默认): 仅当 CNN 顶类与规则流顶类一致时才计入CNN证据,
              增强置信度; 不一致时忽略CNN、以规则流为准(保证不低于规则流单独).
              "weighted"=加权融合: 无条件按 cnn_weight 计入.
    answers: 现场问卷(兼容保留, 传 None 即纯图像).
    返回后验dict+top+risk+advice."""
    post = {h: 1.0 for h in HYP}  # 均匀先验
    evid = []
    if image_lik:
        for h in HYP:
            post[h] *= image_lik[h] ** image_weight
        evid.append("图像·水色CV(主)")
    rule_top = max(image_lik or {h: 1.0 for h in HYP}, key=lambda h: (image_lik or {}).get(h, 0))
    cnn_used = False
    if cnn_lik:
        cnn_top = max(cnn_lik, key=lambda h: cnn_lik[h])
        if cnn_mode == "weighted" or (cnn_mode == "agree" and cnn_top == rule_top):
            for h in HYP:
                post[h] *= cnn_lik[h] ** cnn_weight
            cnn_used = True
            evid.append("图像·宏观CNN(辅助)")
        else:
            evid.append("图像·宏观CNN(提示不一致,未计入)")
    for q in QUESTIONS:
        lab = (answers or {}).get(q["id"])
        if not lab:
            continue
        opt = next((o for o in q["options"] if o["label"] == lab), None)
        if not opt:
            continue
        for h in HYP:
            post[h] *= opt["lik"][h]
        evid.append(q["text"].split(".")[0].split("、")[0].strip())
    tot = sum(post.values()) or 1.0
    post = {h: post[h] / tot for h in HYP}
    top = max(post, key=post.get)
    risk, risk_note = HYP_RISK[top]
    alert = alert_from(risk, post[top])
    return {
        "posterior": {h: round(post[h], 4) for h in HYP},
        "top": top, "top_cn": HYP_CN[top], "confidence": round(post[top], 4),
        "risk": risk, "risk_note": risk_note, "advice": HYP_ADVICE[top],
        "alert": alert,
        "evidence": evid,
        "cnn_used": cnn_used,
        "cnn_top": max(cnn_lik, key=lambda h: cnn_lik[h]) if cnn_lik else None,
    }
