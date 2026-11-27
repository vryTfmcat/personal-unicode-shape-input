(function (root) {
  'use strict';

  const ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');

  function createEngine(data, symbolMap) {
    if (!data || !symbolMap) {
      throw new Error('缺少 V7_DATA 或 V7_SYMBOL_MAP');
    }

    const rows = data.rows.map((r, idx) => ({
      id: idx,
      cp: r[0],
      cpInt: parseInt(r[0].slice(2), 16),
      ch: r[1],
      layer: r[2],
      bcda: r[3],
      abcd: r[3][3] + r[3].slice(0, 3),
      d3: r[4] || [],
      sheet: r[5],
      slot: r[6],
    }));

    const byLayer = { G: [], T: [], X: [] };
    const byBcda = Object.create(null);
    const byAbcd = Object.create(null);
    const byChar = Object.create(null);
    const byCp = Object.create(null);

    for (const r of rows) {
      if (byLayer[r.layer]) byLayer[r.layer].push(r);
      (byBcda[r.bcda] ||= []).push(r);
      (byAbcd[r.abcd] ||= []).push(r);
      (byChar[r.ch] ||= []).push(r);
      byCp[r.cp.toUpperCase()] = r;
    }

    function codeFor(row, order) {
      return order === 'ABCD' ? row.abcd : row.bcda;
    }

    function filterByPrefix(layer, order, seqStr) {
      const pool = byLayer[layer] || [];
      if (!seqStr) return pool;
      const out = [];
      for (let i = 0; i < pool.length; i++) {
        const r = pool[i];
        if (codeFor(r, order).startsWith(seqStr)) {
          out.push(r);
        }
      }
      return out;
    }

    function getBucketInfo(bcda) {
      const b = data.buckets[bcda];
      if (!b) return null;
      return { repChar: b[0], count: b[1], sheet: b[2], slot: b[3] };
    }

    function pickBestSpriteForGroup(list) {
      for (let i = 0; i < list.length; i++) {
        if (list[i].sheet >= 0 && list[i].slot >= 0) {
          return [list[i].sheet, list[i].slot];
        }
      }
      return [-1, -1];
    }

    function describeStage(layer, order, stepIdx) {
      if (layer === 'Z') return 'Z 层 · 远期汉字与谚文保留位';
      if (layer === 'T') {
        const names = ['第 1 位 B · 拟像大类（24 行）', '第 2 位 C · 视觉粗簇', '第 3 位 D · 视觉细桶', '第 4 位 A · 固定拟像桶 T'];
        return names[stepIdx] || names[3];
      }
      if (layer === 'X') {
        const names = ['第 1 位 B · 附标位置（上/下/中/宽）', '第 2 位 C · 视觉粗簇', '第 3 位 D · 视觉细桶', '第 4 位 A · 固定附标桶 X'];
        return names[stepIdx] || names[3];
      }
      if (order === 'ABCD') {
        const names = ['第 1 位 A · 视觉/功能细分桶', '第 2 位 B · 几何主族', '第 3 位 C · 结构细格', '第 4 位 D · 属性与方向'];
        return names[stepIdx] || names[3];
      }
      const names = ['第 1 位 B · 几何主族', '第 2 位 C · 结构细格', '第 3 位 D · 属性与方向', '第 4 位 A · 纯视觉同形桶'];
      return names[stepIdx] || names[3];
    }

    function getStepMeta(layer, order, seqArr, key) {
      const idx = seqArr.length;
      if (layer === 'Z') {
        return { sym: '汉', short: '远期汉字', full: 'Z 层远期汉字/谚文保留位', sprite: null };
      }

      if (layer === 'T') {
        if (idx === 0) {
          const m = symbolMap.T[key];
          return m ? { sym: m.sym, short: m.short, full: m.full, sprite: null } : { sym: key, short: key, full: key, sprite: null };
        }
        if (idx === 3) {
          return { sym: '☀', short: 'T 拟像', full: '第 4 位固定 T（拟像与图标）', sprite: null };
        }
        return { sym: key, short: idx === 1 ? 'C 视觉簇' : 'D 细桶', full: idx === 1 ? '拟像视觉粗簇' : '拟像视觉细桶', sprite: null };
      }

      if (layer === 'X') {
        if (idx === 0) {
          const m = symbolMap.X[key];
          return m ? { sym: m.sym, short: m.short, full: m.full, sprite: null } : { sym: key, short: key, full: key, sprite: null };
        }
        if (idx === 3) {
          return { sym: '◌́', short: 'X 附标', full: '第 4 位固定 X（附标与组合记号）', sprite: null };
        }
        return { sym: key, short: idx === 1 ? 'C 视觉簇' : 'D 细桶', full: idx === 1 ? '附标视觉粗簇' : '附标视觉细桶', sprite: null };
      }

      // 几何层 G
      if (order === 'BCDA') {
        if (idx === 0) {
          const m = symbolMap.B[key];
          return m ? { sym: m.sym, short: m.short, full: m.full, sprite: null } : { sym: key, short: key, full: key, sprite: null };
        }
        if (idx === 1) {
          const bc = seqArr[0] + key;
          const m = symbolMap.C[bc];
          return m ? { sym: m.sym, short: m.short, full: m.full, sprite: null } : { sym: key, short: bc, full: bc, sprite: null };
        }
        if (idx === 2) {
          const m = symbolMap.D[key];
          return m ? { sym: m.sym, short: m.short, full: m.full, sprite: null } : { sym: key, short: key, full: key, sprite: null };
        }
        const m = symbolMap.AOrder[key];
        return m ? { sym: m.sym, short: m.short, full: m.full, sprite: null } : { sym: key, short: 'A1桶', full: 'A1 视觉桶 ' + key, sprite: null };
      } else {
        // ABCD
        if (idx === 0) {
          const m = symbolMap.AOrder[key];
          return m ? { sym: m.sym, short: m.short, full: m.full, sprite: null } : { sym: key, short: 'A1桶', full: 'A1 视觉桶 ' + key, sprite: null };
        }
        if (idx === 1) {
          const m = symbolMap.B[key];
          return m ? { sym: m.sym, short: m.short, full: m.full, sprite: null } : { sym: key, short: key, full: key, sprite: null };
        }
        if (idx === 2) {
          const bc = seqArr[1] + key;
          const m = symbolMap.C[bc];
          return m ? { sym: m.sym, short: m.short, full: m.full, sprite: null } : { sym: key, short: bc, full: bc, sprite: null };
        }
        const m = symbolMap.D[key];
        return m ? { sym: m.sym, short: m.short, full: m.full, sprite: null } : { sym: key, short: key, full: key, sprite: null };
      }
    }

    function getStageKeys(state) {
      const { order, layer, seq } = state;
      const stepIdx = Math.min(seq.length, 3);
      const stageTitle = describeStage(layer, order, stepIdx);

      if (layer === 'Z') {
        return {
          stageIndex: 0,
          stageTitle,
          totalMatches: 0,
          keys: Object.fromEntries(ALPHABET.map((k) => [
            k,
            {
              key: k,
              enabled: false,
              count: 0,
              sym: k === 'Z' ? '汉' : '·',
              short: k === 'Z' ? '远期汉字' : '保留',
              full: k === 'Z' ? '远期汉字/谚文 Z 桶（本版暂未并入）' : '保留位',
              sprite: null,
              repChar: null,
              nextSeq: null,
            },
          ])),
        };
      }

      const seqStr = seq.join('');
      const currentPool = filterByPrefix(layer, order, seqStr);
      const isComplete = seq.length >= 4;

      // 按下一位字母分桶统计
      const groups = Object.create(null);
      if (!isComplete) {
        for (let i = 0; i < currentPool.length; i++) {
          const r = currentPool[i];
          const chKey = codeFor(r, order)[seq.length];
          (groups[chKey] ||= []).push(r);
        }
      }

      const resultKeys = Object.create(null);
      for (const k of ALPHABET) {
        if (isComplete) {
          const activeThis = seq[3] === k;
          const bcda = order === 'ABCD' ? (seqStr.slice(1) + seqStr[0]) : seqStr;
          const bi = activeThis ? getBucketInfo(bcda) : null;
          resultKeys[k] = {
            key: k,
            enabled: false,
            active: activeThis,
            count: activeThis ? currentPool.length : 0,
            sym: bi ? bi.repChar : '·',
            short: bi ? `代表 ${bi.repChar}` : '已满4位',
            full: bi ? `当前已选中四码 ${seqStr}（${currentPool.length} 字）` : '已输入 4 位编码，请选字或退格',
            sprite: bi && bi.sheet >= 0 ? [bi.sheet, bi.slot] : null,
            repChar: bi ? bi.repChar : null,
            nextSeq: null,
          };
          continue;
        }

        const list = groups[k] || [];
        const count = list.length;
        const meta = getStepMeta(layer, order, seq, k);
        let sym = meta.sym;
        let short = meta.short;
        let full = meta.full;
        let sprite = null;
        let repChar = null;

        if (count > 0) {
          const nextSeqStr = seqStr + k;
          if (seq.length === 3) {
            // 第 4 位直达具体四码桶：优先使用桶中心代表字形与雪碧图
            const bcda = order === 'ABCD' ? (nextSeqStr.slice(1) + nextSeqStr[0]) : nextSeqStr;
            const bi = getBucketInfo(bcda);
            if (bi) {
              repChar = bi.repChar;
              if (bi.sheet >= 0) sprite = [bi.sheet, bi.slot];
              if (layer !== 'G' || order === 'BCDA') {
                sym = bi.repChar;
                short = layer === 'G' ? `代表「${bi.repChar}」` : `${meta.short}·${bi.repChar}`;
                full = `${nextSeqStr}（代表字形「${bi.repChar}」，共 ${bi.count} 字）`;
              } else {
                // ABCD 顺序第 4 位为 D 属性，保留清晰属性符号与语义，同时在详情提示代表字形
                full = `${meta.full} → ${nextSeqStr}（代表「${bi.repChar}」，${bi.count} 字）`;
              }
            }
          } else if ((layer === 'T' || layer === 'X') && (seq.length === 1 || seq.length === 2)) {
            // T/X 层第 2/3 位为视觉聚类子簇，展示该簇代表字形
            const firstBcda = list[0].bcda;
            const bi = getBucketInfo(firstBcda);
            const sp = pickBestSpriteForGroup(list);
            const rep = bi ? bi.repChar : list[0].ch;
            repChar = rep;
            sym = rep;
            if (sp[0] >= 0) sprite = sp;
            short = rep === ' ' ? '无图' : `簇「${rep}」`;
            full = `${layer} 层视觉聚类（代表「${rep}」，含 ${count} 字）`;
          }
        }

        resultKeys[k] = {
          key: k,
          enabled: count > 0,
          active: false,
          count,
          sym,
          short,
          full,
          sprite,
          repChar,
          nextSeq: count > 0 ? seqStr + k : null,
        };
      }

      return {
        stageIndex: stepIdx,
        stageTitle,
        totalMatches: currentPool.length,
        keys: resultKeys,
      };
    }

    function getCandidates(state) {
      const { order, layer, seq, groupMode } = state;
      if (layer === 'Z' || seq.length === 0) {
        return { total: 0, mode: 'empty', items: [], exactBucket: null };
      }
      const seqStr = seq.join('');
      const matched = filterByPrefix(layer, order, seqStr);
      if (!matched.length) {
        return { total: 0, mode: 'empty', items: [], exactBucket: null };
      }

      // 如果已满 4 位，直接平铺桶内字符
      if (seq.length >= 4) {
        const bcda = order === 'ABCD' ? (seqStr.slice(1) + seqStr[0]) : seqStr;
        const bi = getBucketInfo(bcda);
        return {
          total: matched.length,
          mode: 'exact',
          exactBucket: {
            bcda,
            abcd: bcda[3] + bcda.slice(0, 3),
            repChar: bi ? bi.repChar : matched[0].ch,
            count: matched.length,
          },
          items: matched.map((r) => ({
            type: 'char',
            row: r,
            displayCode: codeFor(r, order),
          })),
        };
      }

      // 半码 1..3 位：支持 G8 按四码桶聚合代表字 或 平铺全部
      if (groupMode === 'grouped') {
        const bucketMap = Object.create(null);
        for (let i = 0; i < matched.length; i++) {
          const r = matched[i];
          const disp = codeFor(r, order);
          (bucketMap[disp] ||= []).push(r);
        }
        const groups = Object.entries(bucketMap).map(([dispCode, list]) => {
          const bcda = list[0].bcda;
          const bi = getBucketInfo(bcda);
          const repChar = bi ? bi.repChar : list[0].ch;
          const repRow = list.find((x) => x.ch === repChar) || list[0];
          return {
            type: 'bucket',
            displayCode: dispCode,
            remainingCode: dispCode.slice(seq.length),
            bcda,
            abcd: list[0].abcd,
            repChar,
            row: repRow,
            sheet: bi && bi.sheet >= 0 ? bi.sheet : repRow.sheet,
            slot: bi && bi.slot >= 0 ? bi.slot : repRow.slot,
            count: list.length,
          };
        });
        groups.sort((a, b) => b.count - a.count || a.displayCode.localeCompare(b.displayCode));
        return {
          total: matched.length,
          bucketCount: groups.length,
          mode: 'grouped',
          exactBucket: null,
          items: groups,
        };
      }

      return {
        total: matched.length,
        mode: 'flat',
        exactBucket: null,
        items: matched.map((r) => ({
          type: 'char',
          row: r,
          displayCode: codeFor(r, order),
        })),
      };
    }

    function explainCode(row) {
      const parts = [];
      const b = row.bcda[0], c = row.bcda[1], d = row.bcda[2], a = row.bcda[3];
      if (row.layer === 'G') {
        const bMeta = symbolMap.B[b];
        const cMeta = symbolMap.C[b + c];
        const dMeta = symbolMap.D[d];
        parts.push({ key: b, sym: bMeta?.sym || b, label: 'B 主族', desc: bMeta?.full || b });
        parts.push({ key: c, sym: cMeta?.sym || c, label: 'C 细格', desc: cMeta?.full || b + c });
        parts.push({ key: d, sym: dMeta?.sym || d, label: 'D 属性', desc: dMeta?.full || d });
        const bi = getBucketInfo(row.bcda);
        parts.push({ key: a, sym: bi?.repChar || a, label: 'A1 视觉桶', desc: `纯视觉聚簇（代表「${bi?.repChar || ''}」，${bi?.count || 0} 字）` });
      } else if (row.layer === 'T') {
        const tMeta = symbolMap.T[b];
        parts.push({ key: b, sym: tMeta?.sym || b, label: 'T1 大类', desc: tMeta?.full || b });
        parts.push({ key: c, sym: c, label: 'C 视觉簇', desc: '拟像特征聚簇' });
        parts.push({ key: d, sym: d, label: 'D 细桶', desc: '拟像视觉子桶' });
        parts.push({ key: 'T', sym: '☀', label: 'A 拟像层', desc: '固定 T（拟像与图标层）' });
      } else {
        const xMeta = symbolMap.X[b];
        parts.push({ key: b, sym: xMeta?.sym || b, label: 'X 位置', desc: xMeta?.full || b });
        parts.push({ key: c, sym: c, label: 'C 视觉簇', desc: '附标视觉粗簇' });
        parts.push({ key: d, sym: d, label: 'D 细桶', desc: '附标视觉细桶' });
        parts.push({ key: 'X', sym: '◌́', label: 'A 附标层', desc: '固定 X（附标与组合记号）' });
      }
      return parts;
    }

    function reverseSearch(query) {
      const q = (query || '').trim();
      if (!q) return [];
      const uq = q.toUpperCase();
      const hexNoPrefix = uq.startsWith('U+') ? uq.slice(2) : uq;
      const hits = [];
      const seen = new Set();

      const addHit = (r) => {
        if (!seen.has(r.id)) {
          seen.add(r.id);
          hits.push(r);
        }
      };

      // 1. 精确字符匹配（如果输入多字符，按字符拆开查）
      for (const ch of Array.from(q)) {
        if (byChar[ch]) {
          for (const r of byChar[ch]) {
            addHit(r);
            if (hits.length >= 60) return hits;
          }
        }
      }

      // 2. 码点或编码前缀匹配
      for (let i = 0; i < rows.length; i++) {
        const r = rows[i];
        const cpHex = r.cp.slice(2).toUpperCase();
        if (
          r.cp.toUpperCase() === uq ||
          cpHex === hexNoPrefix ||
          (/^[A-Z]{1,4}$/.test(uq) && (r.bcda.startsWith(uq) || r.abcd.startsWith(uq)))
        ) {
          addHit(r);
          if (hits.length >= 60) return hits;
        }
      }

      // 3. 中文键义关键词匹配（匹配 bNames / cells / dKeys / tLines / xLines 后取代表或前若干）
      if (hits.length === 0 && q.length >= 1) {
        const matchedBc = new Set();
        for (const [k, m] of Object.entries(symbolMap.C)) {
          if (m.short.includes(q) || m.full.includes(q)) matchedBc.add(k);
        }
        const matchedB = new Set();
        for (const [k, m] of Object.entries(symbolMap.B)) {
          if (m.short.includes(q) || m.full.includes(q)) matchedB.add(k);
        }
        const matchedT = new Set();
        for (const [k, m] of Object.entries(symbolMap.T)) {
          if (m.short.includes(q) || m.full.includes(q)) matchedT.add(k);
        }
        if (matchedBc.size || matchedB.size || matchedT.size) {
          for (let i = 0; i < rows.length; i++) {
            const r = rows[i];
            if (
              (r.layer === 'G' && (matchedBc.has(r.bcda.slice(0, 2)) || matchedB.has(r.bcda[0]))) ||
              (r.layer === 'T' && matchedT.has(r.bcda[0]))
            ) {
              addHit(r);
              if (hits.length >= 60) return hits;
            }
          }
        }
      }
      return hits;
    }

    return {
      totalRows: rows.length,
      counts: {
        G: byLayer.G.length,
        T: byLayer.T.length,
        X: byLayer.X.length,
      },
      getStageKeys,
      getCandidates,
      explainCode,
      reverseSearch,
      getBucketInfo,
      getStepMeta,
      getRowByChar: (ch) => byChar[ch]?.[0] || null,
    };
  }

  root.V7Engine = { createEngine, ALPHABET };
})(typeof window !== 'undefined' ? window : globalThis);
