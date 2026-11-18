/* CVES motion runtime (docs/MOTION.md). Our own, no third-party code.
 *
 * Contract: a piece is driven ONLY by window.__seek(t), t = seconds since the piece starts. Nothing runs on the wall
 * clock: no requestAnimationFrame timing, no CSS transitions or animations, no Date / Math.random. The same t always
 * gives the same pixels.
 *
 * A piece calls CVES.piece({setup(P, ctx), seek(t, P, ctx), cues(P, ctx)}):
 *   setup  builds the DOM once (fonts are loaded, the viewport is final: measure here);
 *   seek   sets every animated property for time t (pure: never depends on the previous call);
 *   cues   optional: calls CVES.cue(t, sfx, gain_db, kw) for each sound event (piece-relative seconds).
 * P is the params (times named `at` / `*_at` are already piece-relative), ctx is {w, h, fps, dur, exit, u, motion}.
 */
(function () {
  'use strict';
  const C = (window.CVES = window.CVES || {});
  const BOOT = window.__CVES_BOOT || {};
  const M = Object.assign({ ease: 'expo', energy: 0.5, overshoot: 1.6, blur_on_fast: true, blur_max_u: 1.6,
                            exit_s: 0.32, entry_s: 0.28, stagger_s: 0.12, shutter: 0.5 }, BOOT.motion || {});
  C.motion = M;

  // ------------------------------------------------------------------ maths
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const lerp = (a, b, p) => a + (b - a) * p;
  C.clamp = clamp; C.lerp = lerp;
  C.prog = (t, t0, d) => (d > 0 ? clamp((t - t0) / d) : (t >= t0 ? 1 : 0));

  // energy 0..1 scales every duration (calm = longer) and the overshoot (calm = less)
  const TIME = 1.3 - 0.6 * clamp(M.energy);
  const OS = M.overshoot * (0.4 + 1.2 * clamp(M.energy));
  C.D = (s) => s * TIME;                      // a choreography duration / offset, scaled by energy
  C.overshoot = OS;

  // ------------------------------------------------------------------ easing
  const E = {
    linear: (p) => p,
    inQuad: (p) => p * p, outQuad: (p) => 1 - (1 - p) * (1 - p),
    inOutQuad: (p) => (p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2),
    inCubic: (p) => p * p * p, outCubic: (p) => 1 - Math.pow(1 - p, 3),
    inOutCubic: (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2),
    inQuint: (p) => Math.pow(p, 5), outQuint: (p) => 1 - Math.pow(1 - p, 5),
    inOutQuint: (p) => (p < 0.5 ? 16 * Math.pow(p, 5) : 1 - Math.pow(-2 * p + 2, 5) / 2),
    inExpo: (p) => (p <= 0 ? 0 : Math.pow(2, 10 * p - 10)), outExpo: (p) => (p >= 1 ? 1 : 1 - Math.pow(2, -10 * p)),
    inOutExpo: (p) => (p <= 0 ? 0 : p >= 1 ? 1 : p < 0.5 ? Math.pow(2, 20 * p - 10) / 2 : (2 - Math.pow(2, -20 * p + 10)) / 2),
    outBack: (p, s = OS) => { const q = p - 1; return 1 + q * q * ((s + 1) * q + s); },
    inBack: (p, s = OS) => p * p * ((s + 1) * p - s),
    inOutBack: (p, s = OS) => { const c = s * 1.525; return p < 0.5 ? (Math.pow(2 * p, 2) * ((c + 1) * 2 * p - c)) / 2
                                                     : (Math.pow(2 * p - 2, 2) * ((c + 1) * (p * 2 - 2) + c) + 2) / 2; },
    outElastic: (p, amp = 1, period = 0.32) => {
      if (p <= 0 || p >= 1) return clamp(p);
      const s = (period / (2 * Math.PI)) * Math.asin(1 / Math.max(1, amp));
      return Math.max(1, amp) * Math.pow(2, -10 * p) * Math.sin(((p - s) * (2 * Math.PI)) / period) + 1;
    },
  };
  // damped spring normalised to the tween: settles (to 0.1%) exactly at p = 1. zeta: damping ratio 0..1
  E.spring = (zeta = 0.55) => {
    const z = clamp(zeta, 0.05, 0.999), w = Math.log(1000) / z, wd = w * Math.sqrt(1 - z * z);
    return (p) => (p <= 0 ? 0 : p >= 1 ? 1 : 1 - Math.exp(-z * w * p) * (Math.cos(wd * p) + ((z * w) / wd) * Math.sin(wd * p)));
  };
  C.easings = E;
  const FAM = { cubic: 'Cubic', quint: 'Quint', expo: 'Expo', quad: 'Quad' };
  const fam = FAM[M.ease] || 'Expo';
  // the style's house curves: entries decelerate, exits accelerate, moves do both
  C.IN = E['out' + fam]; C.OUT = E['in' + (fam === 'Expo' ? 'Cubic' : fam)]; C.MOVE = E['inOut' + fam];
  C.ease = (e) => {
    if (typeof e === 'function') return e;
    if (!e) return C.IN;
    if (e === 'in') return C.IN; if (e === 'out') return C.OUT; if (e === 'move') return C.MOVE;
    const m = /^spring\(([\d.]+)\)$/.exec(e); if (m) return E.spring(parseFloat(m[1]));
    if (E[e]) return E[e];
    throw new Error('unknown ease ' + e);
  };
  C.tween = (t, t0, dur, from, to, ease) => lerp(from, to, C.ease(ease)(C.prog(t, t0, dur)));

  // ------------------------------------------------------------------ stagger + timeline
  C.stagger = (i, n, each, from = 'start') => {
    if (from === 'center') return Math.abs(i - (n - 1) / 2) * each;
    if (from === 'end') return (n - 1 - i) * each;
    return i * each;
  };
  /** named spans on one clock. tl.at(name, t0, dur) / tl.then(name, dur, gap) place a span; tl.p(name, t, ease)
   *  is its eased progress; tl.t0(name), tl.end(name) read it back; tl.last is the end of the latest span. */
  C.timeline = () => {
    const S = {}; let last = 0;
    const tl = {
      at(name, t0, dur) { S[name] = [t0, Math.max(1e-6, dur)]; last = Math.max(last, t0 + dur); return tl; },
      then(name, dur, gap = 0) { return tl.at(name, last + gap, dur); },
      p(name, t, ease) { const s = S[name]; return s ? C.ease(ease)(C.prog(t, s[0], s[1])) : 0; },
      raw(name, t) { const s = S[name]; return s ? C.prog(t, s[0], s[1]) : 0; },
      t0(name) { return S[name] ? S[name][0] : 0; },
      end(name) { return S[name] ? S[name][0] + S[name][1] : 0; },
      get last() { return last; },
    };
    return tl;
  };

  // ------------------------------------------------------------------ deterministic helpers
  C.rand = (seed) => { let s = (seed >>> 0) || 1; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); };
  /** fake motion blur: a CSS blur (px) from the speed of a moving value fn(t) (px), as a 180-degree shutter would
   *  smear it. Zero on slow moves; capped at motion.blur_max_u. */
  C.mblur = (fn, t) => {
    if (!M.blur_on_fast) return 0;
    const h = 0.5 / CTX.fps, v = Math.abs(fn(t + h) - fn(t - h)) / (2 * h);
    const smear = v * (M.shutter / CTX.fps);
    return smear < 8 ? 0 : Math.min(M.blur_max_u * CTX.u, (smear - 8) * 0.22);
  };
  /** set transform / opacity / filter on an element. x, y px; s scale; r deg; o opacity; blur px; clip = inset % */
  C.set = (el, o) => {
    if (!el) return;
    const tf = [];
    if (o.x || o.y) tf.push(`translate3d(${(o.x || 0).toFixed(2)}px, ${(o.y || 0).toFixed(2)}px, 0)`);
    if (o.r) tf.push(`rotate(${o.r.toFixed(3)}deg)`);
    if (o.s !== undefined && o.s !== 1) tf.push(`scale(${o.s.toFixed(4)})`);
    if (o.sx !== undefined || o.sy !== undefined) tf.push(`scale(${(o.sx ?? 1).toFixed(4)}, ${(o.sy ?? 1).toFixed(4)})`);
    el.style.transform = tf.join(' ');
    if (o.o !== undefined) el.style.opacity = clamp(o.o).toFixed(4);
    if (o.blur !== undefined) el.style.filter = o.blur > 0.05 ? `blur(${o.blur.toFixed(2)}px)` : 'none';
    if (o.clip !== undefined) el.style.clipPath = o.clip;
  };
  /** the common entry: el travels `dist` px (along y, or x with axis:'x') into place over [t0, t0 + dur], fading in
   *  over the first 1/fade of it, with velocity blur on fast frames. Returns the raw progress. */
  C.rise = (el, t, t0, dur, dist, o = {}) => {
    const e = C.ease(o.ease || C.IN), f = (tt) => (1 - e(C.prog(tt, t0, dur))) * dist, p = C.prog(t, t0, dur);
    const v = f(t), op = o.fade === 0 ? 1 : Math.min(1, p * (o.fade || 2.6));
    C.set(el, Object.assign(o.axis === 'x' ? { x: v } : { y: v }, { o: p <= 0 ? 0 : op, blur: o.blur === false ? 0 : C.mblur(f, t) }, o.extra || {}));
    return p;
  };
  /** exit progress (house exit curve) over the last `ex` seconds when the piece exits (ctx.exit), else 0 */
  C.exitP = (t, ex) => {
    if (!CTX.exit) return 0;
    const d = ex || C.motion.exit_s; return C.OUT(C.prog(t, CTX.dur - d - 0.5 / CTX.fps, d));
  };
  C.el = (tag, cls, parent, text) => {
    const e = document.createElement(tag); if (cls) e.className = cls;
    if (text !== undefined && text !== null) e.textContent = text;
    if (parent) parent.appendChild(e); return e;
  };
  /** a monochrome icon (svg / png URI) tinted with currentColor through a CSS mask */
  C.icon = (parent, uri, cls = 'ic') => {
    const e = C.el('i', cls, parent);
    if (uri) { e.style.webkitMaskImage = `url("${uri}")`; e.style.maskImage = `url("${uri}")`; }
    return e;
  };
  /** inline SVG in a viewBox (default 0 0 100 100); strokes use pathLength=1 so CVES.draw(path, p) can draw them on */
  C.svg = (parent, inner, viewBox = '0 0 100 100', cls = '') => {
    const d = document.createElement('div'); d.innerHTML = `<svg class="${cls}" viewBox="${viewBox}" xmlns="http://www.w3.org/2000/svg">${inner}</svg>`;
    const sv = d.firstChild; parent.appendChild(sv); return sv;
  };
  C.draw = (path, p) => { path.style.strokeDasharray = '1 1'; path.style.strokeDashoffset = (1 - clamp(p)).toFixed(4); };
  C.CHECK = '<path d="M26 53 L43 69 L75 33" pathLength="1" fill="none" stroke="currentColor" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/>';
  C.CROSS = '<path d="M33 33 L67 67 M67 33 L33 67" pathLength="1" fill="none" stroke="currentColor" stroke-width="11" stroke-linecap="round"/>';
  /** "*word*" marks accent words (punctuation may touch the stars: "*growing*."). Returns words
   *  [{text, accent, runs: [{text, accent}]}], whitespace collapsed */
  C.tokens = (s) => {
    const out = []; let acc = false;
    String(s ?? '').replace(/\s+/g, ' ').trim().split(' ').forEach((word) => {
      const runs = [];
      word.split(/(\*)/).forEach((part) => { if (part === '*') acc = !acc; else if (part) runs.push({ text: part, accent: acc }); });
      if (runs.length) out.push({ text: runs.map((r) => r.text).join(''), accent: runs.some((r) => r.accent && /\w/.test(r.text)), runs });
    });
    return out;
  };
  C.plain = (s) => C.tokens(s).map((x) => x.text).join(' ');
  /** split a string into word spans inside `parent`: <span class=w><span class=wi>word</span></span>. The outer span
   *  is the mask (overflow clip), the inner one moves. Accent words get class `accent` (only the starred letters are
   *  coloured). data-text marks the block. chars=true also wraps every character in span.ch */
  C.words = (parent, s, chars = false) => {
    parent.dataset.text = C.plain(s);
    const words = [], inners = [], charEls = [];
    C.tokens(s).forEach((tk, i, arr) => {
      const w = C.el('span', 'w' + (tk.accent ? ' accent' : ''), parent);
      const wi = C.el('span', 'wi', w);
      tk.runs.forEach((r) => {
        const host = r.accent ? C.el('span', 'acc', wi) : wi;
        if (chars) [...r.text].forEach((ch) => charEls.push(C.el('span', 'ch', host, ch)));
        else if (r.accent) host.textContent = r.text; else host.appendChild(document.createTextNode(r.text));
      });
      words.push(w); inners.push(wi);
      if (i < arr.length - 1) parent.appendChild(document.createTextNode(' '));
    });
    return { words, inners, chars: charEls };
  };
  /** group laid-out word spans into lines (by their top) */
  C.lines = (wordEls) => {
    const lines = []; let top = null;
    wordEls.forEach((w, i) => { const y = Math.round(w.offsetTop); if (top === null || Math.abs(y - top) > 2) { lines.push([]); top = y; } lines[lines.length - 1].push(i); });
    return lines;
  };
  /** shrink el's font-size (from its CSS size) until it fits maxW x maxH (px) and at most maxLines lines */
  C.fit = (el, maxW, maxH, maxLines = 99, minScale = 0.45) => {
    const cs = getComputedStyle(el); const base = parseFloat(cs.fontSize); let k = 1;
    const lh = () => parseFloat(getComputedStyle(el).lineHeight) || base * k * 1.1;
    for (let n = 0; n < 40; n++) {
      el.style.fontSize = (base * k).toFixed(2) + 'px';
      const r = el.getBoundingClientRect(), c2 = getComputedStyle(el);
      const pad = parseFloat(c2.paddingTop) + parseFloat(c2.paddingBottom) + parseFloat(c2.borderTopWidth) + parseFloat(c2.borderBottomWidth);
      const lines = Math.round((r.height - pad) / lh());
      if (el.scrollWidth <= maxW + 0.5 && r.width <= maxW + 0.5 && r.height <= maxH + 0.5 && lines <= maxLines) break;
      if (k <= minScale) break;
      k *= 0.95;
    }
    return k;
  };
  /** number formatting: grouping intl (1,234,567) | indian (12,34,567) | none */
  C.fmt = (v, decimals = 0, grouping = 'intl') => {
    const neg = v < 0; const s = Math.abs(v).toFixed(decimals); let [i, d] = s.split('.');
    if (grouping === 'indian' && i.length > 3) i = i.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ',') + ',' + i.slice(-3);
    else if (grouping !== 'none') i = i.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return (neg ? '-' : '') + i + (d ? '.' + d : '');
  };

  // ------------------------------------------------------------------ cues
  const CUES = [];
  C.cue = (t, sfx, gain = -18, kw = {}) => CUES.push([+t, String(sfx), +gain, kw || {}]);

  // ------------------------------------------------------------------ parts (element log)
  // Every text block ([data-text]) and every [data-el] element is a *part*: the engine logs it as its own element
  // (id <piece>.<part>, its own bbox, text and entry frame), so QC measures each block on its own.
  function partEls() {
    const els = [...document.querySelectorAll('[data-text], [data-el]')];
    // stable ids: data-el, else the element id, else its first class; repeats get 0, 1, 2 ... (QC groups digits as one class)
    const base = els.map((el) => (el.dataset.el || el.id || String(el.className || '').split(' ')[0] || 'part').replace(/[^\w-]/g, ''));
    const seen = {}, count = {}; base.forEach((b) => { count[b] = (count[b] || 0) + 1; });
    return els.map((el, i) => [count[base[i]] > 1 ? base[i] + (seen[base[i]] = (seen[base[i]] ?? -1) + 1) : base[i], el]);
  }
  /** optical alignment from the engine: {part id: dx px}, measured on the drawn ink of a settled frame. Uses the CSS
   *  `translate` property, which composes with (and never fights) the transforms a piece sets. */
  C.__nudge = (o) => { partEls().forEach(([id, el]) => { if (o[id]) el.style.translate = `${(+o[id]).toFixed(2)}px 0`; }); };
  function parts() {
    const out = [];
    partEls().forEach(([id, el]) => {
      const txt = el.dataset.text || '';
      let o = 1, n = el, hidden = false;
      while (n && n.nodeType === 1) {
        const cs = getComputedStyle(n);
        if (cs.display === 'none' || cs.visibility === 'hidden') { hidden = true; break; }
        o *= parseFloat(cs.opacity); n = n.parentElement;
      }
      if (hidden || !el.isConnected) return;
      // a word mask whose words have not risen yet shows nothing: the block is as visible as its most visible word
      const ws = el.querySelectorAll('.wi');
      if (ws.length) { let m = 0; ws.forEach((w) => { m = Math.max(m, parseFloat(getComputedStyle(w).opacity || '1')); }); o *= m; }
      const r = el.getBoundingClientRect();
      if (r.width < 1 || r.height < 1 || r.right < 0 || r.bottom < 0 || r.left > CTX.w || r.top > CTX.h) return;
      out.push([id, txt, Math.floor(r.left), Math.floor(r.top), Math.ceil(r.right), Math.ceil(r.bottom), +o.toFixed(3)]);
    });
    return out;
  }

  // ------------------------------------------------------------------ boot
  const CTX = (C.ctx = Object.assign({ w: innerWidth, h: innerHeight, fps: 30, dur: 3, exit: false }, BOOT.ctx || {}));
  CTX.motion = M;
  let PIECE = null;
  C.piece = (def) => { PIECE = def; };

  async function ready() {
    if (!PIECE) throw new Error('piece.html never called CVES.piece({...})');
    const fams = (BOOT.fonts || []);
    await Promise.all(fams.map((f) => document.fonts.load(f).catch(() => null)));
    await document.fonts.ready;
    await Promise.all([...document.images].map((im) => (im.complete ? Promise.resolve() : im.decode().catch(() => null))));
    CTX.u = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--u-px')) || Math.min(CTX.w, CTX.h) / 100;
    const P = BOOT.params || {};
    if (PIECE.setup) PIECE.setup(P, CTX);
    await Promise.all([...document.images].map((im) => (im.complete ? Promise.resolve() : im.decode().catch(() => null))));
    await document.fonts.ready;
    if (PIECE.cues) PIECE.cues(P, CTX);
    return { cues: CUES };
  }
  C.__ready = ready;
  window.__seek = (t) => {
    PIECE.seek(t, BOOT.params || {}, CTX);
    return parts();
  };
})();
