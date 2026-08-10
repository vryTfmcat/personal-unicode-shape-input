---
title: Unicode 精选说明
project: 个人 Unicode 音型输入法
unicode_version: 17.0.0
---

# Unicode 精选说明

## 两层语料

1. `输出/unicode-17-全量精选.tsv`：159,345 个候选。保留 Unicode 17 中已编码的字母、组合附加符、数字、标点和符号。
2. `输出/unicode-17-v1-2000.tsv`：2,000 个首版试验字符。除 14 个已确认锚点外，要求可独立输入并被当前 Windows 字体覆盖。

总库不因当前电脑缺少字体而删除字符。`windows_font_covered=false` 只表示这台电脑目前没有在已安装字体的 cmap 中声明它；未来安装字体后可以改变。

## 排除边界

- 排除控制、格式、代理、私用区、未分配、空白与段落分隔类字符。
- 排除 `Default_Ignorable_Code_Point`，避免变体选择符、标签字符等在单独上屏时不可见或干扰文本。
- 保留 2,280 个组合附加符，`requires_base=true`，预览时以虚线圆 `◌` 承载。
- 不自动采用兼容归一化替换；码位身份原样保留。

## 四码容量

`26^4 = 456,976`，不是五十多万。即使从中预留一些短码前缀、控制码和实验空间，承载十几万字符仍有余量。两码 `jj` 若设为自动上屏，应把 `jj??` 的 676 个四码视为被该短码占用。

## 可复现来源

- `UnicodeData.txt`：[https://www.unicode.org/Public/17.0.0/ucd/UnicodeData.txt](https://www.unicode.org/Public/17.0.0/ucd/UnicodeData.txt)；SHA-256 `2e1efc1dcb59c575eedf5ccae60f95229f706ee6d031835247d843c11d96470c`
- `Blocks.txt`：[https://www.unicode.org/Public/17.0.0/ucd/Blocks.txt](https://www.unicode.org/Public/17.0.0/ucd/Blocks.txt)；SHA-256 `c0edefaf1a19771e830a82735472716af6bf3c3975f6c2a23ffbe2580fbbcb15`
- `Scripts.txt`：[https://www.unicode.org/Public/17.0.0/ucd/Scripts.txt](https://www.unicode.org/Public/17.0.0/ucd/Scripts.txt)；SHA-256 `9f5e50d3abaee7d6ce09480f325c706f485ae3240912527e651954d2d6b035bf`
- `DerivedAge.txt`：[https://www.unicode.org/Public/17.0.0/ucd/DerivedAge.txt](https://www.unicode.org/Public/17.0.0/ucd/DerivedAge.txt)；SHA-256 `f8ecdf768bdc210f201abd271d9bc587825618a86a7046a8146cc816393f1998`
- `DerivedCoreProperties.txt`：[https://www.unicode.org/Public/17.0.0/ucd/DerivedCoreProperties.txt](https://www.unicode.org/Public/17.0.0/ucd/DerivedCoreProperties.txt)；SHA-256 `24c7fed1195c482faaefd5c1e7eb821c5ee1fb6de07ecdbaa64b56a99da22c08`
- `emoji-data.txt`：[https://www.unicode.org/Public/17.0.0/ucd/emoji/emoji-data.txt](https://www.unicode.org/Public/17.0.0/ucd/emoji/emoji-data.txt)；SHA-256 `2cb2bb9455cda83e8481541ecf5b6dfda66a3bb89efa3fa7c5297eccf607b72b`
- `ReadMe.txt`：[https://www.unicode.org/Public/17.0.0/ucd/ReadMe.txt](https://www.unicode.org/Public/17.0.0/ucd/ReadMe.txt)；SHA-256 `9fe1a90bd32659d7953616283dc2bffaa165518aae9ace026040c42c559ba606`
- `Unicode-License.txt`：[https://www.unicode.org/license.txt](https://www.unicode.org/license.txt)；SHA-256 `e7a93b009565cfce55919a381437ac4db883e9da2126fa28b91d12732bc53d96`

## 总库类别统计

- `Ll`：2,283
- `Lm`：410
- `Lo`：141,058
- `Lt`：31
- `Lu`：1,886
- `Mc`：471
- `Me`：13
- `Mn`：1,796
- `Nd`：770
- `Nl`：239
- `No`：915
- `Pc`：10
- `Pd`：27
- `Pe`：77
- `Pf`：10
- `Pi`：12
- `Po`：641
- `Ps`：79
- `Sc`：64
- `Sk`：125
- `Sm`：960
- `So`：7,468
