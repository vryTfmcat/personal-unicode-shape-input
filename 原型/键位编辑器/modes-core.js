/* Shared, DOM-free codebook behavior. No Unicode normalization: identity is codepoint. */
(function (root) {
  "use strict";
  const ORDER = ["personal", "block", "shape", "chinese", "extended"];
  const clone = value => JSON.parse(JSON.stringify(value));
  function model(base, book, stage = null, review = null) {
    const reviewAssignments=new Map((review?.records||[]).map(r=>[r.cp,r]));
    if(review)Object.entries(review.collections).forEach(([bucket,cps])=>cps.forEach(cp=>{
      if(reviewAssignments.has(cp))throw Error('核对版身份重复');
      reviewAssignments.set(cp,{cp,bucket,codes:[],familyRoutes:[],collection:true});
    }));
    const stageAssignments = new Map(), reviewed = new Set(stage?.reviewed || []);
    if (stage) {
      if (stage.format !== "unicode-shape-stage-v1") throw Error("未知的阶段分桶格式");
      Object.entries(stage.buckets).forEach(([bucket, codes]) => codes.forEach((cp, rank) => {
        if (stageAssignments.has(cp)) throw Error("阶段分桶包含重复主归属");
        stageAssignments.set(cp, {bucket, rank, aliases: stage.aliases?.[cp] || [], reviewed: reviewed.has(cp)});
      }));
    }
    const blocks = base.blocks.map(b => ({...b, prefixes: b.prefixes.map(p => book.prefixOverrides[p] || p), rules: book.rules[b.id] || b.rules}));
    const characters = base.characters.map(c => {
      let blockCode = c.blockCode && {...c.blockCode, code: (book.prefixOverrides[c.blockCode.code.slice(0, 2)] || c.blockCode.code.slice(0, 2)) + c.blockCode.code.slice(2)};
      blockCode = book.blockOverrides[c.id] || blockCode;
      const metadata = book.metadata[c.id] || {};
      return {...c, blockCode, shape: book.shapeOverrides[c.id] || c.shape,
        stageShape: stage ? stageAssignments.get(c.char.codePointAt(0)) || null : null,
        shapeReview:reviewAssignments.get(c.char.codePointAt(0))||null,
        personal: book.personal[c.id] || [], metadata, favorite: !!metadata.favorite,
        note: metadata.note || "", code: blockCode?.code || "", pageId: c.blockId};
    });
    const byId = new Map(characters.map(c => [c.id, c]));
    const indexes = Object.fromEntries(ORDER.map(k => [k, new Map()]));
    function add(layer, code, c) {
      if (!code) return;
      if (!indexes[layer].has(code)) indexes[layer].set(code, []);
      if (!indexes[layer].get(code).includes(c)) indexes[layer].get(code).push(c);
    }
    characters.forEach(c => {
      c.personal.filter(a => a.enabled).forEach(a => add("personal", a.code, c));
      add("block", c.blockCode?.code, c);
      add("shape", c.shape?.coarse, c);
      (c.shape?.paths || []).filter(p => p.enabled && p.status === "reviewed").forEach(p => {
        [2,3,4].forEach(length => add("shape", p.code.slice(0,length), c));
      });
      c.chinese?.codes.forEach(a => add(c.chinese.extended ? "extended" : "chinese", a.code, c));
    });
    const stageGroups = new Map(), stageIndex = new Map();
    const reviewIndex=new Map(), reviewGroups=new Map();
    if(review){
      const byCp=new Map(characters.map(c=>[c.char.codePointAt(0),c]));
      for(const [cp,r] of reviewAssignments){
        const c=byCp.get(cp);if(!c)throw Error('核对版含未知码位');
        const codes=new Set([r.bucket]);
        (r.familyRoutes||[]).forEach(p=>codes.add(p.bucket+p.familyKey));
        (r.codes||[]).forEach(code=>{for(let n=1;n<=code.length;n++)codes.add(code.slice(0,n));});
        for(const code of codes){if(!reviewIndex.has(code))reviewIndex.set(code,[]);reviewIndex.get(code).push(c);}
        if(!reviewGroups.has(r.bucket))reviewGroups.set(r.bucket,[]);reviewGroups.get(r.bucket).push(c);
      }
    }
    if (stage) {
      Object.keys(stage.buckets).forEach(bucket => {
        const chars = characters.filter(c => c.stageShape?.bucket === bucket).sort((a,b) => a.stageShape.rank-b.stageShape.rank);
        stageGroups.set(bucket, chars);
        if ("abcdefghijklmnopqrstuvw".includes(bucket)) stageIndex.set(bucket, [...chars]);
      });
      characters.forEach(c => {
        if (!c.stageShape || !"abcdefghijklmnopqrstuvw".includes(c.stageShape.bucket)) return;
        c.stageShape.aliases.forEach(bucket => { const list = stageIndex.get(bucket); if (list && !list.includes(c)) list.push(c); });
      });
    }
    function query(code, prefs) {
      const result = new Map();
      ORDER.forEach(layer => {
        const enabled = layer === "chinese" ? prefs.chinese : layer === "extended" ? prefs.chinese && prefs.extended : prefs.modes.includes(layer);
        if (!enabled) return;
        const index = layer==='shape'&&prefs.shapeView==='review'&&review?reviewIndex:layer === "shape" && prefs.shapeView === "stage" && stage ? stageIndex : indexes[layer];
        (index.get(code) || []).forEach(c => {
          if (!result.has(c.id)) result.set(c.id, {character: c, sources: []});
          result.get(c.id).sources.push(layer);
        });
      });
      return [...result.values()];
    }
    return {characters, blocks, byId, indexes, query, stage, stageGroups, stageIndex,review,reviewIndex,reviewGroups};
  }
  function migrateLegacy(book, patch, marker, knownIds) {
    if (book.migrations[marker]) return false;
    if (patch.format !== "unicode-key-editor-patch-v1") throw Error("不是旧版键位草稿");
    Object.entries(patch.characters || {}).forEach(([id, changes]) => {
      if (!knownIds.has(id)) return;
      const aliases = book.personal[id] ||= [];
      if (/^[a-z]{2,4}$/.test(changes.code || "") && !aliases.some(a => a.code === changes.code))
        aliases.push({code: changes.code, enabled: false, note: changes.note || "", origin: "旧浏览器改码"});
      const meta = book.metadata[id] ||= {};
      if (typeof changes.favorite === "boolean" && meta.favorite === undefined) meta.favorite = changes.favorite;
      if (changes.note && !(meta.note || "").includes(changes.note)) meta.note = [meta.note, changes.note].filter(Boolean).join("\n");
    });
    (patch.commonOrder || []).forEach(id => { if (knownIds.has(id) && !book.commonOrder.includes(id)) book.commonOrder.push(id); });
    book.migrations[marker] = {legacyPages: patch.pages || {}, source: "旧浏览器草稿；原稿保留"};
    return true;
  }
  function nextPreset(modes) {
    const presets = [["block"], ["shape"], ["personal"], ["block", "shape", "personal"]];
    const index = presets.findIndex(p => p.length === modes.length && p.every(m => modes.includes(m)));
    return [...presets[index < 0 ? 3 : (index + 1) % 4]];
  }
  function shiftGesture() {
    let pending = false, used = false;
    return {
      down(event) {
        if (event.code === "ShiftLeft" && !event.ctrlKey && !event.altKey && !event.metaKey) {
          if (!event.repeat && !pending) { pending = true; used = false; }
        } else if (pending) used = true;
      },
      up(event) {
        if (event.code !== "ShiftLeft") return false;
        const toggle = pending && !used && !event.ctrlKey && !event.altKey && !event.metaKey;
        pending = false; used = false; return toggle;
      },
      reset() { pending = false; used = false; }
    };
  }
  const api = {model, migrateLegacy, nextPreset, shiftGesture, clone, ORDER};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.UnicodeModes = api;
})(typeof window !== "undefined" ? window : globalThis);
