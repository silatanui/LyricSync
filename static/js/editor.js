/**
 * LyricSync Studio Editor Main Controller
 */
document.addEventListener('DOMContentLoaded', async () => {
    const workspace = document.querySelector('.editor-workspace');
    if (!workspace) return;

    const projectId = workspace.getAttribute('data-project-id');
    const videoEl = document.getElementById('mainVideo');
    const audioEl = document.getElementById('mainAudio');
    const overlayEl = document.getElementById('lyricOverlay');
    const videoContainer = document.getElementById('videoContainer');

    // UI Elements
    const playPauseBtn = document.getElementById('playPauseBtn');
    const playIcon = document.getElementById('playIcon');
    const scrubber = document.getElementById('playbackScrubber');
    const currentTimeDisplay = document.getElementById('currentTimeDisplay');
    const totalDurationDisplay = document.getElementById('totalDurationDisplay');
    const speedSelect = document.getElementById('playbackSpeed');
    const replay5Btn = document.getElementById('replay5Btn');
    const forward5Btn = document.getElementById('forward5Btn');
    const addLineBtn = document.getElementById('addLineBtn');

    const transcribeBtn = document.getElementById('transcribeBtn');
    const saveRevisionBtn = document.getElementById('saveRevisionBtn');
    const exportVideoBtn = document.getElementById('exportVideoBtn');
    const exportBtnLabel = document.getElementById('exportBtnLabel');
    const downloadHeaderBtn = document.getElementById('downloadHeaderBtn');
    const editorProjectName = document.getElementById('editorProjectName');
    const projectPublicToggle = document.getElementById('projectPublicToggle');

    // Canva-Style Left Dock & Drawer Navigation
    const studioLeftDock = document.getElementById('studioLeftDock');
    const studioLeftDrawer = document.getElementById('studioLeftDrawer');
    const closeDrawerBtn = document.getElementById('closeDrawerBtn');
    const drawerTitle = document.getElementById('drawerTitle');
    const dockTabBtns = document.querySelectorAll('.dock-tab-btn');
    const drawerPanels = {
        typography: document.getElementById('drawerPanelTypography'),
        effects: document.getElementById('drawerPanelEffects'),
        backgrounds: document.getElementById('drawerPanelBackgrounds'),
        canvas: document.getElementById('drawerPanelCanvas'),
        lyrics: document.getElementById('drawerPanelLyrics'),
    };

    // Font Preview Picker Elements
    const fontPickerBtn = document.getElementById('fontPickerBtn');
    const fontPickerLabel = document.getElementById('fontPickerLabel');
    const fontPickerDropdown = document.getElementById('fontPickerDropdown');
    const fontPreviewItems = document.querySelectorAll('.font-preview-item');
    const styleFontFamily = document.getElementById('styleFontFamily');

    // Style & Render Controls
    const styleFontSize = document.getElementById('styleFontSize');
    const fontSizeDisplay = document.getElementById('fontSizeDisplay');
    const styleLineHeight = document.getElementById('styleLineHeight');
    const lineHeightDisplay = document.getElementById('lineHeightDisplay');
    const styleLetterSpacing = document.getElementById('styleLetterSpacing');
    const styleFontWeight = document.getElementById('styleFontWeight');
    const styleFontStyle = document.getElementById('styleFontStyle');
    const styleEffect = document.getElementById('styleEffect');
    const renderResolution = document.getElementById('renderResolution');
    const audioVolume = document.getElementById('audioVolume');
    const audioVolumeDisplay = document.getElementById('audioVolumeDisplay');
    const stylePrimaryColor = document.getElementById('stylePrimaryColor');
    const styleHighlightColor = document.getElementById('styleHighlightColor');
    const styleMode = document.getElementById('styleMode');
    const styleFormat = document.getElementById('styleFormat');
    const renderAspectRatio = document.getElementById('renderAspectRatio');

    // Canvas Interactive Text Box & Micro-Toolbar Elements
    const activeLineContainer = document.getElementById('activeLineContainer');
    const canvasBoxToolbar = document.getElementById('canvasBoxToolbar');
    const tbAlignLeft = document.getElementById('tbAlignLeft');
    const tbAlignCenter = document.getElementById('tbAlignCenter');
    const tbAlignRight = document.getElementById('tbAlignRight');
    const tbScaleDown = document.getElementById('tbScaleDown');
    const tbScaleUp = document.getElementById('tbScaleUp');
    const tbPosTop = document.getElementById('tbPosTop');
    const tbPosCenter = document.getElementById('tbPosCenter');
    const tbPosBottom = document.getElementById('tbPosBottom');
    const tbEditLine = document.getElementById('tbEditLine');

    // Custom Lyrics Import Controls
    const drawerLyricsFileInput = document.getElementById('drawerLyricsFileInput');
    const drawerLyricsTextarea = document.getElementById('drawerLyricsTextarea');
    const drawerImportLyricsBtn = document.getElementById('drawerImportLyricsBtn');
    const drawerLyricsAlert = document.getElementById('drawerLyricsAlert');

    // Background Template Controls
    const templateCards = document.querySelectorAll('.template-visual-card');
    const themeApplyStatus = document.getElementById('themeApplyStatus');
    let selectedBackgroundTemplate = 'burgundy_studio';

    // Canvas Aspect Ratio Controls
    const ratioBtns = document.querySelectorAll('.canvas-ratio-choice-btn');
    let currentAspectRatio = '16:9';

    // Lyrics Format & Song Sheet Controls
    let currentLyricsFormat = 'stanza';
    const lyricsSheetList = document.getElementById('lyricsSheetList');
    const lyricsSheetLineCount = document.getElementById('lyricsSheetLineCount');
    const confidenceHeatmap = document.getElementById('confidenceHeatmap');
    const timelineContainer = document.getElementById('timelineContainer');
    const toggleDetailTimelineBtn = document.getElementById('toggleDetailTimelineBtn');

    // Export Modal Elements
    const exportModalEl = document.getElementById('exportModal');
    const exportModal = new bootstrap.Modal(exportModalEl);
    const exportStageText = document.getElementById('exportStageText');
    const exportProgressBar = document.getElementById('exportProgressBar');
    const exportProgressPct = document.getElementById('exportProgressPct');
    const exportSpinner = document.getElementById('exportSpinner');
    const exportErrorBox = document.getElementById('exportErrorBox');
    const downloadFinalVideoBtn = document.getElementById('downloadFinalVideoBtn');

    // Initialize Player & Timeline
    const player = new SynchronizedPlayer(videoEl, audioEl, overlayEl);
    const timeline = new LyricTimeline(document.getElementById('lyricLinesList'), player);

    function renderConfidenceHeatmap(lines = timeline.getLines()) {
        if (!confidenceHeatmap) return;
        confidenceHeatmap.innerHTML = '';
        if (!lines || !lines.length) {
            const empty = document.createElement('div');
            empty.className = 'confidence-empty';
            empty.textContent = 'Sync confidence will appear after lyrics are analyzed';
            confidenceHeatmap.appendChild(empty);
            return;
        }
        const duration = videoEl.duration || audioEl.duration || 1;
        (lines || []).forEach((line, index) => {
            const segment = document.createElement('button');
            const confidence = Number(line.confidence ?? 0.9);
            segment.type = 'button';
            segment.className = `confidence-segment ${confidence >= 0.8 ? 'high' : confidence >= 0.5 ? 'edited' : 'low'}`;
            segment.style.left = `${Math.max(0, line.start / duration) * 100}%`;
            segment.style.width = `${Math.max(0.6, (line.end - line.start) / duration * 100)}%`;
            segment.title = `Line ${index + 1}: ${Math.round(confidence * 100)}% confidence. Click to seek.`;
            segment.addEventListener('click', () => player.seekTo(line.start));
            confidenceHeatmap.appendChild(segment);
        });
    }

    renderConfidenceHeatmap();
    if (toggleDetailTimelineBtn && timelineContainer) {
        toggleDetailTimelineBtn.addEventListener('click', () => {
            const open = timelineContainer.classList.toggle('timeline-details-open');
            if (document.getElementById('lyricLinesList')) {
                document.getElementById('lyricLinesList').classList.toggle('d-none', !open);
                document.getElementById('lyricLinesList').classList.toggle('d-flex', open);
            }
            if (confidenceHeatmap) confidenceHeatmap.closest('.confidence-heatmap-wrap').classList.toggle('d-none', open);
            toggleDetailTimelineBtn.innerHTML = open
                ? '<i class="bi bi-soundwave"></i> Show Waveform'
                : '<i class="bi bi-list-columns-reverse"></i> Edit Timing';
        });
    }

    if (editorProjectName) {
        const saveProjectName = async () => {
            const name = editorProjectName.value.trim();
            if (!name) {
                editorProjectName.value = canonical?.project?.name || 'Untitled Song';
                return;
            }
            try {
                const res = await LyricSyncAPI.updateProject(projectId, { name });
                if (!res.success) throw new Error(res.error?.message || 'Failed to save project name');
                editorProjectName.value = res.project.name;
            } catch (err) {
                console.warn('Could not save project name:', err);
            }
        };
        editorProjectName.addEventListener('change', saveProjectName);
        editorProjectName.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                editorProjectName.blur();
            }
        });
    }

    if (projectPublicToggle) {
        projectPublicToggle.addEventListener('change', async () => {
            try {
                const response = await LyricSyncAPI.updateProject(projectId, {
                    is_public: projectPublicToggle.checked,
                });
                if (!response.success) throw new Error(response.error?.message || 'Could not update visibility');
            } catch (error) {
                projectPublicToggle.checked = !projectPublicToggle.checked;
                console.warn('Could not update project visibility:', error);
            }
        });
    }

    function formatTime(s) {
        const sec = Math.max(0, s);
        const m = Math.floor(sec / 60);
        const remS = Math.floor(sec % 60);
        const cs = Math.floor((sec - Math.floor(sec)) * 100);
        return `${m < 10 ? '0' : ''}${m}:${remS < 10 ? '0' : ''}${remS}.${cs < 10 ? '0' : ''}${cs}`;
    }

    // Helper: update font picker button display
    function updateFontPickerDisplay(fontName) {
        if (!fontPickerLabel) return;
        fontPickerLabel.textContent = fontName;
        let fontFamily = `"${fontName}", sans-serif`;
        if (fontName === 'Caveat') fontFamily = `'Caveat', cursive, sans-serif`;
        else if (['Playfair Display', 'Cinzel', 'Merriweather', 'Georgia', 'Libre Baskerville'].includes(fontName)) fontFamily = `"${fontName}", serif`;
        fontPickerLabel.style.fontFamily = fontFamily;

        fontPreviewItems.forEach(item => {
            if (item.getAttribute('data-font') === fontName) {
                item.classList.add('active');
                if (!item.querySelector('.bi-check2')) {
                    const check = document.createElement('i');
                    check.className = 'bi bi-check2';
                    item.appendChild(check);
                }
            } else {
                item.classList.remove('active');
                const chk = item.querySelector('.bi-check2');
                if (chk) chk.remove();
            }
        });
    }

    // Load Project Data from Server
    let canonical = null;
    try {
        const res = await LyricSyncAPI.getProject(projectId);
        if (res.success && res.canonical) {
            canonical = res.canonical;

            // Apply style & format config with Caveat, 34px, 1.0x line-height defaults
            if (canonical.style) {
                const s = canonical.style;
                if (s.format) {
                    currentLyricsFormat = s.format;
                    if (styleFormat) styleFormat.value = s.format;
                }
                const fontVal = s.font || 'Caveat';
                if (styleFontFamily) styleFontFamily.value = fontVal;
                updateFontPickerDisplay(fontVal);

                const fontSizeVal = s.font_size || 28;
                if (styleFontSize) styleFontSize.value = fontSizeVal;
                if (fontSizeDisplay) fontSizeDisplay.textContent = `${fontSizeVal}px`;

                const lineHeightVal = s.line_height !== undefined ? s.line_height : 0.9;
                if (styleLineHeight) styleLineHeight.value = lineHeightVal;
                if (lineHeightDisplay) lineHeightDisplay.textContent = `${lineHeightVal}x`;

                if (s.primary_color && stylePrimaryColor) stylePrimaryColor.value = s.primary_color;
                if (s.highlight_color && styleHighlightColor) styleHighlightColor.value = s.highlight_color;
                if (s.mode && styleMode) styleMode.value = s.mode;
                if (s.letter_spacing !== undefined && styleLetterSpacing) styleLetterSpacing.value = s.letter_spacing;
                if (s.font_weight && styleFontWeight) styleFontWeight.value = s.font_weight;
                if (s.effect && styleEffect) styleEffect.value = s.effect;
                if (s.font_style && styleFontStyle) styleFontStyle.value = s.font_style;

                const posVal = s.position || 'center';
                const rPos = document.querySelector(`input[name="positionRadio"][value="${posVal}"]`);
                if (rPos) rPos.checked = true;

                const alignVal = s.text_align || 'center';
                const rAlign = document.querySelector(`input[name="alignRadio"][value="${alignVal}"]`);
                if (rAlign) rAlign.checked = true;

                player.setStyle({ ...s, font: fontVal, fontSize: fontSizeVal, lineHeight: lineHeightVal, fontWeight: s.font_weight || 600, fontStyle: s.font_style || 'normal', letterSpacing: s.letter_spacing || 0, effect: s.effect || 'none', position: posVal, textAlign: alignVal });
            }

            // Load lyrics into timeline, player, and right sidebar lyrics sheet
            timeline.setLines(canonical.lyrics || []);
            player.setLyrics(canonical.lyrics || []);
            renderLyricsSheet(canonical.lyrics || []);
            renderConfidenceHeatmap(canonical.lyrics || []);

            // Apply render aspect ratio
            if (canonical.render?.aspect_ratio) {
                updateAspectContainer(canonical.render.aspect_ratio);
            }

            // Apply background template
            if (canonical.meta?.background_template) {
                selectTemplate(canonical.meta.background_template);
            }
        }
    } catch (e) {
        console.error("Failed to load project details:", e);
    }

    if (audioVolume) {
        audioVolume.addEventListener('input', (event) => {
            const value = parseFloat(event.target.value);
            audioEl.volume = value;
            if (audioVolumeDisplay) audioVolumeDisplay.textContent = `${Math.round(value * 100)}%`;
        });
    }

    // Video & Audio metadata loaded
    const updateDuration = () => {
        const dur = videoEl.duration || audioEl.duration || 0;
        scrubber.max = dur;
        totalDurationDisplay.textContent = formatTime(dur);
    };
    videoEl.addEventListener('loadedmetadata', updateDuration);
    audioEl.addEventListener('loadedmetadata', updateDuration);

    // Playback time tracking
    videoEl.addEventListener('timeupdate', () => {
        const cur = videoEl.currentTime;
        if (!scrubber.matches(':active')) {
            scrubber.value = cur;
        }
        currentTimeDisplay.textContent = formatTime(cur);
    });

    // Play/Pause toggle
    const togglePlayback = () => {
        player.togglePlay();
    };
    playPauseBtn.addEventListener('click', togglePlayback);

    videoEl.addEventListener('play', () => {
        playIcon.className = 'bi bi-pause-fill fs-4';
    });
    videoEl.addEventListener('pause', () => {
        playIcon.className = 'bi bi-play-fill fs-4';
    });

    // Keyboard Space shortcut
    window.addEventListener('keydown', (e) => {
        if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
            e.preventDefault();
            togglePlayback();
        }
    });

    // Scrubber drag / input
    scrubber.addEventListener('input', (e) => {
        const t = parseFloat(e.target.value);
        currentTimeDisplay.textContent = formatTime(t);
    });
    scrubber.addEventListener('change', (e) => {
        player.seekTo(parseFloat(e.target.value));
    });

    // Replay / Forward 5s
    replay5Btn.addEventListener('click', () => {
        player.seekTo(Math.max(0, videoEl.currentTime - 5));
    });
    forward5Btn.addEventListener('click', () => {
        player.seekTo(videoEl.currentTime + 5);
    });

    // Playback Speed
    speedSelect.addEventListener('change', (e) => {
        const rate = parseFloat(e.target.value);
        videoEl.playbackRate = rate;
        if (audioEl) audioEl.playbackRate = rate;
    });

    // Add Line
    addLineBtn.addEventListener('click', () => timeline.addLine());

    // ================= CANVA-STYLE LEFT DOCK & DRAWER =================
    let currentDrawerTab = 'typography';

    const drawerTitles = {
        typography: '<i class="bi bi-fonts me-1" style="color: var(--brand-burgundy);"></i> Typography &amp; Styles',
        backgrounds: '<i class="bi bi-palette me-1" style="color: var(--brand-burgundy);"></i> Aesthetic Backgrounds',
        canvas: '<i class="bi bi-aspect-ratio me-1" style="color: var(--brand-burgundy);"></i> Canvas Format',
        lyrics: '<i class="bi bi-file-earmark-text me-1" style="color: var(--brand-burgundy);"></i> Custom Lyrics',
        effects: '<i class="bi bi-stars me-1" style="color: var(--brand-burgundy);"></i> Lyric Effects',
    };

    function openDrawerTab(tabName) {
        if (!studioLeftDrawer) return;

        if (currentDrawerTab === tabName && !studioLeftDrawer.classList.contains('d-none')) {
            closeDrawer();
            return;
        }

        currentDrawerTab = tabName;
        studioLeftDrawer.classList.remove('d-none');

        dockTabBtns.forEach(btn => {
            if (btn.getAttribute('data-dock-tab') === tabName) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        if (drawerTitle && drawerTitles[tabName]) {
            drawerTitle.innerHTML = drawerTitles[tabName];
        }

        Object.entries(drawerPanels).forEach(([name, panel]) => {
            if (panel) {
                if (name === tabName) {
                    panel.classList.remove('d-none');
                } else {
                    panel.classList.add('d-none');
                }
            }
        });
    }

    function closeDrawer() {
        if (studioLeftDrawer) studioLeftDrawer.classList.add('d-none');
        dockTabBtns.forEach(btn => btn.classList.remove('active'));
    }

    dockTabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.getAttribute('data-dock-tab');
            openDrawerTab(tab);
        });
    });

    if (closeDrawerBtn) {
        closeDrawerBtn.addEventListener('click', closeDrawer);
    }

    // ================= FONT PREVIEW PICKER =================
    if (fontPickerBtn && fontPickerDropdown) {
        fontPickerBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fontPickerDropdown.classList.toggle('show');
        });

        fontPreviewItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                const fontName = item.getAttribute('data-font');
                if (styleFontFamily) styleFontFamily.value = fontName;
                updateFontPickerDisplay(fontName);
                fontPickerDropdown.classList.remove('show');
                applyCurrentStyle();
            });
        });

        document.addEventListener('click', (e) => {
            if (!fontPickerBtn.contains(e.target) && !fontPickerDropdown.contains(e.target)) {
                fontPickerDropdown.classList.remove('show');
            }
        });
    }

    // ================= LIVE AUTO-APPLY & DEBOUNCED AUTO-SAVE =================
    function getSelectedPosition() {
        const checked = document.querySelector('input[name="positionRadio"]:checked');
        return checked ? checked.value : 'center';
    }

    function getSelectedAlignment() {
        const checked = document.querySelector('input[name="alignRadio"]:checked');
        return checked ? checked.value : 'center';
    }

    function updateCanvasToolbarButtons(alignVal, posVal) {
        if (tbAlignLeft) tbAlignLeft.classList.toggle('active', alignVal === 'left');
        if (tbAlignCenter) tbAlignCenter.classList.toggle('active', alignVal === 'center');
        if (tbAlignRight) tbAlignRight.classList.toggle('active', alignVal === 'right');

        if (tbPosTop) tbPosTop.classList.toggle('active', posVal === 'top');
        if (tbPosCenter) tbPosCenter.classList.toggle('active', posVal === 'center');
        if (tbPosBottom) tbPosBottom.classList.toggle('active', posVal === 'bottom');
    }

    function applyCurrentStyle() {
        const alignVal = getSelectedAlignment();
        const posVal = getSelectedPosition();
        const fontVal = styleFontFamily ? styleFontFamily.value : 'Caveat';
        const fontSizeVal = styleFontSize ? parseInt(styleFontSize.value) : 28;
        const lineHeightVal = styleLineHeight ? parseFloat(styleLineHeight.value) : 0.9;

        const styleConfig = {
            format: currentLyricsFormat,
            font: fontVal,
            fontSize: fontSizeVal,
            lineHeight: lineHeightVal,
            primaryColor: stylePrimaryColor ? stylePrimaryColor.value : '#FFFFFF',
            highlightColor: styleHighlightColor ? styleHighlightColor.value : '#10B981',
            position: posVal,
            textAlign: alignVal,
            mode: styleMode ? styleMode.value : 'karaoke',
            letterSpacing: styleLetterSpacing ? parseFloat(styleLetterSpacing.value) : 0,
            fontWeight: styleFontWeight ? parseInt(styleFontWeight.value) : 600,
            effect: styleEffect ? styleEffect.value : 'none',
            fontStyle: styleFontStyle ? styleFontStyle.value : 'normal',
        };
        player.setStyle(styleConfig);
        updateCanvasToolbarButtons(alignVal, posVal);
        scheduleAutoSaveStyle();
        return styleConfig;
    }

    async function applyEffectToAllLines(effect) {
        const lines = timeline.getLines();
        if (!lines.length) return;

        lines.forEach(line => {
            line.effect = effect;
        });
        timeline.setLines(lines);
        player.setLyrics(lines);
        renderLyricsSheet(lines);
        renderConfidenceHeatmap(lines);

        try {
            await LyricSyncAPI.saveLyrics(projectId, lines);
        } catch (error) {
            console.warn('Could not save default lyric effect:', error);
        }
    }

    let autoSaveTimer = null;
    function scheduleAutoSaveStyle() {
        if (autoSaveTimer) clearTimeout(autoSaveTimer);
        autoSaveTimer = setTimeout(async () => {
            try {
                const styleConfig = {
                    format: currentLyricsFormat,
                    font: styleFontFamily ? styleFontFamily.value : 'Caveat',
                    font_size: styleFontSize ? parseInt(styleFontSize.value) : 28,
                    line_height: styleLineHeight ? parseFloat(styleLineHeight.value) : 0.9,
                    letter_spacing: styleLetterSpacing ? parseFloat(styleLetterSpacing.value) : 0,
                    font_weight: styleFontWeight ? parseInt(styleFontWeight.value) : 600,
                    effect: styleEffect ? styleEffect.value : 'none',
                    font_style: styleFontStyle ? styleFontStyle.value : 'normal',
                    primary_color: stylePrimaryColor ? stylePrimaryColor.value : '#FFFFFF',
                    highlight_color: styleHighlightColor ? styleHighlightColor.value : '#10B981',
                    position: getSelectedPosition(),
                    text_align: getSelectedAlignment(),
                    mode: styleMode ? styleMode.value : 'karaoke',
                };
                await LyricSyncAPI.updateStyle(projectId, styleConfig, { aspect_ratio: currentAspectRatio, lyrics_format: currentLyricsFormat });
            } catch (e) {
                console.warn("Auto-saving style note:", e);
            }
        }, 300);
    }

    // Real-time style changes
    if (stylePrimaryColor) stylePrimaryColor.addEventListener('input', () => applyCurrentStyle());
    if (styleHighlightColor) styleHighlightColor.addEventListener('input', () => applyCurrentStyle());
    if (styleMode) styleMode.addEventListener('change', () => applyCurrentStyle());
    if (styleFormat) {
        styleFormat.addEventListener('change', (e) => {
            currentLyricsFormat = e.target.value;
            applyCurrentStyle();
        });
    }

    document.querySelectorAll('input[name="positionRadio"]').forEach(r => {
        r.addEventListener('change', () => applyCurrentStyle());
    });
    document.querySelectorAll('input[name="alignRadio"]').forEach(r => {
        r.addEventListener('change', () => applyCurrentStyle());
    });

    if (styleFontSize) {
        styleFontSize.addEventListener('input', (e) => {
            if (fontSizeDisplay) fontSizeDisplay.textContent = `${e.target.value}px`;
            applyCurrentStyle();
        });
    }

    if (styleLineHeight) {
        styleLineHeight.addEventListener('input', (e) => {
            if (lineHeightDisplay) lineHeightDisplay.textContent = `${e.target.value}x`;
            applyCurrentStyle();
        });
    }

    if (styleLetterSpacing) styleLetterSpacing.addEventListener('input', () => applyCurrentStyle());
    if (styleFontWeight) styleFontWeight.addEventListener('change', () => applyCurrentStyle());
    if (styleEffect) styleEffect.addEventListener('change', () => {
        applyCurrentStyle();
        applyEffectToAllLines(styleEffect.value);
    });
    if (styleFontStyle) styleFontStyle.addEventListener('change', () => applyCurrentStyle());

    // ================= CANVAS TEXT BOX & MICRO-TOOLBAR =================
    if (activeLineContainer) {
        activeLineContainer.addEventListener('click', (e) => {
            e.stopPropagation();
            activeLineContainer.classList.add('selected');
        });
    }

    document.addEventListener('click', (e) => {
        if (activeLineContainer && !activeLineContainer.contains(e.target)) {
            activeLineContainer.classList.remove('selected');
        }
    });

    if (tbAlignLeft) tbAlignLeft.addEventListener('click', (e) => {
        e.stopPropagation();
        const r = document.getElementById('alignLeft');
        if (r) { r.checked = true; applyCurrentStyle(); }
    });
    if (tbAlignCenter) tbAlignCenter.addEventListener('click', (e) => {
        e.stopPropagation();
        const r = document.getElementById('alignCenter');
        if (r) { r.checked = true; applyCurrentStyle(); }
    });
    if (tbAlignRight) tbAlignRight.addEventListener('click', (e) => {
        e.stopPropagation();
        const r = document.getElementById('alignRight');
        if (r) { r.checked = true; applyCurrentStyle(); }
    });

    if (tbScaleDown) tbScaleDown.addEventListener('click', (e) => {
        e.stopPropagation();
        if (styleFontSize) {
            styleFontSize.value = Math.max(16, parseInt(styleFontSize.value) - 2);
            if (fontSizeDisplay) fontSizeDisplay.textContent = `${styleFontSize.value}px`;
            applyCurrentStyle();
        }
    });
    if (tbScaleUp) tbScaleUp.addEventListener('click', (e) => {
        e.stopPropagation();
        if (styleFontSize) {
            styleFontSize.value = Math.min(72, parseInt(styleFontSize.value) + 2);
            if (fontSizeDisplay) fontSizeDisplay.textContent = `${styleFontSize.value}px`;
            applyCurrentStyle();
        }
    });

    if (tbPosTop) tbPosTop.addEventListener('click', (e) => {
        e.stopPropagation();
        const r = document.getElementById('posTop');
        if (r) { r.checked = true; applyCurrentStyle(); }
    });
    if (tbPosCenter) tbPosCenter.addEventListener('click', (e) => {
        e.stopPropagation();
        const r = document.getElementById('posCenter');
        if (r) { r.checked = true; applyCurrentStyle(); }
    });
    if (tbPosBottom) tbPosBottom.addEventListener('click', (e) => {
        e.stopPropagation();
        const r = document.getElementById('posBottom');
        if (r) { r.checked = true; applyCurrentStyle(); }
    });

    if (tbEditLine) tbEditLine.addEventListener('click', (e) => {
        e.stopPropagation();
        openCanvasEditor();
    });

    // ================= CANVAS ASPECT RATIO =================
    function updateAspectContainer(aspect) {
        currentAspectRatio = aspect;
        videoContainer.classList.remove('ratio-16-9', 'ratio-9-16', 'ratio-1-1', 'ratio-4-5');
        const cls = 'ratio-' + aspect.replace(':', '-');
        videoContainer.classList.add(cls);

        if (renderAspectRatio) renderAspectRatio.value = aspect;
        if (exportBtnLabel) exportBtnLabel.textContent = `Export ${aspect} Video`;

        ratioBtns.forEach(btn => {
            if (btn.getAttribute('data-ratio') === aspect) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }

    ratioBtns.forEach(btn => {
        btn.addEventListener('click', async () => {
            const aspect = btn.getAttribute('data-ratio');
            updateAspectContainer(aspect);

            try {
                const styleConfig = applyCurrentStyle();
                await LyricSyncAPI.updateStyle(projectId, styleConfig, { aspect_ratio: aspect });
                const res = await LyricSyncAPI.updateBackgroundTemplate(projectId, selectedBackgroundTemplate, aspect);
                if (res.success && res.video_url) {
                    const curTime = videoEl.currentTime;
                    const wasPlaying = !videoEl.paused;
                    videoEl.src = res.video_url;
                    videoEl.load();
                    videoEl.currentTime = curTime;
                    if (wasPlaying) videoEl.play().catch(() => {});
                }
            } catch (e) {
                console.warn("Could not update aspect background video:", e);
            }
        });
    });

    if (renderAspectRatio) {
        renderAspectRatio.addEventListener('change', (e) => {
            updateAspectContainer(e.target.value);
        });
    }

    // ================= BACKGROUND TEMPLATE SWITCHER =================
    function selectTemplate(templateId) {
        selectedBackgroundTemplate = templateId;
        templateCards.forEach(card => {
            if (card.getAttribute('data-template-id') === templateId) {
                card.classList.add('active');
            } else {
                card.classList.remove('active');
            }
        });
    }

    templateCards.forEach(card => {
        card.addEventListener('click', async () => {
            const tid = card.getAttribute('data-template-id');
            selectTemplate(tid);

            // Show the selected artwork immediately while the server prepares the looped video.
            const previewImage = card.querySelector('img');
            if (previewImage) {
                videoContainer.style.backgroundImage = `url("${previewImage.src}")`;
                videoContainer.classList.add('theme-preview-loading');
            }
            if (themeApplyStatus) themeApplyStatus.classList.remove('d-none');

            try {
                const res = await LyricSyncAPI.updateBackgroundTemplate(projectId, tid, currentAspectRatio);
                if (res.success && res.video_url) {
                    const curTime = videoEl.currentTime;
                    const wasPlaying = !videoEl.paused;
                    videoEl.src = res.video_url;
                    videoEl.load();
                    videoEl.currentTime = curTime;
                    if (wasPlaying) {
                        videoEl.play().catch(() => {});
                    }
                }
            } catch (err) {
                console.warn("Background update error:", err);
            } finally {
                videoContainer.classList.remove('theme-preview-loading');
                if (themeApplyStatus) themeApplyStatus.classList.add('d-none');
            }
        });
    });

    // ================= CUSTOM LYRICS IMPORT =================
    if (drawerImportLyricsBtn) {
        drawerImportLyricsBtn.addEventListener('click', async () => {
            const textVal = drawerLyricsTextarea ? drawerLyricsTextarea.value.trim() : '';
            const file = drawerLyricsFileInput && drawerLyricsFileInput.files ? drawerLyricsFileInput.files[0] : null;

            if (!textVal && !file) {
                if (drawerLyricsAlert) {
                    drawerLyricsAlert.className = 'alert alert-warning small py-2';
                    drawerLyricsAlert.textContent = 'Please choose a .txt / .lrc file or paste lyrics text.';
                    drawerLyricsAlert.classList.remove('d-none');
                }
                return;
            }

            const origHtml = drawerImportLyricsBtn.innerHTML;
            drawerImportLyricsBtn.disabled = true;
            drawerImportLyricsBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Importing...';

            try {
                let payload;
                if (file) {
                    const fd = new FormData();
                    fd.append('lyrics_file', file);
                    if (textVal) fd.append('lyrics_text', textVal);
                    payload = fd;
                } else {
                    payload = textVal;
                }

                const res = await LyricSyncAPI.importCustomLyrics(projectId, payload);
                if (res.success && res.lyrics) {
                    timeline.setLines(res.lyrics);
                    player.setLyrics(res.lyrics);
                    renderLyricsSheet(res.lyrics);
                    renderConfidenceHeatmap(res.lyrics);

                    if (drawerLyricsAlert) {
                        drawerLyricsAlert.className = 'alert alert-success small py-2';
                        drawerLyricsAlert.textContent = `Imported ${res.lyrics.length} custom lyric lines successfully!`;
                        drawerLyricsAlert.classList.remove('d-none');
                    }
                    if (drawerLyricsTextarea) drawerLyricsTextarea.value = '';
                    if (drawerLyricsFileInput) drawerLyricsFileInput.value = '';
                } else {
                    throw new Error(res.error?.message || "Failed to parse or import custom lyrics.");
                }
            } catch (err) {
                if (drawerLyricsAlert) {
                    drawerLyricsAlert.className = 'alert alert-danger small py-2';
                    drawerLyricsAlert.textContent = 'Import error: ' + err.message;
                    drawerLyricsAlert.classList.remove('d-none');
                }
            } finally {
                drawerImportLyricsBtn.disabled = false;
                drawerImportLyricsBtn.innerHTML = origHtml;
            }
        });
    }

    // Group lyrics lines into stanzas with musical section tags [Verse 1], [Chorus], etc.
    function groupLyricsIntoStanzas(lines) {
        if (!lines || !lines.length) return [];
        const sectionNames = [
            '[Verse 1]',
            '[Chorus]',
            '[Verse 2]',
            '[Chorus]',
            '[Bridge]',
            '[Chorus]',
            '[Outro]'
        ];

        const stanzas = [];
        let currentStanzaLines = [];
        let currentTitle = (lines[0] && lines[0].section) || sectionNames[0];

        lines.forEach((line, idx) => {
            const prevLine = idx > 0 ? lines[idx - 1] : null;
            const pause = prevLine ? (line.start - prevLine.end) : 0;
            const hasExplicitSection = line.section && line.section !== currentTitle;

            if (idx > 0 && (hasExplicitSection || pause > 2.5 || currentStanzaLines.length >= 4)) {
                stanzas.push({
                    title: currentTitle,
                    lines: currentStanzaLines
                });
                const nextSectionIdx = Math.min(stanzas.length, sectionNames.length - 1);
                currentTitle = line.section || sectionNames[nextSectionIdx];
                currentStanzaLines = [];
            }
            currentStanzaLines.push({ ...line, originalIndex: idx });
        });

        if (currentStanzaLines.length) {
            stanzas.push({
                title: currentTitle,
                lines: currentStanzaLines
            });
        }
        return stanzas;
    }

    // Full Plain Text Song Lyrics Sheet in Right Sidebar (Crisp White Background)
    function renderLyricsSheet(lines) {
        if (!lyricsSheetList) return;
        lyricsSheetList.innerHTML = '';

        if (!lines || lines.length === 0) {
            lyricsSheetList.innerHTML = `
                <div class="text-center py-5 text-secondary">
                    <i class="bi bi-music-note-beamed fs-1 d-block mb-2" style="color: #94A3B8; opacity: 0.4;"></i>
                    <p class="fw-bold mb-1 text-dark">No Lyrics Detected Yet</p>
                    <p class="small text-secondary mb-3">Transcribe audio with Whisper to extract synchronized lyrics.</p>
                    <button class="btn btn-outline-burgundy btn-sm px-3 py-1.5" onclick="document.getElementById('transcribeBtn').click()">
                        <i class="bi bi-stars me-1"></i> Transcribe AI
                    </button>
                </div>
            `;
            if (lyricsSheetLineCount) lyricsSheetLineCount.textContent = '0 lines';
            return;
        }

        if (lyricsSheetLineCount) {
            lyricsSheetLineCount.textContent = `${lines.length} lines`;
        }

        // Always render as clean, structured plain text song sheet
        const stanzas = groupLyricsIntoStanzas(lines);
        stanzas.forEach((stanza, sIdx) => {
            const block = document.createElement('div');
            block.className = 'lyrics-stanza-block';
            block.dataset.stanzaIndex = sIdx;

            const header = document.createElement('div');
            header.className = 'stanza-header-tag';
            header.textContent = stanza.title;
            block.appendChild(header);

            const linesCol = document.createElement('div');
            linesCol.className = 'd-flex flex-column';

            stanza.lines.forEach((line) => {
                const lineEl = document.createElement('div');
                lineEl.className = 'lyrics-song-line';
                lineEl.dataset.lineIndex = line.originalIndex;
                lineEl.textContent = line.text;
                lineEl.title = `Click to seek to line ${line.originalIndex + 1} (${formatTime(line.start)})`;

                lineEl.addEventListener('click', () => {
                    player.seekTo(line.start);
                    highlightLyricsSheetLine(line.originalIndex);
                });

                linesCol.appendChild(lineEl);
            });

            block.appendChild(linesCol);
            lyricsSheetList.appendChild(block);
        });

        // Highlight active line if playback is in progress
        if (player && player.activeLineIndex >= 0) {
            highlightLyricsSheetLine(player.activeLineIndex);
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

    function highlightLyricsSheetLine(activeIdx) {
        if (!lyricsSheetList) return;
        const songLines = lyricsSheetList.querySelectorAll('.lyrics-song-line');
        songLines.forEach((el) => {
            const idx = parseInt(el.getAttribute('data-line-index'));
            if (idx === activeIdx) {
                el.classList.add('active-singing');
                el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } else {
                el.classList.remove('active-singing');
            }
        });
    }

    // Format selection handler (Controls the canvas lyrics display format)
    function setLyricsFormat(format) {
        currentLyricsFormat = format;
        const styleFormatSelect = document.getElementById('styleFormat');
        if (styleFormatSelect) styleFormatSelect.value = format;

        player.setStyle({ format });

        // Persist to project
        const styleConfig = applyCurrentStyle();
        LyricSyncAPI.updateStyle(projectId, styleConfig, { lyrics_format: format }).catch(e => console.warn(e));
    }

    const styleFormatSelect = document.getElementById('styleFormat');
    if (styleFormatSelect) {
        styleFormatSelect.addEventListener('change', (e) => {
            setLyricsFormat(e.target.value);
        });
    }

    // Active line playback tracker
    window.addEventListener('active-line-changed', (e) => {
        const { lineIndex } = e.detail;
        highlightLyricsSheetLine(lineIndex);

    });

    // Direct canvas lyric editing: click the rendered text, edit in place, then press Enter or click away.
    let editingLineIndex = -1;
    let editingOriginalText = '';
    let editingLineIndices = [];

    function getVisibleCanvasLineIndices(lines) {
        const activeIdx = (player.activeLineIndex >= 0 && player.activeLineIndex < lines.length) ? player.activeLineIndex : 0;
        const chunkSize = currentLyricsFormat === 'line' ? 1 : (currentLyricsFormat === 'sentence' ? 2 : 4);
        const chunkStart = Math.floor(activeIdx / chunkSize) * chunkSize;
        return lines.map((_, index) => index).slice(chunkStart, chunkStart + chunkSize);
    }

    function openCanvasEditor() {
        if (!displayActiveText || displayActiveText.contentEditable === 'true') return;
        const lines = timeline.getLines();
        if (!lines || !lines.length) {
            alert("No lyrics loaded to edit.");
            return;
        }
        editingLineIndices = getVisibleCanvasLineIndices(lines);
        const visibleText = editingLineIndices.map(index => lines[index].text || '').join('\n');
        editingLineIndex = editingLineIndices[0];
        editingOriginalText = visibleText;
        player.pause();
        displayActiveText.textContent = visibleText;
        displayActiveText.contentEditable = 'true';
        displayActiveText.classList.add('canvas-direct-editing');
        displayActiveText.focus();
    }

    function cancelCanvasEditor() {
        if (!displayActiveText || displayActiveText.contentEditable !== 'true') return;
        displayActiveText.contentEditable = 'false';
        displayActiveText.classList.remove('canvas-direct-editing');
        editingLineIndex = -1;
        editingLineIndices = [];
        player.renderActiveFrame(videoEl.currentTime);
    }

    async function saveCanvasEditorText() {
        if (!displayActiveText || displayActiveText.contentEditable !== 'true') return;
        const newText = displayActiveText.textContent.trim();
        if (!newText) {
            displayActiveText.textContent = editingOriginalText;
            return;
        }
        const lines = timeline.getLines();
        const editedTexts = newText.split(/\n+/).map(text => text.trim()).filter(Boolean);
        if (!editedTexts.length) return;

        editingLineIndices.forEach((lineIndex, visibleIndex) => {
            const line = lines[lineIndex];
            if (!line) return;
            const text = editedTexts[visibleIndex] || line.text;
            line.text = text;
            line.confidence = Math.min(Number(line.confidence ?? 0.9), 0.55);
            const words = text.split(/\s+/).filter(Boolean);
            const durPerWord = (line.end - line.start) / Math.max(1, words.length);
            line.words = words.map((word, wordIndex) => ({
                text: word,
                start: parseFloat((line.start + wordIndex * durPerWord).toFixed(2)),
                end: parseFloat((line.start + (wordIndex + 1) * durPerWord).toFixed(2))
            }));
        });

        displayActiveText.contentEditable = 'false';
        displayActiveText.classList.remove('canvas-direct-editing');
        editingLineIndex = -1;
        editingLineIndices = [];

        // Update timeline, player, and right lyrics sheet immediately
        timeline.setLines(lines);
        player.setLyrics(lines);
        renderLyricsSheet(lines);
        renderConfidenceHeatmap(lines);

        // Persist to server
        try {
            await LyricSyncAPI.saveLyrics(projectId, lines);
        } catch (err) {
            console.error("Failed to persist lyric edits:", err);
            alert("Warning: failed to save lyric edits: " + err.message);
        }
    }

    if (displayActiveText) {
        displayActiveText.addEventListener('click', (e) => {
            e.stopPropagation();
            openCanvasEditor();
        });
        displayActiveText.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                saveCanvasEditorText();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                cancelCanvasEditor();
            }
        });
        displayActiveText.addEventListener('blur', saveCanvasEditorText);
    }

    if (activeLineContainer) {
        activeLineContainer.style.cursor = 'pointer';
        activeLineContainer.style.pointerEvents = 'auto';
    }

    // Keep lyrics sheet synchronized with timeline edits
    timeline.setOnChange((lines) => {
        renderLyricsSheet(lines);
    });


    // Toggle Timeline Height / Collapse
    const toggleTimelineBtn = document.getElementById('toggleTimelineBtn');
    const toggleTimelineText = document.getElementById('toggleTimelineText');
    const toggleTimelineIcon = document.getElementById('toggleTimelineIcon');
    const editorWorkspace = document.querySelector('.editor-workspace');

    if (toggleTimelineBtn && editorWorkspace) {
        toggleTimelineBtn.addEventListener('click', () => {
            const isCollapsed = editorWorkspace.classList.toggle('timeline-collapsed');
            if (isCollapsed) {
                toggleTimelineText.textContent = 'Expand Timeline';
                toggleTimelineIcon.className = 'bi bi-layout-sidebar-inset';
                toggleTimelineBtn.classList.add('btn-secondary', 'text-white');
                toggleTimelineBtn.classList.remove('btn-outline-secondary');
            } else {
                toggleTimelineText.textContent = 'Collapse Timeline';
                toggleTimelineIcon.className = 'bi bi-layout-sidebar-inset-reverse';
                toggleTimelineBtn.classList.remove('btn-secondary', 'text-white');
                toggleTimelineBtn.classList.add('btn-outline-secondary');
            }
        });
    }

    // Toggle Full Theater Canvas Mode
    const toggleTheaterBtn = document.getElementById('toggleTheaterBtn');
    const toggleTheaterText = document.getElementById('toggleTheaterText');
    const toggleTheaterIcon = document.getElementById('toggleTheaterIcon');

    if (toggleTheaterBtn && editorWorkspace) {
        toggleTheaterBtn.addEventListener('click', () => {
            const isTheater = editorWorkspace.classList.toggle('theater-mode');
            if (isTheater) {
                toggleTheaterText.textContent = 'Exit Theater';
                toggleTheaterIcon.className = 'bi bi-arrows-angle-contract';
                toggleTheaterBtn.classList.add('btn-secondary', 'text-white');
                toggleTheaterBtn.classList.remove('btn-outline-secondary');
            } else {
                toggleTheaterText.textContent = 'Theater';
                toggleTheaterIcon.className = 'bi bi-arrows-angle-expand';
                toggleTheaterBtn.classList.remove('btn-secondary', 'text-white');
                toggleTheaterBtn.classList.add('btn-outline-secondary');
            }
        });
    }
    const transcribeModalEl = document.getElementById('transcribeModal');
    const transcribeModal = new bootstrap.Modal(transcribeModalEl);
    const transcribeStageText = document.getElementById('transcribeStageText');
    const transcribeProgressBar = document.getElementById('transcribeProgressBar');
    const transcribeProgressPct = document.getElementById('transcribeProgressPct');
    const transcribeSpinner = document.getElementById('transcribeSpinner');
    const transcribeSuccessIcon = document.getElementById('transcribeSuccessIcon');
    const transcribeErrorBox = document.getElementById('transcribeErrorBox');
    const transcribeModalFooter = document.getElementById('transcribeModalFooter');

    // Transcribe AI Button with Dedicated Progress Modal
    transcribeBtn.addEventListener('click', async () => {
        transcribeSpinner.classList.remove('d-none');
        transcribeSuccessIcon.classList.add('d-none');
        transcribeErrorBox.classList.add('d-none');
        transcribeModalFooter.classList.add('d-none');
        transcribeProgressBar.style.width = '15%';
        transcribeProgressPct.textContent = '15%';
        transcribeStageText.textContent = 'Connecting to OpenAI Whisper-1 engine...';
        transcribeModal.show();

        let ticker = null;
        const progressHandler = (e) => {
            const job = e.detail;
            if (job && job.progress) {
                transcribeProgressBar.style.width = `${job.progress}%`;
                transcribeProgressPct.textContent = `${job.progress}%`;
                if (job.stage) transcribeStageText.textContent = job.stage;
            }
        };

        try {
            const res = await LyricSyncAPI.triggerTranscription(projectId);
            if (!res.success) throw new Error(res.error?.message || "Failed to trigger transcription");

            // Smooth progress ticker while Whisper-1 processes audio over the wire
            const fakeStages = [
                { pct: 30, text: 'Uploading audio stream to OpenAI Whisper API...' },
                { pct: 55, text: 'Analyzing vocal phonemes & calculating word timestamps...' },
                { pct: 75, text: 'Extracting speech tokens and millisecond boundaries...' },
                { pct: 88, text: 'Aligning words into musical lyric lines...' }
            ];
            let fIdx = 0;
            ticker = setInterval(() => {
                if (fIdx < fakeStages.length) {
                    const st = fakeStages[fIdx];
                    transcribeProgressBar.style.width = `${st.pct}%`;
                    transcribeProgressPct.textContent = `${st.pct}%`;
                    transcribeStageText.textContent = st.text;
                    fIdx++;
                }
            }, 1100);

            window.addEventListener('job-progress', progressHandler);
            await LyricSyncAPI.pollJob(res.job_id);

            if (ticker) clearInterval(ticker);
            window.removeEventListener('job-progress', progressHandler);

            // Fetch newly generated canonical lyrics
            const lyricsRes = await LyricSyncAPI.getLyrics(projectId);
            if (lyricsRes.success && lyricsRes.lyrics) {
                timeline.setLines(lyricsRes.lyrics);
                player.setLyrics(lyricsRes.lyrics);
                renderLyricsSheet(lyricsRes.lyrics);
                const revEl = document.getElementById('revisionDisplay') || document.getElementById('revisionBadge');
                if (revEl) revEl.textContent = `Rev ${lyricsRes.revision}`;
            }

            // Success completion
            transcribeSpinner.classList.add('d-none');
            transcribeSuccessIcon.classList.remove('d-none');
            transcribeProgressBar.style.width = '100%';
            transcribeProgressPct.textContent = '100%';
            transcribeStageText.textContent = 'Transcription Complete! Lyrics Loaded into Studio.';

            setTimeout(() => {
                transcribeModal.hide();
            }, 900);
        } catch (err) {
            if (ticker) clearInterval(ticker);
            window.removeEventListener('job-progress', progressHandler);
            transcribeSpinner.classList.add('d-none');
            transcribeErrorBox.textContent = err.message || "An error occurred during transcription.";
            transcribeErrorBox.classList.remove('d-none');
            transcribeModalFooter.classList.remove('d-none');
        }
    });

    // Save Revision Button
    saveRevisionBtn.addEventListener('click', async () => {
        saveRevisionBtn.disabled = true;
        saveRevisionBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Saving...';

        try {
            const lines = timeline.getLines();
            const res = await LyricSyncAPI.saveLyrics(projectId, lines);
            if (res.success) {
                const revEl = document.getElementById('revisionDisplay') || document.getElementById('revisionBadge');
                if (revEl) revEl.textContent = `Rev ${res.revision}`;
                saveRevisionBtn.classList.remove('btn-outline-secondary');
                saveRevisionBtn.classList.add('btn-green');
                setTimeout(() => {
                    saveRevisionBtn.classList.remove('btn-green');
                    saveRevisionBtn.classList.add('btn-outline-secondary');
                }, 1500);
            } else {
                throw new Error(res.error?.message || "Failed to save revision");
            }
        } catch (err) {
            alert("Error saving lyrics: " + err.message);
        } finally {
            saveRevisionBtn.disabled = false;
            saveRevisionBtn.innerHTML = '<i class="bi bi-cloud-check"></i> Save Revision';
        }
    });

    // Export Video Button & Modal Handling
    exportVideoBtn.addEventListener('click', async () => {
        // Apply latest style first
        const styleConfig = applyCurrentStyle();
        const renderConfig = { aspect_ratio: renderAspectRatio.value, resolution: renderResolution ? renderResolution.value : '1080', lyrics_format: currentLyricsFormat };
        await LyricSyncAPI.updateStyle(projectId, styleConfig, renderConfig);

        // Reset modal state
        exportSpinner.classList.remove('d-none');
        exportErrorBox.classList.add('d-none');
        downloadFinalVideoBtn.classList.add('d-none');
        exportProgressBar.style.width = '20%';
        exportProgressPct.textContent = '20%';
        exportStageText.textContent = 'Queueing FFmpeg render job...';
        exportModal.show();

        try {
            const queueRes = await LyricSyncAPI.queueRender(projectId, {
                aspect_ratio: renderAspectRatio.value,
                resolution: renderResolution ? renderResolution.value : '1080',
                mode: styleMode.value,
                format: currentLyricsFormat,
            });

            if (!queueRes.success) throw new Error(queueRes.error?.message || "Failed to start render");

            const jobId = queueRes.job_id;

            // Listen to progress events
            const progressHandler = (e) => {
                const job = e.detail;
                exportProgressBar.style.width = `${job.progress}%`;
                exportProgressPct.textContent = `${job.progress}%`;
                if (job.stage) exportStageText.textContent = job.stage;
            };
            window.addEventListener('job-progress', progressHandler);

            const completedJob = await LyricSyncAPI.pollJob(jobId);
            window.removeEventListener('job-progress', progressHandler);

            // Completed!
            exportSpinner.classList.add('d-none');
            exportProgressBar.style.width = '100%';
            exportProgressPct.textContent = '100%';
            exportStageText.textContent = 'Video Render Complete!';

            const downloadUrl = `/api/projects/${projectId}/download`;
            downloadFinalVideoBtn.href = downloadUrl;
            downloadFinalVideoBtn.classList.remove('d-none');

            // Also show header download button
            downloadHeaderBtn.href = downloadUrl;
            downloadHeaderBtn.classList.remove('d-none');
            downloadHeaderBtn.classList.add('d-flex');

        } catch (err) {
            exportSpinner.classList.add('d-none');
            exportStageText.textContent = 'Rendering Failed';
            exportErrorBox.textContent = err.message;
            exportErrorBox.classList.remove('d-none');
        }
    });
});
