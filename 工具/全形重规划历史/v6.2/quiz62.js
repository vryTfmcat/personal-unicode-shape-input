(() => {
  const data = JSON.parse(document.querySelector("#quiz-data").textContent);
  const holder = document.querySelector("#questions");
  const output = document.querySelector("#output");
  const check = document.querySelector("#check");
  const progress = document.querySelector("#progress");
  const textarea = document.querySelector("#feedback");
  const state = data.questions.map(() => ({ b: "", c: "", d: "" }));
  const unknown = "?";
  function shuffle(values, seed) {
    const next = [...values];
    for (let i = next.length - 1; i > 0; i--) {
      seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
      const j = seed % (i + 1);
      [next[i], next[j]] = [next[j], next[i]];
    }
    return next;
  }
  function element(tag, text) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function count() {
    const completed = state.filter(r => r.b && r.c && r.d).length;
    progress.textContent = "已完成 "+completed+" / "+state.length+" 题";
    check.disabled = completed !== state.length;
    output.hidden = true;
    document.querySelectorAll(".answer").forEach(n => { n.hidden = true; });
  }
  function options(fieldset, question, layer, entries) {
    fieldset.querySelectorAll("label").forEach(n => n.remove());
    for (const [key, desc] of entries) {
      const label = element("label");
      const input = element("input");
      input.type = "radio";
      input.name = (question + 1)+"-"+layer;
      input.value = key;
      input.checked = state[question][layer] === key;
      input.addEventListener("change", () => {
        state[question][layer] = key;
        if (layer === "b") {
          state[question].c = "";
          const c = fieldset.parentElement.querySelector(".step-c");
          c.disabled = false;
          cOptions(c, question, key);
        }
        count();
      });
      label.append(input, element("span", desc));
      fieldset.append(label);
    }
  }
  function cOptions(field, i, family) {
    const q = data.questions[i];
    const list = data.cells[family] || [];
    const recommended = family === q.code[0] ? list.find(r => r[0] === q.code.slice(0, 2)) : undefined;
    const neighbors = shuffle(list.filter(r => !recommended || r[0] !== recommended[0]), 752 + i * 13);
    const subset = recommended ? [recommended, ...neighbors.slice(0, 3)] : neighbors.slice(0, 4);
    options(field, i, "c", [...shuffle(subset, 1260 + i * 7), [unknown, "都不像／难以判断"]]);
  }
  data.questions.forEach((q, i) => {
    const article = element("article");
    article.id = "q-"+(i+1);
    article.append(element("h2", "第 "+(i+1)+" 题"));
    const glyph = document.querySelector('template[data-num="'+(i+1)+'"]').content.cloneNode(true);
    article.append(glyph);
    const b = element("fieldset");
    const c = element("fieldset");
    const d = element("fieldset");
    c.className = "step-c";
    c.disabled = true;
    b.append(element("legend", "主体大类"));
    c.append(element("legend", "局部子形（先选主体大类）"));
    d.append(element("legend", "方位、对称或空实"));
    article.append(b, c, d);
    options(b, i, "b", [...q.b.map(k => [k, data.families[k]]), [unknown, "都不像／难以判断"]]);
    const grid = element("div");
    grid.className = "compass";
    grid.setAttribute("role", "group");
    grid.setAttribute("aria-label", "八方向和居中");
    const compass = [
      ["J", "↖ 左上"], ["W", "↑ 上"], ["K", "↗ 右上"],
      ["A", "← 左"], ["F", "· 均衡常规"], ["D", "→ 右"],
      ["N", "↙ 左下"], ["S", "↓ 下"], ["M", "↘ 右下"]
    ];
    options(grid, i, "d", compass);
    d.append(grid);
    const more = element("div");
    more.className = "attributes";
    more.setAttribute("role", "group");
    more.setAttribute("aria-label", "其他结构属性");
    options(more, i, "d", [..."HBCEPG LURTVXQI".replaceAll(" ","").split("").map(k => [k,data.attrs[k]]),
      [unknown, "都不像／难以判断"]]);
    d.append(more);
    const answer = element("p");
    answer.className = "answer";
    answer.hidden = true;
    article.append(answer);
    holder.append(article);
  });
  function describe(code) {
    return [data.families[code[0]], data.cells[code[0]].find(r => r[0] === code.slice(0,2))[1], data.attrs[code[2]]];
  }
  function choice(r) {
    return [data.families[r.b], (data.cells[r.b] || []).find(x => x[0] === r.c)?.[1], data.attrs[r.d]].map(v => v || "难以判断");
  }
  check.addEventListener("click", () => {
    if (state.some(r => !r.b || !r.c || !r.d)) return;
    const lines = [
      "| 题号 | 我的选择（主体／子形／属性） | 程序判定 | 差异 |",
      "| --- | --- | --- | --- |"
    ];
    state.forEach((r, i) => {
      const q = data.questions[i];
      const differences = [r.b !== q.code[0], r.c !== q.code.slice(0,2), r.d !== q.code[2]];
      const diff = differences.map((bad,j) => bad ? ["主体", "子形", "属性"][j] : "").filter(Boolean);
      const expected = describe(q.code);
      const own = choice(r);
      const answer = document.querySelector("#q-"+(i+1)+" .answer");
      answer.replaceChildren();
      answer.hidden = false;
      answer.append(element("strong", diff.length ? "有差异："+diff.join("、") : "三项一致"));
      for (let j=0;j<3;j++){
        const item = element("span", ["主体", "子形", "属性"][j]+"："+own[j]+" → "+expected[j]);
        if (differences[j]) item.className = "different";
        answer.append(item);
      }
      const safe = x => x.replaceAll("|", "\\|");
      lines.push("| "+(i+1)+" | "+safe(own.join("／"))+" | "+safe(expected.join("／"))+"（"+q.code+"） | "+(diff.join("、") || "一致")+" |");
    });
    textarea.value = lines.join("\n");
    output.hidden = false;
    output.scrollIntoView({ block: "start" });
  });
  document.querySelector("#copy").addEventListener("click", async () => {
    const status = document.querySelector("#copy-status");
    try {
      await navigator.clipboard.writeText(textarea.value);
      status.textContent = "已复制 Markdown";
    } catch {
      textarea.focus();
      textarea.select();
      status.textContent = document.execCommand("copy") ? "已复制 Markdown" : "文本已选中，按 Ctrl+C 复制";
    }
  });
  count();
})();


