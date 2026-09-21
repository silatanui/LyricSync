/**
 * LyricSync Synchronized Video Player Engine
 * Canva-like clean rendering, font family selector, audio sync, and zero illuminations.
 */
class SynchronizedPlayer {
    constructor(videoEl, audioEl, overlayEl) {
        this.video = videoEl;
        this.audio = audioEl;
        this.overlay = overlayEl;
        this.activeLineContainer = document.getElementById('activeLineContainer');
        this.displayActiveText = document.getElementById('displayActiveText');

        this.lines = [];
        this.allWords = [];
        this.currentWordIndex = 0;
        this.activeLineIndex = -1;
        this.animationFrameId = null;

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
        this.seekToWordIndex(this.video.currentTime);
        this.renderActiveFrame(this.video.currentTime);
    }

    setStyle(styleConfig) {
        this.style = { ...this.style, ...styleConfig };
        this.applyStyleToDOM();
        this.renderActiveFrame(this.video.currentTime);
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
        // Video click to toggle play
        this.video.addEventListener('click', () => this.togglePlay());

        this.video.addEventListener('play', () => {
            this._startRenderLoop();
        });

        this.video.addEventListener('pause', () => {
            if (this.audio) this.audio.pause();
            this._stopRenderLoop();
            this.renderActiveFrame(this.video.currentTime);
        });

        this.video.addEventListener('seeking', () => {
            const t = this.video.currentTime;
            if (this.audio) this.audio.currentTime = t;
            this.seekToWordIndex(t);
            this.renderActiveFrame(t);
        });

        this.video.addEventListener('timeupdate', () => {
            // Keep audio strictly in lockstep with video
            if (this.audio && !this.video.paused) {
                if (Math.abs(this.audio.currentTime - this.video.currentTime) > 0.25) {
                    this.audio.currentTime = this.video.currentTime;
                }
            }
            if (this.video.paused) {
                this.seekToWordIndex(this.video.currentTime);
                this.renderActiveFrame(this.video.currentTime);
            }
        });
    }

    _startRenderLoop() {
        if (this.animationFrameId) cancelAnimationFrame(this.animationFrameId);

        const loop = () => {
            if (!this.video.paused && !this.video.ended) {
                const t = this.video.currentTime;
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
        this.video.currentTime = seconds;
        if (this.audio) this.audio.currentTime = seconds;
        this.seekToWordIndex(seconds);
        this.renderActiveFrame(seconds);
    }

    play() {
        // Visual canvas plays muted to prevent browser autoplay blocking and eliminate double-audio echo
        this.video.muted = true;
        const vPromise = this.video.play();
        if (vPromise) vPromise.catch(e => console.warn("Video play note:", e));

        // Master vocal audio track plays unmuted at full volume
        if (this.audio) {
            this.audio.muted = false;
            this.audio.volume = 1.0;
            this.audio.currentTime = this.video.currentTime;
            const aPromise = this.audio.play();
            if (aPromise) {
                aPromise.catch(err => {
                    console.warn("Audio element could not start; keeping the preview video muted:", err);
                });
            }
        } else {
            this.video.muted = false;
            this.video.volume = 1.0;
        }
    }

    pause() {
        this.video.pause();
        if (this.audio) this.audio.pause();
    }

    togglePlay() {
        if (this.video.paused) {
            this.play();
        } else {
            this.pause();
        }
    }
}

window.SynchronizedPlayer = SynchronizedPlayer;
