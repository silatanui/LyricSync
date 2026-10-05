/**
 * LyricSync Synchronized Video & Audio Player Engine
 * Canva-like clean rendering, font family selector, audio sync, draft/master quality scaling, and zero illuminations.
 */
class SynchronizedPlayer {
    constructor(videoEl, audioEl, overlayEl, options = {}) {
        this.video = videoEl;
        this.audio = audioEl;
        this.overlay = overlayEl;
        this.bgImage = options.bgImageEl || document.getElementById('mainBgImage');
        this.activeLineContainer = document.getElementById('activeLineContainer');
        this.displayActiveText = document.getElementById('displayActiveText');

        // Check data-has-video attribute on videoContainer
        const container = document.getElementById('videoContainer');
        if (container && container.getAttribute('data-has-video') !== null) {
            this.hasVideo = container.getAttribute('data-has-video') === 'true';
        } else {
            this.hasVideo = !!(this.video && !this.video.classList.contains('d-none') && (this.video.currentSrc || this.video.querySelector('source')));
        }

        this.songTitle = options.songTitle || '';
        this.lines = [];
        this.allWords = [];
        this.currentWordIndex = 0;
        this.activeLineIndex = -1;
        this.animationFrameId = null;
        this.quality = '720';
        this._fallbackDuration = 0;
        this._effectPlayKey = null;
        this._lastChunkKey = null;
        this._EFFECT_CLASSES = [
            'lyric-effect-fade',
            'lyric-effect-bounce',
            'lyric-effect-slide',
            'lyric-effect-pulse',
            'lyric-effect-typewriter',
        ];

        // Visual styling configuration kept compact for dense lyric layouts.
        this.style = {
            format: 'stanza',
            mode: 'karaoke',
            font: 'Caveat',
            fontSize: 36,
            lineHeight: 0.9,
            letterSpacing: 0,
            fontWeight: 600,
            textCase: 'as_is',
            primaryColor: '#FFFFFF',
            highlightColor: '#10B981',
            position: 'center',
            textAlign: 'center',
            outlineEnabled: true,
            outline: 2,
            outlineColor: '#000000',
            outlineSoftness: 0,
            shadowEnabled: true,
            shadow: 3,
            shadowColor: '#000000',
            shadowOpacity: 70,
            shadowAngle: 45,
            shadowBlur: 2,
            bevelEnabled: false,
            bevelSize: 2,
            bevelSoftness: 1,
            bevelAngle: 135,
            bevelHighlightColor: '#FFFFFF',
            bevelHighlightOpacity: 55,
            bevelShadowColor: '#000000',
            bevelShadowOpacity: 45,
        };

        this._setupListeners();
    }

    setSongTitle(title) {
        this.songTitle = (title || '').trim();
        this.renderActiveFrame(this.currentTime);
    }

    splitSongCredit(fullTitle) {
        const raw = (fullTitle || '').trim();
        if (!raw) return { artist: '', title: '' };
        const parts = raw.split(/\s+[-–—]\s+/);
        if (parts.length >= 2) {
            return {
                artist: parts[0].trim(),
                title: parts.slice(1).join(' - ').trim(),
            };
        }
        return { artist: '', title: raw };
    }

    _easeOutCubic(t) {
        const x = Math.min(1, Math.max(0, t));
        return 1 - Math.pow(1 - x, 3);
    }

    _escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    _renderCinematicIntro(time, introEnd) {
        const credit = this.splitSongCredit(this.songTitle);
        const displayTitle = this._escapeHtml(credit.title || this.songTitle);
        const artist = this._escapeHtml(credit.artist);
        const accent = this.style.highlightColor || '#10B981';
        const primary = this.style.primaryColor || '#FFFFFF';
        const titleSize = Math.round((this.style.fontSize || 34) * 1.45);

        const fadeInEnd = Math.min(1.15, introEnd * 0.34);
        const holdStart = Math.min(introEnd * 0.72, introEnd - 0.45);
        const fadeOutStart = Math.max(holdStart, introEnd - 0.55);

        let opacity = 1;
        if (time < fadeInEnd) {
            opacity = this._easeOutCubic(time / Math.max(0.2, fadeInEnd));
        } else if (time >= fadeOutStart) {
            opacity = 1 - this._easeOutCubic((time - fadeOutStart) / Math.max(0.2, introEnd - fadeOutStart));
        }

        const rise = (1 - opacity) * 14;
        const scale = 0.94 + (opacity * 0.06);
        const ruleScale = Math.min(1, opacity * 1.15);
        const kickerOpacity = Math.min(1, opacity * 1.2);
        const artistOpacity = artist ? Math.min(1, Math.max(0, (opacity - 0.15) / 0.85)) : 0;

        const artistHtml = artist
            ? `<div class="st-artist" style="color: ${accent}; opacity: ${artistOpacity.toFixed(3)};">${artist}</div>`
            : '';

        this.displayActiveText.innerHTML = `
            <div class="song-title-cinematic" style="opacity: ${opacity.toFixed(3)}; transform: translateY(${rise.toFixed(1)}px) scale(${scale.toFixed(3)});">
                <div class="st-kicker" style="color: ${accent}; opacity: ${kickerOpacity.toFixed(3)};">Now Playing</div>
                <div class="st-rule" style="color: ${accent}; transform: scaleX(${ruleScale.toFixed(3)});"></div>
                <div class="st-title" style="font-size: ${titleSize}px; color: ${primary};">${displayTitle}</div>
                ${artistHtml}
            </div>
        `;
    }

    get usesAudioClock() {
        // Master song audio always drives timeline/lyrics. Theme MP4s are looping wallpaper only.
        return !!(this.audio && !this.audio.error);
    }

    get clockElement() {
        if (this.usesAudioClock) {
            return this.audio;
        }
        if (this.hasVideo && this.video && !this.video.error && this.video.readyState >= 1) {
            return this.video;
        }
        return this.audio || this.video;
    }

    get currentTime() {
        const clock = this.clockElement;
        return clock ? (clock.currentTime || 0) : 0;
    }

    setFallbackDuration(seconds) {
        const n = Number(seconds);
        if (n > 0 && !isNaN(n)) {
            this._fallbackDuration = n;
        }
    }

    get duration() {
        // Prefer master audio length. Never let a short looping theme bed define the song.
        const audioDur = (this.audio && !isNaN(this.audio.duration) && this.audio.duration > 0)
            ? this.audio.duration
            : 0;
        if (audioDur > 0) return audioDur;
        if (this._fallbackDuration > 0) return this._fallbackDuration;
        if (!this.audio && this.hasVideo && this.video && !isNaN(this.video.duration)) {
            return this.video.duration;
        }
        return 0;
    }

    get isPaused() {
        if (this.usesAudioClock) {
            return !!this.audio.paused;
        }
        const clock = this.clockElement;
        return clock ? clock.paused : true;
    }

    get isPlaying() {
        if (this.usesAudioClock) {
            return !this.audio.paused && !this.audio.ended;
        }
        const clock = this.clockElement;
        return clock ? (!clock.paused && !clock.ended) : false;
    }

    _configureThemeVideoElement() {
        if (!this.video) return;
        this.video.loop = true;
        this.video.muted = true;
        this.video.playsInline = true;
        this.video.setAttribute('playsinline', '');
        this.video.setAttribute('muted', '');
        this.video.setAttribute('loop', '');
    }

    _syncWallpaperToAudio(audioTime = null) {
        if (!this.hasVideo || !this.video || !this.audio) return;
        // Never seek theme video before it has metadata — that fires media errors
        // and used to reveal an empty <img> fallback after reload.
        if (this.video.readyState < 1 || this.video.error) return;
        const dur = this.video.duration;
        if (!dur || isNaN(dur) || dur <= 0) return;
        const t = audioTime != null ? audioTime : (this.audio.currentTime || 0);
        const target = ((t % dur) + dur) % dur;
        // Wider threshold so wallpaper looping does not thrash seeks / timeupdates.
        if (Math.abs((this.video.currentTime || 0) - target) > 0.85) {
            try {
                this.video.currentTime = target;
            } catch (_) {
                /* ignore seek race before metadata */
            }
        }
    }

    _fallbackPosterSrc() {
        const container = document.getElementById('videoContainer');
        const poster = container?.getAttribute('data-bg-poster') || '';
        if (poster) return poster;
        if (this.bgImage?.currentSrc) return this.bgImage.currentSrc;
        if (this.video?.poster) return this.video.poster;
        return '';
    }

    _showImageFallback(reason) {
        console.warn("Theme video unavailable, using still fallback:", reason);
        this.hasVideo = false;
        const container = document.getElementById('videoContainer');
        if (container) container.setAttribute('data-has-video', 'false');
        if (this.video) this.video.classList.add('d-none');
        if (this.bgImage) {
            const poster = this._fallbackPosterSrc();
            if (poster && (!this.bgImage.getAttribute('src') || this.bgImage.getAttribute('src') === '')) {
                this.bgImage.src = poster;
            }
            this.bgImage.classList.remove('d-none');
        }
    }

    setQuality(quality) {
        this.quality = quality; // '720' | '1080'
        const container = document.getElementById('videoContainer');
        if (container) {
            if (quality === '720') {
                container.classList.remove('quality-master');
                container.classList.add('quality-draft');
            } else {
                container.classList.remove('quality-draft');
                container.classList.add('quality-master');
            }
        }
        this.renderActiveFrame(this.currentTime);
    }

    setMediaMode({ hasVideo, videoSrc, imageSrc, preserveTime = null }) {
        const keepTime = preserveTime != null
            ? preserveTime
            : ((this.audio && !isNaN(this.audio.currentTime)) ? this.audio.currentTime : 0);
        const wasPlaying = this.isPlaying;

        this.hasVideo = !!hasVideo;
        const container = document.getElementById('videoContainer');
        if (container) {
            container.setAttribute('data-has-video', this.hasVideo ? 'true' : 'false');
            container.style.backgroundImage = '';
        }

        if (this.hasVideo) {
            if (this.bgImage) {
                // Keep a valid still underneath as poster while the theme bed loads.
                if (imageSrc) this.bgImage.src = imageSrc;
                else if (!this.bgImage.getAttribute('src')) {
                    const poster = this._fallbackPosterSrc();
                    if (poster) this.bgImage.src = poster;
                }
                this.bgImage.classList.add('d-none');
            }
            if (this.video) {
                this._configureThemeVideoElement();
                this.video.classList.remove('d-none');
                if (videoSrc) {
                    const ready = new Promise((resolve) => {
                        const done = () => {
                            this.video.removeEventListener('loadedmetadata', done);
                            this.video.removeEventListener('error', done);
                            resolve();
                        };
                        this.video.addEventListener('loadedmetadata', done, { once: true });
                        this.video.addEventListener('error', done, { once: true });
                    });
                    // Clear stale <source> children so direct src wins after theme switches.
                    while (this.video.firstChild) this.video.removeChild(this.video.firstChild);
                    this.video.src = videoSrc;
                    this.video.load();
                    ready.then(() => {
                        if (this.video.error) {
                            this._showImageFallback(this.video.error);
                            return;
                        }
                        this._syncWallpaperToAudio(keepTime);
                        if (this.audio && Math.abs((this.audio.currentTime || 0) - keepTime) > 0.05) {
                            try { this.audio.currentTime = keepTime; } catch (_) { /* ignore */ }
                        }
                        if (wasPlaying) {
                            this.video.play().catch(() => {});
                        }
                    });
                    return ready;
                }
            }
        } else {
            if (this.video) {
                this.video.pause();
                while (this.video.firstChild) this.video.removeChild(this.video.firstChild);
                this.video.removeAttribute('src');
                this.video.load();
                this.video.classList.add('d-none');
            }
            if (this.bgImage) {
                this.bgImage.classList.remove('d-none');
                if (imageSrc) {
                    this.bgImage.src = imageSrc;
                } else if (!this.bgImage.getAttribute('src')) {
                    const poster = this._fallbackPosterSrc();
                    if (poster) this.bgImage.src = poster;
                }
            }
            if (this.audio && Math.abs((this.audio.currentTime || 0) - keepTime) > 0.05) {
                try { this.audio.currentTime = keepTime; } catch (_) { /* ignore */ }
            }
        }
        return Promise.resolve();
    }

    setLyrics(lines) {
        this.lines = lines || [];
        this.allWords = [];

        this.lines.forEach((line, lineIdx) => {
            (line.words || []).forEach((w, wIdx) => {
                this.allWords.push({
                    ...w,
                    lineId: line.id,
                    lineIdx: lineIdx,
                    wordIdxInLine: wIdx,
                });
            });
        });

        this.allWords.sort((a, b) => a.start - b.start);
        this.seekToWordIndex(this.currentTime);
        this.renderActiveFrame(this.currentTime);
    }

    setStyle(styleConfig) {
        const prevEffect = this.style.effect;
        this.style = { ...this.style, ...styleConfig };
        if (prevEffect !== this.style.effect) {
            this._effectPlayKey = null;
            this._lastChunkKey = null;
        }
        this.applyStyleToDOM();
        this.renderActiveFrame(this.currentTime);
    }

    _hexToRgba(hex, opacityPct = 100) {
        let h = String(hex || '#000000').replace('#', '');
        if (h.length === 3) h = h.split('').map((c) => c + c).join('');
        if (h.length !== 6) h = '000000';
        const r = parseInt(h.slice(0, 2), 16);
        const g = parseInt(h.slice(2, 4), 16);
        const b = parseInt(h.slice(4, 6), 16);
        const a = Math.max(0, Math.min(1, (Number(opacityPct) || 0) / 100));
        return `rgba(${r}, ${g}, ${b}, ${a})`;
    }

    _angleToOffset(angleDeg, distance) {
        const rad = ((Number(angleDeg) || 0) * Math.PI) / 180;
        const d = Number(distance) || 0;
        return {
            x: Math.cos(rad) * d,
            y: Math.sin(rad) * d,
        };
    }

    composeTextEffectsCss(style = this.style) {
        const layers = [];
        const s = style || {};

        if (s.outlineEnabled !== false && Number(s.outline) > 0) {
            const size = Number(s.outline) || 0;
            const soft = Math.max(0, Number(s.outlineSoftness) || 0);
            const color = this._hexToRgba(s.outlineColor || '#000000', 100);
            const steps = Math.max(8, Math.min(24, Math.round(size * 4)));
            for (let i = 0; i < steps; i++) {
                const a = (i / steps) * Math.PI * 2;
                const x = Math.cos(a) * size;
                const y = Math.sin(a) * size;
                layers.push(`${x.toFixed(2)}px ${y.toFixed(2)}px ${soft}px ${color}`);
            }
        }

        if (s.bevelEnabled && Number(s.bevelSize) > 0) {
            const size = Number(s.bevelSize) || 0;
            const soft = Math.max(0, Number(s.bevelSoftness) || 0);
            const off = this._angleToOffset(s.bevelAngle ?? 135, size);
            const hi = this._hexToRgba(s.bevelHighlightColor || '#FFFFFF', s.bevelHighlightOpacity ?? 55);
            const sh = this._hexToRgba(s.bevelShadowColor || '#000000', s.bevelShadowOpacity ?? 45);
            layers.push(`${(-off.x).toFixed(2)}px ${(-off.y).toFixed(2)}px ${soft}px ${hi}`);
            layers.push(`${off.x.toFixed(2)}px ${off.y.toFixed(2)}px ${soft}px ${sh}`);
        }

        if (s.shadowEnabled !== false && Number(s.shadow) > 0) {
            const off = this._angleToOffset(s.shadowAngle ?? 45, s.shadow);
            const blur = Math.max(0, Number(s.shadowBlur) || 0);
            const color = this._hexToRgba(s.shadowColor || '#000000', s.shadowOpacity ?? 70);
            layers.push(`${off.x.toFixed(2)}px ${off.y.toFixed(2)}px ${blur}px ${color}`);
        }

        return layers.length ? layers.join(', ') : 'none';
    }

    applyStyleToDOM() {
        if (!this.displayActiveText) return;
        const fontName = this.style.font || 'Caveat';
        const fontFamily = (window.LyricSyncFonts && typeof window.LyricSyncFonts.resolve === 'function')
            ? window.LyricSyncFonts.resolve(fontName)
            : `"${fontName}", sans-serif`;
        this.displayActiveText.style.fontFamily = fontFamily;
        this.displayActiveText.style.fontSize = `${this.style.fontSize || 34}px`;
        this.displayActiveText.style.lineHeight = `${this.style.lineHeight || 1.0}`;
        this.displayActiveText.style.letterSpacing = `${this.style.letterSpacing || 0}em`;
        this.displayActiveText.style.fontWeight = this.style.fontWeight || 600;
        this.displayActiveText.style.fontStyle = this.style.fontStyle || 'normal';
        this._clearEffectClasses(this.displayActiveText);
        this.displayActiveText.style.color = this.style.primaryColor || '#FFFFFF';
        this.displayActiveText.style.textShadow = this.composeTextEffectsCss();
        this.displayActiveText.style.webkitTextStroke = '0';

        const align = this.style.textAlign || 'center';
        if (this.activeLineContainer) {
            this.activeLineContainer.style.textAlign = align;
            if (align === 'left') {
                this.activeLineContainer.style.alignItems = 'flex-start';
                this.activeLineContainer.classList.remove('text-center', 'text-end');
                this.activeLineContainer.classList.add('text-start');
            } else if (align === 'right') {
                this.activeLineContainer.style.alignItems = 'flex-end';
                this.activeLineContainer.classList.remove('text-center', 'text-start');
                this.activeLineContainer.classList.add('text-end');
            } else {
                this.activeLineContainer.style.alignItems = 'center';
                this.activeLineContainer.classList.remove('text-start', 'text-end');
                this.activeLineContainer.classList.add('text-center');
            }
        }
        this.displayActiveText.style.textAlign = align;

        // Vertical positioning
        if (this.style.position === 'top') {
            this.overlay.className = 'lyric-overlay position-absolute top-0 start-0 w-100 h-100 d-flex flex-column pointer-events-none p-4 justify-content-start';
        } else if (this.style.position === 'bottom') {
            this.overlay.className = 'lyric-overlay position-absolute top-0 start-0 w-100 h-100 d-flex flex-column pointer-events-none p-4 justify-content-end';
        } else {
            this.overlay.className = 'lyric-overlay position-absolute top-0 start-0 w-100 h-100 d-flex flex-column pointer-events-none p-4 justify-content-center';
        }
    }

    _setupListeners() {
        // Click stage to toggle play
        if (this.video) this.video.addEventListener('click', () => this.togglePlay());
        if (this.bgImage) this.bgImage.addEventListener('click', () => this.togglePlay());

        const notifyPlay = () => {
            this._startRenderLoop();
            window.dispatchEvent(new CustomEvent('player-play'));
        };

        const notifyPause = () => {
            this._stopRenderLoop();
            this.renderActiveFrame(this.currentTime);
            window.dispatchEvent(new CustomEvent('player-pause'));
        };

        const notifyTimeUpdate = () => {
            const t = this.currentTime;
            // Wallpaper follows the song; never yank master audio back to the short theme loop.
            this._syncWallpaperToAudio(t);
            if (this.isPaused) {
                this.seekToWordIndex(t);
                this.renderActiveFrame(t);
            }
            window.dispatchEvent(new CustomEvent('player-timeupdate', {
                detail: { currentTime: t, duration: this.duration }
            }));
        };

        if (this.video) {
            this._configureThemeVideoElement();
            // Theme video is decorative — do not drive play/pause/timeline from it.
            this.video.addEventListener('error', () => {
                this._showImageFallback(this.video?.error || 'media error');
            });
            this.video.addEventListener('loadedmetadata', () => {
                this._syncWallpaperToAudio();
            });
        }

        if (this.audio) {
            this.audio.addEventListener('play', () => {
                if (this.hasVideo && this.video) {
                    this._configureThemeVideoElement();
                    this._syncWallpaperToAudio();
                    this.video.play().catch(() => {});
                }
                notifyPlay();
            });
            this.audio.addEventListener('pause', () => {
                if (this.hasVideo && this.video) this.video.pause();
                notifyPause();
            });
            this.audio.addEventListener('timeupdate', notifyTimeUpdate);
            this.audio.addEventListener('seeking', () => {
                const t = this.audio.currentTime;
                this._syncWallpaperToAudio(t);
                this.seekToWordIndex(t);
                this.renderActiveFrame(t);
            });
            this.audio.addEventListener('ended', () => {
                if (this.hasVideo && this.video) this.video.pause();
                notifyPause();
            });
            this.audio.addEventListener('error', (err) => {
                console.warn("Audio stream error:", err);
            });
            this.audio.addEventListener('waiting', () => {
                window.dispatchEvent(new CustomEvent('player-buffering', { detail: { buffering: true, reason: 'waiting' } }));
            });
            this.audio.addEventListener('stalled', () => {
                window.dispatchEvent(new CustomEvent('player-buffering', { detail: { buffering: true, reason: 'stalled' } }));
            });
            this.audio.addEventListener('playing', () => {
                window.dispatchEvent(new CustomEvent('player-buffering', { detail: { buffering: false, reason: 'playing' } }));
            });
            this.audio.addEventListener('canplay', () => {
                if (!this.audio.paused) {
                    window.dispatchEvent(new CustomEvent('player-buffering', { detail: { buffering: false, reason: 'canplay' } }));
                }
            });
        }

    }

    _startRenderLoop() {
        if (this.animationFrameId) cancelAnimationFrame(this.animationFrameId);

        const loop = () => {
            if (this.isPlaying) {
                const t = this.currentTime;
                this._syncWallpaperToAudio(t);
                this.update(t);
                this.animationFrameId = requestAnimationFrame(loop);
            }
        };
        this.animationFrameId = requestAnimationFrame(loop);
    }

    _stopRenderLoop() {
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
    }

    seekToWordIndex(time) {
        if (!this.allWords.length) {
            this.currentWordIndex = 0;
            return;
        }
        let lo = 0;
        let hi = this.allWords.length - 1;
        let ans = 0;

        while (lo <= hi) {
            const mid = (lo + hi) >> 1;
            if (this.allWords[mid].start <= time) {
                ans = mid;
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }
        this.currentWordIndex = ans;
    }

    update(time) {
        if (!this.allWords.length) return;

        while (
            this.currentWordIndex + 1 < this.allWords.length &&
            this.allWords[this.currentWordIndex + 1].start <= time
        ) {
            this.currentWordIndex++;
        }

        this.renderActiveFrame(time);
    }

    _getChunks(chunkSize) {
        if (!this.lines || !this.lines.length) return [];
        const chunks = [];
        for (let i = 0; i < this.lines.length; i += chunkSize) {
            chunks.push(this.lines.slice(i, i + chunkSize));
        }
        return chunks;
    }

    applyTextCase(text) {
        const raw = String(text ?? '');
        const mode = (this.style.textCase || 'as_is').toLowerCase();
        if (mode === 'upper') return raw.toUpperCase();
        if (mode === 'lower') return raw.toLowerCase();
        if (mode === 'title') {
            return raw.replace(/\w\S*/g, (word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase());
        }
        return raw;
    }

    _renderLineWordsHtml(line, time, isLineActive) {
        const words = line.words || [];
        const effectShadow = this.composeTextEffectsCss();
        const mode = (this.style.mode || 'karaoke').toLowerCase();
        const highlight = this.style.highlightColor || '#10B981';
        const primary = this.style.primaryColor || '#FFFFFF';

        if (!words.length) {
            const plain = this._escapeHtml(this.applyTextCase(line.text || ''));
            return `<span style="text-shadow: ${effectShadow};">${plain}</span>`;
        }
        return words.map((w) => {
            const isWordActive = time >= w.start && time <= w.end;
            const isPast = time > w.end;
            const displayText = this._escapeHtml(this.applyTextCase(w.text || ''));

            let color = primary;
            let extraClass = '';
            let extraStyle = '';

            if (mode === 'none') {
                color = primary;
            } else if (mode === 'karaoke') {
                if (isWordActive || isPast) {
                    color = highlight;
                }
                if (isWordActive) extraClass = 'active track-karaoke';
            } else if (mode === 'underline') {
                if (isWordActive) {
                    color = highlight;
                    extraClass = 'active track-underline';
                }
            } else if (mode === 'glow') {
                if (isWordActive) {
                    color = highlight;
                    extraClass = 'active track-glow';
                    extraStyle = `filter: drop-shadow(0 0 10px ${highlight});`;
                }
            } else if (mode === 'scale') {
                if (isWordActive) {
                    color = highlight;
                    extraClass = 'active track-scale';
                }
            } else if (mode === 'box') {
                if (isWordActive) {
                    color = primary;
                    extraClass = 'active track-box';
                    extraStyle = `background: ${highlight}cc; padding: 0 0.22em; border-radius: 0.12em;`;
                }
            } else {
                // classic color flash
                if (isWordActive) {
                    color = highlight;
                    extraClass = 'active track-classic';
                }
            }

            return `<span class="karaoke-word ${extraClass}" style="color: ${color}; text-shadow: ${effectShadow}; ${extraStyle}" data-start="${w.start}" data-end="${w.end}">${displayText}</span>`;
        }).join(' ');
    }

    _clearEffectClasses(el) {
        if (!el) return;
        el.classList.remove(...this._EFFECT_CLASSES);
    }

    _resolveEffect(line) {
        // Project-wide effect wins so the Effects picker applies to every line.
        const globalFx = this.style.effect || 'none';
        if (globalFx && globalFx !== 'none') return globalFx;
        if (line?.effect && line.effect !== 'none') return line.effect;
        return 'none';
    }

    _playEffect(el, effect, restartKey) {
        if (!el) return;
        if (!effect || effect === 'none') {
            this._clearEffectClasses(el);
            this._effectPlayKey = null;
            return;
        }
        const cls = `lyric-effect-${effect}`;
        // Only touch classes / restart when the active lyric (or effect) changes.
        // Rebuilding every animation frame must not re-trigger the entrance.
        if (restartKey !== this._effectPlayKey) {
            this._clearEffectClasses(el);
            this._effectPlayKey = restartKey;
            el.classList.add(cls);
            el.style.animation = 'none';
            void el.offsetWidth;
            el.style.animation = '';
            return;
        }
        if (!el.classList.contains(cls)) {
            this._clearEffectClasses(el);
            el.classList.add(cls);
        }
    }

    renderActiveFrame(time) {
        const title = (this.songTitle || '').trim();
        const firstLyricStart = (this.lines && this.lines.length > 0) ? (this.lines[0].start || 0) : 0;

        // Intro: cinematic title card before the first lyric line.
        const isIntro = (this.lines.length > 0) ? (time < firstLyricStart && firstLyricStart >= 0.8) : (time < 4.5);
        if (isIntro && title) {
            const introEnd = (this.lines.length > 0) ? Math.min(5.2, firstLyricStart - 0.15) : 4.2;
            if (time < introEnd) {
                this._clearEffectClasses(this.displayActiveText);
                this._effectPlayKey = null;
                this._renderCinematicIntro(time, introEnd);
                return;
            }
            if (this.lines.length > 0) {
                this.displayActiveText.innerHTML = '';
                return;
            }
        }

        if (!this.lines.length) {
            this.displayActiveText.innerHTML = '<span class="text-secondary small font-monospace">[No lyrics loaded. Click "Transcribe AI" above]</span>';
            return;
        }

        let activeLine = null;
        let activeLineIdx = -1;

        for (let i = 0; i < this.lines.length; i++) {
            const l = this.lines[i];
            if (time >= l.start && time <= l.end + 0.3) {
                activeLine = l;
                activeLineIdx = i;
                break;
            }
        }

        if (activeLineIdx !== this.activeLineIndex) {
            this.activeLineIndex = activeLineIdx;
            window.dispatchEvent(new CustomEvent('active-line-changed', { detail: { lineIndex: activeLineIdx, time } }));
        }

        const format = this.style.format || 'stanza';

        if (format === 'line') {
            if (!activeLine) {
                this.displayActiveText.innerHTML = '';
                this._playEffect(this.displayActiveText, 'none', null);
                return;
            }
            this.displayActiveText.innerHTML = this._renderLineWordsHtml(activeLine, time, true);
            const fx = this._resolveEffect(activeLine);
            this._playEffect(this.displayActiveText, fx, `line-${activeLine.id || activeLineIdx}-${fx}`);
            return;
        }

        const chunkSize = (format === 'sentence') ? 2 : 4;
        const chunks = this._getChunks(chunkSize);

        // Find active chunk
        let activeChunk = null;
        for (const chunk of chunks) {
            const chunkStart = chunk[0].start;
            const chunkEnd = chunk[chunk.length - 1].end + 0.3;
            if (time >= chunkStart && time <= chunkEnd) {
                activeChunk = chunk;
                break;
            }
        }

        if (!activeChunk) {
            // Fallback: if activeLine exists, find chunk containing activeLine
            if (activeLine) {
                activeChunk = chunks.find(c => c.some(l => l.id === activeLine.id));
            }
        }

        if (!activeChunk) {
            this.displayActiveText.innerHTML = '';
            this._lastChunkKey = null;
            this._playEffect(this.displayActiveText, 'none', null);
            return;
        }

        const chunkKey = activeChunk.map((l) => l.id || l.start).join('|');
        this._lastChunkKey = chunkKey;

        // Render each line in activeChunk
        const linesHtml = activeChunk.map((line) => {
            const isCurrLineActive = (activeLine && line.id === activeLine.id);
            const lineContent = this._renderLineWordsHtml(line, time, isCurrLineActive);
            const opacity = isCurrLineActive ? '1' : '0.62';
            const fontWeight = isCurrLineActive ? (this.style.fontWeight || '600') : Math.max(400, (this.style.fontWeight || 600) - 100);
            return `<div class="canvas-stanza-line my-1" style="opacity: ${opacity}; font-weight: ${fontWeight}; transition: opacity 0.15s ease;">${lineContent}</div>`;
        }).join('');

        this.displayActiveText.innerHTML = linesHtml;

        // Entrance effects fire once per stanza/couplet chunk — not again on each line inside it.
        const fxLine = activeChunk[0] || activeLine;
        const fx = this._resolveEffect(fxLine);
        this._playEffect(this.displayActiveText, fx, `chunk-${chunkKey}-${fx}`);
    }

    seekTo(seconds) {
        const t = Math.max(0, Number(seconds) || 0);
        if (this.audio) {
            try { this.audio.currentTime = t; } catch (_) { /* ignore */ }
        }
        this._syncWallpaperToAudio(t);
        this.seekToWordIndex(t);
        this.renderActiveFrame(t);
    }

    play() {
        if (this.audio) {
            this.audio.muted = false;
            this.audio.volume = 1.0;
            this.audio.play().catch(err => {
                console.warn("Audio play note:", err);
            });
        }

        if (this.hasVideo && this.video) {
            this._configureThemeVideoElement();
            this._syncWallpaperToAudio();
            const vPromise = this.video.play();
            if (vPromise && typeof vPromise.catch === 'function') {
                vPromise.catch(e => {
                    // Autoplay can fail without a hard media error — keep the still poster visible.
                    this._showImageFallback(e);
                });
            }
        } else if (!this.audio && this.video) {
            this.video.muted = false;
            this.video.volume = 1.0;
            this.video.play().catch(err => console.warn("Video play note:", err));
        }
        this._startRenderLoop();
    }


    pause() {
        if (this.hasVideo && this.video) this.video.pause();
        if (this.audio) this.audio.pause();
        this._stopRenderLoop();
        this.renderActiveFrame(this.currentTime);
    }

    togglePlay() {
        if (this.isPaused) {
            this.play();
        } else {
            this.pause();
        }
    }
}

window.SynchronizedPlayer = SynchronizedPlayer;
