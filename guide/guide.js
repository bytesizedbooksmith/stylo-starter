
document.querySelectorAll('.copy').forEach(button => {
  button.addEventListener('click', async () => {
    const box = button.closest('.prompt');
    const text = box.querySelector('code').textContent;
    const status = box.querySelector('.copy-status');
    let copied = false;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        copied = true;
      }
    } catch (_) {}
    if (!copied) {
      const field = document.createElement('textarea');
      field.value = text;
      field.style.position = 'fixed';
      field.style.top = '0';
      field.style.left = '-9999px';
      document.body.appendChild(field);
      field.select();
      try { copied = document.execCommand('copy'); } catch (_) {}
      field.remove();
      button.focus();
    }
    status.textContent = copied ? 'Copied. Paste it into your AI conversation.' : 'Select the prompt text and copy it with Ctrl+C (Windows) or Command+C (Mac).';
  });
});
