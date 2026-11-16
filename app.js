/* 경쟁사 메타 광고 — meta_ads.json (meta_ads.py 가 10/14/18시 갱신) */
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const S = { view: 'brand', cat: 'all', brand: 'all' };
const FORMATS = ['영상', '이미지', '캐러셀', '카탈로그', '다이나믹'];
let D = null;

const inCat = (a) => S.cat === 'all' || (S.cat === '기타' ? !a.cats.length : a.cats.includes(S.cat));
const shown = () => D.ads.filter((a) => inCat(a) && (S.brand === 'all' || a.brand === S.brand));
const topN = (counter, n) => Object.entries(counter).sort((a, b) => b[1] - a[1]).slice(0, n);
const count = (arr, key) => arr.reduce((m, a) => { [].concat(key(a)).forEach((k) => { m[k] = (m[k] || 0) + 1; }); return m; }, {});
const pct = (a, b) => b ? Math.round(a * 100 / b) : 0;

function segs(el, items, key) {
  el.innerHTML = items.map(([v, label, n, cls]) => `<button class="seg ${cls || ''} ${S[key] === v ? 'on' : ''}" data-v="${esc(v)}">${esc(label)}${n != null ? `<small>${n}</small>` : ''}</button>`).join('');
  el.querySelectorAll('button').forEach((b) => { b.onclick = () => { S[key] = b.dataset.v; render(); }; });
}

function card(a) {
  const long = a.days >= D.long_days;
  const img = a.img ? `<img src="${esc(a.img)}" loading="lazy" referrerpolicy="no-referrer" alt="" onerror="this.remove()">` : '';
  return `<article class="ad">
    <div class="img">${img}<span class="tag">${esc(a.format)}${a.cards > 1 ? ' ' + a.cards + '장' : ''}</span><span class="tag days ${long ? 'long' : ''}">${a.days}일째</span></div>
    <div class="bd">
      <div class="who"><b>${esc(a.brand)}</b><span class="mono">${a.start.slice(2).replace(/-/g, '.')}~</span></div>
      ${a.title ? `<div class="t">${esc(a.title)}</div>` : ''}
      ${a.body ? `<div class="tx">${esc(a.body)}</div>` : ''}
      <div class="ap">${a.appeals.map((t) => `<i>${esc(t)}</i>`).join('')}</div>
      <a class="lk" href="https://www.facebook.com/ads/library/?id=${a.id}" target="_blank" rel="noopener">광고 라이브러리에서 보기 ↗</a>
    </div></article>`;
}

function insights(ads) {
  const comp = ads;
  const brandsWith = {};   // 소구점 → 쓰는 브랜드 집합
  comp.forEach((a) => a.appeals.forEach((t) => { (brandsWith[t] ||= new Set()).add(a.brand); }));
  const nB = new Set(comp.map((a) => a.brand)).size;
  const rank = Object.entries(brandsWith).map(([t, s]) => [t, s.size, comp.filter((a) => a.appeals.includes(t)).length]).sort((a, b) => b[1] - a[1] || b[2] - a[2]);
  const maxB = Math.max(1, ...rank.map((r) => r[1]));
  const fmt = count(comp, (a) => a.format);
  const longs = comp.filter((a) => a.days >= D.long_days), fresh = comp.filter((a) => a.days <= 7);
  const list = (c) => c.map(([k, v]) => `${esc(k)} ${v}`).join(' · ');
  const lines = [];
  if (rank.length) lines.push(`${nB}곳 중 <b>${rank[0][1]}곳</b>이 <b>‘${esc(rank[0][0])}’</b> 소구 — ${rank.slice(1, 3).map((r) => `‘${esc(r[0])}’(${r[1]}곳)`).join(', ')} 순`);
  if (comp.length) lines.push(`소재 형식: ${list(topN(fmt, 3))} → 영상 비중 <b>${pct(fmt['영상'] || 0, comp.length)}%</b>`);
  if (longs.length) lines.push(`<b>${D.long_days}일+ 장기 집행 ${longs.length}건</b>(=검증된 소재) — 소구 ${list(topN(count(longs, (a) => a.appeals), 3))} / 형식 ${list(topN(count(longs, (a) => a.format), 2))}`);
  if (fresh.length) lines.push(`<b>최근 7일 새로 켠 ${fresh.length}건</b>(=지금 테스트 중) — ${list(topN(count(fresh, (a) => a.appeals), 3))}`);

  const bs = [...new Set(ads.map((a) => a.brand))];
  const fcols = FORMATS.filter((f) => fmt[f]);
  const ftbl = `<div class="ftbl mono" style="grid-template-columns:minmax(64px,1.3fr) repeat(${fcols.length + 1},minmax(0,1fr))">
    <div class="th l">브랜드</div>${fcols.map((f) => `<div class="th">${f}</div>`).join('')}<div class="th">계</div>
    ${bs.map((b) => { const c = count(ads.filter((a) => a.brand === b), (a) => a.format); const n = Object.values(c).reduce((x, y) => x + y, 0);
      return `<div class="l">${esc(b)}</div>${fcols.map((f) => `<div class="${c[f] ? '' : 'z'}">${c[f] || '·'}</div>`).join('')}<div>${n}</div>`; }).join('')}</div>`;

  $('#ins').innerHTML = `<div><div class="h">인사이트 <span class="mono" style="font-size:10px;color:var(--ink3);font-weight:400">자동 집계 · 광고 문구 키워드 기준</span></div>
      <ul>${lines.map((l) => `<li>${l}</li>`).join('') || '<li>광고가 없습니다</li>'}</ul>
      <div class="cap" style="margin-top:16px">소구점별 사용 브랜드 수</div>
      <div class="stack" style="gap:7px;margin-top:10px">${rank.map(([t, b, n]) => `<div class="hrow"><span class="lab">${esc(t)}</span><div class="bar"><i style="width:${b * 100 / maxB}%"></i></div><span class="amt mono">${b}곳 · ${n}건</span></div>`).join('')}</div>
    </div>
    <div><div class="h">브랜드별 소재 형식</div>${ftbl}
      <div class="foot" style="margin-top:14px">브랜드당 최신 30개 + ${D.long_days}일 넘게 켜둔 광고 30개까지 수집. ‘다이나믹’=메타가 문구·이미지를 조합하는 광고, ‘카탈로그’=상품 목록 자동 광고.</div></div>`;
}

function render() {
  segs($('#cats'), [['all', '전체 제품'], ['음식물처리기', '음식물처리기', D.ads.filter((a) => a.cats.includes('음식물처리기')).length], ['김치냉장고', '김치냉장고', D.ads.filter((a) => a.cats.includes('김치냉장고')).length], ['기타', '기타 제품']], 'cat');
  $('#cats').insertAdjacentHTML('afterbegin', '<span class="lab">제품군</span>');
  segs($('#brands'), [['all', '전체 브랜드', D.ads.filter(inCat).length], ...D.brands.map((b) => [b.name, b.name + (b.pick ? ' ★' : ''), D.ads.filter((a) => a.brand === b.name && inCat(a)).length])], 'brand');
  $('#brands').insertAdjacentHTML('afterbegin', '<span class="lab">브랜드</span>');
  document.querySelectorAll('#view .seg').forEach((b) => b.classList.toggle('on', b.dataset.v === S.view));

  const ads = shown();
  insights(ads);
  if (S.view === 'long') {
    const longs = ads.filter((a) => a.days >= D.long_days).sort((a, b) => b.days - a.days);
    $('#list').innerHTML = `<section class="sec"><h2>${D.long_days}일 넘게 켜둔 광고 <small>${longs.length}건 · 오래된 순 · 오래 켤수록 효율이 검증된 소재</small></h2>
      ${longs.length ? `<div class="cards">${longs.map(card).join('')}</div>` : '<div class="empty">해당 광고 없음</div>'}</section>`;
    return;
  }
  const bs = D.brands.filter((b) => S.brand === 'all' || b.name === S.brand);
  $('#list').innerHTML = bs.map((b) => {
    const xs = ads.filter((a) => a.brand === b.name).sort((x, y) => y.start.localeCompare(x.start));
    const st = b.ok === false ? ` · <span class="down">이번 갱신 실패 — 이전 데이터</span>` : '';
    return `<section class="sec"><h2>${esc(b.name)}${b.pick ? ' <small>★추천 추가</small>' : ''}
      <small>집행 중 ${b.total ?? '?'}개 · 여기 ${xs.length}개 · 최신순${st}</small>
      <small><a href="${esc(b.url)}" target="_blank" rel="noopener">라이브러리 전체 ↗</a></small></h2>
      ${xs.length ? `<div class="cards">${xs.map(card).join('')}</div>` : '<div class="empty">현재 집행 중인 광고 없음</div>'}</section>`;
  }).join('');
}

document.querySelectorAll('#view .seg').forEach((b) => { b.onclick = () => { S.view = b.dataset.v; render(); }; });
fetch('meta_ads.json?t=' + Date.now()).then((r) => r.json()).then((d) => {
  D = d;
  $('#meta').textContent = `${d.updated} 갱신 · 매일 10·14·18시 자동 · 광고 ${d.ads.length}건`;
  render();
});
