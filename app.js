(() => {
  'use strict';

  const MODE = document.body.dataset.keyboardMode || 'text'; // 'text' | 'symbol'
  const engine = window.V7Engine.createEngine(window.V7_DATA, window.V7_SYMBOL_MAP);
  const symbolMap = window.V7_SYMBOL_MAP;

  const ROWS = [
    ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
    ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
    ['Z', 'X', 'C', 'V', 'B', 'N', 'M'],
  ];

  const state = {
    order: 'BCDA',
    layer: 'G',
    seq: [],
    groupMode: 'grouped', // 'grouped' | 'flat'
    expanded: false,
    english: false,
    selectedIdx: 0,
    menuOpen: false,
    theme: localStorage.getItem('v7_proto_theme') || 'dark',
    showAlpha: MODE === 'text',
    showHoverHint: true,
    guide: null, // { char, bcda, abcd, desc }
    inspectedRow: null,
    flatLimit: 180,
  };

  let lastStageData = null;
  let lastCandData = null;
  const pressedKeys = new Set();
  let rightShiftAlone = false;

  const $ = (sel) => document.querySelector(sel);

  function applyTheme() {
    document.documentElement.setAttribute('data-theme', state.theme);
    localStorage.setItem('v7_proto_theme', state.theme);
    const btn = $('#themeBtn');
    if (btn) btn.textContent = state.theme === 'dark' ? '☀ 浅色主题' : '🌙 深色主题';
  }

  function applyDisplayFlags() {
    document.body.classList.toggle('show-alpha', state.showAlpha);
    const alphaChk = $('#toggleAlpha');
    if (alphaChk) alphaChk.checked = state.showAlpha;
    const hintChk = $('#toggleHoverHint');
    if (hintChk) hintChk.checked = state.showHoverHint;
    const readout = $('#hoverReadout');
    if (readout) readout.style.display = state.showHoverHint ? 'flex' : 'none';
  }

  function spriteNode(sheet, slot, small = false) {
    const sp = document.createElement('span');
    sp.className = 'sp' + (small ? ' sp-sm' : '');
    if (sheet >= 0 && slot >= 0) {
      const r = Math.floor(slot / 50);
      const c = slot % 50;
      const num = String(sheet).padStart(2, '0');
      sp.style.backgroundImage = `url("data/v7-a1/sprites/s${num}.png")`;
      sp.style.backgroundSize = `${small ? 1200 : 1400}px auto`;
      const unit = small ? 24 : 28;
      sp.style.backgroundPosition = `${-c * unit}px ${-r * unit}px`;
    } else {
      sp.textContent = '∅';
      sp.style.display = 'inline-flex';
      sp.style.alignItems = 'center';
      sp.style.justifyContent = 'center';
    }
    return sp;
  }

  function formatDisplayChar(ch) {
    if (!ch) return '';
    if (ch === ' ') return '␣';
    if (/^\p{M}/u.test(ch)) return '◌' + ch;
    const cp = ch.codePointAt(0);
    if (cp < 0x20 || (cp >= 0x7f && cp <= 0x9f)) return `[${cp.toString(16).toUpperCase()}]`;
    return ch;
  }

  function formatCodepoints(text) {
    const cps = Array.from(text || '');
    if (!cps.length) return 'U+—';
    const last = cps[cps.length - 1];
    const cp = last.codePointAt(0);
    const hex = 'U+' + cp.toString(16).toUpperCase().padStart(4, '0');
    const utf16 = cp > 0xffff ? `UTF-16 代理对 (2 units)` : `BMP (1 unit)`;
    return `末字「${formatDisplayChar(last)}」 ${hex} · ${utf16}`;
  }

  function insertTextAtCaret(text) {
    const ta = $('#editorArea');
    const start = ta.selectionStart ?? ta.value.length;
    const end = ta.selectionEnd ?? ta.value.length;
    const val = ta.value;
    ta.value = val.slice(0, start) + text + val.slice(end);
    const pos = start + text.length;
    ta.selectionStart = ta.selectionEnd = pos;
    updateCaretInfo();
  }

  function deleteLastCodepointInEditor() {
    const ta = $('#editorArea');
    const start = ta.selectionStart ?? ta.value.length;
    const end = ta.selectionEnd ?? ta.value.length;
    const val = ta.value;
    if (start !== end) {
      ta.value = val.slice(0, start) + val.slice(end);
      ta.selectionStart = ta.selectionEnd = start;
    } else if (start > 0) {
      const before = Array.from(val.slice(0, start));
      before.pop();
      const head = before.join('');
      ta.value = head + val.slice(start);
      ta.selectionStart = ta.selectionEnd = head.length;
    }
    updateCaretInfo();
  }

  function updateCaretInfo() {
    const ta = $('#editorArea');
    const pos = ta.selectionStart ?? ta.value.length;
    const prefix = ta.value.slice(0, pos);
    const totalChars = Array.from(ta.value).length;
    $('#caretCode').textContent = formatCodepoints(prefix || ta.value);
    $('#caretCount').textContent = `总字符 ${totalChars}`;
  }

  function layerBadgeInfo() {
    if (state.english) return { cls: 'dot-en', text: 'EN · 英文直通' };
    if (state.layer === 'G') return { cls: 'dot-g', text: '形 · 几何 (29,092)' };
    if (state.layer === 'T') return { cls: 'dot-t', text: '拟 · 拟像 (4,366)' };
    if (state.layer === 'X') return { cls: 'dot-x', text: '附 · 附标 (2,269)' };
    return { cls: 'dot-z', text: '汉 · Z 保留位' };
  }

  function guideTargetCode() {
    if (!state.guide) return null;
    return state.order === 'ABCD' ? state.guide.abcd : state.guide.bcda;
  }

  function expectedGuideKey() {
    if (!state.guide || state.english || state.layer !== state.guide.layer) return null;
    const code = guideTargetCode();
    const typed = state.seq.join('');
    if (!code.startsWith(typed) || typed.length >= code.length) return null;
    return code[typed.length];
  }

  function renderStatusAndSlots(stageData) {
    const info = layerBadgeInfo();
    $('#modeChip').innerHTML = `<span class="dot ${info.cls}"></span><span>${info.text}</span>`;
    $('#orderChip').textContent = state.order;

    const slotsEl = $('#slots');
    slotsEl.innerHTML = '';
    for (let i = 0; i < 4; i++) {
      const div = document.createElement('button');
      div.type = 'button';
      div.className = 'slot';
      if (i < state.seq.length) div.classList.add('filled');
      if (i === state.seq.length && !state.english) div.classList.add('current');

      const k = state.seq[i];
      if (k) {
        const meta = engine.getStepMeta(state.layer, state.order, state.seq.slice(0, i), k);
        let symDisp = meta.sym;
        if (i === 3) {
          const seq4 = state.seq.join('');
          const bcda = state.order === 'ABCD' ? seq4.slice(1) + seq4[0] : seq4;
          const bi = engine.getBucketInfo(bcda);
          if (bi) symDisp = formatDisplayChar(bi.repChar);
        }
        div.innerHTML = `<span class="slot-k">${k}</span><span class="slot-sym">${symDisp}</span>${MODE === 'text' ? `<span class="slot-txt">${meta.short}</span>` : ''}`;
        div.title = `点击退回到第 ${i + 1} 位之前`;
        div.onclick = () => {
          state.seq = state.seq.slice(0, i);
          state.selectedIdx = 0;
          state.flatLimit = 180;
          renderAll();
        };
      } else {
        const posLabel = state.layer === 'G'
          ? (state.order === 'BCDA' ? ['B', 'C', 'D', 'A'][i] : ['A', 'B', 'C', 'D'][i])
          : ['B', 'C', 'D', 'A'][i];
        div.innerHTML = `<span class="slot-k" style="opacity:.45">${posLabel}</span><span class="slot-txt">待选</span>`;
        div.disabled = true;
      }
      slotsEl.appendChild(div);
    }

    $('#stageDesc').textContent = state.english ? '英文直通中（按 右Shift 或底部 [EN/Uni] 切回 Unicode）' : stageData.stageTitle;
    $('#matchTotal').textContent = state.english ? '' : `当前候选 ${stageData.totalMatches.toLocaleString()} 字`;
  }

  function renderCandidates(candData) {
    const strip = $('#candStrip');
    strip.classList.toggle('expanded', state.expanded);
    strip.innerHTML = '';

    const groupBtn = $('#toggleGroupBtn');
    const expandBtn = $('#expandBtn');
    groupBtn.classList.toggle('active', state.groupMode === 'grouped');
    groupBtn.textContent = state.groupMode === 'grouped' ? 'G8 代表字聚合' : '平铺全部字符';
    expandBtn.textContent = state.expanded ? '收起 (Ctrl+Shift+E)' : '全铺 (Ctrl+Shift+E)';

    if (state.english) {
      $('#candSummary').textContent = '英文直通模式：按键直接输入字母';
      return;
    }
    if (state.layer === 'Z') {
      $('#candSummary').textContent = 'Z 桶预留给远期汉字与谚文 IDS 结构键盘';
      return;
    }
    if (!state.seq.length) {
      $('#candSummary').textContent = state.guide
        ? `引导中：按提示键输入「${state.guide.char}」(${guideTargetCode()})`
        : '请按下键盘第 1 位开始查码，或从右侧选一个体验引导';
      return;
    }
    if (!candData.items.length) {
      $('#candSummary').textContent = `空结果：${state.seq.join('')} 无匹配，按 Backspace 退格`;
      return;
    }

    const items = candData.items;
    const maxCount = state.expanded
      ? Math.min(items.length, state.flatLimit)
      : Math.min(items.length, 9);

    if (state.selectedIdx >= maxCount) state.selectedIdx = Math.max(0, maxCount - 1);

    if (candData.mode === 'grouped') {
      $('#candSummary').textContent = `命中 ${candData.total} 字 → 聚合为 ${candData.bucketCount} 个全码代表位`;
    } else if (candData.mode === 'exact') {
      $('#candSummary').textContent = `四码 ${state.seq.join('')} · 共 ${candData.total} 字（回车上屏高亮字）`;
    } else {
      $('#candSummary').textContent = `平铺共 ${candData.total} 字${items.length > maxCount ? `（已显示 ${maxCount}）` : ''}`;
    }

    for (let i = 0; i < maxCount; i++) {
      const item = items[i];
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'cand-item' + (i === state.selectedIdx ? ' selected' : '');
      btn.dataset.idx = String(i);

      if (!state.expanded && i < 9) {
        const idxSpan = document.createElement('span');
        idxSpan.className = 'cand-idx';
        idxSpan.textContent = String(i + 1);
        btn.appendChild(idxSpan);
      }

      if (item.type === 'bucket') {
        const badge = document.createElement('span');
        badge.className = 'cand-badge';
        badge.textContent = `${item.count}字`;
        btn.appendChild(badge);

        const gw = document.createElement('div');
        gw.className = 'cand-glyph-wrap';
        if (item.sheet >= 0) gw.appendChild(spriteNode(item.sheet, item.slot, true));
        const ch = document.createElement('span');
        ch.className = 'cand-char';
        ch.textContent = formatDisplayChar(item.repChar);
        gw.appendChild(ch);
        btn.appendChild(gw);

        const sub = document.createElement('span');
        sub.className = 'cand-sub';
        sub.textContent = `+${item.remainingCode} (${item.displayCode})`;
        btn.appendChild(sub);

        btn.title = `代表字「${item.repChar}」· 点击展开全码桶 ${item.displayCode}（${item.count} 字）`;
        btn.onclick = () => {
          state.selectedIdx = i;
          commitSelectedCandidate();
        };
      } else {
        const r = item.row;
        const gw = document.createElement('div');
        gw.className = 'cand-glyph-wrap';
        if (r.sheet >= 0) gw.appendChild(spriteNode(r.sheet, r.slot, true));
        const ch = document.createElement('span');
        ch.className = 'cand-char';
        ch.textContent = formatDisplayChar(r.ch);
        gw.appendChild(ch);
        btn.appendChild(gw);

        const sub = document.createElement('span');
        sub.className = 'cand-sub';
        sub.textContent = r.cp.slice(2);
        btn.appendChild(sub);

        btn.title = `${r.ch} ${r.cp} · ${r.bcda}`;
        btn.onclick = () => {
          state.selectedIdx = i;
          state.inspectedRow = r;
          commitSelectedCandidate();
        };
      }
      btn.addEventListener('mouseenter', () => {
        const row = item.row;
        if (row) {
          state.inspectedRow = row;
          renderInspector();
        }
      });
      strip.appendChild(btn);
    }

    if (state.expanded && items.length > maxCount) {
      const more = document.createElement('button');
      more.type = 'button';
      more.className = 'cand-item';
      more.style.justifyContent = 'center';
      more.innerHTML = `<strong>+180</strong><span class="cand-sub">还有 ${items.length - maxCount} 项</span>`;
      more.onclick = () => {
        state.flatLimit += 180;
        renderCandidates(lastCandData);
      };
      strip.appendChild(more);
    }

    const selEl = strip.querySelector('.cand-item.selected');
    if (selEl) selEl.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  }

  function updateHoverReadout(keyInfo) {
    const el = $('#hoverReadout');
    if (!el || !state.showHoverHint) return;
    if (!keyInfo) {
      el.innerHTML = '<span>悬停或按下按键查看当前层含义</span><span>v7-A1 · 35,727</span>';
      return;
    }
    el.innerHTML = `<span><strong>${keyInfo.key}</strong> · ${keyInfo.sym} · ${keyInfo.full}</span><span>${keyInfo.count} 字</span>`;
  }

  function createLetterKey(letter, stageData, guideKey) {
    const info = stageData.keys[letter];
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'vk-key';
    btn.dataset.letter = letter;

    if (state.english) {
      btn.innerHTML = `<span class="vk-alpha">${letter}</span><span class="vk-sym">${letter}</span>`;
      btn.onclick = () => pressLetter(letter);
      return btn;
    }

    if (!info.enabled) btn.classList.add('disabled');
    if (pressedKeys.has('Key' + letter)) btn.classList.add('pressed');
    if (guideKey === letter && info.enabled) btn.classList.add('guided');

    const alpha = document.createElement('span');
    alpha.className = 'vk-alpha';
    alpha.textContent = letter;
    btn.appendChild(alpha);

    if (info.sprite && info.sprite[0] >= 0) {
      const sp = spriteNode(info.sprite[0], info.sprite[1], false);
      btn.appendChild(sp);
    } else {
      const sym = document.createElement('span');
      sym.className = 'vk-sym';
      sym.textContent = info.sym;
      btn.appendChild(sym);
    }

    const txt = document.createElement('span');
    txt.className = 'vk-txt';
    txt.textContent = info.short;
    btn.appendChild(txt);

    if (info.count > 0) {
      const cnt = document.createElement('span');
      cnt.className = 'vk-count';
      cnt.textContent = String(info.count);
      btn.appendChild(cnt);
    }

    btn.title = `${letter} · ${info.full} (${info.count} 字)`;
    btn.addEventListener('mouseenter', () => updateHoverReadout(info));
    btn.addEventListener('click', () => {
      if (info.enabled) {
        updateHoverReadout(info);
        pressLetter(letter);
      }
    });
    return btn;
  }

  function createFnKey(label, sub, className, onClick) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'vk-key fn-key ' + (className || '');
    btn.innerHTML = `<span class="vk-txt">${label}</span>${sub ? `<span style="font-size:10px;opacity:.75">${sub}</span>` : ''}`;
    btn.onclick = onClick;
    return btn;
  }

  function renderKeyboard(stageData) {
    const board = $('#vkBoard');
    board.innerHTML = '';
    const guideKey = expectedGuideKey();

    // Row 0: Q..P
    const r0 = document.createElement('div');
    r0.className = 'vk-row vk-row-0';
    for (const l of ROWS[0]) r0.appendChild(createLetterKey(l, stageData, guideKey));
    board.appendChild(r0);

    // Row 1: spacer + A..L + spacer
    const r1 = document.createElement('div');
    r1.className = 'vk-row vk-row-1';
    r1.appendChild(Object.assign(document.createElement('div'), { className: 'vk-spacer' }));
    for (const l of ROWS[1]) r1.appendChild(createLetterKey(l, stageData, guideKey));
    r1.appendChild(Object.assign(document.createElement('div'), { className: 'vk-spacer' }));
    board.appendChild(r1);

    // Row 2: 层切换 + Z..M + 退格
    const r2 = document.createElement('div');
    r2.className = 'vk-row vk-row-2';
    r2.appendChild(createFnKey(
      state.layer === 'G' ? '形' : state.layer === 'T' ? '拟' : state.layer === 'X' ? '附' : 'Z',
      '切层',
      '',
      cycleLayer
    ));
    for (const l of ROWS[2]) r2.appendChild(createLetterKey(l, stageData, guideKey));
    r2.appendChild(createFnKey('⌫', '退格', '', handleBackspace));
    board.appendChild(r2);

    // Row 3: 菜单 / EN / 空格选字 / 顺序 / 回车上屏
    const r3 = document.createElement('div');
    r3.className = 'vk-row vk-row-3';
    r3.appendChild(createFnKey('菜单', 'Ctrl+`', state.menuOpen ? 'active-fn' : '', toggleMenu));
    r3.appendChild(createFnKey(state.english ? '中/Uni' : 'EN', '右Shift', state.english ? 'active-fn' : '', toggleEnglish));
    r3.appendChild(createFnKey('空格 · 确认高亮', state.seq.length ? 'Space' : '输入空格', '', handleSpaceOrCommit));
    r3.appendChild(createFnKey(state.order, '切序', '', toggleOrder));
    r3.appendChild(createFnKey('↵', '上屏', '', handleEnterOrNewline));
    board.appendChild(r3);
  }

  function renderInspector() {
    const box = $('#inspectBox');
    let row = state.inspectedRow;
    if (!row && lastCandData?.items?.length) {
      row = lastCandData.items[state.selectedIdx]?.row || lastCandData.items[0]?.row;
    }
    if (!row) {
      box.innerHTML = '<div class="muted" style="grid-column:1/-1">输入编码或点击任意候选后，在这里查看码点、结构拆解与 D3 次路径。</div>';
      return;
    }
    const parts = engine.explainCode(row);
    const preview = document.createElement('div');
    preview.className = 'inspect-preview';
    if (row.sheet >= 0) preview.appendChild(spriteNode(row.sheet, row.slot, false));
    const chEl = document.createElement('div');
    chEl.className = 'inspect-char';
    chEl.textContent = formatDisplayChar(row.ch);
    preview.appendChild(chEl);

    const detail = document.createElement('div');
    detail.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap">
        <strong>${row.cp} · 层 ${row.layer}</strong>
        <span style="font-family:var(--font-mono);color:var(--accent)">BCDA: ${row.bcda} / ABCD: ${row.abcd}</span>
      </div>
      ${row.d3?.length ? `<div class="muted" style="font-size:12px;margin-top:3px">D3 次路径：${row.d3.join(' 、 ')}</div>` : ''}
      <div class="parts-row">
        ${parts.map((p) => `
          <div class="part-pill">
            <div class="p-top"><span>${p.key} · ${p.sym}</span><span>${p.label}</span></div>
            <div class="muted" style="font-size:11px;margin-top:2px">${p.desc}</div>
          </div>
        `).join('')}
      </div>
      <div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap">
        <button type="button" id="inspectCommitBtn" class="primary">上屏此字符</button>
        <button type="button" id="inspectReplayBtn">用虚拟键盘演示打法</button>
      </div>
    `;
    box.innerHTML = '';
    box.append(preview, detail);
    $('#inspectCommitBtn').onclick = () => insertTextAtCaret(row.ch);
    $('#inspectReplayBtn').onclick = () => startGuide({
      layer: row.layer,
      char: row.ch,
      cp: row.cp,
      bcda: row.bcda,
      abcd: row.abcd,
      desc: `演示「${formatDisplayChar(row.ch)}」(${row.bcda})`,
    });
  }

  function renderGuides() {
    const list = $('#guideList');
    if (!list) return;
    list.innerHTML = '';
    for (const g of symbolMap.guides) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'guide-btn';
      btn.innerHTML = `
        <span class="guide-ch">${formatDisplayChar(g.char)}</span>
        <span class="guide-meta">
          <strong>${g.bcda}</strong> · ${g.cp}<br>
          <span class="muted">${g.desc}</span>
        </span>
      `;
      btn.onclick = () => startGuide(g);
      list.appendChild(btn);
    }
  }

  function runReverseSearch() {
    const q = $('#searchInput').value.trim();
    const out = $('#searchOut');
    if (!q) {
      out.innerHTML = '<div class="muted">支持输入字符（如 ○、↗、🐱）、码点（U+25CB）、四码前缀（如 PBK）或中文关键词（如 箭头、双孔）。</div>';
      return;
    }
    const hits = engine.reverseSearch(q);
    if (!hits.length) {
      out.innerHTML = '<div class="muted">未找到匹配结果。</div>';
      return;
    }
    out.innerHTML = '';
    for (const r of hits) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'sr-card';
      if (r.sheet >= 0) btn.appendChild(spriteNode(r.sheet, r.slot, true));
      const info = document.createElement('div');
      info.innerHTML = `<strong>${formatDisplayChar(r.ch)}</strong> <span class="muted" style="font-size:11px">${r.cp}</span><br><span style="font-family:var(--font-mono);font-size:11px;color:var(--accent)">${r.bcda}</span> <span class="muted" style="font-size:11px">(${r.layer})</span>`;
      btn.appendChild(info);
      btn.onclick = () => {
        state.inspectedRow = r;
        renderInspector();
        startGuide({
          layer: r.layer,
          char: r.ch,
          cp: r.cp,
          bcda: r.bcda,
          abcd: r.abcd,
          desc: `反查引导「${formatDisplayChar(r.ch)}」(${r.bcda})`,
        });
      };
      out.appendChild(btn);
    }
  }

  function renderModeMenu() {
    const menu = $('#modeMenu');
    menu.hidden = !state.menuOpen;
    if (!state.menuOpen) return;
    menu.querySelectorAll('[data-layer]').forEach((b) => b.classList.toggle('active', b.dataset.layer === state.layer));
    menu.querySelectorAll('[data-order]').forEach((b) => b.classList.toggle('active', b.dataset.order === state.order));
    menu.querySelectorAll('[data-group]').forEach((b) => b.classList.toggle('active', b.dataset.group === state.groupMode));
  }

  function renderAll() {
    lastStageData = engine.getStageKeys(state);
    lastCandData = engine.getCandidates(state);
    renderStatusAndSlots(lastStageData);
    renderCandidates(lastCandData);
    renderKeyboard(lastStageData);
    renderInspector();
    renderModeMenu();
  }

  // 交互动作
  function startGuide(g) {
    state.english = false;
    state.layer = g.layer;
    state.seq = [];
    state.selectedIdx = 0;
    state.expanded = false;
    state.guide = g;
    state.menuOpen = false;
    const row = engine.getRowByChar(g.char);
    if (row) state.inspectedRow = row;
    renderAll();
  }

  function pressLetter(letter) {
    if (state.english) {
      insertTextAtCaret(letter.toLowerCase());
      return;
    }
    if (state.layer === 'Z') return;
    const info = lastStageData?.keys?.[letter];
    if (!info || !info.enabled) return;
    state.seq.push(letter);
    state.selectedIdx = 0;
    state.flatLimit = 180;
    // 如果新状态只剩唯一全码桶且只有 1 个字，仍留在当前让用户确认，不抢自动上屏（遵守设计约定）
    renderAll();
  }

  function commitSelectedCandidate() {
    if (!lastCandData || !lastCandData.items.length) return false;
    const item = lastCandData.items[state.selectedIdx] || lastCandData.items[0];
    if (!item) return false;
    if (item.type === 'bucket') {
      // 点击或确认 G8 代表位：直接补全四码进入该桶，展开全桶精准选字
      state.seq = item.displayCode.split('');
      state.selectedIdx = 0;
      state.expanded = false;
      renderAll();
      return true;
    }
    insertTextAtCaret(item.row.ch);
    state.inspectedRow = item.row;
    state.seq = [];
    state.selectedIdx = 0;
    state.expanded = false;
    state.guide = null;
    renderAll();
    return true;
  }

  function handleBackspace() {
    if (!state.english && state.seq.length > 0) {
      state.seq.pop();
      state.selectedIdx = 0;
      state.flatLimit = 180;
      renderAll();
    } else {
      deleteLastCodepointInEditor();
    }
  }

  function handleSpaceOrCommit() {
    if (!state.english && state.seq.length > 0 && lastCandData?.items?.length) {
      commitSelectedCandidate();
    } else {
      insertTextAtCaret(' ');
    }
  }

  function handleEnterOrNewline() {
    if (!state.english && state.seq.length > 0 && lastCandData?.items?.length) {
      commitSelectedCandidate();
    } else {
      insertTextAtCaret('\n');
    }
  }

  function cycleLayer() {
    const orderLayers = ['G', 'T', 'X', 'Z'];
    state.english = false;
    state.layer = orderLayers[(orderLayers.indexOf(state.layer) + 1) % orderLayers.length];
    state.seq = [];
    state.selectedIdx = 0;
    state.expanded = false;
    renderAll();
  }

  function toggleOrder() {
    state.order = state.order === 'BCDA' ? 'ABCD' : 'BCDA';
    state.seq = [];
    state.selectedIdx = 0;
    renderAll();
  }

  function toggleEnglish() {
    if (!state.english && state.seq.length) {
      insertTextAtCaret(state.seq.join('').toLowerCase());
      state.seq = [];
    }
    state.english = !state.english;
    state.selectedIdx = 0;
    renderAll();
  }

  function toggleMenu() {
    state.menuOpen = !state.menuOpen;
    renderModeMenu();
  }

  function toggleExpand() {
    if (state.english || !lastCandData?.items?.length) return;
    state.expanded = !state.expanded;
    if (!state.expanded && state.selectedIdx >= 9) state.selectedIdx = 0;
    renderCandidates(lastCandData);
  }

  function moveSelection(delta) {
    const maxVisible = state.expanded
      ? Math.min(lastCandData?.items?.length || 0, state.flatLimit)
      : Math.min(lastCandData?.items?.length || 0, 9);
    if (!maxVisible) return;
    state.selectedIdx = (state.selectedIdx + delta + maxVisible) % maxVisible;
    renderCandidates(lastCandData);
    renderInspector();
  }

  function moveVertical(dir) {
    const strip = $('#candStrip');
    const maxVisible = state.expanded
      ? Math.min(lastCandData?.items?.length || 0, state.flatLimit)
      : Math.min(lastCandData?.items?.length || 0, 9);
    if (!maxVisible) return;
    const cols = Math.max(1, Math.floor((strip.clientWidth + 6) / 78));
    const next = state.selectedIdx + dir * cols;
    if (next >= 0 && next < maxVisible) {
      state.selectedIdx = next;
    } else if (next >= maxVisible) {
      state.selectedIdx = maxVisible - 1;
    } else {
      state.selectedIdx = 0;
    }
    renderCandidates(lastCandData);
    renderInspector();
  }

  // 实体键盘全局绑定
  window.addEventListener('keydown', (e) => {
    if (e.code === 'ShiftRight' && !e.ctrlKey && !e.altKey && !e.metaKey && !e.repeat) {
      rightShiftAlone = true;
    } else if (e.code !== 'ShiftRight') {
      rightShiftAlone = false;
    }

    if (e.code) {
      pressedKeys.add(e.code);
      document.querySelectorAll('.vk-key[data-letter]').forEach((el) => {
        el.classList.toggle('pressed', pressedKeys.has('Key' + el.dataset.letter));
      });
    }

    // 焦点在反查框内时不拦截输入
    if (document.activeElement && document.activeElement.id === 'searchInput') {
      if (e.key === 'Escape') document.activeElement.blur();
      return;
    }

    // Ctrl + ` 打开/关闭模式菜单
    if (e.ctrlKey && !e.shiftKey && !e.altKey && e.code === 'Backquote') {
      e.preventDefault();
      toggleMenu();
      return;
    }

    // Ctrl + Shift + E 展开/收起候选
    if (e.ctrlKey && e.shiftKey && !e.altKey && e.code === 'KeyE') {
      e.preventDefault();
      toggleExpand();
      return;
    }

    // 菜单打开时接管 1-4 / U / I / Esc
    if (state.menuOpen) {
      if (e.key === 'Escape') { e.preventDefault(); state.menuOpen = false; renderModeMenu(); return; }
      if (['1', '2', '3', '4'].includes(e.key)) {
        e.preventDefault();
        const map = { '1': 'G', '2': 'T', '3': 'X', '4': 'Z' };
        state.english = false;
        state.layer = map[e.key];
        state.seq = [];
        state.selectedIdx = 0;
        state.menuOpen = false;
        renderAll();
        return;
      }
      if (e.code === 'KeyU') { e.preventDefault(); state.menuOpen = false; renderModeMenu(); $('#searchInput').focus(); return; }
      if (e.code === 'KeyI') { e.preventDefault(); state.menuOpen = false; renderModeMenu(); $('#inspectBox').scrollIntoView({ behavior: 'smooth' }); return; }
    }

    if (e.ctrlKey || e.altKey || e.metaKey) return;

    // 字母键 A-Z
    if (/^Key[A-Z]$/.test(e.code)) {
      const letter = e.code.slice(3);
      e.preventDefault();
      if (state.english) {
        insertTextAtCaret(e.shiftKey ? letter : letter.toLowerCase());
      } else {
        pressLetter(letter);
      }
      return;
    }

    // 收起态数字 1-9 直选
    if (!state.english && state.seq.length > 0 && !state.expanded && /^[1-9]$/.test(e.key)) {
      const idx = Number(e.key) - 1;
      if (lastCandData && idx < Math.min(9, lastCandData.items.length)) {
        e.preventDefault();
        state.selectedIdx = idx;
        commitSelectedCandidate();
        return;
      }
    }

    if (e.key === 'Backspace') {
      if (document.activeElement?.id !== 'editorArea' || (!state.english && state.seq.length > 0)) {
        e.preventDefault();
        handleBackspace();
      }
      return;
    }

    if (e.key === 'Escape') {
      if (state.expanded) { e.preventDefault(); state.expanded = false; renderCandidates(lastCandData); return; }
      if (state.seq.length > 0) { e.preventDefault(); state.seq = []; state.selectedIdx = 0; state.guide = null; renderAll(); return; }
    }

    if (!state.english && state.seq.length > 0 && lastCandData?.items?.length) {
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        commitSelectedCandidate();
        return;
      }
      if (e.key === 'ArrowRight') { e.preventDefault(); moveSelection(1); return; }
      if (e.key === 'ArrowLeft') { e.preventDefault(); moveSelection(-1); return; }
      if (e.key === 'ArrowDown') { e.preventDefault(); moveVertical(1); return; }
      if (e.key === 'ArrowUp') { e.preventDefault(); moveVertical(-1); return; }
      if (e.key === 'PageDown') { e.preventDefault(); moveSelection(9); return; }
      if (e.key === 'PageUp') { e.preventDefault(); moveSelection(-9); return; }
    }
  });

  window.addEventListener('keyup', (e) => {
    if (e.code === 'ShiftRight' && rightShiftAlone) {
      rightShiftAlone = false;
      toggleEnglish();
    }
    if (e.code) {
      pressedKeys.delete(e.code);
      document.querySelectorAll('.vk-key[data-letter]').forEach((el) => {
        el.classList.toggle('pressed', pressedKeys.has('Key' + el.dataset.letter));
      });
    }
  });

  window.addEventListener('blur', () => {
    pressedKeys.clear();
    rightShiftAlone = false;
    document.querySelectorAll('.vk-key.pressed').forEach((el) => el.classList.remove('pressed'));
  });

  // 绑定界面按钮
  $('#themeBtn').onclick = () => {
    state.theme = state.theme === 'dark' ? 'light' : 'dark';
    applyTheme();
  };
  $('#toggleAlpha').onchange = (e) => { state.showAlpha = e.target.checked; applyDisplayFlags(); };
  $('#toggleHoverHint').onchange = (e) => { state.showHoverHint = e.target.checked; applyDisplayFlags(); };
  $('#toggleGroupBtn').onclick = () => {
    state.groupMode = state.groupMode === 'grouped' ? 'flat' : 'grouped';
    state.selectedIdx = 0;
    renderAll();
  };
  $('#expandBtn').onclick = toggleExpand;
  $('#resetSeqBtn').onclick = () => { state.seq = []; state.selectedIdx = 0; state.guide = null; renderAll(); };
  $('#copyTextBtn').onclick = async () => {
    const val = $('#editorArea').value;
    try { await navigator.clipboard.writeText(val); } catch {}
  };
  $('#clearTextBtn').onclick = () => { $('#editorArea').value = ''; updateCaretInfo(); };
  $('#editorArea').addEventListener('input', updateCaretInfo);
  $('#editorArea').addEventListener('click', updateCaretInfo);
  $('#editorArea').addEventListener('keyup', updateCaretInfo);
  $('#searchInput').addEventListener('input', runReverseSearch);
  $('#closeMenuBtn').onclick = () => { state.menuOpen = false; renderModeMenu(); };

  $('#modeMenu').addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    if (btn.dataset.layer) {
      state.english = false;
      state.layer = btn.dataset.layer;
      state.seq = [];
      state.selectedIdx = 0;
      state.menuOpen = false;
      renderAll();
    } else if (btn.dataset.order) {
      state.order = btn.dataset.order;
      state.seq = [];
      state.selectedIdx = 0;
      state.menuOpen = false;
      renderAll();
    } else if (btn.dataset.group) {
      state.groupMode = btn.dataset.group;
      state.selectedIdx = 0;
      state.menuOpen = false;
      renderAll();
    }
  });

  applyTheme();
  applyDisplayFlags();
  renderGuides();
  runReverseSearch();
  updateCaretInfo();
  renderAll();
})();
