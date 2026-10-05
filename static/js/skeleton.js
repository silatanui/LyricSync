/**
 * LyricSync skeleton helpers: shimmer placeholders for images and text.
 */
(function () {
    function markLoaded(el) {
        if (!el) return;
        el.classList.add('is-loaded');
        el.classList.remove('is-loading');
        const wrap = el.closest('.sk-media');
        if (wrap) wrap.classList.add('is-ready');
    }

    function watchMedia(el) {
        if (!el) return;
        el.dataset.skBound = '1';
        el.classList.add('is-loading');
        el.classList.remove('is-loaded');
        const wrap = el.closest('.sk-media');
        if (wrap) wrap.classList.remove('is-ready');

        if (el.tagName === 'IMG') {
            if (el.complete && el.naturalWidth > 0) {
                markLoaded(el);
            } else {
                el.addEventListener('load', () => markLoaded(el), { once: true });
                el.addEventListener('error', () => markLoaded(el), { once: true });
            }
        } else if (el.tagName === 'VIDEO') {
            if (el.readyState >= 2) {
                markLoaded(el);
            } else {
                el.addEventListener('loadeddata', () => markLoaded(el), { once: true });
                el.addEventListener('error', () => markLoaded(el), { once: true });
            }
        }
    }

    function bindMedia(root) {
        const scope = root && root.querySelectorAll ? root : document;
        scope.querySelectorAll('img.sk-img, video.sk-img').forEach((el) => {
            if (el.dataset.skBound === '1') return;
            watchMedia(el);
        });
    }

    function rebindMedia(root) {
        const scope = root && root.querySelectorAll ? root : document;
        const nodes = scope.matches && scope.matches('img.sk-img, video.sk-img')
            ? [scope]
            : Array.from(scope.querySelectorAll('img.sk-img, video.sk-img'));
        nodes.forEach((el) => {
            delete el.dataset.skBound;
            watchMedia(el);
        });
    }

    function themeGridSkeleton(count) {
        const n = Math.max(4, Number(count) || 8);
        let html = '';
        for (let i = 0; i < n; i++) {
            html += `
            <div class="col-6">
                <div class="sk-theme-card" aria-hidden="true">
                    <div class="sk-block sk-img-block"></div>
                    <div class="sk-line sk-w-70"></div>
                    <div class="sk-line sk-w-45"></div>
                </div>
            </div>`;
        }
        return html;
    }

    function lyricsSheetSkeleton() {
        return `
            <div class="sk-lyrics" aria-busy="true" aria-live="polite">
                <div class="sk-line sk-w-30 sk-mb"></div>
                <div class="sk-line sk-w-90"></div>
                <div class="sk-line sk-w-80"></div>
                <div class="sk-line sk-w-85"></div>
                <div class="sk-line sk-w-55 sk-mb"></div>
                <div class="sk-line sk-w-30 sk-mb"></div>
                <div class="sk-line sk-w-88"></div>
                <div class="sk-line sk-w-75"></div>
                <div class="sk-line sk-w-92"></div>
                <div class="sk-line sk-w-60"></div>
            </div>`;
    }

    function filesGridSkeleton(count) {
        const n = Math.max(3, Number(count) || 6);
        let html = '<div class="sk-files-grid" aria-busy="true">';
        for (let i = 0; i < n; i++) {
            html += `<div class="sk-block sk-file-tile"></div>`;
        }
        html += '</div>';
        return html;
    }

    function projectCardSkeleton(count) {
        const n = Math.max(3, Number(count) || 6);
        let html = '';
        for (let i = 0; i < n; i++) {
            html += `
            <article class="project-item sk-project-item" aria-hidden="true">
                <div class="project-card sk-project-card">
                    <div class="sk-block sk-project-thumb"></div>
                    <div class="project-card-body">
                        <div class="sk-line sk-w-40"></div>
                        <div class="sk-line sk-w-80 sk-mb"></div>
                        <div class="sk-line sk-w-95"></div>
                        <div class="sk-line sk-w-70"></div>
                    </div>
                </div>
            </article>`;
        }
        return html;
    }

    window.LyricSyncSkeleton = {
        bindMedia,
        rebindMedia,
        markLoaded,
        themeGridSkeleton,
        lyricsSheetSkeleton,
        filesGridSkeleton,
        projectCardSkeleton,
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => bindMedia(document));
    } else {
        bindMedia(document);
    }
})();
