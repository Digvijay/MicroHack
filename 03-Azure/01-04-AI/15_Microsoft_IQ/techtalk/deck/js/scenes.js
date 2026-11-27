/* 02:13: the choreography of every slide. The engine (beat-engine.js) plays beat 0 on arrival and one beat
   per click. Every step sets absolute state, so a step back, Show all, print and reduced motion all land on
   the same settled picture. Numbers come from data.js. */
(() => {
  const T = window.TALK;
  const q = s => Beat.$(Beat.el(), s);
  const qa = s => Beat.$$(Beat.el(), s);
  const show = (sel, l, d) => (typeof sel === 'string' ? qa(sel) : [].concat(sel)).forEach(e => Beat.show(e, l, d));
  const head = [0, l => show('.kicker, .title, .subtitle', l)];
  const cls = (sel, on, ...names) => qa(sel).forEach(e => names.forEach(n => e.classList.toggle(n, on)));
  const setText = (sel, text, l, flip) => { const e = q(sel); e.textContent = text; if (flip) Beat.go(e, l, 'flipping'); };
  const keep = (sec, sel) => sec.querySelectorAll(sel).forEach(e => { e.dataset.t0 = e.textContent; });
  const restore = (sec, sel) => sec.querySelectorAll(sel).forEach(e => { if (e.dataset.t0 !== undefined) e.textContent = e.dataset.t0; e.classList.remove('flipping'); });
  const S = {};

  S.cover = {
    beats: [[
      [0, l => show('.cv-event', l)],
      ...[0, 1, 2, 3, 4].map(i => [300 + i * 160, l => show(qa('.dg')[i], l)]),
      [1400, l => show('.cv-sub', l)],
      ...[0, 1, 2].map(i => [2200 + i * 450, l => { show(`.r${i}`, l); show(`.s${i}`, l, 700); }]),
      [3900, l => show('.strip', l)],
      [4400, l => { show('.now', l); Beat.pulse(q('.c-ring'), l); }],
      [4900, l => show('.cv-foot', l)],
      [5600, () => Beat.el().classList.add('alive')],
    ]],
    reset(sec) { sec.classList.remove('alive'); },
  };

  S.cold = {
    beats: [
      [head, [900, l => show('.unit', l)], [1500, l => show('.calm', l)], [2700, l => show('.shake', l)],
        [3500, l => show('.alarm', l)], [5200, l => show('.deadline', l)], [5800, l => show('.deadline .fill', l)]],
      [[0, l => show('.instr', l)], [4200, l => show('.moral', l)]],
    ],
  };

  S.doors = {
    beats: [
      [head, [800, l => show('.maria', l)],
        ...[0, 1, 2].map(i => [1600 + i * 500, l => { show(`.l${i}`, l); show(`.c${i}`, l, 600); }])],
      [[0, l => show('.c0 .ans', l)], [1600, l => show('.c2 .ans', l)], [3600, l => show('.c1 .ans', l)], [5600, l => show('.moral', l)]],
    ],
  };

  S.models = {
    beats: [
      [head, ...[0, 1, 2].map(i => [900 + i * 400, l => { show(`.d${i}`, l); show(`.n${i}`, l, 200); }])],
      [...[0, 1, 2].map(i => [i * 1800, l => show(`.f${i}`, l)]),
        [5600, () => Beat.el().classList.add('lit')], [6400, l => show('.moral', l)]],
    ],
    reset(sec) { sec.classList.remove('lit'); },
  };

  S.locks = {
    beats: [
      [head, [800, l => show('.n-l', l)], [1200, l => show('.corridor', l)],
        ...[0, 1, 2].map(i => [1600 + i * 700, l => show(`.g${i}`, l)]), [3800, l => show('.n-r', l)]],
      [...[0, 1, 2].map(i => [i * 2600, l => show(`.q${i}`, l)]), [8000, l => show('.moral', l)]],
    ],
  };

  S.team = {
    beats: [
      [head, [800, l => show('.cs', l)], [1500, l => { show('.hand', l); show('.hand-tip', l, 900); }], [2300, l => show('.hub', l)]],
      [...[0, 1, 2, 3].map(i => [i * 700, l => { show(`.p${i}`, l); show(`.s${i}`, l, 700); }]), [4200, l => show('.moral', l)]],
    ],
  };

  // Parts: rows from data.js, a scan of the rules, then the ontology chain behind the reserved unit.
  S.parts = {
    init(sec) {
      sec.querySelector('.rows').innerHTML = T.units.map((u, i) => `
        <div class="ur k-rise u${i}"><span class="c1">${u.serial}</span><span class="c2">${u.model}</span><span class="c3">${u.site}</span><span class="c4">${u.status}</span>
          <span class="tg ${u.kind} k-pop">${u.tag}</span></div>`).join('');
    },
    beats: [
      [head, [700, l => show('.th', l)], ...T.units.map((_, i) => [1000 + i * 250, l => show(`.u${i}`, l)]),
        [4600, l => Beat.go(q('.scan'), l)],
        ...T.units.map((u, i) => u.kind === 'why' ? [4600 + 300 + 2100 * (i + 0.5) / T.units.length, l => { q(`.u${i}`).classList.add('out'); show(`.u${i} .tg`, l); }] : null).filter(Boolean),
        [7400, l => { q('.u0').classList.add('in'); show('.u0 .tg', l); }]],
      [[0, l => { q('.u1').classList.add('held'); show('.u1 .tg', l); }],
        ...[0, 1, 2, 3].flatMap(i => [[600 + i * 900, l => show(`.o${i}`, l)], ...(i < 3 ? [[1000 + i * 900, l => { show(`.e${i}`, l); show(`.x${i}`, l, 300); }]] : [])]),
        [5200, l => show('.moral', l)]],
    ],
    reset(sec) { sec.querySelectorAll('.ur').forEach(r => r.classList.remove('out', 'in', 'held')); sec.querySelector('.scan').classList.remove('go'); },
  };

  S.rules = {
    beats: [
      [head, [900, l => show('.note', l)], [4500, l => show('.vote', l)]],
      [[0, l => show('.doc', l)], [900, l => Beat.go(q('.doc .scan'), l)], [2100, () => q('.doc').classList.add('hit')],
        [4200, l => show('.f0', l)], [5000, l => show('.f1', l)], [6400, l => show('.moral', l)]],
    ],
    reset(sec) { sec.querySelector('.doc').classList.remove('hit'); sec.querySelector('.doc .scan').classList.remove('go'); },
  };

  S.people = {
    beats: [
      [head, [800, l => show('.reads', l)], [1600, l => show('.w0', l)], [3600, l => show('.w1', l)], [5600, l => show('.w2', l)],
        [7000, l => show('.tools', l)], [7600, l => show('.thread', l)]],
      [[0, l => show('.p0', l)], [1400, l => show('.appr', l)]],
      [[0, l => show('.p1', l)], [4000, l => show('.moral', l)]],
    ],
  };

  // Routes: a time axis from Tuesday 08:00 to Thursday 06:00, bars to scale.
  const A = T.axis, px = h => (h / A.hours) * (A.x1 - A.x0);
  S.routes = {
    init(sec) {
      const lane = (r, i, top) => `
        <div class="lane k-rise ln${i}" style="top:${top}px">
          <div class="ln"><p class="u">${r.unit}</p><p class="h">${r.from}: ${r.how}</p></div>
          <div class="rb k-growx b${i}" style="width:${px(r.at)}px"><span class="e">${r.arrives}</span></div>
          <div class="mg k-fade m${i}" style="left:${A.x0 - 72 + px(r.at) + 10}px;width:${A.x1 - A.x0 - px(r.at) - 20}px"><span class="mgl">${r.margin}</span></div>
          <p class="meta k-fade t${i}"><b>${r.cost}</b> · ${r.note}</p>
        </div>`;
      const s = T.slot;
      sec.querySelector('.lanes').innerHTML = lane(T.routes[0], 0, 200) + lane(T.routes[1], 1, 318) + `
        <div class="lane k-rise ln2" style="top:432px">
          <div class="ln"><p class="u">Technician</p><p class="h">FS-04, ${s.label}</p></div>
          <div class="rb slot k-growx b2" style="left:${A.x0 - 72 + px(s.from)}px;width:${px(s.to - s.from) - 4}px"><span class="e">${s.id}</span></div>
        </div>`;
      const ticks = [[0, 'Tue 08:00'], [16, 'Wed 00:00'], [28, 'Wed 12:00'], [40, 'Thu 00:00'], [46, 'Thu 06:00']];
      sec.querySelector('.ticks').innerHTML = ticks.map(([h, t]) => `<span style="left:${A.x0 + px(h)}px">${t}</span>`).join('');
    },
    beats: [
      [head, [800, l => show('.axis, .ticks', l)], [1400, l => show('.dead, .deadl', l)],
        [3200, l => show('.ln0', l)], [3800, l => show('.b0', l)], [5000, l => show('.t0', l)], [5800, l => show('.m0', l)]],
      [[0, l => show('.ln1', l)], [600, l => show('.b1', l)], [1800, l => show('.t1', l)], [2600, l => show('.m1', l)],
        [4200, l => show('.ln2', l)], [4800, l => show('.b2', l)], [7000, l => show('.webnote', l)], [9000, l => show('.moral', l)]],
    ],
  };

  // The wow scene: the proposal assembles, dawn comes up at 06:30, Alex decides at 07:30.
  S.night = {
    init(sec) {
      sec.querySelector('.pl').innerHTML = T.proposal.map((p, i) =>
        `<div class="pr k-rise y${i}" style="--c:var(--${p.c})"><span class="tx">${p.tx}</span><span class="src k-pop">${p.src}</span></div>`).join('');
      keep(sec, '.bigclock, .cap, .kicker .tm');
    },
    beats: [
      [head, [700, l => show('.bigclock', l)], [1100, l => show('.cap', l)], [1500, l => show('.thread', l)],
        [2200, l => show('.h0', l)], [2600, l => show('.h1', l)], [3400, l => show('.h2', l)],
        ...T.proposal.map((_, i) => [4400 + i * 1500, l => { show(`.y${i}`, l); show(`.y${i} .src`, l, 350); }]),
        [4400 + T.proposal.length * 1500 + 400, l => show('.last', l)]],
      [[0, l => { setText('.bigclock', '06:30', l, true); setText('.kicker .tm', '06:30', l); }],
        [300, l => show('.sky', l)],
        [900, l => setText('.cap', 'Alex wakes up to one thread.', l, true)],
        [2400, l => show('.opts', l)]],
      [[0, l => { setText('.bigclock', '07:30', l, true); setText('.kicker .tm', '07:30', l); }],
        [300, l => show('.sun', l)],
        [900, l => setText('.cap', 'Alex makes the call.', l, true)],
        [1900, l => { show('.both', l); Beat.pulse(q('.bburst'), l, 300); }],
        [3200, l => show('.alex', l)], [5200, l => show('.moral', l)]],
    ],
    reset(sec) { restore(sec, '.bigclock, .cap, .kicker .tm'); },
  };

  S.trust = {
    init(sec) {
      sec.querySelector('.bars').innerHTML = T.evaluation.rubric.map((r, i) => `
        <div class="br ${r.version} k-rise r${i}"><span class="v">${r.version}</span><span class="w">${r.what}</span>
          <div class="tk"><div class="fl k-growx" style="width:${r.pct * 3}px"></div></div>
          <span class="pc"><span class="cnt">0</span>%</span><span class="n">${r.n}</span></div>`).join('');
    },
    beats: [
      [head, [800, l => show('.ev', l)],
        ...T.evaluation.rubric.map((r, i) => [1400 + i * 1600, l => { show(`.r${i}`, l); show(`.r${i} .fl`, l, 200); Beat.count(q(`.r${i} .cnt`), r.pct, l, 1100); }]),
        [5400, l => show('.safe', l)]],
      [[0, l => show('.cmp', l)], [1800, l => show('.stamp', l)], [3200, l => show('.moral', l)]],
      [[0, l => show('.tr', l)], ...[0, 1, 2, 3, 4, 5, 6].map(i => [500 + i * 450, l => show(`.t${i}`, l)]), [4200, l => show('.badges', l)]],
    ],
    reset(sec) { sec.querySelectorAll('.cnt').forEach(n => { n.textContent = '0'; }); },
  };

  // Board: columns x positions inside the 1136px table.
  const COL = i => 250 + i * 128;
  S.board = {
    init(sec) {
      const B = T.board;
      sec.querySelector('.sc').innerHTML =
        `<div class="hr k-rise">${B.cols.map((c, i) => `<span style="left:${COL(i)}px">${c}</span>`).join('')}<span style="left:896px;width:240px;text-align:left">Verdict</span></div>` +
        B.rows.map((r, i) => `<div class="rw k-rise w${i}${i === 0 ? ' you' : ''}"><p class="nm">${r.name}</p><p class="kd">${r.kind}</p>
          ${r.cells.map((v, k) => `<span class="cell k-pop k${k} ${v ? 'y' : 'n'}" style="left:${COL(k) + 28}px">${v ? 'Yes' : 'No'}</span>`).join('')}
          <p class="vd k-rise">${r.verdict}</p></div>`).join('');
    },
    beats: [
      [head, [800, l => show('.hr', l)], ...[0, 1, 2].map(i => [1200 + i * 300, l => show(`.w${i}`, l)]),
        ...[0, 1, 2, 3, 4].map(k => [2600 + k * 900, l => qa(`.k${k}`).forEach((e, j) => Beat.show(e, l, j * 120))])],
      [[0, l => show('.w1 .vd', l)], [1600, l => show('.w2 .vd', l)], [3200, l => { show('.w0 .vd', l); q('.w0').classList.add('lit'); }], [5200, l => show('.ask', l)]],
    ],
    reset(sec) { sec.querySelector('.w0').classList.remove('lit'); },
  };

  const mins = c => { const [h, m] = c.split(':').map(Number); return (h - 2) * 60 + m - 10; };
  S.close = {
    init(sec) {
      sec.querySelector('.dots').innerHTML = T.challenges.filter(c => /^\d\d:\d\d$/.test(c.clock))
        .map((c, i) => `<span class="dot k-pop d${i}" style="left:${72 + (mins(c.clock) / 320) * 1136}px"></span>`).join('');
      sec.querySelector('.list').innerHTML = T.challenges.map((c, i) => `
        <div class="cr k-rise c${i}"><span class="ck">${c.clock}</span><span class="ct">${c.title}</span><span class="cp">${c.product}</span>
          ${c.status ? `<span class="cs ${/GA/.test(c.status) ? 'ga' : 'pv'}">${c.status}</span>` : ''}<span class="cm">${c.min} min</span></div>`).join('');
    },
    beats: [[
      head, [700, l => show('.track', l)],
      ...T.challenges.map((c, i) => [1300 + i * 600, l => { show(`.c${i}`, l); if (/^\d\d:\d\d$/.test(c.clock)) show(`.d${i}`, l); }]),
      [6600, l => show('.moral', l)],
    ]],
  };

  S.thanks = {
    beats: [[
      [200, l => show('.track', l)], [600, l => { show('.m0', l); show('.e0', l); }],
      [1500, l => { show('.sky', l); show('.sunc', l); show('.e1', l); Beat.pulse(q('.t-ring'), l, 400); }],
      [2400, l => show('.ty', l)], [3200, l => show('.tag', l)], [3800, l => show('.by', l)], [4200, l => show('.rp', l)], [4600, l => show('.cr', l)],
      [5000, () => Beat.el().classList.add('alive')],
    ]],
    reset(sec) { sec.classList.remove('alive'); },
  };

  window.SCENES = S;
})();
