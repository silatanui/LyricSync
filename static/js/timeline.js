/**
 * LyricSync Interactive Timeline & Manual Editing Engine
 * Implements Section 17: Split, Merge, Nudge, Inline Edit, and Seek operations.
 */
class LyricTimeline {
    constructor(containerEl, player) {
        this.container = containerEl;
        this.player = player;
        this.lines = [];
        this.activeLineIdx = -1;
        this.onChangeCallback = null;

        // Listen for active line changes from player
        window.addEventListener('active-line-changed', (e) => {
            this.highlightActiveLine(e.detail.lineIndex);
        });
    }

    setLines(lines) {
        this.lines = JSON.parse(JSON.stringify(lines || []));
        this.render();
    }

    getLines() {
        return this.lines;
    }

    setOnChange(cb) {
        this.onChangeCallback = cb;
    }

    _notifyChange() {
        if (this.onChangeCallback) {
            this.onChangeCallback(this.lines);
        }
        if (this.player) {
            this.player.setLyrics(this.lines);
        }
    }

    formatTime(sec) {
        const s = Math.max(0, sec);
        const m = Math.floor(s / 60);
        const remS = (s % 60).toFixed(2);
        return `${m < 10 ? '0' : ''}${m}:${remS < 10 ? '0' : ''}${remS}`;
    }

    render() {
        this.container.innerHTML = '';

        if (!this.lines.length) {
            this.container.innerHTML = `
                <div class="text-center py-4 text-white-50">
                    <i class="bi bi-chat-square-quote fs-2 d-block mb-1"></i>
                    No lyrics detected yet. Click <strong>"Transcribe AI"</strong> to generate lyrics with word timing.
                </div>
            `;
            return;
        }

        this.lines.forEach((line, idx) => {
            const card = document.createElement('div');
            card.className = `timeline-card d-flex flex-column gap-2 ${idx === this.activeLineIdx ? 'active-playback-line' : ''}`;
            card.dataset.lineIndex = idx;

            // Header row: index, timing, actions
            const headerRow = document.createElement('div');
            headerRow.className = 'd-flex justify-content-between align-items-center flex-wrap gap-2';

            const infoGroup = document.createElement('div');
            infoGroup.className = 'd-flex align-items-center gap-2';
            infoGroup.innerHTML = `
                <span class="fw-bold text-dark font-mono small">Line ${idx + 1}</span>
                <button class="btn btn-outline-secondary btn-sm font-mono py-1 px-2.5 seek-trigger" title="Click to seek player">
                    <i class="bi bi-play-fill me-1" style="color: var(--brand-burgundy);"></i>${this.formatTime(line.start)} &rarr; ${this.formatTime(line.end)}
                </button>
            `;

            // Action buttons: Nudge earlier/later, Split, Merge, Delete (Square & Spacious)
            const actionsGroup = document.createElement('div');
            actionsGroup.className = 'd-flex align-items-center gap-1.5';
            actionsGroup.innerHTML = `
                <button class="btn btn-light btn-sm border py-1 px-2 nudge-btn" data-dir="-1" title="Nudge 100ms earlier"><i class="bi bi-dash"></i>100ms</button>
                <button class="btn btn-light btn-sm border py-1 px-2 nudge-btn" data-dir="1" title="Nudge 100ms later"><i class="bi bi-plus"></i>100ms</button>
                <button class="btn btn-light btn-sm border py-1 px-2 split-btn" title="Split line in half"><i class="bi bi-scissors me-1"></i>Split</button>
                ${idx < this.lines.length - 1 ? '<button class="btn btn-light btn-sm border py-1 px-2 merge-btn" title="Merge with next line"><i class="bi bi-arrow-down-up me-1"></i>Merge</button>' : ''}
                <button class="btn btn-outline-danger btn-sm py-1 px-2 delete-btn" title="Delete line"><i class="bi bi-trash3"></i></button>
            `;

            headerRow.appendChild(infoGroup);
            headerRow.appendChild(actionsGroup);

            // Text input row (Spacious & Clean)
            const textInput = document.createElement('input');
            textInput.type = 'text';
            textInput.className = 'form-control bg-white text-dark border line-text-input py-2 px-3 fw-semibold';
            textInput.value = line.text;

            const effectSelect = document.createElement('select');
            effectSelect.className = 'form-select form-select-sm line-effect-select';
            effectSelect.title = 'Effect for this lyric line';
            effectSelect.innerHTML = `
                <option value="none">No effect</option>
                <option value="fade">Fade</option>
                <option value="bounce">Bounce</option>
                <option value="slide">Slide</option>
                <option value="pulse">Pulse</option>
                <option value="typewriter">Typewriter</option>`;
            effectSelect.value = line.effect && line.effect !== 'none'
                ? line.effect
                : (this.player?.style?.effect || 'none');
            effectSelect.addEventListener('change', () => {
                line.effect = effectSelect.value;
                this._notifyChange();
            });

            // Word chips container (Square, Spacious)
            const wordsRow = document.createElement('div');
            wordsRow.className = 'd-flex flex-wrap gap-1.5 mt-2';
            (line.words || []).forEach(w => {
                const chip = document.createElement('span');
                chip.className = 'word-chip';
                chip.textContent = `${w.text} (${w.start.toFixed(2)}s)`;
                wordsRow.appendChild(chip);
            });

            card.appendChild(headerRow);
            card.appendChild(textInput);
            card.appendChild(effectSelect);
            card.appendChild(wordsRow);

            // Event Listeners
            // Click timestamp to seek
            infoGroup.querySelector('.seek-trigger').addEventListener('click', () => {
                this.player.seekTo(line.start);
            });

            // Nudge
            actionsGroup.querySelectorAll('.nudge-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const dir = parseInt(btn.dataset.dir);
                    this.nudgeLine(idx, dir * 0.1);
                });
            });

            // Split
            actionsGroup.querySelector('.split-btn')?.addEventListener('click', (e) => {
                e.stopPropagation();
                this.splitLine(idx);
            });

            // Merge
            actionsGroup.querySelector('.merge-btn')?.addEventListener('click', (e) => {
                e.stopPropagation();
                this.mergeLine(idx);
            });

            // Delete
            actionsGroup.querySelector('.delete-btn')?.addEventListener('click', (e) => {
                e.stopPropagation();
                this.deleteLine(idx);
            });

            // Edit text inline
            textInput.addEventListener('change', (e) => {
                this.updateLineText(idx, e.target.value.trim());
            });

            this.container.appendChild(card);
        });
    }

    highlightActiveLine(lineIdx) {
        if (this.activeLineIdx === lineIdx) return;
        this.activeLineIdx = lineIdx;

        const cards = this.container.querySelectorAll('.timeline-card');
        cards.forEach((c, idx) => {
            if (idx === lineIdx) {
                c.classList.add('active-playback-line');
                // Scroll smoothly into view if not visible
                c.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } else {
                c.classList.remove('active-playback-line');
            }
        });
    }

    nudgeLine(lineIdx, deltaSec) {
        const line = this.lines[lineIdx];
        if (!line) return;

        line.start = Math.max(0, +(line.start + deltaSec).toFixed(3));
        line.end = Math.max(line.start + 0.1, +(line.end + deltaSec).toFixed(3));

        (line.words || []).forEach(w => {
            w.start = Math.max(0, +(w.start + deltaSec).toFixed(3));
            w.end = Math.max(w.start + 0.05, +(w.end + deltaSec).toFixed(3));
        });

        this._notifyChange();
        this.render();
    }

    splitLine(lineIdx) {
        const line = this.lines[lineIdx];
        if (!line || !line.words || line.words.length < 2) {
            alert("Line must have at least 2 words to split.");
            return;
        }

        const mid = Math.floor(line.words.length / 2);
        const words1 = line.words.slice(0, mid);
        const words2 = line.words.slice(mid);

        const line1 = {
            id: line.id,
            text: words1.map(w => w.text).join(' '),
            start: words1[0].start,
            end: words1[words1.length - 1].end,
            words: words1
        };

        const line2 = {
            id: line.id + '_b',
            text: words2.map(w => w.text).join(' '),
            start: words2[0].start,
            end: words2[words2.length - 1].end,
            words: words2
        };

        this.lines.splice(lineIdx, 1, line1, line2);
        this._notifyChange();
        this.render();
    }

    mergeLine(lineIdx) {
        if (lineIdx >= this.lines.length - 1) return;

        const line1 = this.lines[lineIdx];
        const line2 = this.lines[lineIdx + 1];

        const mergedWords = [...(line1.words || []), ...(line2.words || [])];
        const mergedLine = {
            id: line1.id,
            text: `${line1.text} ${line2.text}`,
            start: line1.start,
            end: line2.end,
            words: mergedWords
        };

        this.lines.splice(lineIdx, 2, mergedLine);
        this._notifyChange();
        this.render();
    }

    deleteLine(lineIdx) {
        if (!confirm("Delete this lyric line?")) return;
        this.lines.splice(lineIdx, 1);
        this._notifyChange();
        this.render();
    }

    addLine() {
        const lastLine = this.lines[this.lines.length - 1];
        const newStart = lastLine ? lastLine.end + 0.5 : 0.0;
        const newEnd = newStart + 3.0;

        const newLine = {
            id: `line_${Date.now()}`,
            text: "New lyric line",
            start: +(newStart).toFixed(2),
            end: +(newEnd).toFixed(2),
            words: [
                { text: "New", start: newStart, end: newStart + 0.8 },
                { text: "lyric", start: newStart + 0.9, end: newStart + 1.8 },
                { text: "line", start: newStart + 1.9, end: newEnd }
            ]
        };

        this.lines.push(newLine);
        this._notifyChange();
        this.render();
    }

    updateLineText(lineIdx, newText) {
        const line = this.lines[lineIdx];
        if (!line) return;

        line.text = newText;
        const tokens = newText.split(/\s+/).filter(Boolean);

        // If word count matches, update texts preserving timing
        if (tokens.length === (line.words || []).length) {
            tokens.forEach((t, i) => line.words[i].text = t);
        } else {
            // Distribute proportionally across line duration
            const dur = Math.max(0.2, line.end - line.start);
            const slot = dur / Math.max(1, tokens.length);
            line.words = tokens.map((t, i) => ({
                text: t,
                start: +(line.start + (i * slot)).toFixed(3),
                end: +(line.start + ((i + 1) * slot) - 0.02).toFixed(3),
            }));
        }

        this._notifyChange();
        this.render();
    }
}

window.LyricTimeline = LyricTimeline;
