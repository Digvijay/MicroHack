/* Into focus: the choreography of every slide. The engine (beat-engine.js) plays beat 0 on arrival and one
   beat per click. Every step sets absolute state, so a step back, Show all, print and reduced motion
   all land on the same settled picture. Numbers come from data.js. */
(() => {
  const T = window.TALK;
  const q = s => Beat.$(Beat.el(), s);
  const qa = s => Beat.$$(Beat.el(), s);
  const show = (sel, l, d) => (typeof sel === 'string' ? qa(sel) : [].concat(sel)).forEach(e => Beat.show(e, l, d));
  const head = [0, l => show('.kicker, .title, .subtitle', l)];
  const iqcol = at => [
    [at, l => show('.iqlens', l)],
    [at + 400, l => show('.badges', l)],
    [at + 800, l => show('.knows', l)],
    [at + 1200, l => show('.brings', l)],
  ];
  const keep = (sec, sel) => sec.querySelectorAll(sel).forEach(e => { e.dataset.t0 = e.innerHTML; });
  const restore = (sec, sel) => sec.querySelectorAll(sel).forEach(e => { if (e.dataset.t0 !== undefined) e.innerHTML = e.dataset.t0; });
  const colour = { none: '#6B7180', web: 'var(--web)', fabric: 'var(--fabric)', foundry: 'var(--foundry)', work: 'var(--work)', playbook: 'var(--light)', agent: 'var(--fg)' };
  const S = {};

  S.cover = {
    beats: [[
      [0, l => show('.cv-copy .k-wipe, .cv-copy .k-rise', l)],
      [500, l => show(qa('.cv-art .k-lens')[0], l)],
      [800, l => show(qa('.cv-art .k-lens')[1], l)],
      [1100, l => show(qa('.cv-art .k-lens')[2], l)],
      [1400, l => show(qa('.cv-art .k-lens')[3], l)],
      [2400, l => show('.lens-label', l)],
      [2700, l => { show('.core', l); Beat.pulse(q('.c-ring'), l); }],
      [3000, l => show('.cv-foot', l, 0)],
      [3600, () => Beat.el().classList.add('alive')],
    ]],
    reset(sec) { sec.classList.remove('alive'); },
  };

  S.cold = {
    init(sec) { const s = sec.querySelector('.s-blind'); s.dataset.text = T.blind; Beat.prepStream(s); },
    beats: [
      [head, [900, l => show('.f1', l)], [1500, l => show('.f2', l)], [2100, l => show('.f3', l)], [4500, l => show('.ask', l)]],
      [[0, l => show('.bot', l)], [500, l => Beat.stream(q('.s-blind'), l, 70)], [2600, l => show('.moral', l)]],
    ],
  };

  S.models = {
    beats: [
      [head,
        [700, l => show('.m-main', l)],
        [1300, l => show('.g1', l)], [1600, l => show('.g2', l)], [1900, l => show('.g3', l)], [2200, l => show('.g4', l)],
        [6000, l => show('.plus', l)],
        ...[0, 1, 2, 3].map(i => [6600 + i * 800, l => { show(`.ln${i}`, l); show(`.r${i}`, l, 250); }]),
        [9800, l => show('.mine', l)]],
      [[0, l => { const g = q('.m-grp'); g.classList.add('dim'); Beat.go(g, l, 'dimgo'); }],
        [600, l => show('.perm', l)], [1800, l => show('.moral', l)]],
    ],
    reset(sec) { sec.querySelector('.m-grp').classList.remove('dim', 'dimgo'); },
  };

  S.webiq = {
    init(sec) {
      sec.querySelector('.bars').innerHTML = T.web.map((r, i) => `
        <div class="brow k-rise w${i}"><p class="bq">${r.q}</p>
          <div class="track"><div class="b1 k-growx" style="width:${r.after * 60}px"></div><div class="b0 k-growx" style="width:${r.before * 60}px"></div></div>
          <p class="sc"><span class="a">${r.before}</span><span class="arrow k-fade">→</span><span class="web k-fade bb">${r.after}</span></p></div>`).join('');
    },
    beats: [
      [head, ...iqcol(600),
        ...T.web.map((_, i) => [2600 + i * 800, l => { show(`.w${i}`, l); show(`.w${i} .b0`, l, 200); }])],
      [...T.web.map((_, i) => [i * 700, l => { show(`.w${i} .b1`, l); show(`.w${i} .arrow`, l, 300); show(`.w${i} .bb`, l, 500); }]),
        [3200, l => show('.ck0', l)], [3700, l => show('.ck1', l)], [5000, l => show('.moral', l)]],
    ],
  };

  S.fabiq = {
    init(sec) {
      sec.querySelector('.grid').innerHTML = T.fabric.map((c, i) => `
        <div class="cell k-rise c${i}"><span class="lab">${c.id} · ${c.what}</span><span class="s k-pop">${c.score}/10</span>
          <p class="v">${c.value}<small>${c.unit}</small></p><p class="d">${c.detail}</p></div>`).join('');
      keep(sec, '.where, .mode');
    },
    beats: [
      [head, ...iqcol(600), [2400, l => show('.sql', l)], [4200, l => show('.r0', l)]],
      [[0, l => {
          q('.where').textContent = "component_id = 'HX-220'"; Beat.go(q('.where'), l, 'flipping');
          q('.mode').textContent = 'Data agent · four example queries';
          q('.r0').classList.add('gone');
        }],
        [900, l => show('.r1', l)],
        ...T.fabric.map((_, i) => [2000 + i * 600, l => { show(`.c${i}`, l); show(`.c${i} .s`, l, 350); }]),
        [5000, l => show('.moral', l)]],
    ],
    reset(sec) { restore(sec, '.where, .mode'); sec.querySelector('.r0').classList.remove('gone'); sec.querySelector('.where').classList.remove('flipping'); },
  };

  S.fdyiq = {
    beats: [
      [head, ...iqcol(600), [2200, l => show('.ask', l)],
        [2800, l => show('.d0', l)], [3100, l => show('.d1', l)], [3400, l => show('.d2', l)],
        [5000, l => Beat.go(q('.scan'), l)],
        [5480, () => q('.d0').classList.add('hit')], [6510, () => q('.d1').classList.add('hit')], [7540, () => q('.d2').classList.add('hit')]],
      [[0, l => show('.verdict', l)], [1600, l => show('.moral', l)]],
    ],
    reset(sec) { sec.querySelectorAll('.doc').forEach(d => d.classList.remove('hit')); sec.querySelector('.scan').classList.remove('go'); },
  };

  // Two graphs: node and edge states are classes on SVG groups, set absolutely by each step.
  const cls = (sel, add, ...names) => qa(sel).forEach(e => names.forEach(n => e.classList.toggle(n, add)));
  const LRES = {
    miss: '<span class="tag bad">MISS</span>One product, two nodes: “PV-400” and “PV-400 pump valve”. The walk from HX-220 found Solvik only.',
    hit: '<span class="tag good">3 OF 3</span>With naming rules in the ontology: Brennmark, Østerdal and Solvik. Not Ferrovia.',
    v1: '<span class="tag bad">V1</span>“Yes, buy from Teglbruk.” The ontology had a backup link, but no notion of a quality hold.',
    v2: '<span class="tag v2">V2</span>Adds QualityReport and Policy: “Teglbruk is on quality hold.”',
  };
  S.graphs = {
    init(sec) { keep(sec, '.qt'); },
    beats: [
      [head, [800, l => show('.qbar', l)], [1200, l => show('.panel', l)], [1800, l => show('.lg', l)], [2100, l => show('.rg', l)],
        [3600, () => cls('.n-nord', true, 'hit')],
        [4100, () => cls('.e-nh, .n-hx', true, 'hit')],
        [4600, () => cls('.e-hp, .n-pv, .e-hc, .n-cv', true, 'hit')],
        [5100, () => cls('.e-cs, .n-sol', true, 'hit')],
        [5700, () => cls('.n-dup, .n-bren, .n-ost', true, 'miss')],
        [6300, l => { q('.lres').innerHTML = LRES.miss; show('.lres', l); }]],
      [[0, l => Beat.go(q('.merge'), l)],
        [1400, () => { cls('.merge, .e-db, .e-do', true, 'gone'); cls('.e-pb, .e-po', false, 'gone'); cls('.n-dup, .n-bren, .n-ost', false, 'miss'); }],
        [1900, () => cls('.e-pb, .e-po, .n-bren, .n-ost', true, 'hit')],
        [2500, l => { q('.lres').innerHTML = LRES.hit; Beat.pulse(q('.lres'), l); }],
        ...[0, 1, 2, 3, 4].map(i => [3500 + i * 300, () => cls(`.en${i}${i ? `, .a${i - 1}` : ''}`, true, 'hit')]),
        [5200, l => show('.rres1', l)]],
      [[0, l => {
          q('.qt').textContent = 'Can we buy HX-220 from Teglbruk Metall AS?'; Beat.go(q('.qt'), l, 'flipping');
          cls('.lg .nd, .lg .ed, .rg .ent, .rg .arw', false, 'hit');
        }],
        [800, () => { cls('.n-tegl, .n-hx', true, 'hit'); cls('.e-th', true, 'red'); }],
        [1400, l => { q('.lres').innerHTML = LRES.v1; Beat.pulse(q('.lres'), l); }],
        [2200, () => cls('.en0', true, 'hit')],
        [2800, l => show('.rres2', l)],
        [5600, l => { show('.n-qr', l); cls('.e-qt', false, 'gone'); }],
        [6300, () => { cls('.n-tegl', false, 'hit'); cls('.n-tegl', true, 'held'); }],
        [6900, l => { q('.lres').innerHTML = LRES.v2; Beat.pulse(q('.lres'), l); }],
        [8200, l => show('.moral', l)]],
    ],
    reset(sec) {
      restore(sec, '.qt'); sec.querySelector('.qt').classList.remove('flipping');
      sec.querySelectorAll('.lg .nd, .lg .ed, .rg .ent, .rg .arw, .merge').forEach(e => e.classList.remove('hit', 'miss', 'held', 'red', 'gone', 'go'));
      sec.querySelectorAll('.e-pb, .e-po, .e-qt').forEach(e => e.classList.add('gone'));
      sec.querySelector('.lres').innerHTML = '';
    },
  };

  S.wrkiq = {
    beats: [
      [head, ...iqcol(600), [2200, l => show('.call', l)], [3000, l => show('.m1', l)], [3800, l => show('.m5', l)]],
      [[0, l => show('.lab-ep', l)], [700, l => show('.tools', l)], [1400, l => show('.prod', l)], [2600, l => show('.moral', l)]],
    ],
  };

  const view = (who, l) => qa('.tile').forEach((t, i) => {
    const seen = t.dataset[who] === '1';
    t.classList.toggle('seen', seen); t.classList.toggle('hidden', !seen);
    t.classList.add('flash'); Beat.pulse(t, l, i * 90);
  });
  S.perm = {
    init(sec) { sec.querySelectorAll('.stream').forEach(Beat.prepStream); },
    beats: [
      [head, [800, l => show('.qbar', l)], ...[1, 2, 3, 4, 5, 6, 7, 8].map((n, i) => [1300 + i * 200, l => show(`.t${n}`, l)]),
        [3400, l => show('.l1', l)], [3700, l => show('.l2', l)]],
      [[0, l => view('sl', l)], [1000, l => Beat.stream(q('.s-sl'), l, 90)], [2600, l => show('.w-sl', l)]],
      [[0, l => view('sp', l)], [1000, l => Beat.stream(q('.s-sp'), l, 80)], [3600, l => show('.w-sp', l)], [5000, l => show('.moral', l)]],
    ],
    reset(sec) { sec.querySelectorAll('.tile').forEach(t => t.classList.remove('seen', 'hidden', 'flash')); },
  };

  S.focus = {
    beats: [
      [head, [800, l => show('.ask', l)], [1400, l => show('.slots', l)], [1800, l => show('.answer', l)]],
      [...[0, 1, 2, 3].flatMap(i => [
        [i * 3000, l => show(`.fl${i}`, l)],
        [i * 3000 + 700, l => show(`.z${i}`, l)],
        [i * 3000 + 900, () => { q('.cnt').textContent = `IQs in focus: ${i + 1} of 4`; }],
      ])],
      [[0, l => { qa('.fl').forEach(e => { e.classList.add('cv'); Beat.go(e, l, 'conv'); }); q('.slots').classList.add('faded'); Beat.go(q('.slots'), l, 'fadego'); }],
        [1500, l => { show('.fcore', l); Beat.pulse(q('.fburst'), l); }],
        [2300, l => show('.decision', l)], [3600, l => show('.after', l)]],
    ],
    reset(sec) {
      sec.querySelector('.cnt').textContent = 'IQs in focus: 0 of 4';
      sec.querySelectorAll('.fl').forEach(e => e.classList.remove('cv', 'conv')); sec.querySelector('.slots').classList.remove('faded', 'fadego');
    },
  };

  const LB = T.leaderboard;
  const X = v => 348 + (v / LB.max) * 680;
  S.curve = {
    init(sec) {
      const names = { none: 'No IQ', web: '+ Web IQ', fabric: '+ Fabric IQ', foundry: '+ Foundry IQ', work: '+ Work IQ', playbook: '+ team playbook' };
      sec.querySelector('.board').innerHTML =
        `<span class="axis" style="left:${X(150)}px">150: a good team</span><span class="vline" style="left:${X(150)}px"></span>` +
        `<span class="axis" style="left:${X(LB.max)}px">${LB.max} max</span><span class="vline" style="left:${X(LB.max)}px"></span>` +
        LB.runs.map((r, i) => {
          const d = i ? r.score - LB.runs[i - 1].score : 0;
          const delta = i ? ` · ${d < 0 ? 'down' : 'up'} ${Math.abs(d)} point${Math.abs(d) === 1 ? '' : 's'}` : '';
          return `<div class="crow k-rise r${i}" style="top:${i * 62}px;--c:${colour[r.add]}">
            <p class="cl" style="color:${r.add === 'none' ? 'var(--muted)' : colour[r.add]}">${names[r.add]}</p>
            <p class="cd${d < 0 ? ' down' : ''}${i === LB.runs.length - 1 ? ' up' : ''}">challenge ${i + 1}${delta}</p>
            <div class="ct"><div class="cb k-growx" style="width:${(r.score / LB.max) * 680}px"></div></div>
            <p class="cs"><span class="n">0</span></p></div>`;
        }).join('');
      sec.querySelector('.foot').textContent = LB.illustrative
        ? `Illustrative: an earlier complete reference run (${LB.source}), rounded. Scores move a few points between runs.`
        : `Measured: src/.caldova/leaderboard.json, 26 November 2026, rounded. A second run with the playbook scored ${LB.second}.`;
    },
    beats: (() => {
      const row = (i, at) => [
        [at, l => show(`.r${i}`, l)],
        [at + 300, l => { show(`.r${i} .cb`, l); Beat.count(q(`.r${i} .n`), LB.runs[i].score, l, 1200); }],
      ];
      return [
        [head, ...[0, 1, 2, 3].flatMap(i => row(i, 1200 + i * 1500))],
        [...row(4, 0), [1700, () => q('.r4').classList.add('drop')]],
        [...row(5, 0), [2400, l => show('.moral', l)]],
      ];
    })(),
    reset(sec) { sec.querySelectorAll('.crow .n').forEach(n => { n.textContent = '0'; }); sec.querySelector('.r4').classList.remove('drop'); },
  };

  S.fails = {
    beats: [
      [head, ...[0, 1, 2].flatMap(i => [[1000 + i * 3200, l => show(`.c${i}`, l)], [2600 + i * 3200, l => show(`.c${i} .rl`, l)]])],
      [[0, l => show('.c3', l)], [1500, l => show('.c3 .stamp', l)], [3200, l => show('.c3 .rl', l)], [4600, l => show('.moral', l)]],
    ],
  };

  S.ga = {
    init(sec) {
      sec.querySelector('.tbl').innerHTML =
        '<div class="gh k-rise"><span class="lab" style="left:28px">Feature</span><span class="lab" style="left:810px">Status</span><span class="lab" style="left:1000px">Challenge</span></div>' +
        T.ga.map((r, i) => `<div class="gr k-rise g${i}${r.status === 'Preview' ? ' pvrow' : ''}" style="--c:${colour[r.iq]}">
          <span class="iqd"></span><p class="gf">${r.feature}${r.note ? ` <span class="muted">· ${r.note}</span>` : ''}</p>
          <span class="gs"><span class="pill ${r.status === 'GA' ? 'ga' : 'pv'} k-pop">${r.status}</span></span><p class="gc">${r.ch}</p></div>`).join('');
    },
    beats: [
      [head, [800, l => show('.gh', l)], ...T.ga.map((_, i) => [1100 + i * 700, l => { show(`.g${i}`, l); show(`.g${i} .pill`, l, 300); }])],
      [[0, () => qa('.pvrow').forEach(r => r.classList.add('mark'))], [700, l => show('.moral', l)]],
    ],
    reset(sec) { sec.querySelectorAll('.pvrow').forEach(r => r.classList.remove('mark')); },
  };

  S.close = {
    beats: [[
      head,
      ...[0, 1, 2, 3, 4, 5].flatMap(i => [
        [1200 + i * 1400, l => { qa(`.x${i} .k-pop, .x${i}.k-pop`).forEach((e, k) => Beat.show(e, l, k * 160)); show(`.h${i}`, l, 200); }],
        ...(i === 5 ? [[1200 + i * 1400 + 900, l => show('.x5 .core', l)]] : []),
      ]),
      [9800, l => show('.state', l)], [10800, l => show('.paths', l)], [11400, l => show('.repo', l)],
    ]],
  };

  S.thanks = {
    beats: [[
      ...[0, 1, 2, 3].map(i => [300 + i * 200, l => show(qa('.k-lens')[i], l)]),
      [2200, l => { show('.core', l); Beat.pulse(q('.t-ring'), l); }],
      [2700, l => show('.ty', l)], [3600, l => show('.by', l)], [4000, l => show('.rp', l)],
      [4400, () => Beat.el().classList.add('alive')],
    ]],
    reset(sec) { sec.classList.remove('alive'); },
  };

  window.SCENES = S;
})();
