export default function({data, setTriggerValue}) {
  const doc = document;
  const stateKey = '__meteaConfirmationViewport';
  const prefix = `st-key-confirmation_form_${data.jobId}_`;
  const selector = `[class*="${prefix}"]`;
  let timer, restoreTimer;
  const classKey = el => [...el.classList].find(c => c.startsWith(prefix));
  function scroller() {
    const main = doc.querySelector('[data-testid="stMain"]');
    return main && main.scrollHeight > main.clientHeight ? main : doc.scrollingElement;
  }
  function capture(event) {
    const target = event.target instanceof Element ? event.target : null;
    if (!target?.closest('.st-key-local_job_evaluation [data-testid="stFormSubmitButton"]')) return;
    const form = target.closest(selector);
    if (!form) return;
    const forms = [...doc.querySelectorAll(selector)];
    const index = forms.indexOf(form);
    const next = forms.slice(index + 1).find(el => el.getBoundingClientRect().height > 0);
    const open = [...doc.querySelectorAll('[class*="st-key-"]')].filter(el =>
      [...el.classList].some(c => c.startsWith('st-key-job_evaluation_details_') || c.startsWith(prefix)) && el.querySelector('details[open]'))
      .map(el => [...el.classList].find(c => c.startsWith('st-key-job_evaluation_details_') || c.startsWith(prefix)));
    doc[stateKey] = {jobId:data.jobId, anchor:classKey(next || form),
      top:Math.min(160, Math.max(32, form.getBoundingClientRect().top)),
      scrollTop:scroller()?.scrollTop || 0, open, started:Date.now()};
  }
  function restore() {
    const saved = doc[stateKey];
    if (!saved || saved.jobId !== data.jobId) return;
    if (Date.now() - saved.started > 10000) { delete doc[stateKey]; return; }
    if (doc.querySelector('[data-testid="stApp"]')?.getAttribute('data-test-script-state') === 'running') {
      restoreTimer=setTimeout(restore,100); return;
    }
    for (const key of saved.open) {
      const details=doc.querySelector(`.${CSS.escape(key)} details`);
      if (details) details.open=true;
    }
    const anchor=saved.anchor && doc.querySelector(`.${CSS.escape(saved.anchor)}`);
    const scroll=scroller();
    if (scroll) {
      // 保存ボタンが確認済み欄へ移動したときの、ブラウザの自動フォーカス追従を止める。
      if (doc.activeElement?.closest('[data-testid="stFormSubmitButton"]')) doc.activeElement.blur();
      anchor?.querySelector('summary')?.focus({preventScroll:true});
      scroll.scrollTop = anchor && anchor.getBoundingClientRect().height > 0
        ? scroll.scrollTop + anchor.getBoundingClientRect().top - saved.top : saved.scrollTop;
    }
    delete doc[stateKey];
  }
  function cancelRestore() { delete doc[stateKey]; }
  doc.addEventListener('click',capture,true);
  doc.addEventListener('wheel',cancelRestore,{passive:true});
  doc.addEventListener('touchstart',cancelRestore,{passive:true});
  restoreTimer=setTimeout(restore,100);
  function poll() {
    const focused=doc.activeElement;
    const editing=focused?.closest('.st-key-local_job_evaluation') && focused.matches('input, textarea, [role="combobox"], [contenteditable="true"]');
    if (editing) { timer=setTimeout(poll,3000); return; }
    setTriggerValue('poll',Date.now());
  }
  if (data.pending) timer=setTimeout(poll,3000);
  return () => {
    clearTimeout(timer); clearTimeout(restoreTimer);
    doc.removeEventListener('click',capture,true);
    doc.removeEventListener('wheel',cancelRestore);
    doc.removeEventListener('touchstart',cancelRestore);
  };
}
