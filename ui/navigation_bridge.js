export default function({data, setTriggerValue}) {
  const doc = document;
  const app = doc.querySelector('[data-testid="stApp"]');
  const allowed = new Set(data.pages);
  let timer;
  let idleTimer;
  let pending = false;
  let sawRunning = false;
  let banner = doc.getElementById('metea-transition-status');
  if (!banner) {
    banner = doc.createElement('div');
    banner.id = 'metea-transition-status';
    banner.setAttribute('role', 'status');
    banner.setAttribute('aria-live', 'polite');
    banner.textContent = '処理しています。画面が切り替わるまでお待ちください…';
    Object.assign(banner.style, {position:'fixed',top:'12px',left:'50%',transform:'translateX(-50%)',zIndex:'999999',padding:'12px 18px',border:'1px solid #bdd3f7',borderRadius:'10px',background:'#f3f7ff',color:'#123b75',fontSize:'14px',boxShadow:'0 3px 12px #16345b22',width:'max-content',maxWidth:'calc(100vw - 28px)',pointerEvents:'none',display:'none'});
    doc.body.appendChild(banner);
  }
  function show() { clearTimeout(idleTimer); if (banner.style.display === 'none') banner.textContent = '処理しています。画面が切り替わるまでお待ちください…'; banner.style.display = 'block'; }
  function hide() { clearTimeout(timer); banner.style.display = 'none'; pending = false; sawRunning = false; }
  function running() { return app?.getAttribute('data-test-script-state') === 'running'; }
  function stateChanged() {
    if (running()) { sawRunning = true; if (pending || !doc.querySelector('.st-key-local_job_evaluation')) show(); }
    else if (!pending || sawRunning) { clearTimeout(idleTimer); idleTimer = setTimeout(hide, 180); }
  }
  function click(event) {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const target = event.target instanceof Element ? event.target : null;
    const link = target?.closest('a[href]');
    if (link) {
      if (link.hasAttribute('download') || (link.target && link.target !== '_self')) return;
      const raw = link.getAttribute('href');
      if (!raw || raw.startsWith('#')) return;
      const url = new URL(raw, doc.baseURI);
      if (url.origin !== location.origin || url.pathname !== location.pathname || url.hash) return;
      const page = url.searchParams.get('page') || 'home';
      if (!allowed.has(page)) return;
      event.preventDefault();
      if (pending) return;
      pending = true; sawRunning = false; show();
      // URLや入力内容をHTML化せず、検証対象データとしてPythonへ渡す。
      setTriggerValue('navigate', url.search || '?');
      clearTimeout(timer);
      timer = setTimeout(() => { if (pending) banner.textContent = '処理に時間がかかっています。接続状態をご確認ください。'; }, 15000);
    } else if (target?.closest('[data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button')) {
      if (target.closest('.st-key-local_job_evaluation')) { hide(); return; }
      show();
      clearTimeout(idleTimer);
      idleTimer = setTimeout(() => { if (!running()) hide(); }, 500);
    }
  }
  const observer = new MutationObserver(stateChanged);
  if (app) observer.observe(app, {attributes:true,attributeFilter:['data-test-script-state']});
  doc.addEventListener('click', click);
  stateChanged();
  return () => {doc.removeEventListener('click',click); observer.disconnect();clearTimeout(timer);clearTimeout(idleTimer);};
}
