window.initializeRichTextEditors = function initializeRichTextEditors(options) {
  const config = options || {};
  document.querySelectorAll('[data-rich-editor]').forEach(function (editorRoot) {
    const textarea = editorRoot.querySelector('.rich-text-source');
    const surface = editorRoot.querySelector('[data-editor-surface]');
    const buttons = editorRoot.querySelectorAll('[data-command]');
    const linkInput = editorRoot.querySelector('[data-link-url]');

    if (!textarea || !surface) {
      return;
    }

    surface.setAttribute('data-placeholder', textarea.getAttribute('placeholder') || '');
    if (!surface.innerHTML.trim()) {
      surface.innerHTML = textarea.value || '';
    }

    function sync() {
      textarea.value = surface.innerHTML.trim();
    }

    buttons.forEach(function (button) {
      button.addEventListener('click', function () {
        const command = button.getAttribute('data-command');
        const commandValue = button.getAttribute('data-value') || null;
        surface.focus();
        if (command === 'createLink') {
          const url = linkInput ? linkInput.value.trim() : '';
          if (!url) {
            return;
          }
          document.execCommand(command, false, url);
          if (linkInput) {
            linkInput.value = '';
          }
        } else {
          document.execCommand(command, false, commandValue);
        }
        sync();
      });
    });

    surface.addEventListener('input', sync);
    surface.closest('form').addEventListener('submit', sync);
    sync();
  });
};