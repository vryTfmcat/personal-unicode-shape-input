#!/usr/bin/env python3
"""Build a balanced jj-prefixed Egyptian Hieroglyph shape catalog.

Version 3 first divides Gardiner groups among four user-confirmed prefixes,
then clusters normalized glyph silhouettes into balanced main-shape families
and assigns state keys with a hard five-candidate cap per four-letter code.
The result is an editable machine first pass, not an official classification.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
except ImportError as error:  # pragma: no cover
    raise SystemExit("需要 NumPy 与 Pillow；请使用 Codex 工作区 Python 运行本脚本。") from error


PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / "数据" / "𓆟Egyptian Hieroglyph字块.md"
OUTPUT = PROJECT / "数据" / "𓆟字块-编码.tsv"
README = PROJECT / "数据" / "𓆟字块-编码说明.md"
SOURCE_RELATIVE = "30_项目/个人Unicode音型输入法/数据/𓆟Egyptian Hieroglyph字块.md"
ALGORITHM_VERSION = "visual-balanced-4prefix-v3"
MAX_CANDIDATES = 5
CLUSTER_COUNT = 26
CLUSTER_CAPACITY = 44

PREFIX_LABELS = {
    "jj": "生命形（人物、人体、动物、鸟、鱼）",
    "jn": "自然、天地、水和植物",
    "jw": "器物、建筑和工具",
    "jx": "图形、抽象与未分类",
}
PREFIX_GROUPS = {
    "jj": set("ABCDEFGHIKL"),
    "jn": {"M", "N"},
    "jw": set("OPQRSTU"),
    "jx": {"V", "W", "X", "Y", "Z", "Aa"},
}
MANUAL_OVERRIDES = {
    0x1319F: ("jj", "g", "h", "用户锚点：𓆟为生命形、动物有机体、横向"),
}

MAIN_LABELS = {
    "a": "角折", "b": "块面", "c": "曲弧", "d": "点状", "e": "椭圆",
    "f": "人物轮廓", "g": "动物有机体", "h": "枝杈", "i": "细柱",
    "j": "钩弯", "k": "绳结", "l": "线条", "m": "复合", "n": "成列成排",
    "o": "圆环", "p": "螺旋回环", "q": "其他", "r": "放射星芒",
    "s": "方框", "t": "三角尖形", "u": "容器U形", "v": "开口V形",
    "w": "波浪流线", "x": "交叉", "y": "分叉翼形", "z": "阶梯锯齿",
}
STATE_LABELS = {
    "a": "偏置不对称", "b": "下重", "c": "闭合", "d": "向下",
    "e": "空心低填充", "f": "实心高填充", "g": "缺口开放", "h": "横向",
    "i": "内含", "j": "下垂钩", "k": "钩尾", "l": "向左", "m": "重复多部件",
    "n": "狭长", "o": "外包", "p": "成对", "q": "倾斜", "r": "向右",
    "s": "对称", "t": "上重", "u": "向上", "v": "纵向", "w": "宽展",
    "x": "穿过交叠", "y": "分叉", "z": "层叠错列",
}

# Stable cluster IDs come from deterministic balanced k-means. The labels were
# chosen after inspecting the nearest silhouettes in each cluster.
CLUSTER_MAIN = {
    0: "x",   # crossing, branching and compound marks
    1: "l",   # long horizontal lines and tools
    2: "y",   # winged and forked bird silhouettes
    3: "i",   # thin upright staffs and stems
    4: "n",   # rows, repeated marks and capsules
    5: "g",   # animals and organic bodies
    6: "z",   # stepped, sloped and zigzag outlines
    7: "r",   # radiating wings and spread silhouettes
    8: "m",   # elaborate multi-part signs
    9: "o",   # circles, rings and enclosed round signs
    10: "t",  # tapered, leaf-like and triangular forms
    11: "w",  # flowing curves, boats and waves
    12: "k",  # interlocked and repeated vertical parts
    13: "v",  # open and bent objects
    14: "f",  # compact human figures
    15: "u",  # vessels, containers and standards
    16: "d",  # simple isolated marks
    17: "j",  # hooked and bent strokes
    18: "p",  # looped, curled and spiral-like signs
    19: "a",  # angled horizontal strokes and tools
    20: "e",  # arched and elliptical silhouettes
    21: "b",  # dense block-like standards
    22: "s",  # frames, grids and regular arrays
    23: "h",  # branch-like human silhouettes
    24: "c",  # slim organic curves
    25: "q",  # isolated exceptional form
}

ITEM_PATTERN = re.compile(
    r"\n\s*([\U00013000-\U0001342F])\s*\n\s*([0-9A-F]{5})\s*\n\s*Egyptian Hieroglyph ([A-Za-z0-9]+)"
)


@dataclass(frozen=True)
class Metrics:
    width: int
    height: int
    density: float
    components: tuple[int, ...]
    largest_hole_ratio: float
    vertical_symmetry: float
    horizontal_symmetry: float
    center_x: float
    center_y: float
    diagonal_bias: float

    @property
    def aspect(self) -> float:
        return self.width / self.height


def connected_components(mask: list[list[bool]], foreground: bool) -> tuple[list[int], list[bool]]:
    height, width = len(mask), len(mask[0])
    seen: set[tuple[int, int]] = set()
    sizes: list[int] = []
    touches_edge: list[bool] = []
    for y in range(height):
        for x in range(width):
            if mask[y][x] != foreground or (x, y) in seen:
                continue
            stack = [(x, y)]
            seen.add((x, y))
            size = 0
            touches = False
            while stack:
                px, py = stack.pop()
                size += 1
                touches = touches or px in (0, width - 1) or py in (0, height - 1)
                for nx, ny in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                    if 0 <= nx < width and 0 <= ny < height and mask[ny][nx] == foreground and (nx, ny) not in seen:
                        seen.add((nx, ny))
                        stack.append((nx, ny))
            sizes.append(size)
            touches_edge.append(touches)
    return sizes, touches_edge


def gardiner_group(code: str) -> str:
    return "Aa" if code.startswith("Aa") else code[0]


def prefix_for(gardiner: str) -> str:
    group = gardiner_group(gardiner)
    matches = [prefix for prefix, groups in PREFIX_GROUPS.items() if group in groups]
    if len(matches) != 1:
        raise ValueError(f"Gardiner 组 {group} 没有唯一前缀")
    return matches[0]


def render(character: str, font: ImageFont.FreeTypeFont) -> tuple[Metrics, np.ndarray]:
    bbox = font.getbbox(character)
    width = max(1, bbox[2] - bbox[0]) + 8
    height = max(1, bbox[3] - bbox[1]) + 8
    image = Image.new("L", (width, height), 255)
    ImageDraw.Draw(image).text((4 - bbox[0], 4 - bbox[1]), character, font=font, fill=0)
    mask = [[image.getpixel((x, y)) < 160 for x in range(width)] for y in range(height)]
    total = width * height
    points = [(x, y) for y in range(height) for x in range(width) if mask[y][x]]
    if not points:
        raise ValueError(f"字体未渲染 U+{ord(character):04X}")
    ink_components, _ = connected_components(mask, True)
    background_components, touches = connected_components(mask, False)
    holes = [size for size, edge in zip(background_components, touches) if not edge]
    vertical_difference = sum(
        mask[y][x] != mask[y][width - 1 - x] for y in range(height) for x in range(width)
    )
    horizontal_difference = sum(
        mask[y][x] != mask[height - 1 - y][x] for y in range(height) for x in range(width)
    )
    xs = np.asarray([point[0] for point in points], dtype=np.float64)
    ys = np.asarray([point[1] for point in points], dtype=np.float64)
    normalized_x = xs / max(1, width - 1)
    normalized_y = ys / max(1, height - 1)
    diagonal_bias = abs(float(np.corrcoef(normalized_x, normalized_y)[0, 1])) if len(points) > 1 else 0.0
    if math.isnan(diagonal_bias):
        diagonal_bias = 0.0
    metrics = Metrics(
        width=width,
        height=height,
        density=len(points) / total,
        components=tuple(size for size in ink_components if size >= 4),
        largest_hole_ratio=max(holes, default=0) / total,
        vertical_symmetry=1 - vertical_difference / total,
        horizontal_symmetry=1 - horizontal_difference / total,
        center_x=float(normalized_x.mean()),
        center_y=float(normalized_y.mean()),
        diagonal_bias=diagonal_bias,
    )

    inverse = Image.eval(image, lambda pixel: 255 - pixel)
    crop_box = inverse.getbbox()
    cropped = inverse.crop(crop_box) if crop_box else inverse
    cropped.thumbnail((26, 26), Image.Resampling.LANCZOS)
    normalized = Image.new("L", (32, 32), 0)
    normalized.paste(cropped, ((32 - cropped.width) // 2, (32 - cropped.height) // 2))
    pixels = np.asarray(normalized, dtype=np.float64) / 255.0
    projections = np.concatenate((pixels.mean(axis=0), pixels.mean(axis=1)))
    vector = np.concatenate((pixels.reshape(-1) * 0.65, projections * 2.0))
    return metrics, vector


def balanced_assignment(vectors: np.ndarray, centroids: np.ndarray, capacity: int) -> tuple[np.ndarray, np.ndarray]:
    distances = ((vectors[:, None, :] - centroids[None, :, :]) ** 2).mean(axis=2)
    if len(centroids) == 1:
        if len(vectors) > capacity:
            raise ValueError("单一视觉聚类容量不足")
        return np.zeros(len(vectors), dtype=np.int64), distances
    preferences = np.argsort(distances, axis=1)
    nearest = np.take_along_axis(distances, preferences[:, :1], axis=1)[:, 0]
    second = np.take_along_axis(distances, preferences[:, 1:2], axis=1)[:, 0]
    confidence = second - nearest
    labels = np.full(len(vectors), -1, dtype=np.int64)
    counts = np.zeros(len(centroids), dtype=np.int64)
    for index in np.argsort(-confidence):
        for cluster in preferences[index]:
            if counts[cluster] < capacity:
                labels[index] = cluster
                counts[cluster] += 1
                break
    if np.any(labels < 0):
        raise ValueError("视觉聚类容量不足")
    return labels, distances


def balanced_kmeans(
    vectors: np.ndarray,
    cluster_count: int,
    capacity: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    standardized = vectors - vectors.mean(axis=0)
    deviations = standardized.std(axis=0)
    standardized /= np.where(deviations > 0.03, deviations, 1.0)
    random = np.random.default_rng(seed)
    centroids = [standardized[random.integers(len(standardized))]]
    for _ in range(1, cluster_count):
        stacked = np.stack(centroids)
        distances = ((standardized[:, None, :] - stacked[None, :, :]) ** 2).mean(axis=2).min(axis=1)
        centroids.append(standardized[random.choice(len(standardized), p=distances / distances.sum())])
    centroid_array = np.stack(centroids)
    for _ in range(30):
        labels, _ = balanced_assignment(standardized, centroid_array, capacity)
        centroid_array = np.stack([standardized[labels == cluster].mean(axis=0) for cluster in range(cluster_count)])
    labels, distances = balanced_assignment(standardized, centroid_array, capacity)
    return labels, distances, centroid_array


def clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def state_scores(metrics: Metrics, codepoint: int) -> dict[str, float]:
    aspect = metrics.aspect
    wide = clamp((aspect - 1.0) / 1.7)
    narrow = clamp((1.0 / max(aspect, 0.05) - 1.0) / 1.7)
    symmetry = max(metrics.vertical_symmetry, metrics.horizontal_symmetry)
    asymmetry = 1.0 - min(metrics.vertical_symmetry, metrics.horizontal_symmetry)
    hole = clamp(metrics.largest_hole_ratio * 5.0)
    component_count = len(metrics.components)
    repeated = clamp((component_count - 1) / 5.0)
    paired = 1.0 if component_count == 2 and min(metrics.components) / max(metrics.components) > 0.4 else 0.0
    left = clamp((0.5 - metrics.center_x) * 4.0)
    right = clamp((metrics.center_x - 0.5) * 4.0)
    top = clamp((0.5 - metrics.center_y) * 4.0)
    bottom = clamp((metrics.center_y - 0.5) * 4.0)
    scores = {
        "a": asymmetry,
        "b": bottom,
        "c": hole * 0.75 + symmetry * 0.25,
        "d": bottom * 0.7 + narrow * 0.3,
        "e": clamp((0.22 - metrics.density) * 5.0),
        "f": clamp((metrics.density - 0.18) * 4.0),
        "g": (1.0 - hole) * (0.55 * asymmetry + 0.45 * (1.0 - metrics.density)),
        "h": wide,
        "i": hole,
        "j": bottom * 0.55 + narrow * 0.25 + asymmetry * 0.20,
        "k": asymmetry * 0.55 + metrics.diagonal_bias * 0.45,
        "l": left,
        "m": repeated,
        "n": narrow,
        "o": hole * 0.55 + symmetry * 0.30 + (1.0 - metrics.density) * 0.15,
        "p": paired,
        "q": metrics.diagonal_bias,
        "r": right,
        "s": symmetry,
        "t": top,
        "u": top * 0.7 + narrow * 0.3,
        "v": narrow,
        "w": wide * 0.7 + (1.0 - metrics.density) * 0.3,
        "x": symmetry * 0.45 + metrics.density * 0.35 + metrics.diagonal_bias * 0.20,
        "y": repeated * 0.45 + asymmetry * 0.30 + metrics.diagonal_bias * 0.25,
        "z": repeated * 0.65 + symmetry * 0.20 + wide * 0.15,
    }
    # Stable microscopic tie-breaking prevents Unicode-order bands without
    # changing a visibly stronger state preference.
    for key in scores:
        scores[key] += ((codepoint * 131 + ord(key) * 17) % 997) / 997_000.0
    return scores


def assign_states(
    labels: np.ndarray,
    prefixes: list[str],
    vectors: np.ndarray,
    metrics: list[Metrics],
    codepoints: list[int],
) -> tuple[list[str], list[str], list[bool], list[int]]:
    selected = [""] * len(metrics)
    preferred = [""] * len(metrics)
    balanced = [False] * len(metrics)
    state_clusters = [-1] * len(metrics)
    visual_families = sorted({(prefixes[index], int(labels[index])) for index in range(len(labels))})
    for prefix, cluster in visual_families:
        indices = [
            index for index, label in enumerate(labels)
            if int(label) == cluster and prefixes[index] == prefix
        ]
        subgroup_count = math.ceil(len(indices) / 4)
        local_labels, _, _ = balanced_kmeans(
            vectors[np.asarray(indices)],
            cluster_count=subgroup_count,
            capacity=MAX_CANDIDATES,
            seed=20260809 + cluster + sum(ord(character) for character in prefix),
        )
        members = {
            subgroup: [indices[local] for local, label in enumerate(local_labels) if label == subgroup]
            for subgroup in range(subgroup_count)
        }
        aggregate_scores: dict[tuple[int, str], float] = {}
        subgroup_preferred: dict[int, str] = {}
        for subgroup, subgroup_members in members.items():
            score_maps = [state_scores(metrics[index], codepoints[index]) for index in subgroup_members]
            for state in STATE_LABELS:
                aggregate_scores[subgroup, state] = sum(scores[state] for scores in score_maps) / len(score_maps)
            subgroup_preferred[subgroup] = max(STATE_LABELS, key=lambda state: (aggregate_scores[subgroup, state], -ord(state)))

        assignments: dict[int, str] = {}
        used_states: set[str] = set()
        pairs = sorted(
            ((score, subgroup, state) for (subgroup, state), score in aggregate_scores.items()),
            key=lambda item: (-item[0], item[1], item[2]),
        )
        for _, subgroup, state in pairs:
            if subgroup not in assignments and state not in used_states:
                assignments[subgroup] = state
                used_states.add(state)
        if len(assignments) != subgroup_count:
            raise ValueError(f"{prefix} 主形聚类 {cluster} 无法获得唯一状态键")

        for subgroup, subgroup_members in members.items():
            state = assignments[subgroup]
            for index in subgroup_members:
                state_clusters[index] = subgroup
                preferred[index] = subgroup_preferred[subgroup]
                selected[index] = state
                balanced[index] = state != preferred[index]
    return selected, preferred, balanced, state_clusters


def parse_items() -> list[tuple[str, int, str]]:
    text = SOURCE.read_text(encoding="utf-8")
    items = [(match.group(1), int(match.group(2), 16), match.group(3)) for match in ITEM_PATTERN.finditer(text)]
    if len(items) != 1072 or len({character for character, _, _ in items}) != 1072:
        raise ValueError(f"预期 1,072 个唯一字符，实际得到 {len(items)} 个")
    if items[0][1] != 0x13000 or items[-1][1] != 0x1342F:
        raise ValueError("𓆟字块范围不是 U+13000..U+1342F")
    return items


def build(font_path: Path, font_size: int) -> list[dict[str, str]]:
    font = ImageFont.truetype(str(font_path), font_size)
    items = parse_items()
    prefixes = [prefix_for(gardiner) for _, _, gardiner in items]
    rendered = [render(character, font) for character, _, _ in items]
    metrics = [item[0] for item in rendered]
    vectors = np.stack([item[1] for item in rendered])
    labels, distances, _ = balanced_kmeans(
        vectors,
        cluster_count=CLUSTER_COUNT,
        capacity=CLUSTER_CAPACITY,
        seed=20260810,
    )
    state_keys, preferred_states, rebalanced, state_clusters = assign_states(
        labels, prefixes, vectors, metrics, [item[1] for item in items]
    )
    rows: list[dict[str, str]] = []
    for index, ((character, codepoint, gardiner), shape_metrics) in enumerate(zip(items, metrics)):
        cluster = int(labels[index])
        main = CLUSTER_MAIN[cluster]
        prefix = prefixes[index]
        state = state_keys[index]
        preferred_state = preferred_states[index]
        was_rebalanced = rebalanced[index]
        state_cluster = state_clusters[index]
        override_note = ""
        if codepoint in MANUAL_OVERRIDES:
            prefix, main, state, override_note = MANUAL_OVERRIDES[codepoint]
            preferred_state = state
            was_rebalanced = False
            state_cluster = -1
        nearest_distance = float(distances[index, cluster])
        rows.append({
            "char": character,
            "codepoint": f"U+{codepoint:05X}",
            "unicode_name": f"EGYPTIAN HIEROGLYPH {gardiner.upper()}",
            "gardiner": gardiner,
            "prefix": prefix,
            "visual_cluster": str(cluster),
            "main_key": main,
            "main_shape": MAIN_LABELS[main],
            "preferred_state_key": preferred_state,
            "state_cluster": str(state_cluster),
            "state_key": state,
            "state_shape": STATE_LABELS[state],
            "input_code": prefix + main + state,
            "classification_reason": (
                override_note if override_note else
                f"{prefix}:{PREFIX_LABELS[prefix]};视觉聚类C{cluster}→{main};"
                f"族内视觉组S{state_cluster};组状态首选{preferred_state};"
                + (f"唯一键平衡→{state}" if was_rebalanced else f"采用首选→{state}")
            ),
            "rebalanced": str(was_rebalanced).lower(),
            "cluster_distance": f"{nearest_distance:.6f}",
            "aspect": f"{shape_metrics.aspect:.4f}",
            "density": f"{shape_metrics.density:.4f}",
            "components": str(len(shape_metrics.components)),
            "largest_hole_ratio": f"{shape_metrics.largest_hole_ratio:.4f}",
            "vertical_symmetry": f"{shape_metrics.vertical_symmetry:.4f}",
            "horizontal_symmetry": f"{shape_metrics.horizontal_symmetry:.4f}",
            "source": SOURCE_RELATIVE,
            "status": "machine-initial-v3",
            "algorithm": ALGORITHM_VERSION,
        })
    code_counts = Counter(row["input_code"] for row in rows)
    if max(code_counts.values()) > MAX_CANDIDATES:
        raise ValueError(f"形码候选超过 {MAX_CANDIDATES}：{code_counts.most_common(1)[0]}")
    return rows


def write_tsv(rows: list[dict[str, str]]) -> None:
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_readme(rows: list[dict[str, str]], font_path: Path, font_size: int) -> None:
    by_code: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        by_code[row["input_code"]].append(row["char"])
    main_counts = Counter(row["main_key"] for row in rows)
    state_counts = Counter(row["state_key"] for row in rows)
    candidate_counts = Counter(len(characters) for characters in by_code.values())
    rebalanced_count = sum(row["rebalanced"] == "true" for row in rows)
    lines = [
        "---", "title: 𓆟字块编码说明", "project: 个人 Unicode 音型输入法",
        "prefixes: [jj, jn, jw, jx]", "count: 1072", f"algorithm: {ALGORITHM_VERSION}",
        "max_candidates_per_code: 5", "status: machine-initial-v3", "---", "",
        "# 𓆟字块编码说明", "",
        "[[𓆟字块]] 保持为原始清单；生成结果保存在 `𓆟字块-编码.tsv`。", "",
        "## v3 结果", "",
        f"- 字符：{len(rows):,} 个，范围 U+13000..U+1342F。",
        f"- 四个前缀合计实际使用 {len(by_code)} 个四码。",
        f"- 每个四码最多 {max(len(items) for items in by_code.values())} 个候选；达到“不超过5个”的硬约束。",
        f"- 候选数量分布：{', '.join(f'{size}个候选的码={count}' for size, count in sorted(candidate_counts.items()))}。",
        f"- 所属视觉小组因状态键唯一性采用非首选标签：{rebalanced_count} 个字符；TSV 中保留首选与调整记录。",
        "- `𓆟 = jj` 二码保留；形态四码按人工锚点固定为 `jjgh`。",
        f"- 轮廓字体：`{font_path}`，字号 {font_size}。", "",
        "## 分类办法", "",
        "1. 把每个字形等比例归一化为32×32轮廓，并加入横纵投影特征。",
        "2. Gardiner 大类只用于分配用户确认的 `jj / jn / jw / jx` 前缀，不直接决定后两键。",
        "3. 用固定随机种子的平衡聚类建立26个视觉主形族，每族不超过44个字符。",
        "4. 每个“前缀＋主形族”再按轮廓聚成平均4个、最多5个字符的小组；因此同码候选本身在视觉上接近。",
        "5. 依据小组的长宽比、填充度、内孔、部件数、对称、重心和倾斜度给26种状态评分，并在同一前缀主形族内为各小组分配不同状态键。", "",
        "这是项目的机器初分，不是 Unicode 或埃及学官方分类。`preferred_state_key` 与 `rebalanced` 可帮助检查容量平衡是否违背直觉。", "",
        "## 前缀分布", "",
        *[
            f"- `{prefix}` {PREFIX_LABELS[prefix]}：{sum(row['prefix'] == prefix for row in rows)} 个"
            for prefix in PREFIX_LABELS
        ],
        "", "## 使用的主形键", "",
        f"{', '.join(f'`{key}`={MAIN_LABELS[key]}（{count}）' for key, count in sorted(main_counts.items()))}", "",
        "## 使用的状态键", "",
        f"{', '.join(f'`{key}`={STATE_LABELS[key]}（{count}）' for key, count in sorted(state_counts.items()))}", "",
        "## 同码预览", "",
    ]
    for code, characters in sorted(by_code.items()):
        lines.append(f"- `{code}`（{len(characters)}）：{' '.join(characters)}")
    lines += [
        "", "## 人工修订", "",
        "优先检查 `rebalanced=true` 且视觉直觉不一致的行。人工确定后，应把修订写入生成器的覆盖表，再重新生成；直接修改 TSV 会在下次构建时被覆盖。",
    ]
    README.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--font", type=Path, default=Path(r"C:\Windows\Fonts\seguihis.ttf"))
    parser.add_argument("--font-size", type=int, default=96)
    args = parser.parse_args()
    rows = build(args.font, args.font_size)
    write_tsv(rows)
    write_readme(rows, args.font, args.font_size)
    counts = Counter(row["input_code"] for row in rows)
    prefix_counts = Counter(row["prefix"] for row in rows)
    print(f"生成 {len(rows)} 个四前缀字块条目：{dict(prefix_counts)}；使用 {len(counts)} 个四码，单码最多 {max(counts.values())} 个候选。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
