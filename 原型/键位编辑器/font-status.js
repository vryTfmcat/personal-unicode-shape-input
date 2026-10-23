"use strict";
// A failed font request must not silently turn rare characters into boxes.
if (document.fonts) {
  document.fonts.addEventListener("loadingerror", () => {
    const status = document.getElementById("fontLoadStatus");
    status.hidden = false;
    status.textContent = "部分字符字体加载失败，请刷新页面；若仍显示方框，请检查编辑器 fonts 文件夹是否完整。";
  });
}

// A small, generated list distinguishes a known coverage gap from a broken
// character. This changes the preview only; copy/export still use model.char.
fetch("fonts/missing-codepoints.json").then(response => {
  if (!response.ok) throw Error("Missing font coverage metadata");
  return response.json();
}).then(codepoints => {
  const missing = new Set(codepoints);
  if (!missing.size) return;
  function markMissingGlyphs() {
    document.querySelectorAll(".glyph,.inspector-glyph,.graph-node-symbol").forEach(element => {
      const chars = Array.from(element.textContent);
      if (chars.length !== 1 || !missing.has(chars[0].codePointAt(0))) return;
      const label = "U+" + chars[0].codePointAt(0).toString(16).toUpperCase().padStart(4,"0");
      element.textContent = label;
      element.classList.add("glyph-unavailable");
      element.title = "当前字体尚未覆盖此字符；复制和导出仍保留原始字符。";
      element.setAttribute("aria-label", label + "，暂缺预览字体");
    });
  }
  new MutationObserver(markMissingGlyphs).observe(document.body,{childList:true,subtree:true});
  markMissingGlyphs();
}).catch(() => {
  // Font rendering remains available if the optional coverage list is absent.
});
