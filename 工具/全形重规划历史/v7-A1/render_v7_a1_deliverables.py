"""Render the three v7-A1 acceptance deliverables: Markdown report, HTML cards, and interactive browser."""
import base64
import html
import io
import json
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parent
DATA_JSON = OUT / "全形全键位基线-35727-v7-A1.json"
SPRITE_DIR = OUT / "sprites"

REPORT_MD = OUT / "v7-A1全键位基线验收报告.md"
CARDS_HTML = OUT / "v7-A1视觉归桶审图卡片.html"
BROWSER_HTML = OUT / "v7-A1全键位交互浏览器.html"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def pct(n, d):
    return f"{(n / d * 100):.2f}%" if d else "0.00%"


def md_table(headers, rows):
    def fmt(r):
        return "| " + " | ".join(str(x).replace("|", "&#124;") for x in r) + " |"
    return [fmt(headers), fmt(["---"] * len(headers)), *(fmt(r) for r in rows)]


def sprite_crop_b64(sprite_idx, slot_idx, cache):
    if sprite_idx < 0:
        return ""
    if sprite_idx not in cache:
        cache[sprite_idx] = Image.open(SPRITE_DIR / f"s{sprite_idx:02d}.png")
    img = cache[sprite_idx]
    r_i, c_i = divmod(slot_idx, 50)
    tile = img.crop((c_i * 32, r_i * 32, (c_i + 1) * 32, (r_i + 1) * 32))
    buf = io.BytesIO()
    tile.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def render_report(data):
    gm = data["geomMetrics"]
    stab = data["stability"]
    rows = data["rows"]
    counts = data["counts"]
    lines = []

    lines += [
        "# v7-A1 全键位首版基线验收报告",
        "",
        f"2026-11-27 · 全域 **{counts['total']:,} 字**（几何 `{counts['G']:,}` + 拟像图标 `{counts['T']:,}` + 附标 `{counts['X']:,}`，保留 `Z` 汉字/谚文入口） · 0 跨层重叠 · `BCDA ↔ ABCD` 100% 双向可逆。",
        "",
        "## 一、六版演进定量对照（v4.1 → v7-A1）",
        "",
    ]

    six_rows = [
        ("几何域字数", "29,096", "29,096", "29,096", "29,092", "29,092", f"{counts['G']:,}"),
        ("全键位纳入域", "29,096（仅几何）", "29,096（仅几何）", "29,096（仅几何）", "33,458（+T1）", "33,458（+T1）", f"{counts['total']:,}（G+T+X）"),
        ("B 默认 / Z 待核", "22,210（76.33%）", "8,640（29.69%）", "459（1.58%）", "495（1.70%）", "483（1.66%）", "483（1.66%，已冻结）"),
        ("有效 3/4 码格数", "1,146 (BCD)", "1,986 (BCD)", "848 (BCD)", "1,196 (BCD)", "1,051 (BCD)", f"{gm['bcdaUsed']:,} (几何 BCDA)"),
        ("最大单格负载", "1,821 (GZZ)", "401 (GCD)", "874 (HBF)", "528 (VFQ)", "528 (VFQ)", f"{gm['maxBCDA'][1]} ({gm['maxBCDA'][0]})"),
        ("按字候选数 p50 / p90", "117 / 597", "48 / 254", "137 / 452", "73 / 322", "98 / 328", f"{gm['p50']} / {gm['p90']}"),
        ("候选 ≤20 字占比", "14.23%", "27.59%", "12.04%", "18.80%", "15.93%", pct(gm["atMost20"], gm["total"])),
        ("候选 ≤10 字占比", "—", "—", "—", "—", "—", pct(gm["atMost10"], gm["total"])),
        ("A 位阈值稳定改码率", "52.0%（旧方案C）", "3.17%–3.32%（规则A）", "A 静默", "A 静默", "A 静默", f"{stab['112']['fixedBcdARate']:.2%} / {stab['144']['fixedBcdARate']:.2%}"),
    ]
    lines += md_table(("指标", "v4.1", "v5-draft", "v6", "v6.1", "v6.2 (BCD)", "v7-A1 (BCDA)"), six_rows)
    lines += [
        "",
        "说明：v7-A1 100% 保留 v6.2 已冻结的几何 BCD 主码与 D3 次路径（0 字改写）；O 类 20 字全部保持 `AAYA ↔ AAAY`，7 个无图占位保持 `ZAZA ↔ AZAZ`。",
        "",
        "## 二、A 位 26 字母零冲突分布与全四码负载",
        "",
        f"- **保留专用 3 键**：`T` = 拟像与图标（**{counts['T']:,} 字**）、`X` = 附标与组合记号（**{counts['X']:,} 字**）、`Z` = 远期汉字/谚文入口保留位；",
        f"- **几何层专用 23 键**：`{' '.join(data['geomAKeys'])}`（0 字占用 `T/X/Z`）；",
        f"- **桶内视觉紧致度（N>16 拆桶统计均值）**：平均簇内欧氏距离 `{gm['meanIntra']}` vs 平均簇间质心距离 `{gm['meanInter']}`（比值 `{gm['meanInter']/max(1e-6, gm['meanIntra']):.2f}×`）。",
        "",
    ]

    a_counts = gm["aKeyCounts"]
    a_rows = []
    keys23 = data["geomAKeys"]
    for i in range(0, len(keys23), 4):
        chunk = keys23[i:i + 4]
        row = []
        for k in chunk:
            row.extend([k, f"{a_counts.get(k, 0):,}"])
        while len(row) < 8:
            row.extend(["", ""])
        a_rows.append(row)
    lines += md_table(("A", "几何字数", "A", "几何字数", "A", "几何字数", "A", "几何字数"), a_rows)

    lines += ["", "### 前 20 大冻结 BCD 格 A1 拆分前后对照", ""]
    by_bcd = defaultdict(list)
    for cp, r in rows.items():
        if r["layer"] == "G":
            by_bcd[r["BCD"]].append(r["BCDA"])
    top20_bcd = sorted(by_bcd.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:20]
    top20_rows = []
    for bcd, bcdas in top20_bcd:
        sub_cnt = Counter(bcdas)
        reps = " ".join(data["buckets"][code]["representativeChar"] for code in sorted(sub_cnt)[:8])
        top20_rows.append((bcd, len(bcdas), len(sub_cnt), max(sub_cnt.values()), min(sub_cnt.values()), reps))
    lines += md_table(("冻结 BCD", "原字数", "拆分 A 桶数", "拆后最大桶", "拆后最小桶", "代表字形（前8桶）"), top20_rows)

    lines += [
        "",
        "## 三、三阈值稳定性（112 / 128 / 144，分母 29,085 有图几何字）",
        "",
    ]
    stab_rows = [
        ("112 ↔ 128", f"{stab['112']['fixedBcdAChanged']:,}（{stab['112']['fixedBcdARate']:.2%}）",
         f"{stab['112']['indepBcdaChanged']:,}（{stab['112']['indepBcdaRate']:.2%}）"),
        ("144 ↔ 128", f"{stab['144']['fixedBcdAChanged']:,}（{stab['144']['fixedBcdARate']:.2%}）",
         f"{stab['144']['indepBcdaChanged']:,}（{stab['144']['indepBcdaRate']:.2%}）"),
    ]
    lines += md_table(("阈值对比", "固定 BCD 下纯 A 位改码（对比旧方案 C 52%）", "完全独立四键 BCDA 改码"), stab_rows)

    t_total_buckets = sum(1 for v in data["buckets"].values() if v["layer"] == "T")
    t_imaged_buckets = sum(r["subBuckets"] for r in data["tLineSummary"])
    lines += [
        "",
        "## 四、`t`（4,366 字）与 `x`（2,269 字）视觉分桶统计",
        "",
        f"### `t` 拟像与图标桶 24 行（共 {t_total_buckets} 个四码桶：{t_imaged_buckets} 个有图视觉桶 + {t_total_buckets - t_imaged_buckets} 组墨迹不足 ZZ）",
        "",
    ]
    t_rows = [(r["line"], f"{r['total']:,}", r["imaged"], r["missing"], r["cCount"], r["subBuckets"], r["maxImagedBucket"])
              for r in data["tLineSummary"]]
    lines += md_table(("T1 行", "总字数", "有图数", "墨迹不足(ZZ)", "C 簇", "总子桶", "最大有图桶"), t_rows)

    lines += ["", "### `x` 附标与组合记号桶（共 2,269 字，A 位固定 `X`）", ""]
    x_names = {"A": "上附标", "B": "下附标", "C": "居中/穿插附标", "D": "复合/宽跨附标", "Z": "无图待核"}
    x_rows = [(f"X{r['b']}", x_names.get(r["b"], r["b"]), r["count"], r["subBuckets"]) for r in data["xSummary"]]
    lines += md_table(("X 分支", "语义", "字数", "视觉子桶数"), x_rows)

    lines += [
        "",
        "## 五、D 位方向四条铁律（正式规范沿用）",
        "",
        "1. **有离散附标，看附标相对主体的位置**（上下两侧都有取 `V`）；",
        "2. **箭尖、尾巴和枝头，看向哪边**（`PF` 弧弯箭开放全部 8 向）；",
        "3. **开口弧、折角和单叉，看弧背、尖角或分叉所在侧**（开口反方向，与墨迹重心同向）；",
        "4. **复杂无开口且无附标，先看对称、双线、斜倾，再看哪边更重**（居中均衡取 `F`）。",
        "",
        f"复算脚本：`python -B build_v7_a1.py && python -B render_v7_a1_deliverables.py`。已校验 {len(data['inputSHA256']):,} 项输入与图源 SHA256。",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_cards(data, js_rows):
    buckets = data["buckets"]
    by_bcda = defaultdict(list)
    row_meta = {r[0]: r for r in js_rows}  # cp -> [cp, char, layer, bcda, d3, sheet, slot]
    for cp, r in data["rows"].items():
        by_bcda[r["BCDA"]].append(cp)

    sprite_cache = {}
    char_lookup = {(r["layer"], r["char"]): cp for cp, r in data["rows"].items()}
    esc = html.escape

    sections = ['''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>v7-A1 视觉归桶审图卡片</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f6f2;color:#1d2b22;font:15px/1.5 system-ui,sans-serif}
main{max-width:1180px;margin:auto;padding:18px 22px 60px}h1{font-size:32px;margin:0 0 8px}h2{margin:28px 0 10px;border-bottom:2px solid #d4ded4;padding-bottom:4px}
article{background:#fff;border:1px solid #d5ded5;border-radius:10px;padding:14px;margin-bottom:14px}
.repbar{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 12px;padding:8px;background:#eef3ee;border-radius:8px}
.rep{display:inline-flex;flex-direction:column;align-items:center;padding:4px 6px;background:#fff;border:1px solid #cad6ca;border-radius:6px;font:11px/1.2 ui-monospace,monospace}
.rep img,.tile img{width:32px;height:32px;image-rendering:pixelated;mix-blend-mode:multiply}
.buckets{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:10px}
.bucket{border:1px solid #e1e8e1;border-radius:8px;padding:10px;background:#fafcfa}
.bucket h4{margin:0 0 6px;font:600 13px ui-monospace,monospace;color:#284635}
.tiles{display:flex;flex-wrap:wrap;gap:4px}
.tile{display:inline-flex;flex-direction:column;align-items:center;width:44px;padding:3px;background:#eff3ee;border-radius:4px;font:10px ui-monospace,monospace}
</style><main><h1>v7-A1 视觉归桶审图卡片</h1>
<p>重点检验超大冻结 BCD 格与 t/x 桶在纯视觉聚类后的键面代表字形与桶内视觉一致性（每桶展示前 12 个样本）。</p>''']

    def img_tag(cp_str, alt):
        meta = row_meta.get(cp_str)
        if not meta or meta[5] < 0:
            return f"<span>{esc(alt)}</span>"
        b64 = sprite_crop_b64(meta[5], meta[6], sprite_cache)
        return f'<img width="32" height="32" alt="{esc(alt)}" src="data:image/png;base64,{b64}">'

    def add_group(title, prefix_codes, layer):
        sections.append(f"<h2>{esc(title)}</h2>")
        for pfx in prefix_codes:
            if layer == "G":
                matched = sorted(b for b in buckets if buckets[b]["layer"] == "G" and b[:3] == pfx)
            elif layer == "T":
                matched = sorted(b for b in buckets if buckets[b]["layer"] == "T" and b[0] == pfx and not b.endswith("ZZT"))
            else:
                matched = sorted(b for b in buckets if buckets[b]["layer"] == "X" and b[0] == pfx)
            total_n = sum(buckets[b]["count"] for b in matched)
            sections.append(f"<article><h3>{esc(pfx)}（{total_n} 字 → {len(matched)} 个视觉桶）</h3><div class=\"repbar\">")
            for b in matched[:23]:
                rep = buckets[b]["representativeChar"]
                rep_cp = char_lookup.get((layer, rep), "")
                key_label = b[3] if layer == "G" else b[1:3]
                sections.append(f'<div class="rep" title="{esc(b)}">{img_tag(rep_cp, rep)}<span>{esc(key_label)}·{buckets[b]["count"]}</span></div>')
            sections.append('</div><div class="buckets">')
            for b in matched[:12]:
                cps = sorted(by_bcda[b], key=lambda c: int(c[2:], 16))
                rep = buckets[b]["representativeChar"]
                sections.append(f'<div class="bucket"><h4>{esc(b)} · 代表「{esc(rep)}」· {len(cps)} 字</h4><div class="tiles">')
                for cp_str in cps[:12]:
                    ch = data["rows"][cp_str]["char"]
                    sections.append(f'<div class="tile" title="{esc(cp_str)} {esc(ch)}">{img_tag(cp_str, ch)}<span>{esc(cp_str[2:])}</span></div>')
                sections.append("</div></div>")
            sections.append("</div></article>")

    add_group("一、六大冻结 BCD 格的 A1 视觉拆分实拍", ["VFQ", "SFV", "NAD", "CAA", "HBF", "FCD"], "G")
    add_group("二、T1 拟像两大行（tA 人物与动作 / tD 动物）视觉分桶抽样", ["A", "D"], "T")
    add_group("三、X 附标与组合记号分桶抽样（上/下/中/宽）", ["A", "B", "C", "D"], "X")
    sections.append("</main></html>")
    CARDS_HTML.write_text("\n".join(sections), encoding="utf-8")


def render_browser():
    html_text = r'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>v7-A1 全键位交互浏览器（35,727 全域四键）</title>
<style>
*{box-sizing:border-box}
html{color-scheme:light}
body{margin:0;background:#f4f6f1;color:#1d2b22;font:15px/1.5 system-ui,sans-serif}
main{max-width:1220px;margin:auto;padding:16px 20px 64px}
header{background:#fff;border:1px solid #d5ded5;border-radius:12px;padding:16px 18px;margin-bottom:14px}
h1{margin:0 0 6px;font-size:26px}
.sub{color:#495c50;font-size:13px;margin:0 0 12px}
.toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.tabs{display:inline-flex;border:1px solid #b8c8bc;border-radius:8px;overflow:hidden;background:#eef3ee}
.tabs button{border:0;background:transparent;padding:7px 12px;font:inherit;cursor:pointer;color:#274232}
.tabs button.active{background:#2d6a4f;color:#fff;font-weight:600}
input[type=search]{flex:1;min-width:240px;padding:8px 12px;border:1px solid #b8c8bc;border-radius:8px;font:inherit}
button.btn{padding:7px 12px;border:1px solid #6b8474;border-radius:8px;background:#e4efe7;color:#173b24;font:inherit;cursor:pointer}
.panel{background:#fff;border:1px solid #d5ded5;border-radius:12px;padding:16px;margin-bottom:14px}
.panel h2{margin:0 0 10px;font-size:18px}
.crumbs{font:14px ui-monospace,monospace;color:#24523b;margin-bottom:10px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.keys{display:grid;grid-template-columns:repeat(auto-fill,minmax(138px,1fr));gap:8px}
.keybtn{display:flex;align-items:center;gap:8px;padding:8px 10px;border:1px solid #cfd9cf;border-radius:8px;background:#f8faf7;cursor:pointer;text-align:left;font:inherit}
.keybtn:hover{background:#eaf3ec;border-color:#5b8c71}
.keybtn.sel{background:#d4ebe0;border-color:#2d6a4f;font-weight:600}
.kcode{font:700 16px ui-monospace,monospace;color:#1a4731;min-width:20px}
.kmeta{font-size:12px;color:#4a5e52;line-height:1.25;overflow-wrap:anywhere}
.sp{width:32px;height:32px;display:inline-block;flex:0 0 32px;background-repeat:no-repeat;image-rendering:pixelated;border-radius:4px;background-color:#eef2ed}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(112px,1fr));gap:8px;margin-top:10px}
.card{border:1px solid #dce4dc;border-radius:8px;padding:8px;background:#fafcfa;display:flex;flex-direction:column;align-items:center;gap:4px;text-align:center}
.card .ch{font-size:18px;line-height:1.2}
.card .code{font:600 12px ui-monospace,monospace;color:#1e4d36}
.card .cp{font:11px ui-monospace,monospace;color:#5f7066}
.card .d3{font:11px ui-monospace,monospace;color:#7a5320}
.card button{font-size:11px;padding:3px 7px;border:1px solid #b9c8bc;border-radius:5px;background:#fff;cursor:pointer}
.card button.marked{background:#fbe9e0;border-color:#c06b45;color:#7c2f12}
.note{padding:10px 12px;background:#f0f5ef;border-left:4px solid #3c7a5c;border-radius:4px;font-size:13px;margin-bottom:10px}
textarea{width:100%;min-height:130px;font:13px ui-monospace,monospace;padding:8px;border:1px solid #c5d1c6;border-radius:8px}
.muted{color:#5e6e64;font-size:13px}
</style>
</head>
<body>
<main>
<header>
  <h1>v7-A1 全键位交互浏览器（35,727 全域四键）</h1>
  <p class="sub">冻结基线：几何 29,092 字（v6.2 BCD + 23 个 A1 纯视觉桶） · T 拟像与图标 4,366 字（T1） · X 附标 2,269 字 · Z 预留远期汉字/谚文</p>
  <div class="toolbar">
    <div class="tabs" id="orderTabs">
      <button data-order="BCDA" class="active">BCDA 顺序（先规则后视觉）</button>
      <button data-order="ABCD">ABCD 顺序（先视觉/大类后规则）</button>
    </div>
    <div class="tabs" id="layerTabs">
      <button data-layer="G" class="active">几何 29,092</button>
      <button data-layer="T">T 拟像图标 4,366</button>
      <button data-layer="X">X 附标 2,269</button>
      <button data-layer="Z">Z 汉字/谚文（保留）</button>
    </div>
    <input type="search" id="searchBox" placeholder="反查：输入字符、U+XXXX 或四码（如 % / U+2332 / PFM / AAYA）">
  </div>
</header>

<section class="panel" id="searchPanel" hidden>
  <h2>字符与编码反查</h2>
  <div id="searchResults"></div>
</section>

<section class="panel" id="navPanel">
  <div class="crumbs" id="crumbs"></div>
  <div id="stage"></div>
</section>

<section class="panel" id="bucketPanel" hidden>
  <h2 id="bucketTitle">桶内字符</h2>
  <div class="grid" id="bucketGrid"></div>
</section>

<section class="panel">
  <h2>待优化标注清单（自动本地保存）</h2>
  <p class="muted">浏览或反查时可点击任意字符下的「标记待优化」，全部微调意见可一键复制成 Markdown 发回调整。</p>
  <div class="toolbar" style="margin-bottom:8px">
    <button class="btn" id="copyMarks">复制待优化 Markdown</button>
    <button class="btn" id="clearMarks">清空标注</button>
    <span class="muted" id="markStatus"></span>
  </div>
  <textarea id="marksOut" readonly></textarea>
</section>
</main>

<script src="keymap-data.js"></script>
<script>
(() => {
  const D = window.V7_DATA;
  const rows = D.rows.map(r => ({
    cp: r[0], ch: r[1], layer: r[2], bcda: r[3], abcd: r[3][3] + r[3].slice(0, 3),
    d3: r[4], sheet: r[5], slot: r[6]
  }));
  const byBucket = {};
  for (const r of rows) {
    (byBucket[r.bcda] ||= []).push(r);
  }
  const byBCD = {};
  for (const r of rows) {
    if (r.layer === "G") (byBCD[r.bcda.slice(0, 3)] ||= []).push(r);
  }

  let order = "BCDA";
  let layer = "G";
  let sel = [];
  const marksKey = "v7_a1_opt_marks_v1";
  let marks = {};
  try { marks = JSON.parse(localStorage.getItem(marksKey) || "{}"); } catch {}

  const orderTabs = document.getElementById("orderTabs");
  const layerTabs = document.getElementById("layerTabs");
  const searchBox = document.getElementById("searchBox");
  const searchPanel = document.getElementById("searchPanel");
  const searchResults = document.getElementById("searchResults");
  const crumbs = document.getElementById("crumbs");
  const stage = document.getElementById("stage");
  const bucketPanel = document.getElementById("bucketPanel");
  const bucketTitle = document.getElementById("bucketTitle");
  const bucketGrid = document.getElementById("bucketGrid");
  const marksOut = document.getElementById("marksOut");
  const markStatus = document.getElementById("markStatus");

  function spriteEl(sheet, slot) {
    const s = document.createElement("span");
    s.className = "sp";
    if (sheet >= 0 && slot >= 0) {
      const r = Math.floor(slot / 50), c = slot % 50;
      const num = String(sheet).padStart(2, "0");
      s.style.backgroundImage = `url("sprites/s${num}.png")`;
      s.style.backgroundSize = "1600px auto";
      s.style.backgroundPosition = `${-c * 32}px ${-r * 32}px`;
    } else {
      s.textContent = "∅";
      s.style.display = "inline-flex";
      s.style.alignItems = "center";
      s.style.justifyContent = "center";
    }
    return s;
  }

  function saveMarks() {
    localStorage.setItem(marksKey, JSON.stringify(marks));
    const entries = Object.values(marks);
    const lines = ["| 码点 | 字 | 层 | BCDA / ABCD | 备注 |", "| --- | --- | --- | --- | --- |"];
    for (const m of entries) {
      lines.push(`| ${m.cp} | ${m.ch} | ${m.layer} | ${m.bcda} / ${m.abcd} | ${(m.note || "").replaceAll("|", "\\|")} |`);
    }
    marksOut.value = entries.length ? lines.join("\n") : "";
    markStatus.textContent = `已标记 ${entries.length} 项`;
  }

  function makeCard(r, showNeighborsBtn = false) {
    const div = document.createElement("div");
    div.className = "card";
    div.appendChild(spriteEl(r.sheet, r.slot));
    const ch = document.createElement("div");
    ch.className = "ch";
    ch.textContent = r.ch;
    const code = document.createElement("div");
    code.className = "code";
    code.textContent = order === "BCDA" ? r.bcda : r.abcd;
    const sub = document.createElement("div");
    sub.className = "cp";
    sub.textContent = `${r.cp} · ${order === "BCDA" ? r.abcd : r.bcda}`;
    div.append(ch, code, sub);
    if (r.d3 && r.d3.length) {
      const d3 = document.createElement("div");
      d3.className = "d3";
      d3.textContent = "D3: " + r.d3.join(" ");
      div.appendChild(d3);
    }
    const binfo = D.buckets[r.bcda];
    if (binfo && showNeighborsBtn) {
      const nb = document.createElement("button");
      nb.textContent = `看同桶 (${binfo[1]}字 · 代表${binfo[0]})`;
      nb.onclick = () => showBucket(r.bcda);
      div.appendChild(nb);
    }
    const mk = document.createElement("button");
    const isMarked = !!marks[r.cp];
    mk.className = isMarked ? "marked" : "";
    mk.textContent = isMarked ? "已标记（点修改/取消）" : "标记待优化";
    mk.onclick = () => {
      if (marks[r.cp]) {
        const next = prompt("修改备注（留空删除此条标记）：", marks[r.cp].note || "");
        if (next === null) return;
        if (!next.trim()) delete marks[r.cp];
        else marks[r.cp].note = next.trim();
      } else {
        const note = prompt(`备注 ${r.cp} ${r.ch} (${r.bcda}) 的调整建议：`, "视觉归桶或D3微调");
        if (note === null) return;
        marks[r.cp] = { ...r, note: note.trim() };
      }
      saveMarks();
      mk.className = marks[r.cp] ? "marked" : "";
      mk.textContent = marks[r.cp] ? "已标记（点修改/取消）" : "标记待优化";
    };
    div.appendChild(mk);
    return div;
  }

  function showBucket(bcda) {
    const list = byBucket[bcda] || [];
    const binfo = D.buckets[bcda];
    const dispCode = order === "BCDA" ? bcda : (bcda[3] + bcda.slice(0, 3));
    bucketTitle.textContent = `${dispCode}（${bcda} / ${bcda[3] + bcda.slice(0, 3)}）· 代表字形「${binfo ? binfo[0] : ""}」· 共 ${list.length} 字`;
    bucketGrid.innerHTML = "";
    for (const r of list) bucketGrid.appendChild(makeCard(r, false));
    bucketPanel.hidden = false;
  }

  function renderCrumbs(steps) {
    crumbs.innerHTML = "";
    const reset = document.createElement("button");
    reset.className = "btn";
    reset.textContent = "回到顶层";
    reset.onclick = () => { sel = []; bucketPanel.hidden = true; render(); };
    crumbs.appendChild(reset);
    const label = document.createElement("span");
    label.textContent = "当前路径：" + (steps.length ? steps.join(" → ") : "未选");
    crumbs.appendChild(label);
    if (steps.length) {
      const back = document.createElement("button");
      back.className = "btn";
      back.textContent = "返回上一级";
      back.onclick = () => { sel.pop(); bucketPanel.hidden = true; render(); };
      crumbs.appendChild(back);
    }
  }

  function addKeyBtn(container, code, title, sub, spritePair, onClick) {
    const btn = document.createElement("button");
    btn.className = "keybtn";
    if (spritePair) btn.appendChild(spriteEl(spritePair[0], spritePair[1]));
    const wrap = document.createElement("div");
    wrap.innerHTML = `<div class="kcode">${code}</div><div class="kmeta">${title}${sub ? "<br>" + sub : ""}</div>`;
    btn.appendChild(wrap);
    btn.onclick = onClick;
    container.appendChild(btn);
  }

  function render() {
    renderCrumbs(sel);
    stage.innerHTML = "";
    if (layer === "Z") {
      stage.innerHTML = '<div class="note"><strong>Z 桶（远期汉字 + 谚文入口保留位）</strong>：本轮已从全形键面与 A 位保留隔离，不与 35,727 几何/拟像/附标冲突，留待后续 IDS/汉字键面统一接入。</div>';
      bucketPanel.hidden = true;
      return;
    }

    const keysBox = document.createElement("div");
    keysBox.className = "keys";
    stage.appendChild(keysBox);

    if (layer === "G") {
      const gRows = rows.filter(r => r.layer === "G");
      if (order === "BCDA") {
        if (sel.length === 0) {
          const cnt = {};
          for (const r of gRows) cnt[r.bcda[0]] = (cnt[r.bcda[0]] || 0) + 1;
          for (const b of Object.keys(D.bNames)) {
            if (!cnt[b]) continue;
            addKeyBtn(keysBox, b, D.bNames[b], `${cnt[b]} 字`, null, () => { sel = [b]; render(); });
          }
        } else if (sel.length === 1) {
          const b = sel[0];
          const cnt = {};
          for (const r of gRows) if (r.bcda[0] === b) cnt[r.bcda.slice(0, 2)] = (cnt[r.bcda.slice(0, 2)] || 0) + 1;
          for (const bc of Object.keys(cnt).sort()) {
            const desc = D.cells[bc] || bc;
            addKeyBtn(keysBox, bc[1], desc, `${cnt[bc]} 字`, null, () => { sel = [b, bc[1]]; render(); });
          }
        } else if (sel.length === 2) {
          const bc = sel[0] + sel[1];
          const cnt = {};
          for (const r of gRows) if (r.bcda.slice(0, 2) === bc) cnt[r.bcda.slice(0, 3)] = (cnt[r.bcda.slice(0, 3)] || 0) + 1;
          for (const bcd of Object.keys(cnt).sort()) {
            const dKey = bcd[2];
            addKeyBtn(keysBox, dKey, D.dKeys[dKey] || dKey, `${cnt[bcd]} 字`, null, () => { sel = [sel[0], sel[1], dKey]; render(); });
          }
        } else {
          const bcd = sel[0] + sel[1] + sel[2];
          const matched = Object.keys(D.buckets).filter(k => D.buckets[k] && k.slice(0, 3) === bcd && byBucket[k]?.[0]?.layer === "G").sort();
          const note = document.createElement("div");
          note.className = "note";
          note.textContent = `${bcd} 共拆为 ${matched.length} 个纯视觉 A 键桶，每个按键图标为该桶的中心代表字形：`;
          stage.insertBefore(note, keysBox);
          for (const bcda of matched) {
            const bi = D.buckets[bcda];
            addKeyBtn(keysBox, bcda[3], `代表「${bi[0]}」`, `${bi[1]} 字`, [bi[2], bi[3]], () => showBucket(bcda));
          }
          if (matched.length === 1) showBucket(matched[0]);
        }
      } else {
        // ABCD order for Geometry
        if (sel.length === 0) {
          const cnt = {};
          for (const r of gRows) cnt[r.abcd[0]] = (cnt[r.abcd[0]] || 0) + 1;
          for (const a of D.geomAKeys) {
            addKeyBtn(keysBox, a, "A1 几何视觉桶", `${cnt[a] || 0} 字`, null, () => { sel = [a]; render(); });
          }
        } else if (sel.length === 1) {
          const a = sel[0];
          const cnt = {};
          for (const r of gRows) if (r.abcd[0] === a) cnt[r.abcd[1]] = (cnt[r.abcd[1]] || 0) + 1;
          for (const b of Object.keys(cnt).sort()) {
            addKeyBtn(keysBox, b, D.bNames[b] || b, `${cnt[b]} 字`, null, () => { sel = [a, b]; render(); });
          }
        } else if (sel.length === 2) {
          const ab = sel[0] + sel[1];
          const cnt = {};
          for (const r of gRows) if (r.abcd.slice(0, 2) === ab) cnt[r.abcd[2]] = (cnt[r.abcd[2]] || 0) + 1;
          for (const c of Object.keys(cnt).sort()) {
            const bc = sel[1] + c;
            addKeyBtn(keysBox, c, D.cells[bc] || bc, `${cnt[c]} 字`, null, () => { sel = [sel[0], sel[1], c]; render(); });
          }
        } else {
          const abc = sel[0] + sel[1] + sel[2];
          const matched = gRows.filter(r => r.abcd.slice(0, 3) === abc);
          const cnt = {};
          for (const r of matched) cnt[r.bcda] = (cnt[r.bcda] || 0) + 1;
          for (const bcda of Object.keys(cnt).sort()) {
            const bi = D.buckets[bcda];
            const dKey = bcda[2];
            addKeyBtn(keysBox, dKey, `${D.dKeys[dKey] || dKey} · 代表「${bi[0]}」`, `${bi[1]} 字`, [bi[2], bi[3]], () => showBucket(bcda));
          }
        }
      }
      return;
    }

    // Layer T or X
    const subRows = rows.filter(r => r.layer === layer);
    const names = layer === "T" ? D.tLines : D.xLines;
    if (sel.length === 0) {
      const cnt = {};
      for (const r of subRows) cnt[r.bcda[0]] = (cnt[r.bcda[0]] || 0) + 1;
      for (const b of Object.keys(cnt).sort()) {
        const label = layer === "T" ? (names["t" + b] || b) : (names[b] || b);
        addKeyBtn(keysBox, b, label, `${cnt[b]} 字`, null, () => { sel = [b]; render(); });
      }
    } else if (sel.length === 1) {
      const b = sel[0];
      const cnt = {};
      for (const r of subRows) if (r.bcda[0] === b) cnt[r.bcda[1]] = (cnt[r.bcda[1]] || 0) + 1;
      for (const c of Object.keys(cnt).sort()) {
        const firstBucket = Object.keys(byBucket).filter(k => byBucket[k][0].layer === layer && k[0] === b && k[1] === c).sort()[0];
        const bi = D.buckets[firstBucket];
        addKeyBtn(keysBox, c, c === "Z" ? "墨迹不足待补图" : `视觉 C 簇 · 代表「${bi[0]}」`, `${cnt[c]} 字`, [bi[2], bi[3]], () => { sel = [b, c]; render(); });
      }
    } else {
      const b = sel[0], c = sel[1];
      const matched = Object.keys(byBucket).filter(k => byBucket[k][0].layer === layer && k[0] === b && k[1] === c).sort();
      for (const bcda of matched) {
        const bi = D.buckets[bcda];
        addKeyBtn(keysBox, bcda[2], bcda[2] === "Z" ? "待补图桶" : `代表「${bi[0]}」`, `${bi[1]} 字`, [bi[2], bi[3]], () => showBucket(bcda));
      }
      if (matched.length === 1) showBucket(matched[0]);
    }
  }

  function runSearch() {
    const q = searchBox.value.trim();
    if (!q) { searchPanel.hidden = true; return; }
    const uq = q.toUpperCase();
    const hits = [];
    for (const r of rows) {
      if (r.ch === q || r.cp.toUpperCase() === uq || r.cp.slice(2).toUpperCase() === uq ||
          r.bcda.startsWith(uq) || r.abcd.startsWith(uq)) {
        hits.push(r);
        if (hits.length >= 60) break;
      }
    }
    searchResults.innerHTML = "";
    if (!hits.length) {
      searchResults.innerHTML = '<p class="muted">未找到匹配字符或编码。</p>';
    } else {
      const g = document.createElement("div");
      g.className = "grid";
      for (const r of hits) g.appendChild(makeCard(r, true));
      searchResults.appendChild(g);
    }
    searchPanel.hidden = false;
  }

  orderTabs.addEventListener("click", e => {
    if (e.target.tagName !== "BUTTON") return;
    order = e.target.dataset.order;
    orderTabs.querySelectorAll("button").forEach(b => b.classList.toggle("active", b === e.target));
    sel = [];
    bucketPanel.hidden = true;
    render();
    if (!searchPanel.hidden) runSearch();
  });

  layerTabs.addEventListener("click", e => {
    if (e.target.tagName !== "BUTTON") return;
    layer = e.target.dataset.layer;
    layerTabs.querySelectorAll("button").forEach(b => b.classList.toggle("active", b === e.target));
    sel = [];
    bucketPanel.hidden = true;
    render();
  });

  searchBox.addEventListener("input", runSearch);
  document.getElementById("copyMarks").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(marksOut.value);
      markStatus.textContent = "已复制 Markdown";
    } catch {
      marksOut.select();
      markStatus.textContent = document.execCommand("copy") ? "已复制 Markdown" : "已全选，请 Ctrl+C 复制";
    }
  });
  document.getElementById("clearMarks").addEventListener("click", () => {
    marks = {};
    saveMarks();
    render();
    if (!searchPanel.hidden) runSearch();
  });

  saveMarks();
  render();
})();
</script>
</body>
</html>
'''
    BROWSER_HTML.write_text(html_text, encoding="utf-8")


def main():
    data = read_json(DATA_JSON)
    # Also read compact js rows cleanly
    js_txt = (OUT / "keymap-data.js").read_text(encoding="utf-8")
    js_obj = json.loads(js_txt[js_txt.index("{"):js_txt.rindex("}") + 1])
    render_report(data)
    render_cards(data, js_obj["rows"])
    render_browser()
    print("Delivered:", REPORT_MD.name, CARDS_HTML.name, BROWSER_HTML.name, flush=True)


if __name__ == "__main__":
    main()
