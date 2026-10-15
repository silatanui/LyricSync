/**
 * Show / hide password fields that use .password-field markup.
 */
(() => {
    function bindToggle(btn) {
        if (!btn || btn.dataset.bound === '1') return;
        const targetId = btn.getAttribute('data-password-toggle');
        const input = targetId
            ? document.getElementById(targetId)
            : btn.closest('.password-field')?.querySelector('input');
        if (!input) return;
        btn.dataset.bound = '1';

        const icon = btn.querySelector('i');
        const setState = (visible) => {
            input.type = visible ? 'text' : 'password';
            btn.setAttribute('aria-pressed', visible ? 'true' : 'false');
            btn.setAttribute('aria-label', visible ? 'Hide password' : 'Show password');
            btn.title = visible ? 'Hide password' : 'Show password';
            if (icon) {
                icon.classList.toggle('bi-eye', !visible);
                icon.classList.toggle('bi-eye-slash', visible);
            }
        };

        setState(input.type === 'text');
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            setState(input.type === 'password');
        });
    }

    function init(root = document) {
        root.querySelectorAll('[data-password-toggle]').forEach(bindToggle);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => init());
    } else {
        init();
    }
    window.LyricSyncPasswordToggle = { init };
})();
