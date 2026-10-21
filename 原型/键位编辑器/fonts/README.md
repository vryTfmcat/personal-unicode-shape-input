# Editor webfonts

Generated for the Unicode 17 editor data. Same-origin URL sources only; no local() dependencies. Native Noto/Gentium outlines precede Plangothic and existing fallback outlines. See manifest.json for exact coverage and source identities.

Plangothic webfont distribution: @free-fonts/plangothic 1.0.0, upstream https://github.com/Fitzgerald-Porthmouth-Koenigsegg/Plangothic_Project (SIL OFL). CSS declarations are restricted to actual cmap coverage. Bundled fonts are not copied from SYMBL.

Rebuild: python 工具/build_editor_fonts.py. FontTools and Brotli plus the documented local font assets are required.

Source preparation (only needed to rebuild): unpack the pinned npm tarball from `source-lock.json` into `工具/work/editor-fonts/plangothic/`, with `fonts/` directly beneath it. Verify the archive's SHA-512 against the recorded npm integrity. Retain the upstream `LICENSE-OFL.txt` there. Additional Egyptian/Math Noto TTF sources are downloaded from the official Google Fonts URLs in that lock into `工具/work/editor-fonts/`. The optional Tangut source is https://raw.githubusercontent.com/google/fonts/main/ofl/notoseriftangut/NotoSerifTangut-Regular.ttf. Existing project Noto sources remain in `数据/三模式/规则库/字体/`; universal fonts remain in the external font asset directory supplied via `--assets`.

Validation on 2026-10-15: all 159,345 editor identities mapped to non-.notdef glyphs in 761 referenced fonts (29,162,600 bytes); representative visible outlines were checked. This is coverage validation, not a promise of perfect shaping for arbitrary sequences. Include all fonts and licenses when copying the editor. No Windows proprietary fonts are embedded.

Outline quality update: all 80 Gurmukhi characters now use Noto Sans Gurmukhi, with curve-command regression checks. Additional native Noto and Egyptology sources replaced pixel fallbacks. outline-sources.json records downloaded source assets; only manifest.json lists active shipped faces. Run the incremental promotion tool with --exclude-family NotoSansCJKsc-Regular to avoid rebuilding the optional large CJK source.

## Storage update (2026-10-15)

Build source fonts and validation outputs now use the external `cache/font-sources/editor-fonts/` directory under the project engineering root. On ThinkBook this is `C:/Users/86137/Documents/Codex/codex资料/项目/个人Unicode音型输入法/`. Set `UNICODE_EXTERNAL_ROOT` to override that project root. The helper `工具/external_paths.py` preserves existing local source paths on devices that have not migrated. Shipped editor fonts and licenses remain in this directory.
