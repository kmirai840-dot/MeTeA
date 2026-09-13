export default function({data}) {
  // No server events: inputs stay in the form until its submit button is pressed.
  const update = () => {
    for (const rule of data.rules) {
      const control = document.querySelector(`.st-key-${rule.control}`);
      const target = document.querySelector(`.st-key-${rule.target}`);
      if (!target || !control) continue;
      const tokens = Array.from(control.querySelectorAll('[data-baseweb="tag"] [title], [data-testid="stMultiSelectToken"]')).map(e => (e.getAttribute('title') || e.textContent).trim());
      const selected = control.querySelector('input[role="combobox"]')?.value ?? control.querySelector('[data-baseweb="select"]')?.textContent.trim();
      const checked = rule.values ? rule.values.includes(selected)
        : rule.kind === 'multi' ? tokens.includes(rule.value)
        : rule.kind === 'multi_any' ? tokens.length > 0
        : rule.value === null
        ? !!control.querySelector('input[type="checkbox"]')?.checked
        : (control.querySelector('input[role="combobox"]')?.value ?? control.querySelector('[data-baseweb="select"]')?.textContent.trim()) === rule.value;
      const additional = !rule.andControl || document.querySelector(`.st-key-${rule.andControl} input[role="combobox"]`)?.value !== rule.notValue;
      target.style.display = ((rule.invert ? !checked : checked) && additional) ? 'flex' : 'none';
    }
  };
  const timer = setInterval(update, 100);
  update();
  return () => clearInterval(timer);
}
