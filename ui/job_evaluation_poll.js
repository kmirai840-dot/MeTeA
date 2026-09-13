export default function({data, setTriggerValue}) {
  if (!data.pending) return;
  let timer;
  function poll() {
    const focused = document.activeElement;
    const editing = focused?.closest('.st-key-local_job_evaluation') &&
      (focused.matches('input, textarea, [role="combobox"], [contenteditable="true"]'));
    // 入力中の選択肢・下書きを更新で閉じない。入力を離れると確認を再開する。
    if (editing) { timer = setTimeout(poll, 3000); return; }
    setTriggerValue('poll', Date.now());
  }
  timer = setTimeout(poll, 3000);
  return () => clearTimeout(timer);
}
