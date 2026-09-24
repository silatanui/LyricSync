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

        // Visual styling configuration kept compact for dense lyric layouts.
        this.style = {
            format: 'stanza',
            mode: 'karaoke',
            font: 'Caveat',
            fontSize: 28,
            lineHeight: 0.9,
            letterSpacing: 0,
            fontWeight: 600,
            primaryColor: '#FFFFFF',
            highlightColor: '#10B981',
            position: 'center',
            textAlign: 'center',
        };

        this._setupListeners();
    }

    setSongTitle(title) {
        this.songTitle = (title || '').trim();
        this.renderActiveFrame(this.currentTime);
    }

    get clockElement() {
        if (this.hasVideo && this.video && !this.video.error && this.video.readyState >= 1) {
            return this.video;
        }
        if (this.audio && !this.audio.error) {
            return this.audio;
        }
        return this.audio || this.video;
    }

    get currentTime() {
        const clock = this.clockElement;
        return clock ? (clock.currentTime || 0) : 0;
    }

    get duration() {
        const audioDur = (this.audio && !isNaN(this.audio.duration)) ? this.audio.duration : 0;
        const videoDur = (this.hasVideo && this.video && !isNaN(this.video.duration)) ? this.video.duration : 0;
        const dur = Math.max(audioDur, videoDur);
        return isNaN(dur) ? 0 : dur;
    }


    get isPaused() {
        const clock = this.clockElement;
        return clock ? clock.paused : true;
    }

    get isPlaying() {
        const clock = this.clockElement;
        return clock ? (!clock.paused && !clock.ended) : false;
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

    setMediaMode({ hasVideo, videoSrc, imageSrc }) {
        this.hasVideo = !!hasVideo;
        const container = document.getElementById('videoContainer');
        if (container) {
            container.setAttribute('data-has-video', this.hasVideo ? 'true' : 'false');
        }

        if (this.hasVideo) {
            if (this.bgImage) this.bgImage.classList.add('d-none');
            if (this.video) {
                this.video.classList.remove('d-none');
                if (videoSrc) {
                    this.video.src = videoSrc;
                    this.video.load();
                }
            }
        } else {
            if (this.video) {
                this.video.pause();
                this.video.classList.add('d-none');
            }
            if (this.bgImage) {
                this.bgImage.classList.remove('d-none');
                if (imageSrc) {
                    this.bgImage.src = imageSrc;
                }
            }
        }
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
        this.style = { ...this.style, ...styleConfig };
        this.applyStyleToDOM();
        this.renderActiveFrame(this.currentTime);
    }

    applyStyleToDOM() {
        if (!this.displayActiveText) return;
        const fontName = this.style.font || 'Caveat';
        let fontFamily = `"${fontName}", sans-serif`;
        if (fontName === 'Caveat') {
            fontFamily = `'Caveat', cursive, sans-serif`;
        } else if (['Playfair Display', 'Cinzel', 'Merriweather', 'Georgia', 'Libre Baskerville'].includes(fontName)) {
            fontFamily = `"${fontName}", serif`;
        }
        this.displayActiveText.style.fontFamily = fontFamily;
        this.displayActiveText.style.fontSize = `${this.style.fontSize || 34}px`;
        this.displayActiveText.style.lineHeight = `${this.style.lineHeight || 1.0}`;
        this.displayActiveText.style.letterSpacing = `${this.style.letterSpacing || 0}em`;
        this.displayActiveText.style.fontWeight = this.style.fontWeight || 600;
        this.displayActiveText.style.fontStyle = this.style.fontStyle || 'normal';
        this.displayActiveText.classList.remove('lyric-effect-fade', 'lyric-effect-bounce', 'lyric-effect-slide', 'lyric-effect-pulse', 'lyric-effect-typewriter');
        if (this.style.effect && this.style.effect !== 'none') {
            this.displayActiveText.classList.add(`lyric-effect-${this.style.effect}`);
        }
        this.displayActiveText.style.color = this.style.primaryColor || '#FFFFFF';
        // Sharp, clean contrast without any glowing illumination
        this.displayActiveText.style.textShadow = '0 1px 2px rgba(0, 0, 0, 0.7)';

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
            if (this.hasVideo && this.video && this.audio && !this.video.paused) return;
            this._stopRenderLoop();
            this.renderActiveFrame(this.currentTime);
            window.dispatchEvent(new CustomEvent('player-pause'));
        };

        const notifyTimeUpdate = () => {
            const t = this.currentTime;
            // When playing video with separate master audio, keep them in sync
            if (this.hasVideo && this.video && this.audio && !this.video.paused) {
                if (Math.abs(this.audio.currentTime - this.video.currentTime) > 0.25) {
                    this.audio.currentTime = this.video.currentTime;
                }
            }
            if (this.isPaused) {
                this.seekToWordIndex(t);
                this.renderActiveFrame(t);
            }
            window.dispatchEvent(new CustomEvent('player-timeupdate', {
                detail: { currentTime: t, duration: this.duration }
            }));
        };

        if (this.video) {
            this.video.addEventListener('play', notifyPlay);
            this.video.addEventListener('pause', notifyPause);
            this.video.addEventListener('timeupdate', notifyTimeUpdate);
            this.video.addEventListener('seeking', () => {
                const t = this.currentTime;
                if (this.audio) this.audio.currentTime = t;
                this.seekToWordIndex(t);
                this.renderActiveFrame(t);
            });
            this.video.addEventListener('error', (err) => {
                console.warn("Video playback element failed, seamlessly falling back to audio mode:", err);
                this.hasVideo = false;
                if (this.video) this.video.classList.add('d-none');
                if (this.bgImage) this.bgImage.classList.remove('d-none');
                if (this.isPlaying && this.audio && this.audio.paused) {
                    this.audio.play().catch(e => console.warn("Audio play error:", e));
                }
            });
        }

        if (this.audio) {
            this.audio.addEventListener('play', () => {
                if (!this.hasVideo) notifyPlay();
            });
            this.audio.addEventListener('pause', () => {
                if (!this.hasVideo) notifyPause();
            });
            this.audio.addEventListener('timeupdate', () => {
                if (!this.hasVideo) notifyTimeUpdate();
            });
            this.audio.addEventListener('seeking', () => {
                if (!this.hasVideo) {
                    const t = this.audio.currentTime;
                    this.seekToWordIndex(t);
                    this.renderActiveFrame(t);
                }
            });
            this.audio.addEventListener('error', (err) => {
                console.warn("Audio stream error:", err);
            });
        }

    }

    _startRenderLoop() {
        if (this.animationFrameId) cancelAnimationFrame(this.animationFrameId);

        const loop = () => {
            const clock = this.clockElement;
            if (clock && !clock.paused && !clock.ended) {
                const t = clock.currentTime;
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

    _renderLineWordsHtml(line, time, isLineActive) {
        const words = line.words || [];
        if (!words.length) {
            return `<span>${line.text}</span>`;
        }
        return words.map((w) => {
            const isWordActive = time >= w.start && time <= w.end;
            const isPast = time > w.end;

            let color = this.style.primaryColor || '#FFFFFF';
            let extraClass = '';

            if (this.style.mode === 'karaoke') {
                if (isWordActive) {
                    color = this.style.highlightColor || '#10B981';
                    extraClass = 'active';
                } else if (isPast) {
                    color = this.style.highlightColor || '#10B981';
                }
            } else {
                if (isWordActive) {
                    color = this.style.highlightColor || '#10B981';
                    extraClass = 'active';
                }
            }

            return `<span class="karaoke-word ${extraClass}" style="color: ${color};" data-start="${w.start}" data-end="${w.end}">${w.text}</span>`;
        }).join(' ');
    }

    renderActiveFrame(time) {
        const title = (this.songTitle || '').trim();
        const firstLyricStart = (this.lines && this.lines.length > 0) ? (this.lines[0].start || 0) : 0;

        // Intro mode: reveal song title with typewriter effect before music vocals start
        const isIntro = (this.lines.length > 0) ? (time < firstLyricStart && firstLyricStart >= 0.8) : (time < 4.5);
        if (isIntro && title) {
            const introEnd = (this.lines.length > 0) ? Math.min(4.5, firstLyricStart - 0.2) : 4.0;
            if (time < introEnd) {
                const typingDuration = Math.max(0.6, introEnd * 0.72);
                const progress = Math.min(1.0, Math.max(0.0, time / typingDuration));
                const charIndex = Math.min(title.length, Math.floor(progress * title.length));
                const typedTitle = title.slice(0, charIndex);
                const isBlinking = Math.floor(time * 3.5) % 2 === 0;
                const cursorHtml = `<span class="typewriter-cursor" style="color: ${this.style.highlightColor || '#10B981'}; opacity: ${isBlinking ? '1' : '0.15'}; margin-left: 2px;">|</span>`;

                this.displayActiveText.innerHTML = `
                    <div class="song-title-intro-box text-center py-2" style="max-width: 90%; margin: 0 auto; user-select: none;">
                        <div class="song-title-kicker font-mono mb-2" style="letter-spacing: 0.18em; font-size: 0.72rem; color: ${this.style.highlightColor || '#10B981'}; font-weight: 700;">
                            <i class="bi bi-disc me-1"></i> NOW PLAYING
                        </div>
                        <div class="song-title-heading fw-bold" style="font-size: ${Math.round((this.style.fontSize || 34) * 1.35)}px; color: ${this.style.primaryColor || '#FFFFFF'}; line-height: 1.15; word-break: break-word;">
                            <span>${typedTitle}</span>${cursorHtml}
                        </div>
                    </div>
                `;
                return;
            } else if (this.lines.length > 0) {
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
                return;
            }
            this.displayActiveText.innerHTML = this._renderLineWordsHtml(activeLine, time, true);
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
            return;
        }

        // Render each line in activeChunk
        const linesHtml = activeChunk.map(line => {
            const isCurrLineActive = (activeLine && line.id === activeLine.id);
            const lineContent = this._renderLineWordsHtml(line, time, isCurrLineActive);
            const opacity = isCurrLineActive ? '1' : '0.62';
            const fontWeight = isCurrLineActive ? (this.style.fontWeight || '600') : Math.max(400, (this.style.fontWeight || 600) - 100);
            return `<div class="canvas-stanza-line my-1" style="opacity: ${opacity}; font-weight: ${fontWeight}; transition: opacity 0.15s ease;">${lineContent}</div>`;
        }).join('');

        this.displayActiveText.innerHTML = linesHtml;
        const activeEffect = activeLine?.effect && activeLine.effect !== 'none'
            ? activeLine.effect
            : (this.style.effect || 'none');
        this.displayActiveText.classList.remove('lyric-effect-fade', 'lyric-effect-bounce', 'lyric-effect-slide', 'lyric-effect-pulse', 'lyric-effect-typewriter');
        if (activeEffect !== 'none') this.displayActiveText.classList.add(`lyric-effect-${activeEffect}`);
    }

    seekTo(seconds) {
        if (this.audio) this.audio.currentTime = seconds;
        if (this.hasVideo && this.video) this.video.currentTime = seconds;
        this.seekToWordIndex(seconds);
        this.renderActiveFrame(seconds);
    }

    play() {
        if (this.hasVideo && this.video) {
            this.video.muted = true;
            const vPromise = this.video.play();
            if (vPromise && typeof vPromise.catch === 'function') {
                vPromise.catch(e => {
                    console.warn("Video play error, falling back to audio only:", e);
                    this.hasVideo = false;
                    if (this.video) this.video.classList.add('d-none');
                    if (this.bgImage) this.bgImage.classList.remove('d-none');
                    if (this.audio && this.audio.paused) {
                        this.audio.play().catch(aErr => console.warn("Audio play error:", aErr));
                    }
                });
            }
        }

        if (this.audio) {
            this.audio.muted = false;
            this.audio.volume = 1.0;
            if (this.hasVideo && this.video && !isNaN(this.video.currentTime)) {
                this.audio.currentTime = this.video.currentTime;
            }
            this.audio.play().catch(err => {
                console.warn("Audio play note:", err);
            });
        } else if (this.video) {
            this.video.muted = false;
            this.video.volume = 1.0;
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
