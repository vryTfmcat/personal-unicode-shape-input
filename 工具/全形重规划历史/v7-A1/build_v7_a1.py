"""Build the v7-A1 35,727 full-keymap baseline (frozen v6.2 BCD + T1 + x + A1 visual clustering)."""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
V41 = BASE / "整体重规划-20261121-BC族表v0"
V5 = BASE / "整体重规划-20261124-B分流与可解释A层"
V6 = BASE / "整体重规划-20261124-v6-BCD规则重构"
V62 = BASE / "整体重规划-20261125-v6.2-BCD终局收口"
ROOT = next(p for p in OUT.parents if p.name == "worktree")

if (V5 / "deps").is_dir():
    sys.path.insert(0, str(V5 / "deps"))
for p in (V6, V5, V41):
    if str(p) not in sys.path:
        sys.path.append(str(p))

import stage3 as P  # noqa: E402
from fontTools.pens.boundsPen import BoundsPen  # noqa: E402
from geometry import font_manifest, font_path, outline, pictorial_images, pil_face  # noqa: E402
from pictorial import INTAKE, lookup as tb_lookup  # noqa: E402
from rules import D_KEYS, NAMES  # noqa: E402
from visual_embed import cluster_cell, embed_glyph  # noqa: E402

GEOM_A_KEYS = "ABCDEFGHIJKLMNOPQRSUVWY"  # 23 keys; T, X, Z reserved!
RESERVED_A_KEYS = set("TXZ")
THRESHOLDS = (112, 128, 144)

V62_BCD = V62 / "BCD分配结果-全域-v6.2.json"
V62_T1 = V62 / "tb落地结果-T1-v6.2.json"
FEATURES_V41 = V41 / "全域特征标注-29096-v4.1.json"
SHAPE_STAGE = ROOT / "原型/键位编辑器/data/shape-stage.json"
AUDIT = ROOT / "数据/三模式/规则库/四键实验/人工审议.json"
MANIFEST = ROOT / "原型/键位编辑器/fonts/manifest.json"
V4_SCRIPT = V41 / "BC分配-全域-v4.py"

OUTPUT_JSON = OUT / "全形全键位基线-35727-v7-A1.json"
KEYMAP_JS = OUT / "keymap-data.js"
SPRITE_DIR = OUT / "sprites"


def sha(path, hashes):
    k = str(Path(path).resolve())
    if k not in hashes:
        hashes[k] = P.digest(Path(path))
    return hashes[k]


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def render_x_glyph(cp_int, face, hashes):
    font = pil_face(font_path(face, hashes))
    text = chr(cp_int)
    x, y, x1, y1 = font.getbbox(text)
    if x1 <= x or y1 <= y:
        return None
    image = Image.new("L", (x1 - x, y1 - y), 255)
    ImageDraw.Draw(image).text((-x, -y), text, font=font, fill=0)
    image.thumbnail((56, 56), Image.Resampling.LANCZOS)
    canvas = Image.new("L", (64, 64), 255)
    canvas.paste(image, ((64 - image.width) // 2, (64 - image.height) // 2))
    return np.asarray(canvas, dtype=np.uint8)


def x_vertical_bucket(cp_int, face, hashes):
    if not face:
        return "Z"
    font = outline(font_path(face, hashes))
    name = font.getBestCmap().get(cp_int)
    if not name:
        return "Z"
    gs = font.getGlyphSet()
    pen = BoundsPen(gs)
    gs[name].draw(pen)
    if not pen.bounds:
        return "Z"
    left, bottom, right, top = pen.bounds
    em = max(1, font["head"].unitsPerEm)
    mid_y = (bottom + top) / 2.0
    width = right - left
    height = top - bottom
    if width <= 0 or height <= 0:
        return "Z"
    if bottom >= 0.45 * em or mid_y >= 0.62 * em:
        return "A"  # above / superscript diacritic
    if top <= 0.22 * em or mid_y <= 0.12 * em:
        return "B"  # below / subscript diacritic
    if width > 0.90 * em or height > 0.85 * em:
        return "D"  # wide / spanning / enclosing combining mark
    return "C"  # middle / overlay diacritic


def build():
    hashes = {}
    for p in (V62_BCD, V62_T1, FEATURES_V41, SHAPE_STAGE, AUDIT, MANIFEST, V4_SCRIPT, INTAKE):
        sha(p, hashes)

    import runpy
    o20_set = set(runpy.run_path(str(V4_SCRIPT))["O20"])

    v62_bcd = read_json(V62_BCD)
    v62_t1 = read_json(V62_T1)
    features_list = read_json(FEATURES_V41)["rows"]
    features = {r["codepoint"]: r for r in features_list}
    shape_stage = read_json(SHAPE_STAGE)

    geom_rows = v62_bcd["rows"]
    t1_rows = v62_t1["rows"]
    x_cps = shape_stage["buckets"]["x"]

    # 1. Disjointness & exact 35,727 check
    g_set = {int(cp[2:], 16) for cp in geom_rows}
    t_set = {int(k) for k in t1_rows}
    x_set = {int(k) for k in x_cps}
    assert len(g_set) == 29092, len(g_set)
    assert len(t_set) == 4366, len(t_set)
    assert len(x_set) == 2269, len(x_set)
    assert not (g_set & t_set) and not (g_set & x_set) and not (t_set & x_set)
    assert len(g_set | t_set | x_set) == 35727

    print("1/5 Input sets verified: 29,092 + 4,366 + 2,269 = 35,727 (0 overlap)", flush=True)

    # 2. Extract visual embeddings for geometric layer at 112, 128, 144
    geom_feat_sub = {cp: features[cp] for cp in geom_rows if features[cp]["source"]}
    assert len(geom_feat_sub) == 29085, len(geom_feat_sub)

    geom_vecs = {t: {} for t in THRESHOLDS}
    tiles32 = {}  # int_cp -> 32x32 uint8 gray tile

    for idx, (cp, gray) in enumerate(P.glyph_pages(geom_feat_sub, hashes), 1):
        cp_int = int(cp[2:], 16)
        mask_cache = {}
        for t in THRESHOLDS:
            key = (gray < t).tobytes()
            if key not in mask_cache:
                vec, tile = embed_glyph(gray, threshold=t)
                mask_cache[key] = (vec, tile)
            vec, tile = mask_cache[key]
            geom_vecs[t][cp] = vec
            if t == 128 and tile is not None:
                tiles32[cp_int] = tile
        if idx % 5000 == 0:
            print(f"  Embedded geometric glyphs: {idx} / {len(geom_feat_sub)}", flush=True)

    # Check all 29,085 have valid 128-threshold embeddings (fallback to 144 if extremely faint)
    for cp in geom_feat_sub:
        if geom_vecs[128][cp] is None:
            raise ValueError(f"Empty embedding at 128 for {cp}")

    # 3. Cluster within each frozen v6.2 BCD cell (1,051 cells)
    by_bcd = defaultdict(list)
    for cp, row in geom_rows.items():
        by_bcd[row["BCD"]].append(cp)

    cell_centroids = {}  # bcd -> (k_eff, centroids ndarray)
    geom_buckets = {}    # bcda -> dict(representativeChar, count, members, intra, inter)
    geom_assign = {}     # cp -> (bcda, rep_char)
    compactness_stats = []

    for bcd, cps in sorted(by_bcd.items()):
        cps_sorted = sorted(cps, key=lambda c: int(c[2:], 16))
        if bcd == "AAY":
            assert set(cps_sorted) == o20_set
            a_key = "A"
            bcda = bcd + a_key
            rep = "o" if "o" in [geom_rows[c]["char"] for c in cps_sorted] else geom_rows[cps_sorted[0]]["char"]
            geom_buckets[bcda] = dict(representativeChar=rep, count=len(cps_sorted), intra=0.0, inter=0.0)
            for c in cps_sorted:
                geom_assign[c] = (bcda, rep)
            continue
        if bcd == "ZAZ":
            assert len(cps_sorted) == 7
            a_key = "A"
            bcda = bcd + a_key
            rep = geom_rows[cps_sorted[0]]["char"]
            geom_buckets[bcda] = dict(representativeChar=rep, count=len(cps_sorted), intra=0.0, inter=0.0)
            for c in cps_sorted:
                geom_assign[c] = (bcda, rep)
            continue

        valid_cps = [c for c in cps_sorted if c in geom_vecs[128]]
        missing_cps = [c for c in cps_sorted if c not in geom_vecs[128]]
        assert not missing_cps, (bcd, missing_cps)

        n = len(valid_cps)
        if n <= 16:
            k = 1
        else:
            k = min(23, math.ceil(n / 20))
        X = np.vstack([geom_vecs[128][c] for c in valid_cps])
        labels, centroids, medoids, intra, inter = cluster_cell(X, k, max_size=45)
        k_eff = len(centroids)
        assert k_eff <= 23
        cell_centroids[bcd] = (k_eff, centroids)
        if n > 16:
            compactness_stats.append((bcd, n, k_eff, intra, inter))

        for cid in range(k_eff):
            pts = np.where(labels == cid)[0]
            a_key = GEOM_A_KEYS[cid]
            assert a_key not in RESERVED_A_KEYS
            bcda = bcd + a_key
            rep = geom_rows[valid_cps[medoids[cid]]]["char"]
            geom_buckets[bcda] = dict(
                representativeChar=rep,
                count=int(len(pts)),
                intra=round(intra, 4),
                inter=round(inter, 4),
            )
            for idx_pt in pts:
                geom_assign[valid_cps[idx_pt]] = (bcda, rep)

    print("2/5 Geometric A1 clustering complete:", len(geom_buckets), "BCDA buckets", flush=True)

    # 4. Three-threshold stability check (112 / 128 / 144) on 29,085 imaged geometric chars
    stability = {}
    for t in (112, 144):
        a_changed_fixed_bcd = 0
        bcda_changed_indep = 0
        a_changed_indep_valid = 0
        for cp in geom_feat_sub:
            bcd128 = geom_rows[cp]["BCD"]
            bcda128 = geom_assign[cp][0]
            a128 = bcda128[3]
            vec_t = geom_vecs[t][cp]
            if vec_t is None:
                vec_t = geom_vecs[128][cp]

            # (a) Fixed BCD: nearest 128 centroid inside bcd128
            if bcd128 == "AAY":
                a_fixed = "A"
            elif bcd128 not in cell_centroids:
                a_fixed = "A"
            else:
                k_eff, c_arr = cell_centroids[bcd128]
                if k_eff == 1:
                    a_fixed = "A"
                else:
                    cid = int(np.argmin(np.linalg.norm(c_arr - vec_t, axis=1)))
                    a_fixed = GEOM_A_KEYS[cid]
            if a_fixed != a128:
                a_changed_fixed_bcd += 1

            # (b) Independent BCD_t + nearest 128 centroid in BCD_t
            bcd_t = geom_rows[cp]["independent"][str(t)]
            if bcd_t == "AAY" or bcd_t not in cell_centroids:
                a_indep = "A"
            else:
                k_eff_t, c_arr_t = cell_centroids[bcd_t]
                if k_eff_t == 1:
                    a_indep = "A"
                else:
                    cid_t = int(np.argmin(np.linalg.norm(c_arr_t - vec_t, axis=1)))
                    a_indep = GEOM_A_KEYS[cid_t]
            bcda_t = bcd_t + a_indep
            if bcda_t != bcda128:
                bcda_changed_indep += 1
            if bcd_t == bcd128 and a_indep != a128:
                a_changed_indep_valid += 1

        denom = len(geom_feat_sub)
        stability[str(t)] = dict(
            denom=denom,
            fixedBcdAChanged=a_changed_fixed_bcd,
            fixedBcdARate=round(a_changed_fixed_bcd / denom, 5),
            indepBcdaChanged=bcda_changed_indep,
            indepBcdaRate=round(bcda_changed_indep / denom, 5),
            sameBcdIndepAChanged=a_changed_indep_valid,
        )
        print(f"  Stability @{t}: fixed-BCD A change={a_changed_fixed_bcd}/{denom} ({a_changed_fixed_bcd/denom:.2%}), indep BCDA change={bcda_changed_indep}/{denom} ({bcda_changed_indep/denom:.2%})", flush=True)

    # 5. Process t bucket (4,366 chars, A='T')
    _, previews = tb_lookup()
    faces = font_manifest()
    t_gray = {}
    for cp_int, gray, kind in pictorial_images(previews, hashes, faces):
        t_gray[cp_int] = gray
    # Also fetch the 4 moved geometric chars from v4.1 glyph_pages
    moved_cps = {f"U+{int(k):04X}": features[f"U+{int(k):04X}"] for k in t_set - set(previews.keys())}
    assert len(moved_cps) == 4, moved_cps
    for cp_str, gray in P.glyph_pages(moved_cps, hashes):
        t_gray[int(cp_str[2:], 16)] = gray

    t_by_line = defaultdict(list)
    for k_str, info in t1_rows.items():
        t_by_line[info["tPrimary"]].append(int(k_str))

    t_assign = {}   # cp_int -> (bcda, rep_char, has_img)
    t_buckets = {}  # bcda -> dict(...)
    t_line_summary = []

    for line_code in sorted(t_by_line):
        b_key = line_code[1]  # A..X
        cps = sorted(t_by_line[line_code])
        imaged = []
        missing = []
        vecs = []
        for cp_int in cps:
            gray = t_gray.get(cp_int)
            vec, tile = embed_glyph(gray, 128) if gray is not None else (None, None)
            if vec is not None:
                imaged.append(cp_int)
                vecs.append(vec)
                tiles32[cp_int] = tile
            else:
                missing.append(cp_int)

        c_cnt = 0
        d_cnt = 0
        max_sub = 0
        if imaged:
            X_line = np.vstack(vecs)
            k_c = min(25, max(1, math.ceil(len(imaged) / 60)))
            c_labels, _, _, _, _ = cluster_cell(X_line, k_c, max_size=75)
            c_used = sorted(set(c_labels.tolist()))
            c_cnt = len(c_used)
            for ci, cid in enumerate(c_used):
                c_key = chr(65 + ci)  # A..Y (never Z)
                pts_c = np.where(c_labels == cid)[0]
                if len(pts_c) > 30:
                    k_d = min(25, math.ceil(len(pts_c) / 22))
                    d_labels, _, d_meds, _, _ = cluster_cell(X_line[pts_c], k_d, max_size=40)
                    d_used = sorted(set(d_labels.tolist()))
                    for di, did in enumerate(d_used):
                        d_key = chr(65 + di)
                        pts_d = pts_c[d_labels == did]
                        d_cnt += 1
                        bcda = f"{b_key}{c_key}{d_key}T"
                        rep = t1_rows[str(imaged[pts_c[d_meds[di]]])]["char"]
                        t_buckets[bcda] = dict(representativeChar=rep, count=int(len(pts_d)), imaged=True)
                        max_sub = max(max_sub, int(len(pts_d)))
                        for idx_pt in pts_d:
                            t_assign[imaged[idx_pt]] = (bcda, rep, True)
                else:
                    d_cnt += 1
                    sub = X_line[pts_c]
                    dmat = np.linalg.norm(sub[:, None, :] - sub[None, :, :], axis=2)
                    med = int(pts_c[int(np.argmin(dmat.sum(axis=1)))])
                    bcda = f"{b_key}{c_key}AT"
                    rep = t1_rows[str(imaged[med])]["char"]
                    t_buckets[bcda] = dict(representativeChar=rep, count=int(len(pts_c)), imaged=True)
                    max_sub = max(max_sub, int(len(pts_c)))
                    for idx_pt in pts_c:
                        t_assign[imaged[idx_pt]] = (bcda, rep, True)

        if missing:
            bcda = f"{b_key}ZZT"
            rep = t1_rows[str(missing[0])]["char"]
            t_buckets[bcda] = dict(representativeChar=rep, count=len(missing), imaged=False)
            for cp_int in missing:
                t_assign[cp_int] = (bcda, rep, False)

        t_line_summary.append(dict(line=line_code, total=len(cps), imaged=len(imaged), missing=len(missing),
                                   cCount=c_cnt, subBuckets=d_cnt, maxImagedBucket=max_sub))

    print("3/5 T1 bucket clustering complete:", len(t_buckets), "t-buckets across 24 lines", flush=True)

    # 6. Process x bucket (2,269 chars, A='X')
    x_by_b = defaultdict(list)
    x_vecs = {}
    for cp_int in sorted(x_cps):
        face = faces.get(cp_int)
        b_key = x_vertical_bucket(cp_int, face, hashes)
        gray = render_x_glyph(cp_int, face, hashes) if face else None
        vec, tile = embed_glyph(gray, 128) if gray is not None else (None, None)
        if vec is not None:
            x_vecs[cp_int] = vec
            tiles32[cp_int] = tile
        else:
            b_key = "Z"
        x_by_b[b_key].append(cp_int)

    x_assign = {}
    x_buckets = {}
    x_summary = []
    for b_key in sorted(x_by_b):
        cps = x_by_b[b_key]
        if b_key == "Z":
            bcda = "ZZZX"
            rep = chr(cps[0])
            x_buckets[bcda] = dict(representativeChar=rep, count=len(cps), imaged=False)
            for cp_int in cps:
                x_assign[cp_int] = (bcda, rep, False)
            x_summary.append(dict(b=b_key, count=len(cps), subBuckets=1))
            continue

        X_line = np.vstack([x_vecs[c] for c in cps])
        k_c = min(25, max(1, math.ceil(len(cps) / 55)))
        c_labels, _, _, _, _ = cluster_cell(X_line, k_c, max_size=75)
        c_used = sorted(set(c_labels.tolist()))
        sub_cnt = 0
        for ci, cid in enumerate(c_used):
            c_key = chr(65 + ci)
            pts_c = np.where(c_labels == cid)[0]
            if len(pts_c) > 28:
                k_d = min(25, math.ceil(len(pts_c) / 22))
                d_labels, _, d_meds, _, _ = cluster_cell(X_line[pts_c], k_d, max_size=35)
                d_used = sorted(set(d_labels.tolist()))
                for di, did in enumerate(d_used):
                    d_key = chr(65 + di)
                    pts_d = pts_c[d_labels == did]
                    sub_cnt += 1
                    bcda = f"{b_key}{c_key}{d_key}X"
                    rep = chr(cps[pts_c[d_meds[di]]])
                    x_buckets[bcda] = dict(representativeChar=rep, count=int(len(pts_d)), imaged=True)
                    for idx_pt in pts_d:
                        x_assign[cps[idx_pt]] = (bcda, rep, True)
            else:
                sub_cnt += 1
                sub = X_line[pts_c]
                dmat = np.linalg.norm(sub[:, None, :] - sub[None, :, :], axis=2)
                med = int(pts_c[int(np.argmin(dmat.sum(axis=1)))])
                bcda = f"{b_key}{c_key}AX"
                rep = chr(cps[med])
                x_buckets[bcda] = dict(representativeChar=rep, count=int(len(pts_c)), imaged=True)
                for idx_pt in pts_c:
                    x_assign[cps[idx_pt]] = (bcda, rep, True)
        x_summary.append(dict(b=b_key, count=len(cps), subBuckets=sub_cnt))

    print("4/5 X bucket clustering complete:", len(x_buckets), "x-buckets", flush=True)

    # 7. Combine 35,727 entries & run strict D7 bijective + non-overlap assertions
    all_rows = {}
    all_buckets = {}
    all_buckets.update({k: dict(v, layer="G") for k, v in geom_buckets.items()})
    all_buckets.update({k: dict(v, layer="T") for k, v in t_buckets.items()})
    all_buckets.update({k: dict(v, layer="X") for k, v in x_buckets.items()})

    for cp, row in geom_rows.items():
        bcda, rep = geom_assign[cp]
        abcd = bcda[3] + bcda[:3]
        assert bcda[3] in GEOM_A_KEYS and bcda[3] not in RESERVED_A_KEYS
        all_rows[cp] = dict(
            char=row["char"],
            layer="G",
            BCD=row["BCD"],
            BCDA=bcda,
            ABCD=abcd,
            secondaryPaths=row["secondaryPaths"],
            representativeChar=rep,
        )

    for k_str, info in t1_rows.items():
        cp_int = int(k_str)
        cp = f"U+{cp_int:04X}"
        bcda, rep, has_img = t_assign[cp_int]
        abcd = bcda[3] + bcda[:3]
        assert bcda[3] == "T" and abcd[0] == "T"
        all_rows[cp] = dict(
            char=info["char"],
            layer="T",
            tLine=info["tPrimary"],
            category=info["category"],
            BCD=bcda[:3],
            BCDA=bcda,
            ABCD=abcd,
            secondaryPaths=info["geometricD3"],
            representativeChar=rep,
            hasImage=has_img,
        )

    for cp_int in sorted(x_cps):
        cp = f"U+{cp_int:04X}"
        bcda, rep, has_img = x_assign[cp_int]
        abcd = bcda[3] + bcda[:3]
        assert bcda[3] == "X" and abcd[0] == "X"
        all_rows[cp] = dict(
            char=chr(cp_int),
            layer="X",
            BCD=bcda[:3],
            BCDA=bcda,
            ABCD=abcd,
            secondaryPaths=[],
            representativeChar=rep,
            hasImage=has_img,
        )

    assert len(all_rows) == 35727
    # Check D7 bijective correspondence BCDA <-> ABCD
    bcda_groups = defaultdict(list)
    abcd_groups = defaultdict(list)
    for cp, r in all_rows.items():
        bcda_groups[r["BCDA"]].append(cp)
        abcd_groups[r["ABCD"]].append(cp)
        assert r["ABCD"] == r["BCDA"][3] + r["BCDA"][:3]
    assert len(bcda_groups) == len(abcd_groups) == len(all_buckets)
    for bcda, cps in bcda_groups.items():
        abcd = bcda[3] + bcda[:3]
        assert set(cps) == set(abcd_groups[abcd])
    # Verify frozen O20 and Z7
    assert all(all_rows[cp]["BCDA"] == "AAYA" and all_rows[cp]["ABCD"] == "AAAY" for cp in o20_set)
    z7 = [cp for cp, r in geom_rows.items() if r["BCD"] == "ZAZ"]
    assert len(z7) == 7 and all(all_rows[cp]["BCDA"] == "ZAZA" and all_rows[cp]["ABCD"] == "AZAZ" for cp in z7)

    # Geometry load metrics
    geom_bcda_counts = Counter(r["BCDA"] for r in all_rows.values() if r["layer"] == "G")
    geom_char_loads = sorted(geom_bcda_counts[all_rows[cp]["BCDA"]] for cp in geom_rows)
    n_g = len(geom_char_loads)
    geom_metrics = dict(
        total=n_g,
        bcdaUsed=len(geom_bcda_counts),
        maxBCDA=max(geom_bcda_counts.items(), key=lambda kv: (kv[1], kv[0])),
        p50=geom_char_loads[n_g // 2],
        p90=geom_char_loads[int(0.9 * (n_g - 1))],
        atMost20=sum(1 for v in geom_char_loads if v <= 20),
        atMost10=sum(1 for v in geom_char_loads if v <= 10),
        aKeyCounts=dict(Counter(all_rows[cp]["BCDA"][3] for cp in geom_rows)),
        meanIntra=round(float(np.mean([x[3] for x in compactness_stats])), 4),
        meanInter=round(float(np.mean([x[4] for x in compactness_stats])), 4),
    )
    print(f"  Geom metrics: buckets={geom_metrics['bcdaUsed']}, max={geom_metrics['maxBCDA']}, p50={geom_metrics['p50']}, p90={geom_metrics['p90']}, <=20={geom_metrics['atMost20']/n_g:.2%}", flush=True)

    # 8. Export 32x32 sprite sheets (50x50 grid = 2500 tiles per PNG) + compact browser data
    SPRITE_DIR.mkdir(parents=True, exist_ok=True)
    for old_png in SPRITE_DIR.glob("*.png"):
        old_png.unlink()

    sorted_cps = sorted(all_rows, key=lambda c: int(c[2:], 16))
    imaged_cp_list = [c for c in sorted_cps if int(c[2:], 16) in tiles32]
    sprite_index = {}  # cp -> [sheet_idx, slot_idx]
    per_sheet = 2500
    cols = 50
    for s_idx in range(math.ceil(len(imaged_cp_list) / per_sheet)):
        chunk = imaged_cp_list[s_idx * per_sheet:(s_idx + 1) * per_sheet]
        rows_n = math.ceil(len(chunk) / cols)
        sheet = Image.new("L", (cols * 32, rows_n * 32), 255)
        for slot, cp_str in enumerate(chunk):
            r_i, c_i = divmod(slot, cols)
            sheet.paste(Image.fromarray(tiles32[int(cp_str[2:], 16)]), (c_i * 32, r_i * 32))
            sprite_index[cp_str] = [s_idx, slot]
        sheet.save(SPRITE_DIR / f"s{s_idx:02d}.png", optimize=True)

    print(f"5/5 Exported {math.ceil(len(imaged_cp_list) / per_sheet)} sprite sheets for {len(imaged_cp_list)} imaged chars", flush=True)

    # Prepare friendly cell labels (fixing YP description!)
    cells_meta = dict(v62_bcd["cells"])
    cells_meta["YP"] = "繁复无孔曲线 + 离散附标"

    payload = dict(
        version="v7-A1",
        date="2026-11-27",
        counts=dict(total=len(all_rows), G=len(g_set), T=len(t_set), X=len(x_set)),
        reservedAKeys=sorted(RESERVED_A_KEYS),
        geomAKeys=list(GEOM_A_KEYS),
        geomMetrics=geom_metrics,
        stability=stability,
        tLineSummary=t_line_summary,
        xSummary=x_summary,
        compactnessSample=compactness_stats,
        cells=cells_meta,
        bNames=NAMES,
        dKeys=D_KEYS,
        buckets=all_buckets,
        rows=all_rows,
        inputSHA256=hashes,
    )
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    # Compact JS payload for offline interactive browser
    # Encode rows as compact arrays: [cpHex, char, layer, bcda, d3List, sheetIdx, slotIdx]
    compact_rows = []
    for cp_str in sorted_cps:
        r = all_rows[cp_str]
        sp = sprite_index.get(cp_str, [-1, -1])
        compact_rows.append([cp_str, r["char"], r["layer"], r["BCDA"], r["secondaryPaths"], sp[0], sp[1]])

    # Compact bucket reps: bcda -> [repChar, count, sheetIdx, slotIdx]
    char_to_cp_by_layer = {}
    for cp_str, r in all_rows.items():
        char_to_cp_by_layer[(r["layer"], r["char"])] = cp_str
    compact_buckets = {}
    for bcda, binfo in all_buckets.items():
        rep = binfo["representativeChar"]
        rep_cp = char_to_cp_by_layer.get((binfo["layer"], rep), "")
        sp = sprite_index.get(rep_cp, [-1, -1])
        compact_buckets[bcda] = [rep, binfo["count"], sp[0], sp[1]]

    t_line_names = {r["code"]: r["name"] for r in v62_t1["lines"]}
    x_line_names = {"A": "上附标", "B": "下附标", "C": "居中/穿插附标", "D": "复合/宽跨附标", "Z": "无图待核"}
    browser_data = dict(
        bNames=NAMES,
        cells=cells_meta,
        dKeys=D_KEYS,
        tLines=t_line_names,
        xLines=x_line_names,
        geomAKeys=list(GEOM_A_KEYS),
        buckets=compact_buckets,
        rows=compact_rows,
    )
    KEYMAP_JS.write_text("window.V7_DATA = " + json.dumps(browser_data, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    print("Wrote", OUTPUT_JSON.name, "and", KEYMAP_JS.name, flush=True)


if __name__ == "__main__":
    build()
