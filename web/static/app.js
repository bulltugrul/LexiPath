const screen = document.querySelector('#screen');
const errorBox = document.querySelector('#error-message');
let catalog = null;
let learnerState = null;
let chosenTopics = new Set();
let showingHow = false;
let busy = false;
const storageKey = new URLSearchParams(location.search).get('qa') === '1' ? 'kelime-qa-learner' : 'kelime-learner';

const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const percent = value => value == null ? 'Henüz kayıt yok' : `%${Math.round(value * 100)}`;
const probabilityText = value => value > .999 ? '%99,9’dan fazla' : value < .001 ? '%0,1’den az' : `%${(value*100).toLocaleString('tr-TR',{minimumFractionDigits:1,maximumFractionDigits:1})}`;
const modeName = mode => mode === 'listen' ? 'Dinleme' : 'Metin';
const categoryName = kind => ({diagnostic:'Başlangıç',review:'Tekrar',new:'Yeni kelime'}[kind] || kind);

async function api(path, data) {
  const response = await fetch(path, data === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'İşlem tamamlanamadı. Yeniden dene.');
  return body;
}

function showError(error) {
  errorBox.textContent = error.message || String(error);
  errorBox.hidden = false;
  setTimeout(() => errorBox.hidden = true, 6000);
}

async function act(action) {
  if (busy) return;
  busy = true;
  document.querySelectorAll('.topbar button').forEach(b => b.disabled = true);
  screen.querySelectorAll('button[type="submit"],button[data-action]').forEach(b => b.disabled = true);
  try { await action(); } catch (error) { showError(error); }
  finally {
    busy = false;
    document.querySelectorAll('.topbar button').forEach(b => b.disabled = false);
    screen.querySelectorAll('button[type="submit"],button[data-action]').forEach(b => b.disabled = false);
    const start = document.querySelector('#start-button');
    if (start) start.disabled = chosenTopics.size === 0;
  }
}

function journey(active) {
  const order = ['topics','diagnostic','practice','progress'];
  document.querySelectorAll('[data-step]').forEach(el => {
    el.classList.toggle('active', el.dataset.step === active);
    el.classList.toggle('done', order.indexOf(el.dataset.step) < order.indexOf(active));
  });
  document.querySelector('#home-button').hidden = !showingHow;
}

async function welcome() {
  showingHow = false;
  learnerState = null;
  chosenTopics = new Set();
  journey('topics');
  const learners = await api('/api/learners');
  screen.innerHTML = `
    <p class="eyebrow">İLGİ ALANLARINDAN BAŞLA</p>
    <h1>İngilizce kelimeler,<br>senin dünyandan.</h1>
    <p class="lead">Sevdiğin konuları seç. Kısa bir başlangıç çalışmasının ardından sana uygun kelimelerle tekrar yapalım.</p>
    <form id="welcome-form" class="panel">
      <div class="name-row"><label for="learner-name">Adın veya takma adın</label><input id="learner-name" name="name" maxlength="40" autocomplete="given-name" placeholder="Örn. Deniz"></div>
      <div class="topic-grid">${catalog.topics.map(topic => `
        <button class="topic-card" type="button" data-topic="${topic.id}" aria-pressed="false">
          <img src="${topic.image}" alt="${escapeHtml(topic.title)} konusunu temsil eden çizim">
          <span class="topic-check" aria-hidden="true">✓</span>
          <span class="topic-copy"><strong>${escapeHtml(topic.title)}</strong><small>${escapeHtml(topic.description)}</small></span>
        </button>`).join('')}</div>
      <div class="action-row"><button type="submit" class="primary-button" id="start-button" disabled>Başlangıç çalışmasına başla</button><p class="hint">Bir veya daha fazla konu seçebilirsin.<br>Başlangıç çalışması: 6 metin + 6 dinleme sorusu.</p></div>
    </form>
    ${learners.length ? `<div class="resume-box"><label for="resume-select">Kaldığın yerden devam et</label><select id="resume-select">${learners.map(l => `<option value="${l.id}">${escapeHtml(l.name)} · ${l.answers} cevap</option>`).join('')}</select><button type="button" class="outline-button" id="resume-button">Devam et</button></div>` : ''}
    <p class="hint welcome-note">Bu çalışma, belirli kelimelerdeki gözlenen performansını izler; resmî bir dil seviyesi sınavı değildir.</p>`;
  window.scrollTo(0, 0);
  screen.querySelectorAll('[data-topic]').forEach(button => button.addEventListener('click', () => {
    const id = button.dataset.topic;
    chosenTopics.has(id) ? chosenTopics.delete(id) : chosenTopics.add(id);
    button.classList.toggle('selected', chosenTopics.has(id));
    button.setAttribute('aria-pressed', String(chosenTopics.has(id)));
    document.querySelector('#start-button').disabled = chosenTopics.size === 0;
  }));
  document.querySelector('#welcome-form').addEventListener('submit', event => {
    event.preventDefault();
    act(async () => setState(await api('/api/learners', {name:document.querySelector('#learner-name').value,topics:[...chosenTopics]})));
  });
  document.querySelector('#resume-button')?.addEventListener('click', () => act(async () => setState(await api('/api/learners/' + document.querySelector('#resume-select').value))));
}

function setState(state) {
  learnerState = state;
  localStorage.setItem(storageKey, state.learner.id);
  showingHow = false;
  render();
}

function profileCard(progress) {
  const profile = progress.profile;
  if (!profile.group) return `<h2>Ön profilin hazırlanıyor</h2><p class="small-copy">Her iki biçimden altışar cevap tamamlandığında son sonuçların birlikte incelenir.</p><div class="count-grid"><span>Metin ${profile.counts.reverse_translate}/6</span><span>Dinleme ${profile.counts.listen}/6</span></div>`;
  return `<h2>Yakın dönem örüntüsü</h2><div class="profile-label">Grup ${profile.group.number}</div><p class="small-copy">Son 6 metin ve 6 dinleme sonucuna göre geçici bir eşleştirme.</p><div class="count-grid"><span>Metin ${percent(profile.features.text_target_accuracy)}</span><span>Dinleme ${percent(profile.features.listen_target_accuracy)}</span></div><p class="small-copy">Bu grup kalıcı bir öğrenci tipi veya öğrenme stili değildir.</p><p><strong>Çalışma önerisi:</strong> ${escapeHtml(progress.guidance.text)}</p><p class="small-copy">${escapeHtml(progress.guidance.note||'')}</p>`;
}

function tracking(progress) {
  return `<aside class="tracking"><section class="panel"><h2>Gözlenen performans</h2>${['text','listen'].map(key => {
    const m = progress.modes[key];
    return `<div class="mode-stat"><div><span>${key === 'text' ? 'Metin' : 'Dinleme'}</span><strong>${m.count ? `${m.correct}/${m.count}` : '—'}</strong></div><div class="mini-bar"><i style="width:${100*(m.rate || 0)}%"></i></div></div>`;
  }).join('')}<p class="small-copy">Tamamladığın ${progress.total} cevabın özeti.</p></section><section class="panel">${profileCard(progress)}</section><section class="panel topic-panel"><h2>Seçtiğin konular</h2><div class="topic-tags">${catalog.topics.filter(t => learnerState.learner.topics.includes(t.id)).map(t => `<span>${escapeHtml(t.title)}</span>`).join('')}</div></section></aside>`;
}

function audioControl(url) {
  return `<div class="audio-area"><audio id="word-audio" preload="metadata" src="${url}"></audio><button id="play-audio" type="button" class="play-button"><span class="speaker" aria-hidden="true">▶</span>Kaydı dinle</button><span class="audio-note" id="audio-note">İstediğin kadar tekrar dinleyebilirsin.</span></div>`;
}

function wireAudio() {
  const audio = document.querySelector('#word-audio');
  const button = document.querySelector('#play-audio');
  if (!audio || !button) return;
  button.addEventListener('click', async () => {
    try { audio.currentTime = 0; await audio.play(); button.textContent = 'Dinleniyor…'; }
    catch { showError(new Error('Ses başlatılamadı. Kaydı yeniden dinlemeyi dene.')); }
  });
  audio.addEventListener('ended', () => button.innerHTML = '<span class="speaker" aria-hidden="true">▶</span>Yeniden dinle');
  audio.addEventListener('error', () => { document.querySelector('#audio-note').textContent = 'Ses kaydı yüklenemedi.'; });
}

const historyLabels = {general:'Tüm cevapların',word:'Bu kelime',format:'Bu soru biçimi',word_format:'Bu kelime ve soru biçimi',recent:'Son 10 tamamlanmış alıştırma'};
const historyValue = value => `${value.count} kayıt · ${value.correct} doğru · ${percent(value.smoothed_rate)}`;

function predictionCard(prediction) {
  const history = prediction.history;
  const count = history.general.count;
  return `<section class="prediction-card" aria-label="Yanıt öncesi model tahmini">
    <div class="prediction-heading"><h3>Bu soruyu doğru cevaplama tahmini</h3><strong id="prediction-value">${probabilityText(prediction.p_correct)}</strong></div>
    <p>Yanıt vermeden önceki geçmişinden hesaplandı. Kesin sonuç veya öğrenme yüzdesi değildir.</p>
    <p class="history-context">${count === 0 ? 'Henüz kişisel cevap geçmişin yok; tahmin eğitim verisindeki örüntülere dayanıyor.' : `${count < 10 ? 'Kişisel geçmişin henüz sınırlı. ' : ''}Bu biçimde ${history.format.count} cevabın, bu kelimeyle ${history.word.count} önceki karşılaşman var.`}</p>
    <details class="prediction-details"><summary>Tahmin hangi geçmişe dayanıyor?</summary>
      <dl>${Object.entries(historyLabels).map(([key,label])=>`<dt>${label}</dt><dd>${historyValue(history[key])}</dd>`).join('')}</dl>
      <p>Oranlar (doğru + 1) / (kayıt + 2) ile dengelenir; geçmiş yoksa %50 başlar. Bunlar model girdileridir. Son pencere şu an ${history.recent.exercises}/10 alıştırma içeriyor; bu uygulamada her alıştırma tek kelimedir.</p>
    </details></section>`;
}

function historyUpdate(update) {
  if (!update) return '<p class="hint">Bu cevap önceki sürümde kaydedildi; o sıradaki tahmin korunuyor. Ayrıntılı önce/sonra tablosu yeni cevaplarda bulunur.</p>';
  return `<details class="detail-box history-update"><summary>Bu cevap geçmişimi nasıl güncelledi?</summary>
    <ol><li>Model yalnız önceki tamamlanmış cevapları kullanarak tahmin yaptı.</li><li>Cevabın kontrol edilip bir kez kaydedildi.</li><li>İlgili sayaçlar ve son 10 alıştırma penceresi güncellendi. Sonraki soru bu geçmişi kullanacak.</li></ol>
    <div class="history-table-wrap"><table><caption>Oran = (doğru + 1) / (kayıt + 2)</caption><thead><tr><th scope="col">Geçmiş</th><th scope="col">Yanıt öncesi</th><th scope="col">Yanıt sonrası</th></tr></thead>
    <tbody>${Object.entries(historyLabels).map(([key,label])=>`<tr><th scope="row">${label}</th><td>${historyValue(update.before[key])}</td><td>${historyValue(update.after[key])}</td></tr>`).join('')}</tbody></table></div>
    <p>Son pencere ${update.before.recent.exercises}/10 → ${update.after.recent.exercises}/10 alıştırma. On kayıt dolduğunda en eski alıştırma çıkar. Yanıt öncesi tahmin geriye dönük değiştirilmez; model ağırlıkları sabittir. K-Means ayrıca son 6 metin ve 6 dinleme sonucunu kullanır.</p>
  </details>`;
}

function visualPanel() {
  const task=learnerState.visual;
  if (!task) return `<section class="panel" style="margin-top:20px"><h2>Görselle tekrar</h2><p class="hint">Yanlış cevapladığın ve görsel bankasında bulunan kelimelerden model destekli bir tekrar yap.</p><button class="outline-button" id="visual-start">Görsel çalışma aç</button></section>`;
  return `<section class="panel" style="margin-top:20px"><h2>Resimdeki nesneyi seç</h2><img src="${task.image}" alt="Kelime alıştırması için nesne resmi" style="width:100%;max-width:320px;display:block;margin:auto">${task.answered ? `<p>${task.correct?'Doğru seçim.':'Doğru kelimeyi birlikte görelim.'} <strong>${escapeHtml(task.expected)}</strong></p><p>${escapeHtml(task.example)}</p><p class="hint">Bu kelime, tekrar aralığına uygun sonraki metin/dinleme kontrolüne eklendi. Görsel seçim ayrı kaydedildi; model geçmişine yalnız o kontrolün sonucu girecek.</p>` : `<div class="action-row">${task.options.map(w=>`<button class="outline-button" data-visual-choice="${w}">${w}</button>`).join('')}</div>`}<p class="hint" style="margin-top:15px">${escapeHtml(task.reason)}</p></section>`;
}
function wireVisual() {
 document.querySelector('#visual-start')?.addEventListener('click',()=>act(async()=>setState(await api(`/api/learners/${learnerState.learner.id}/visual`,{}))));
 document.querySelectorAll('[data-visual-choice]').forEach(button=>button.addEventListener('click',()=>act(async()=>setState(await api(`/api/learners/${learnerState.learner.id}/visual-answer`,{task_id:learnerState.visual.id,choice:button.dataset.visualChoice})))));
}

function render() {
  const state = learnerState;
  if (!state) return;
  journey(state.stage === 'summary' ? 'progress' : state.session.kind === 'diagnostic' ? 'diagnostic' : 'practice');
  if (state.stage === 'summary') return renderSummary();
  const s = state.session;
  const title = s.kind === 'diagnostic' ? 'Başlangıç çalışması' : `Çalışma turu ${s.round_number}`;
  const position = state.stage === 'question' ? s.position + 1 : s.position;
  let card;
  if (state.stage === 'question') {
    const q = state.question;
    card = `<div class="badge ${q.mode === 'listen' ? 'listen' : ''}">${modeName(q.mode)}</div> <span class="badge ${q.category === 'new' ? 'new' : ''}">${categoryName(q.category)}</span>
      <h2>${q.mode === 'listen' ? 'Duyduğun kelimeyi yaz.' : 'Bu kelimenin İngilizcesini yaz.'}</h2>
      <p class="topic-line">${escapeHtml(q.topic)}</p>
      ${q.mode === 'listen' ? audioControl(q.audio) : `<div class="word-cue">${escapeHtml(q.prompt)}</div>`}
      ${q.letter_hint ? `<p class="hint">İlk harf: <strong>${escapeHtml(q.letter_hint.first)}</strong> · ${q.letter_hint.length} harf. Bu bilgiye uygun tek kelime yaz.</p>` : ''}
      ${q.prediction ? predictionCard(q.prediction) : '<p class="hint">Başlangıç ölçümü: bu bölümde tahmin gösterilmez.</p>'}
      <form id="answer-form" class="answer-form"><label for="answer-input" class="answer-label">İngilizce cevabın</label><input id="answer-input" class="answer-input" name="answer" placeholder="Bir kelime yaz" maxlength="80" required autocomplete="off" autocapitalize="none" spellcheck="false"><button class="primary-button" type="submit">Cevabı kontrol et</button></form>`;
  } else {
    const f = state.feedback;
    card = `<div class="feedback-symbol ${f.correct ? '' : 'incorrect'}" aria-hidden="true">${f.correct ? '✓' : '·'}</div><h2 class="feedback-title">${f.correct ? 'Doğru cevap.' : 'Doğru kelimeyi birlikte görelim.'}</h2>
      ${!f.correct ? `<p class="submitted">Senin cevabın: ${escapeHtml(f.submitted)}</p>` : ''}
      <div class="expected-word">${escapeHtml(f.expected)}</div><div class="translation">${escapeHtml(f.turkish)}</div>
      <p class="example-sentence">${escapeHtml(f.example)}</p>
      ${f.deferred ? '<p class="deferred-note">Bu kelimeyi sonraki çalışma turuna bıraktık.</p>' : ''}
      <button type="button" class="primary-button" data-action id="next-button">${f.last_question ? 'Sonuçları gör' : 'Sonraki soru'}</button>
      ${f.p_correct_before == null ? '' : `<div class="prediction-recap">${f.model_version === 'lr6-v1' ? 'Önceki sürümdeki yanıt öncesi tahmin' : 'Yanıt öncesi model tahmini'}: <strong>${probabilityText(f.p_correct_before)}</strong></div>`}
      ${historyUpdate(f.history_update)}
      <details class="detail-box"><summary>Bu soru nasıl seçildi?</summary><p>${escapeHtml(f.reason)}</p><p>Tahmin yanıtından önce hesaplandı. Geri bildirimde aynı değer korunur; sonraki sorunun tahmini güncel geçmişle ayrıca hesaplanır.</p></details>`;
  }
  screen.innerHTML = `<p class="greeting">${escapeHtml(state.learner.name)}, kaldığımız yerden.</p><div class="section-heading"><h1>${title}</h1><span class="counter">${position} / ${s.total}</span></div><div class="progress-track"><div class="progress-fill" style="width:${100*s.position/s.total}%"></div></div><div class="question-layout"><section class="panel question-card">${card}</section>${tracking(state.progress)}</div>`;
  if (state.notice) screen.insertAdjacentHTML('afterbegin', `<p class="migration-note">${escapeHtml(state.notice)}</p>`);
  document.querySelector('#answer-form')?.addEventListener('submit', event => {
    event.preventDefault();
    const answer = document.querySelector('#answer-input').value;
    act(async () => setState(await api(`/api/learners/${state.learner.id}/answer`, {question_id:state.question.id, answer})));
  });
  document.querySelector('#next-button')?.addEventListener('click', () => act(async () => setState(await api(`/api/learners/${state.learner.id}/next`, {}))));
  if (state.diagnostic_complete && state.stage === 'feedback') { screen.insertAdjacentHTML('beforeend',visualPanel()); wireVisual(); }
  wireAudio();
  window.scrollTo(0, 0);
  if (state.stage === 'question') document.querySelector('#answer-input').focus({preventScroll:true});
}

function progressChart(points) {
  if (!points.length) return '<div class="empty-chart">Cevapların burada görünecek.</div>';
  const width = 480, height = 180, left = 40, right = 15, top = 18, bottom = 30;
  const x = index => left + (index-1)/Math.max(points.length-1,1)*(width-left-right);
  const y = value => height-bottom-value*(height-top-bottom);
  const line = points.map(p => `${x(p.index)},${y(p.rate)}`).join(' ');
  return `<svg class="line-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Cevap anlarındaki genel doğruluk değişimi">${[0,.5,1].map(v => `<line x1="${left}" x2="${width-right}" y1="${y(v)}" y2="${y(v)}" stroke="#dce6ed"/><text x="${left-8}" y="${y(v)+4}" text-anchor="end" fill="#6b8092" font-size="12">${100*v}%</text>`).join('')}<polyline points="${line}" fill="none" stroke="#147780" stroke-width="3"/>${points.map(p => `<circle cx="${x(p.index)}" cy="${y(p.rate)}" r="3" fill="#147780"><title>${p.index}. cevap · ${percent(p.rate)} · ${escapeHtml(new Date(p.timestamp).toLocaleTimeString('tr-TR'))}</title></circle>`).join('')}<text x="${left}" y="${height-7}" fill="#6b8092" font-size="12">1. cevap</text><text x="${width-right}" y="${height-7}" text-anchor="end" fill="#6b8092" font-size="12">${points.length}. cevap</text></svg>`;
}

function evidencePanel(e) {
 const mode=m=>m==='listen'?'Dinleyerek yazma':'Metinden yazma';
 return `<section class="panel" style="margin-top:22px"><h2>Konu ve biçime göre kanıt</h2><p>${escapeHtml(e.interpretation)}</p><div class="history-table-wrap"><table style="width:100%;text-align:left"><thead><tr><th>Konu / biçim</th><th>Aşama</th><th>Doğru / toplam</th><th>Kelime / tur</th></tr></thead><tbody>${e.areas.map(a=>`<tr><th>${escapeHtml(a.topic)} / ${mode(a.format)}</th><td>${a.phase}</td><td>${a.correct}/${a.count} · ${percent(a.rate)}</td><td>${a.words} / ${a.rounds}</td></tr>`).join('')}</tbody></table></div><h3>Tekrarlı kelime kanıtı</h3>${e.repeated_words.length?`<ul>${e.repeated_words.map(a=>`<li>${escapeHtml(a.word)} / ${mode(a.format)}: ${a.label}; son sonuçlar ${a.last_three.map(v=>v?'D':'Y').join(' → ')}, ${a.rounds} tur.</li>`).join('')}</ul>`:'<p>Henüz en az iki turda üç alıştırma kaydı olan belirgin kelime örüntüsü yok. Alanlar için yalnız gözlenen sayılar gösteriliyor.</p>'}<details><summary>Tur ve zamana göre ilerleme</summary><p>Aşağıdaki oranlar farklı görevlerdeki gözlemlerdir; değişim tek başına öğrenme etkisi değildir.</p><ul>${e.timeline.map((a,i)=>`<li>${a.phase} / ${mode(a.format)}: ${a.correct}/${a.count} · ${percent(a.rate)} · ${escapeHtml(new Date(a.last_at).toLocaleString('tr-TR'))}</li>`).join('')}</ul></details></section>`;
}

function renderSummary() {
  const state = learnerState, s = state.session, p = state.progress;
  screen.innerHTML = `<p class="eyebrow">ÇALIŞMANIN ÖZETİ</p><div class="panel"><div class="summary-intro"><div><h1>${s.kind === 'diagnostic' ? 'Başlangıç çalışman tamamlandı.' : 'Bu çalışma turu tamamlandı.'}</h1><p class="lead">${escapeHtml(state.learner.name)}, cevapların kaydedildi. Bir sonraki turda seçtiğin konularla devam edebilirsin.</p></div><div class="score-large">${s.correct}/${s.total}<small>bu çalışmada doğru</small></div></div><div class="action-row"><button type="button" class="primary-button" data-action id="round-button">${s.kind === 'diagnostic' ? '6 soruluk çalışmaya başla' : 'Yeni çalışma turu'}</button><a class="export-link" href="/api/learners/${state.learner.id}/export">Çalışma kaydını indir</a></div><p class="hint" style="margin-top:17px">Tur planı: 3 metin + 3 dinleme; uygun havuz varsa 4 tekrar + 2 yeni kelime.</p></div>
    <div class="summary-grid"><section class="panel"><h2>Gözlenen doğruluğun değişimi</h2>${progressChart(p.chart)}<p>Cevap anlarında hesaplanan genel doğruluk. Grafikteki kümülatif oran tek başına konu yeterliliği değildir; konu ve biçim bazlı oranlar aşağıdaki tabloda ayrı gösterilir.</p><div class="word-tags">${s.wrong_words.map(w => `<span>${escapeHtml(w)}</span>`).join('')}</div>${s.wrong_words.length ? '<p>Bu çalışmada yanlış cevaplanan kelimeler.</p>' : '<p>Bu çalışmadaki bütün hedefleri doğru cevapladın.</p>'}</section><section class="panel"><div class="summary-profile">${profileCard(p)}</div><p>Grup eşleştirmesi son cevaplardan oluşur; soru seçimini değiştirmez. Yeni cevaplarla güncellenebilir.</p></section><section class="panel"><h2>Son cevapların</h2><ul class="recent-list">${p.recent.map(r => `<li><span>${escapeHtml(r.word)}<small>${modeName(r.format)} · ${escapeHtml(new Date(r.timestamp).toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit'}))}</small></span><strong class="${r.correct ? 'result-ok' : 'result-error'}">${r.correct ? 'Doğru' : 'Yanlış'}</strong></li>`).join('')}</ul></section><section class="panel"><h2>İki çalışma biçimi</h2>${['text','listen'].map(key => {const m=p.modes[key];return `<div class="mode-stat"><div><span>${key==='text'?'Metin':'Dinleme'}</span><strong>${m.correct}/${m.count} · ${percent(m.rate)}</strong></div><div class="mini-bar"><i style="width:${100*(m.rate||0)}%"></i></div></div>`;}).join('')}<p>Toplam ${p.total} tamamlanmış cevabının özeti.</p></section></div>`;
  screen.insertAdjacentHTML('beforeend',evidencePanel(p.evidence));
  screen.insertAdjacentHTML('beforeend',visualPanel()); wireVisual();
  document.querySelector('#round-button').addEventListener('click', () => act(async () => setState(await api(`/api/learners/${state.learner.id}/round`, {}))));
  window.scrollTo(0, 0);
}

function renderHow() {
  showingHow = true;
  journey(learnerState?.diagnostic_complete ? 'practice' : learnerState ? 'diagnostic' : 'topics');
  screen.innerHTML = `<p class="eyebrow">SİSTEMİN İŞLEYİŞİ</p><h1>İki model, ortak cevap geçmişi.</h1><p class="lead">Tamamlanan her cevap bir kez kaydedilir. Aynı geçmişten sonraki sorunun olasılığı ve yakın dönem öğrenci profili hazırlanır.</p><div class="explanation-grid"><section class="panel"><span class="badge">Denetimli öğrenme</span><h2 style="margin-top:15px">Lojistik regresyon</h2><p>12 girdili lojistik regresyon; hedef kelime, soru biçimi, genel ve kelime geçmişi, biçime özel geçmiş ve son 10 tamamlanmış alıştırmadaki performansı kullanır. Tahmin yanıt öncesinde gösterilir ve açık soru seçme kurallarına girdi sağlar.</p></section><section class="panel"><span class="badge listen">Denetimsiz öğrenme</span><h2 style="margin-top:15px">K-Means</h2><p>Son 6 metin ve 6 dinleme hedefinin gerçek sonuçlarını gruplandırır. En az altışar kayıt olmadan profil atanmaz. Lojistik regresyonun tahminleri bu modelin girdisi değildir.</p></section></div><section class="architecture-section"><h2>Öğrenme görevlerinin blok diyagramı</h2><p class="hint">Dikdörtgenler öğrenme görevlerini, okların yanındaki alanlar giriş ve çıkışları gösterir.</p><a href="/diagrams/ml_blok_diyagrami.svg" target="_blank" rel="noopener"><img class="architecture-img" src="/diagrams/ml_blok_diyagrami.svg" alt="Lojistik regresyon ve K-Means giriş çıkış blok diyagramı"></a></section><section class="architecture-section"><h2>Dört kelimelik öğretim modülü</h2><p class="hint">Bu şekil dört kelimelik öğretim pilotunu gösterir. Ana alıştırma modülü konu seçimi, 12 soruluk başlangıç ve 6 soruluk turlarla ilerler; her modül kendi geçmişini tutar.</p><a href="/diagrams/ogrenci_akisi.svg" target="_blank" rel="noopener"><img class="architecture-img" src="/diagrams/ogrenci_akisi.svg" alt="Dört kelimelik pilot: ölçüm, öğretim, yardımsız kontrol, 24 saat kontrolü ve tekrar"></a></section><p class="hint welcome-note">Modeller önceden eğitilmiştir. Çalışma sırasında ağırlıkları değiştirilmez; yalnız tamamlanan cevap geçmişi güncellenir.</p>`;
  window.scrollTo(0, 0);
}

document.querySelector('#how-button').addEventListener('click', renderHow);
document.querySelector('#home-button').addEventListener('click', () => {showingHow=false;learnerState ? render() : welcome().catch(showError);});
document.querySelector('#new-button').addEventListener('click', () => {localStorage.removeItem(storageKey);welcome().catch(showError);});

(async () => {
  try {
    catalog = await api('/api/catalog');
    const learner = new URLSearchParams(location.search).get('learner') || localStorage.getItem(storageKey);
    if (learner) { try { setState(await api('/api/learners/'+learner)); return; } catch {localStorage.removeItem(storageKey);} }
    await welcome();
  } catch (error) { showError(error); screen.innerHTML='<div class="panel"><h1>Çalışma alanı açılamadı.</h1><p>Yerel uygulamanın çalıştığından emin olup sayfayı yenile.</p></div>'; }
})();
