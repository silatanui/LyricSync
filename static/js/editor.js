/**
 * LyricSync Studio Editor Main Controller
 */
document.addEventListener('DOMContentLoaded', async () => {
    const workspace = document.querySelector('.editor-workspace');
    if (!workspace) return;

    const projectId = workspace.getAttribute('data-project-id');
    const isAdmin = workspace.getAttribute('data-is-admin') === 'true';

    const friendlyStage = (stage) => {
        if (isAdmin || !stage) return stage || '';
        if (stage.includes('Whisper') || stage.includes('OpenAI')) return 'Analyzing song vocals with AI...';
        if (stage.includes('ASS') || stage.includes('subtitles') || stage.includes('FFmpeg')) return 'Styling synchronized lyrics...';
        if (stage.includes('Encoding') || stage.includes('libass')) return 'Rendering lyric video...';
        return stage;
    };

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
    const exportSelectView = document.getElementById('exportSelectView');
    const exportProgressView = document.getElementById('exportProgressView');
    const startExportActionBtn = document.getElementById('startExportActionBtn');
    const exportQualityBadgeText = document.getElementById('exportQualityBadgeText');
    const exportTierLabel720 = document.getElementById('exportTierLabel720');
    const exportTierLabel1080 = document.getElementById('exportTierLabel1080');
    const exportStageText = document.getElementById('exportStageText');
    const exportProgressBar = document.getElementById('exportProgressBar');
    const exportProgressPct = document.getElementById('exportProgressPct');
    const exportSpinner = document.getElementById('exportSpinner');
    const exportErrorBox = document.getElementById('exportErrorBox');
    const downloadFinalVideoBtn = document.getElementById('downloadFinalVideoBtn');

    // Preview Quality Switcher Elements
    const previewQualityDropdown = document.getElementById('previewQualityDropdown');
    const previewQualityLabel = document.getElementById('previewQualityLabel');
    const previewQualityIcon = document.getElementById('previewQualityIcon');
    const qualityOpt720 = document.getElementById('qualityOpt720');
    const qualityOpt1080 = document.getElementById('qualityOpt1080');

    // Initialize Player & Timeline
    const initialTitle = editorProjectName ? editorProjectName.value : '';
    const player = new SynchronizedPlayer(videoEl, audioEl, overlayEl, { songTitle: initialTitle });
    const timeline = new LyricTimeline(document.getElementById('lyricLinesList'), player);


    // Wire Preview Quality Switcher
    function setPreviewQuality(quality) {
        player.setQuality(quality);
        if (quality === '720') {
            if (previewQualityLabel) previewQualityLabel.textContent = '720p Draft';
            if (previewQualityIcon) previewQualityIcon.className = 'bi bi-lightning-charge-fill text-warning';
            if (qualityOpt720) {
                qualityOpt720.classList.add('active');
                qualityOpt720.querySelector('.check-icon')?.classList.remove('d-none');
            }
            if (qualityOpt1080) {
                qualityOpt1080.classList.remove('active');
                qualityOpt1080.querySelector('.check-icon')?.classList.add('d-none');
            }
        } else {
            if (previewQualityLabel) previewQualityLabel.textContent = '1080p Studio';
            if (previewQualityIcon) previewQualityIcon.className = 'bi bi-stars text-primary';
            if (qualityOpt1080) {
                qualityOpt1080.classList.add('active');
                qualityOpt1080.querySelector('.check-icon')?.classList.remove('d-none');
            }
            if (qualityOpt720) {
                qualityOpt720.classList.remove('active');
                qualityOpt720.querySelector('.check-icon')?.classList.add('d-none');
            }
        }
    }
    if (qualityOpt720) qualityOpt720.addEventListener('click', () => setPreviewQuality('720'));
    if (qualityOpt1080) qualityOpt1080.addEventListener('click', () => setPreviewQuality('1080'));

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
                player.setSongTitle(res.project.name);
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
        if (s == null || isNaN(s)) return "00:00.00";
        const sec = Math.max(0, Number(s));
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

            // Set song title in player for intro typewriter effect
            const songTitle = canonical.project?.name || res.project?.name || editorProjectName?.value || 'Untitled Song';
            player.setSongTitle(songTitle);

            // Pre-seed total duration from canonical media metadata
            if (canonical.media?.audio_duration && canonical.media.audio_duration > 0) {
                const dur = Number(canonical.media.audio_duration);
                scrubber.max = dur;
                totalDurationDisplay.textContent = formatTime(dur);
            }

            // If a rendered video is already available, reveal header download button immediately
            if (res.has_render && downloadHeaderBtn) {
                downloadHeaderBtn.href = res.download_url || `/api/projects/${projectId}/download`;
                downloadHeaderBtn.classList.remove('d-none');
                downloadHeaderBtn.classList.add('d-flex');
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
        const pDur = player.duration;
        const vDur = (videoEl && !isNaN(videoEl.duration)) ? videoEl.duration : 0;
        const aDur = (audioEl && !isNaN(audioEl.duration)) ? audioEl.duration : 0;
        const dur = (pDur && !isNaN(pDur) && pDur > 0) ? pDur : Math.max(vDur, aDur);
        if (dur > 0 && !isNaN(dur)) {
            scrubber.max = dur;
            totalDurationDisplay.textContent = formatTime(dur);
        }
    };
    videoEl.addEventListener('loadedmetadata', updateDuration);
    audioEl.addEventListener('loadedmetadata', updateDuration);
    if ((audioEl && audioEl.readyState >= 1) || (videoEl && videoEl.readyState >= 1)) {
        updateDuration();
    }


    // Playback time tracking via player unified events
    const onTimeTick = (cur, dur) => {
        if (!scrubber.matches(':active')) {
            scrubber.value = cur;
        }
        currentTimeDisplay.textContent = formatTime(cur);
        if (dur && scrubber.max != dur) {
            scrubber.max = dur;
            totalDurationDisplay.textContent = formatTime(dur);
        }
    };

    window.addEventListener('player-timeupdate', (e) => {
        onTimeTick(e.detail?.currentTime ?? player.currentTime, e.detail?.duration ?? player.duration);
    });
    videoEl.addEventListener('timeupdate', () => {
        onTimeTick(videoEl.currentTime, videoEl.duration);
    });
    audioEl.addEventListener('timeupdate', () => {
        if (!player.hasVideo) {
            onTimeTick(audioEl.currentTime, audioEl.duration);
        }
    });

    // Play/Pause icon sync
    window.addEventListener('player-play', () => {
        playIcon.className = 'bi bi-pause-fill fs-4';
    });
    window.addEventListener('player-pause', () => {
        playIcon.className = 'bi bi-play-fill fs-4';
    });
    videoEl.addEventListener('play', () => {
        playIcon.className = 'bi bi-pause-fill fs-4';
    });
    videoEl.addEventListener('pause', () => {
        playIcon.className = 'bi bi-play-fill fs-4';
    });
    audioEl.addEventListener('play', () => {
        if (!player.hasVideo) playIcon.className = 'bi bi-pause-fill fs-4';
    });
    audioEl.addEventListener('pause', () => {
        if (!player.hasVideo) playIcon.className = 'bi bi-play-fill fs-4';
    });

    // Play/Pause toggle
    const togglePlayback = () => {
        player.togglePlay();
    };
    playPauseBtn.addEventListener('click', togglePlayback);

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
        player.seekTo(Math.max(0, player.currentTime - 5));
    });
    forward5Btn.addEventListener('click', () => {
        player.seekTo(player.currentTime + 5);
    });

    // Playback Speed
    speedSelect.addEventListener('change', (e) => {
        const rate = parseFloat(e.target.value);
        if (videoEl) videoEl.playbackRate = rate;
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
                    const curTime = player.currentTime;
                    const wasPlaying = player.isPlaying;
                    if (res.is_image !== false) {
                        player.setMediaMode({ hasVideo: false, imageSrc: res.video_url });
                    } else {
                        player.setMediaMode({ hasVideo: true, videoSrc: res.video_url });
                    }
                    player.seekTo(curTime);
                    if (wasPlaying) player.play();
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
                    const curTime = player.currentTime;
                    const wasPlaying = player.isPlaying;
                    if (res.is_image !== false) {
                        player.setMediaMode({ hasVideo: false, imageSrc: res.video_url });
                    } else {
                        player.setMediaMode({ hasVideo: true, videoSrc: res.video_url });
                    }
                    player.seekTo(curTime);
                    if (wasPlaying) {
                        player.play();
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
        player.renderActiveFrame(player.currentTime);
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
        
        let currentPct = 15;
        transcribeProgressBar.style.width = '15%';
        transcribeProgressPct.textContent = '15%';
        transcribeStageText.textContent = isAdmin ? 'Preparing audio for OpenAI Whisper-1...' : 'Listening to song vocals & timing...';
        transcribeModal.show();

        let ticker = null;
        const progressHandler = (e) => {
            const job = e.detail;
            if (job) {
                // Advance progress monotonically (never jump backward to 25%)
                if (typeof job.progress === 'number' && job.progress > currentPct) {
                    currentPct = job.progress;
                    transcribeProgressBar.style.width = `${currentPct}%`;
                    transcribeProgressPct.textContent = `${currentPct}%`;
                }
                if (job.stage) {
                    transcribeStageText.textContent = friendlyStage(job.stage);
                }
            }
        };

        try {
            const res = await LyricSyncAPI.triggerTranscription(projectId);
            if (!res.success) throw new Error(res.error?.message || "Failed to trigger transcription");

            window.addEventListener('job-progress', progressHandler);

        // Asymptotic progress ticker: drifts toward ~88% while Whisper API runs.
        // The bar always moves — users see progress even for 4-5 minute songs.
        // Rate slows exponentially as it approaches the ceiling so it never stalls.
        const TICKER_CEILING = 88;
        ticker = setInterval(() => {
            if (currentPct < TICKER_CEILING) {
                // Slowing exponential decay: starts fast, slows as it approaches ceiling
                const remaining = TICKER_CEILING - currentPct;
                const increment = Math.max(0.3, remaining * 0.04);
                currentPct = Math.min(TICKER_CEILING, currentPct + increment);
                transcribeProgressBar.style.width = `${Math.round(currentPct)}%`;
                transcribeProgressPct.textContent = `${Math.round(currentPct)}%`;

                if (currentPct >= 20 && currentPct < 38) {
                    transcribeStageText.textContent = isAdmin
                        ? 'Compressing audio with FFmpeg for fast transfer...'
                        : 'Preparing your song for analysis...';
                } else if (currentPct >= 38 && currentPct < 55) {
                    transcribeStageText.textContent = isAdmin
                        ? 'Uploading compressed audio to OpenAI Whisper API...'
                        : 'Sending audio to AI — this may take a minute...';
                } else if (currentPct >= 55 && currentPct < 70) {
                    transcribeStageText.textContent = isAdmin
                        ? 'Whisper-1 is decoding speech tokens and phonemes...'
                        : 'AI is listening to every word and beat...';
                } else if (currentPct >= 70 && currentPct < 80) {
                    transcribeStageText.textContent = isAdmin
                        ? 'Extracting word-level timestamps from Whisper response...'
                        : 'Identifying words and their exact timing...';
                } else if (currentPct >= 80) {
                    transcribeStageText.textContent = isAdmin
                        ? 'Finalising Whisper token alignment — almost done...'
                        : 'Wrapping up — this takes longer for full-length songs...';
                }
            }
        }, 700);

        await LyricSyncAPI.pollJob(res.job_id);

            if (ticker) clearInterval(ticker);
            window.removeEventListener('job-progress', progressHandler);

            // Jump to 95% — Whisper done, now loading lyrics from server
            currentPct = 95;
            transcribeProgressBar.style.width = '95%';
            transcribeProgressPct.textContent = '95%';
            transcribeStageText.textContent = isAdmin ? 'Loading aligned lyrics into studio...' : 'Almost there — loading your synced lyrics...';

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
            transcribeStageText.textContent = isAdmin ? 'Transcription Complete. Lyrics loaded into Studio.' : 'Done! Your lyrics are synced and ready to edit.';

            setTimeout(() => {
                transcribeModal.hide();
            }, 1200);
        } catch (err) {
            if (ticker) clearInterval(ticker);
            window.removeEventListener('job-progress', progressHandler);
            transcribeSpinner.classList.add('d-none');
            const isTimeout = err.message?.toLowerCase().includes('took longer') || err.message?.toLowerCase().includes('timeout');
            transcribeErrorBox.innerHTML = isTimeout
                ? `<strong>The transcription is taking longer than expected.</strong><br><span class="small">This usually happens with long songs or slow connections. Click Retry below — the server may have already finished processing.</span>`
                : (err.message || "An error occurred during transcription.");
            transcribeErrorBox.classList.remove('d-none');
            transcribeModalFooter.classList.remove('d-none');
        }
    });

    // Retry button: hide modal and re-trigger the transcription
    document.getElementById('transcribeRetryBtn')?.addEventListener('click', () => {
        transcribeModal.hide();
        setTimeout(() => transcribeBtn.click(), 300);
    });

    if (new URLSearchParams(window.location.search).get('auto_transcribe') === '1') {
        window.history.replaceState({}, document.title, window.location.pathname);
        setTimeout(() => transcribeBtn.click(), 250);
    }

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

    // Export Quality Tier Card Selection
    let selectedExportResolution = '720';

    if (exportTierLabel720) {
        exportTierLabel720.addEventListener('click', () => {
            selectedExportResolution = '720';
            exportTierLabel720.classList.add('bg-light');
            exportTierLabel1080.classList.remove('bg-light');
            const radio = exportTierLabel720.querySelector('input[type="radio"]');
            if (radio) radio.checked = true;
        });
    }

    if (exportTierLabel1080) {
        exportTierLabel1080.addEventListener('click', () => {
            selectedExportResolution = '1080';
            exportTierLabel1080.classList.add('bg-light');
            exportTierLabel720.classList.remove('bg-light');
            const radio = exportTierLabel1080.querySelector('input[type="radio"]');
            if (radio) radio.checked = true;
        });
    }

    // Open Export Modal in Quality Selection View
    exportVideoBtn.addEventListener('click', () => {
        if (exportSelectView) exportSelectView.classList.remove('d-none');
        if (exportProgressView) exportProgressView.classList.add('d-none');
        if (startExportActionBtn) startExportActionBtn.classList.remove('d-none');
        if (downloadHeaderBtn && !downloadHeaderBtn.classList.contains('d-none') && downloadFinalVideoBtn) {
            downloadFinalVideoBtn.href = downloadHeaderBtn.href;
            downloadFinalVideoBtn.classList.remove('d-none');
        } else if (downloadFinalVideoBtn) {
            downloadFinalVideoBtn.classList.add('d-none');
        }
        if (exportErrorBox) exportErrorBox.classList.add('d-none');
        exportModal.show();
    });


    // Execute Export Render upon clicking Start Render button
    if (startExportActionBtn) {
        startExportActionBtn.addEventListener('click', async () => {
            const chosenRes = document.querySelector('input[name="exportResolutionTier"]:checked')?.value || selectedExportResolution || '720';

            // Transition to progress view
            if (exportSelectView) exportSelectView.classList.add('d-none');
            if (exportProgressView) exportProgressView.classList.remove('d-none');
            if (startExportActionBtn) startExportActionBtn.classList.add('d-none');
            if (exportSpinner) exportSpinner.classList.remove('d-none');
            if (exportErrorBox) exportErrorBox.classList.add('d-none');
            if (exportQualityBadgeText) {
                exportQualityBadgeText.textContent = chosenRes === '720' 
                    ? (isAdmin ? '720p Fast Draft MP4' : '720p Fast Draft Video') 
                    : (isAdmin ? '1080p Studio Master MP4' : '1080p Full HD Video');
            }

            exportProgressBar.style.width = '15%';
            exportProgressPct.textContent = '15%';
            exportStageText.textContent = isAdmin ? 'Queueing FFmpeg render job...' : 'Preparing high quality lyric video...';

            try {
                // Apply latest style first
                const styleConfig = applyCurrentStyle();
                const renderConfig = {
                    aspect_ratio: renderAspectRatio.value,
                    resolution: chosenRes,
                    lyrics_format: currentLyricsFormat
                };
                await LyricSyncAPI.updateStyle(projectId, styleConfig, renderConfig);

                const queueRes = await LyricSyncAPI.queueRender(projectId, {
                    aspect_ratio: renderAspectRatio.value,
                    resolution: chosenRes,
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
                    if (job.stage) exportStageText.textContent = friendlyStage(job.stage);
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
                if (exportSpinner) exportSpinner.classList.add('d-none');
                exportStageText.textContent = 'Rendering Failed';
                exportErrorBox.textContent = err.message;
                exportErrorBox.classList.remove('d-none');
                if (startExportActionBtn) startExportActionBtn.classList.remove('d-none');
            }
        });
    }
});
