# -*- coding: utf-8 -*-
"""app.py —— Streamlit 前端: 海洋微藻智能识别与赤潮风险提示工具(双分支)
主分支: 宏观海面照片 → 图像双证据(规则流水色CV × 宏观CNN) → 贝叶斯融合 → 致灾类群/风险/建议
次分支: 显微照片 → MobileNetV3-Small(MindSpore) 7类识别(实验室确认)
v4(纯图像判定): 删除现场问卷, 宏观仅凭海面照片判定(规则流为主92%、宏观CNN为辅80%),
大白话三句话结论+语音播报+一键复制上报文案+定位附注+拍照示例+历史查询记录。
运行: streamlit run app.py
"""
import os, io, json, glob, tempfile, datetime
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

st.set_page_config(page_title="赤潮快查 · 拍海面看风险", page_icon="🌊", layout="wide")

MODEL_DIR = r"D:\train\model"
RAW = r"D:\train\dataset_raw\macro\raw"
# 历史记录放到独立缓存目录(源码目录不落运行时文件; tools/ 下旧文件可能被锁)
HIST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".cache")
os.makedirs(HIST_DIR, exist_ok=True)
HIST = os.path.join(HIST_DIR, "usage_history.jsonl")

EXAMPLE_GOOD = os.path.join(RAW, "warm", "keep", "warm_algae_Xiamen_2007_FIELD_01.jpg")
EXAMPLE_BAD = os.path.join(RAW, "warm", "drop_curated", "warm_gb2xphaeoc_164d5339.jpg")


def render_alert(a):
    """醒目四级预警信号卡: 色标 + 等级 + 预警指数 + 含义."""
    st.markdown(
        f'<div style="border-left:8px solid {a["color_hex"]};'
        f'background:{a["color_hex"]}1A;padding:12px 16px;border-radius:6px;margin:6px 0 10px 0;">'
        f'<div style="font-size:22px;font-weight:700;color:{a["color_hex"]};line-height:1.25;">'
        f'{a["color_cn"]}预警 · {a["level"]}级'
        f'<span style="font-size:15px;font-weight:500;">　预警指数 {a["index"]}/100</span></div>'
        f'<div style="font-size:13px;color:#333;margin-top:4px;">{a["meaning"]}</div></div>',
        unsafe_allow_html=True)


def sec_head(n, title, color="#2E75B6"):
    st.markdown(
        f'<div style="border-left:6px solid {color};background:{color}14;padding:6px 12px;'
        f'border-radius:4px;margin:14px 0 6px 0;font-weight:700;font-size:15px;color:#222;">'
        f'{n}. {title}</div>',
        unsafe_allow_html=True)


def plain_sentences(meta, res, a):
    """渔民三句话: 现在什么情况 / 我现在该干什么 / 我该找谁."""
    conf = res["confidence"] * 100
    if res["top"] == "none":
        s1 = f"照片里的海是{meta['color_cn']}, 没看出赤潮, 眼下基本放心。"
    else:
        s1 = f"照片里的海是{meta['color_cn']}, 大概是{res['top_cn']}, 十成里把握约{conf:.0f}成; 预警牌:{a['color_cn']}{a['level']}级。"
    s2 = a["measures"].split(";")[0].split(";")[0] + "。"
    if res["top"] == "none":
        s3 = "不用上报; 哪天水变色、见死鱼, 再拍一张来查。"
    else:
        s3 = "要上报: 打12345或找镇里渔业技术员; 也可点下面「复制上报话术」, 粘贴到渔业微信群。"
    return s1, s2, s3


def action_buttons(tts_text, report_text):
    """语音播报 / 复制上报话术 / 附上我的位置 (浏览器端JS, 仅localhost/https可用)."""
    components.html(
        f"""
<div style="font-family:sans-serif;margin:4px 0 10px 0;">
<button id="tts" style="font-size:15px;padding:6px 14px;margin-right:8px;">🔊 念给我听</button>
<button id="cp" style="font-size:15px;padding:6px 14px;margin-right:8px;">📋 复制上报话术</button>
<button id="loc" style="font-size:15px;padding:6px 14px;">📍 附上我的位置</button>
<span id="msg" style="margin-left:8px;color:#2E75B6;"></span>
</div>
<script>
var TTS = {json.dumps(tts_text, ensure_ascii=False)};
var REP = {json.dumps(report_text, ensure_ascii=False)};
var LOC = "";
document.getElementById("tts").onclick = function() {{
    var u = new SpeechSynthesisUtterance(TTS); u.lang = "zh-CN"; u.rate = 0.95;
    speechSynthesis.cancel(); speechSynthesis.speak(u);
    document.getElementById("msg").textContent = "正在朗读…";
}};
document.getElementById("loc").onclick = function() {{
    navigator.geolocation.getCurrentPosition(function(p) {{
        LOC = " 位置: " + p.coords.latitude.toFixed(4) + "," + p.coords.longitude.toFixed(4);
        document.getElementById("msg").textContent = "位置已附上, 再点复制即可带位置。";
    }}, function() {{ document.getElementById("msg").textContent = "取不到位置(需允许定位)。"; }});
}};
document.getElementById("cp").onclick = function() {{
    navigator.clipboard.writeText(REP + LOC).then(function() {{
        document.getElementById("msg").textContent = "已复制, 去微信群粘贴即可。";
    }}, function() {{ document.getElementById("msg").textContent = "复制失败, 请长按手写。"; }});
}};
</script>
""", height=52)


def append_history(rec):
    """写一条查询历史。失败只提示不阻断(历史是辅助功能)."""
    try:
        with open(HIST, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[历史记录写入失败(不影响本页分析)] {e}")


def load_history(n=5):
    if not os.path.exists(HIST):
        return []
    lines = io.open(HIST, encoding="utf-8").read().splitlines()[-n:]
    out = []
    for l in reversed(lines):
        try:
            out.append(json.loads(l))
        except Exception:
            pass
    return out


RISK_COLOR = {"高": "🔴", "中—高": "🟠", "低—中": "🟡", "中": "🟡", "低": "🟢", "无": "🟢"}


@st.cache_resource(show_spinner="正在加载显微模型…(仅化验室页面需要)")
def get_predictor():
    from predict import Predictor
    return Predictor()


def load_train_log():
    p = os.path.join(MODEL_DIR, "train_log.json")
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    return {}


# ---------- 侧边栏(大白话) ----------
with st.sidebar:
    st.title("🌊 赤潮快查")
    st.caption("拍一张海面的照片, 三句话告诉您: 什么情况、现在该干什么、该找谁。")
    st.divider()
    st.write("**怎么用**")
    st.write("1. 点「拍海面查风险」, 传一张海面照片")
    st.write("2. 等几秒出结果(只看照片, 不用答任何问题)")
    st.write("3. 看橙色/红色牌子, 听语音, 需要上报就复制话术")
    st.divider()
    log = load_train_log()
    if log:
        st.caption(f"化验室显微识别准确率 {log.get('best_val_acc', 0) * 100:.1f}%(7类)")
    with st.expander("我给专家看的: 技术原理"):
        st.write("- 宏观: 图像双证据贝叶斯融合——规则流水色CV(主,25张真实图验证92%) × 宏观CNN(辅,80%),纯照片判定、无需问卷")
        st.write("- 微观: MobileNetV3-Small / MindSpore, 7类, 验证集 "
                 f"{log.get('best_val_acc', 0) * 100:.1f}%" if log else "- 微观: 未训练")
        st.markdown("图像与判定依据均可公开溯源(GBIF等), 见 `provenance.csv`; "
                    "宏观规则流在25张精选海面验证集上准确92%。")
    with st.expander("我最近查过的"):
        hs = load_history()
        if hs:
            for h in hs:
                st.write(f"- {h['ts']}　{h['alert']}　{h['top_cn']}　({h['color_cn']})")
        else:
            st.write("还没有记录。查一次就记一次, 关掉也在。")
    st.caption("结果供参考, 以福建省海洋与渔业局官方通报为准。")

# ---------- 主页 ----------
st.title("拍海面, 查赤潮风险")
st.markdown("在岸边或船上**拍一大片水面**传上来, 用三句话告诉您结果;"
            "化验室的显微照片请走第二个页面。")

tab_macro, tab_micro = st.tabs(["📷 拍海面查风险(渔民用)", "🔬 显微照片(化验室人员用)"])

# ================= 分支一: 宏观 =================
with tab_macro:
    import fusion
    gc, bc = st.columns(2)
    with gc:
        if os.path.exists(EXAMPLE_GOOD):
            st.image(EXAMPLE_GOOD, caption="✅ 这样拍对: 拍一大片水面", use_container_width=True)
    with bc:
        if os.path.exists(EXAMPLE_BAD):
            st.image(EXAMPLE_BAD, caption="❌ 这样拍错: 只拍藻团/礁石特写", use_container_width=True)
    ups = st.file_uploader("上传海面照片(可多张, 手机拍的就行)", type=["jpg", "jpeg", "png"],
                           accept_multiple_files=True, key="macro_up")
    st.caption("只凭照片判断, 不用答任何问题; 多张一起传, 每张都出结论。")

    if not ups:
        st.info("👆 传一张海面照片, 马上出结果。")
        st.stop()

    for uf in ups:
        img = Image.open(io.BytesIO(uf.getvalue())).convert("RGB")
        is_sea, _src, _score, _detail = fusion.sea_precheck(img)
        if not is_sea:
            st.warning(f"《{uf.name}》看起来不像海面照片(预检:{_detail})。"
                       "请站到岸边/船上, 拍一大片水面; 显微照片请走第二个页面。")
            continue
        label, lik, meta = fusion.image_color_likelihood(img)
        if meta["sat"] < 0.10:
            st.warning(f"《{uf.name}》看着不像海面照片(颜色太淡, 像显微镜下拍的)。"
                       "请站到岸边/船上, 拍一大片水面; 显微照片请走第二个页面。")
            continue
        cnn_ok, cnn_lik = fusion.image_cnn_likelihood(img)
        res = fusion.fuse(lik, None, cnn_lik=cnn_lik)
        c1, c2 = st.columns([1, 2])
        with c1:
            st.image(img, caption=uf.name, use_container_width=True)
            st.caption(f"照片水色:{meta['color_cn']} "
                       f"(粉色块{meta['f_pink']:.0%}/褐{meta['f_brown']:.0%}/"
                       f"绿{meta['f_green']:.0%}/泡沫{meta['f_foam']:.0%})")
        with c2:
            a = res["alert"]
            s1, s2, s3 = plain_sentences(meta, res, a)
            st.markdown(
                f'<div style="background:#F2F7FC;border:1px solid #BDD7EE;border-radius:8px;'
                f'padding:10px 14px;font-size:16px;line-height:1.7;">'
                f'<b>① 情况:</b>{s1}<br><b>② 该干什么:</b>{s2}<br><b>③ 该找谁:</b>{s3}</div>',
                unsafe_allow_html=True)
            ts = datetime.datetime.now().strftime("%m-%d %H:%M")
            report = (f"【赤潮快查上报】{ts} 拍于海面; 水色{meta['color_cn']}; "
                      f"研判{res['top_cn']}(把握{res['confidence'] * 100:.0f}%); "
                      f"预警{a['color_cn']}{a['level']}级, 指数{a['index']}/100; 请核实。")
            action_buttons(s1 + s2 + s3, report)
            append_history({"ts": ts, "file": uf.name, "color_cn": meta["color_cn"],
                            "top": res["top"], "top_cn": res["top_cn"],
                            "alert": f"{a['color_cn']}{a['level']}级", "index": a["index"]})
            sec_head(1, "可能藻种")
            st.markdown(f"{res['top_cn']}　(融合置信度 {res['confidence'] * 100:.1f}%)")
            st.progress(min(res["confidence"], 1.0))
            _top3 = sorted(res["posterior"].items(), key=lambda kv: -kv[1])[:3]
            st.caption("后验Top3:" + "、".join(f"{fusion.HYP_CN[h]} {p * 100:.1f}%" for h, p in _top3))
            if res.get("cnn_used") is False and res.get("cnn_top"):
                st.caption(f"💡 宏观CNN提示:{fusion.HYP_CN.get(res['cnn_top'], res['cnn_top'])}"
                           "(与主判据不一致,按保守原则以规则流为准,未计入预警)")
            sec_head(2, "相关危害", "#ED7D31")
            st.markdown(res["risk_note"])
            sec_head(3, "严重性", "#C00000")
            render_alert(a)
            sec_head(4, "应对措施", "#34A853")
            st.markdown(a["measures"])
            st.markdown(res["advice"])
            with st.expander("📊 证据链与预警依据(给专家看)"):
                for h, p in sorted(res["posterior"].items(), key=lambda kv: -kv[1]):
                    st.write(f"- {fusion.HYP_CN[h]}:{p * 100:.1f}%")
                st.caption("参与融合的证据:" + "、".join(res["evidence"]))
                st.caption(a["trigger"])
        st.divider()

# ================= 分支二: 显微 =================
with tab_micro:
    st.info("这一页给**化验室/技站人员**用: 需要有显微镜拍的藻体照片。"
            "渔民朋友请回上一页「拍海面查风险」。")
    st.markdown("上传海洋微藻**显微照片**,由 MobileNetV3-Small(MindSpore) 做7类识别, 作为实验室级确认。")
    mups = st.file_uploader("选择显微图像(可多选)", type=["jpg", "jpeg", "png"],
                            accept_multiple_files=True, key="micro_up")
    if mups:
        pred = get_predictor()
        for uf in mups:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            tmp.write(uf.getbuffer()); tmp.close()
            img = Image.open(tmp).convert("RGB")
            r = pred.predict(tmp, topk=3)
            os.unlink(tmp)
            top = r[0]
            c1, c2 = st.columns([1, 2])
            with c1:
                st.image(img, caption=uf.name, use_container_width=True)
            with c2:
                a2 = fusion.alert_from(top.get("risk", "无"), top["prob"])
                sec_head(1, "可能藻种")
                st.markdown(f"{top['cn']}　*{top.get('sci', '')}*　(置信度 {top['prob'] * 100:.1f}%)")
                st.progress(min(top["prob"], 1.0))
                st.caption("Top3:" + "、".join(f"{x['cn']} {x['prob'] * 100:.1f}%" for x in r))
                sec_head(2, "相关危害", "#ED7D31")
                st.markdown(f"毒素类型:{top.get('toxin', '—')}")
                st.markdown(f"对养殖/人体影响:{top.get('impact', '—')}")
                sec_head(3, "严重性", "#C00000")
                render_alert(a2)
                sec_head(4, "应对措施", "#34A853")
                st.markdown(a2["measures"])
                st.caption(f"监测优先级:{top.get('priority', '—')}")
                with st.expander("🔎 生态特性/爆发规律与预警依据"):
                    st.markdown(f"**生态特性**:{top.get('eco', '—')}")
                    st.markdown(f"**爆发规律**:{top.get('pattern', '—')}")
                    st.caption(a2["trigger"])
            st.divider()

st.caption("宏观:水色CV+贝叶斯融合(25张海面验证集92%) | 显微:MobileNetV3-Small / MindSpore | "
           "数据:GBIF 等可溯源来源 | 结果供参考, 以福建省海洋与渔业局"
           "(https://hyyyj.fujian.gov.cn/)官方通报为准")
