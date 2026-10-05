/**
 * LyricSync Studio Editor Main Controller
 */
document.addEventListener('DOMContentLoaded', async () => {
    const workspace = document.querySelector('.editor-workspace');
    if (!workspace) return;

    const projectId = workspace.getAttribute('data-project-id');
    const isAdmin = workspace.getAttribute('data-is-admin') === 'true';
    let activeStream = null;
    let resumeWhenStreamAdvances = false;
    let streamCursor = -1;

    const friendlyStage = (stage) => {
        if (!stage) return '';
        if (stage.includes('already known') || stage.includes('Known lyrics') || stage.includes('Found ')) return stage;
        if (stage.includes('catalog') || stage.includes('identify the song') || stage.includes('Matching opening')) return stage;
        if (isAdmin) return stage;
        if (stage.includes('·') || stage.includes('preview') || stage.includes('Sync') || stage.includes('Detect')) return stage;
        if (stage.includes('Whisper') || stage.includes('OpenAI')) return 'Analyzing song vocals with AI...';
        if (stage.includes('ASS') || stage.includes('subtitles') || stage.includes('FFmpeg')) return 'Styling synchronized lyrics...';
        if (stage.includes('Encoding') || stage.includes('libass')) return 'Rendering lyric video...';
        return stage;
    };

    const videoEl = document.getElementById('mainVideo');
    const audioEl = document.getElementById('mainAudio');
    const overlayEl = document.getElementById('lyricOverlay');
    const videoContainer = document.getElementById('videoContainer');
    const mainBgImage = document.getElementById('mainBgImage');

    // Restore theme media after reload (never leave an empty broken <img>).
    function ensureBackgroundMedia() {
        if (!videoContainer) return;
        const hasVideo = videoContainer.getAttribute('data-has-video') === 'true';
        const streamUrl = videoContainer.getAttribute('data-bg-stream') || '';
        const posterUrl = videoContainer.getAttribute('data-bg-poster') || '';
        if (mainBgImage) {
            const src = mainBgImage.getAttribute('src') || '';
            if (!src && posterUrl) mainBgImage.src = posterUrl;
            else if (!src && streamUrl && !hasVideo) mainBgImage.src = streamUrl;
        }
        if (hasVideo && videoEl) {
            const current = videoEl.currentSrc || videoEl.getAttribute('src') || '';
            if (!current && streamUrl) {
                videoEl.src = streamUrl;
                videoEl.load();
            }
            videoEl.classList.remove('d-none');
            if (mainBgImage) mainBgImage.classList.add('d-none');
        } else if (mainBgImage) {
            mainBgImage.classList.remove('d-none');
            if (videoEl) videoEl.classList.add('d-none');
        }
    }
    ensureBackgroundMedia();

    // UI Elements
    const playPauseBtn = document.getElementById('playPauseBtn');
    const playIcon = document.getElementById('playIcon');
    const scrubber = document.getElementById('playbackScrubber');
    const currentTimeDisplay = document.getElementById('currentTimeDisplay');
    const totalDurationDisplay = document.getElementById('totalDurationDisplay');
    // Song length for the scrubber — never the short looping theme-bed duration.
    let masterDurationSec = 0;
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
    const styleTextCase = document.getElementById('styleTextCase');
    const styleEffect = document.getElementById('styleEffect');
    const renderResolution = document.getElementById('renderResolution');
    const audioVolume = document.getElementById('audioVolume');
    const audioVolumeDisplay = document.getElementById('audioVolumeDisplay');
    const stylePrimaryColor = document.getElementById('stylePrimaryColor');
    const styleHighlightColor = document.getElementById('styleHighlightColor');
    const styleMode = document.getElementById('styleMode');
    const styleFormat = document.getElementById('styleFormat');
    const renderAspectRatio = document.getElementById('renderAspectRatio');

    // Text effect controls (outline / drop shadow / bevel)
    const styleOutlineEnabled = document.getElementById('styleOutlineEnabled');
    const styleOutlineColor = document.getElementById('styleOutlineColor');
    const styleOutlineSize = document.getElementById('styleOutlineSize');
    const styleOutlineSoftness = document.getElementById('styleOutlineSoftness');
    const styleShadowEnabled = document.getElementById('styleShadowEnabled');
    const styleShadowColor = document.getElementById('styleShadowColor');
    const styleShadowOpacity = document.getElementById('styleShadowOpacity');
    const styleShadowDistance = document.getElementById('styleShadowDistance');
    const styleShadowBlur = document.getElementById('styleShadowBlur');
    const styleShadowAngle = document.getElementById('styleShadowAngle');
    const styleBevelEnabled = document.getElementById('styleBevelEnabled');
    const styleBevelSize = document.getElementById('styleBevelSize');
    const styleBevelSoftness = document.getElementById('styleBevelSoftness');
    const styleBevelAngle = document.getElementById('styleBevelAngle');
    const styleBevelHighlightColor = document.getElementById('styleBevelHighlightColor');
    const styleBevelHighlightOpacity = document.getElementById('styleBevelHighlightOpacity');
    const styleBevelShadowColor = document.getElementById('styleBevelShadowColor');
    const styleBevelShadowOpacity = document.getElementById('styleBevelShadowOpacity');
    const shadowDirPad = document.getElementById('shadowDirPad');

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
    const themeApplyStatus = document.getElementById('themeApplyStatus');
    const drawerTemplatesList = document.getElementById('drawerTemplatesList');
    const themeMoodChips = document.getElementById('themeMoodChips');
    const themeSearchInput = document.getElementById('themeSearchInput');
    const themeCountLabel = document.getElementById('themeCountLabel');
    let selectedBackgroundTemplate = 'burgundy_studio';
    let allThemes = [];
    let activeMood = 'all';
    let activeMediaFilter = 'all';
    let themeSearchQuery = '';

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

    // Export modal (quality pick) + background progress dock
    const exportModalEl = document.getElementById('exportModal');
    const exportModal = new bootstrap.Modal(exportModalEl);
    const exportSelectView = document.getElementById('exportSelectView');
    const startExportActionBtn = document.getElementById('startExportActionBtn');
    const exportQualityBadgeText = document.getElementById('exportQualityBadgeText');
    const exportTierLabel720 = document.getElementById('exportTierLabel720');
    const exportTierLabel1080 = document.getElementById('exportTierLabel1080');
    const exportStageText = document.getElementById('exportStageText');
    const exportSubText = document.getElementById('exportSubText');
    const exportProgressBar = document.getElementById('exportProgressBar');
    const exportProgressPct = document.getElementById('exportProgressPct');
    const exportSpinner = document.getElementById('exportSpinner');
    const exportErrorBox = document.getElementById('exportErrorBox');
    const downloadFinalVideoBtn = document.getElementById('downloadFinalVideoBtn');
    const exportJobDock = document.getElementById('exportJobDock');
    const exportDockCard = document.getElementById('exportDockCard');
    const exportDockCollapsed = document.getElementById('exportDockCollapsed');
    const exportDockPillText = document.getElementById('exportDockPillText');
    const exportDockPillPct = document.getElementById('exportDockPillPct');
    const minimizeExportDockBtn = document.getElementById('minimizeExportDockBtn');
    const dismissExportDockBtn = document.getElementById('dismissExportDockBtn');
    const hideExportDockBtn = document.getElementById('hideExportDockBtn');
    let exportInProgress = false;
    let exportIdleLabel = exportBtnLabel ? exportBtnLabel.textContent : 'Export';

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
        const duration = masterDurationSec || audioEl.duration || player.duration || 1;
        (lines || []).forEach((line, index) => {
            const segment = document.createElement('button');
            const confidence = Number(line.confidence ?? 0.9);
            segment.type = 'button';
            segment.className = `confidence-segment ${confidence >= 0.8 ? 'high' : confidence >= 0.5 ? 'edited' : 'low'}`;
            segment.style.left = `${Math.max(0, line.start / duration) * 100}%`;
            segment.style.width = `${Math.max(0.6, (line.end - line.start) / duration * 100)}%`;
            segment.title = `Line ${index + 1}: ${Math.round(confidence * 100)}% confidence. Click to seek.`;
            segment.addEventListener('click', () => seekWithinStream(line.start));
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
        fontPickerLabel.style.fontFamily = (window.LyricSyncFonts && typeof window.LyricSyncFonts.resolve === 'function')
            ? window.LyricSyncFonts.resolve(fontName)
            : `"${fontName}", sans-serif`;

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

                const fontSizeVal = s.font_size || 36;
                if (styleFontSize) styleFontSize.value = fontSizeVal;
                if (fontSizeDisplay) fontSizeDisplay.textContent = `${fontSizeVal}px`;

                const lineHeightVal = s.line_height !== undefined ? s.line_height : 0.9;
                if (styleLineHeight) styleLineHeight.value = lineHeightVal;
                if (lineHeightDisplay) lineHeightDisplay.textContent = `${lineHeightVal}x`;

                if (s.primary_color && stylePrimaryColor) stylePrimaryColor.value = s.primary_color;
                if (s.highlight_color && styleHighlightColor) styleHighlightColor.value = s.highlight_color;
                if (s.mode && styleMode) {
                    // Keep legacy classic/karaoke; accept new tracking modes.
                    styleMode.value = s.mode;
                }
                if (s.letter_spacing !== undefined && styleLetterSpacing) styleLetterSpacing.value = s.letter_spacing;
                if (s.font_weight && styleFontWeight) styleFontWeight.value = s.font_weight;
                if (s.effect && styleEffect) styleEffect.value = s.effect;
                if (s.effect_strength != null) {
                    const strengthEl = document.getElementById('styleEffectStrength');
                    if (strengthEl) strengthEl.value = s.effect_strength;
                }
                if (s.font_style && styleFontStyle) styleFontStyle.value = s.font_style;
                if (s.text_case && styleTextCase) styleTextCase.value = s.text_case;
                applyTextEffectsFromCanonical(s);
                // Card UI sync runs after helpers are initialized (see syncEffectCards below).
                window.__pendingLyricEffect = s.effect || 'none';
                window.__pendingEffectStrength = s.effect_strength;

                const posVal = s.position || 'center';
                const rPos = document.querySelector(`input[name="positionRadio"][value="${posVal}"]`);
                if (rPos) rPos.checked = true;

                const alignVal = s.text_align || 'center';
                const rAlign = document.querySelector(`input[name="alignRadio"][value="${alignVal}"]`);
                if (rAlign) rAlign.checked = true;

                player.setStyle({
                    font: fontVal,
                    fontSize: fontSizeVal,
                    lineHeight: lineHeightVal,
                    fontWeight: s.font_weight || 600,
                    fontStyle: s.font_style || 'normal',
                    textCase: s.text_case || 'as_is',
                    letterSpacing: s.letter_spacing || 0,
                    effect: s.effect || 'none',
                    effectStrength: s.effect_strength,
                    primaryColor: s.primary_color || '#FFFFFF',
                    highlightColor: s.highlight_color || '#10B981',
                    mode: s.mode || 'karaoke',
                    format: s.format || currentLyricsFormat,
                    position: posVal,
                    textAlign: alignVal,
                    ...collectTextEffectStyleCamel(),
                });
            }

            // Load lyrics into timeline, player, and right sidebar lyrics sheet
            applyStreamLyrics(canonical.lyrics || [], canonical.transcription || null);
            const preferredLanguage = canonical.meta?.preferred_language;
            const languageSelect = document.getElementById('transcribeLanguage');
            if (languageSelect) {
                const saved = preferredLanguage || localStorage.getItem('lyricsync_language') || 'auto';
                if ([...languageSelect.options].some((opt) => opt.value === saved)) {
                    languageSelect.value = saved;
                }
                languageSelect.addEventListener('change', () => {
                    localStorage.setItem('lyricsync_language', languageSelect.value);
                });
            }
            if (canonical.transcription?.partial || res.project?.status === 'transcribing') {
                watchPartialLyrics();
                if (canonical.transcription?.partial) setStreamBanner('playing');
            }

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

            // Pre-seed total duration from canonical media metadata (never theme-bed length)
            if (canonical.media?.audio_duration && canonical.media.audio_duration > 0) {
                const dur = Number(canonical.media.audio_duration);
                masterDurationSec = dur;
                scrubber.max = dur;
                totalDurationDisplay.textContent = formatTime(dur);
                if (player && typeof player.setFallbackDuration === 'function') {
                    player.setFallbackDuration(dur);
                }
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

    const resolveMasterDuration = () => {
        const aDur = (audioEl && !isNaN(audioEl.duration) && audioEl.duration > 0) ? audioEl.duration : 0;
        const next = Math.max(masterDurationSec || 0, aDur || 0);
        if (next > 0 && Math.abs(next - (masterDurationSec || 0)) > 0.01) {
            masterDurationSec = next;
            scrubber.max = next;
            totalDurationDisplay.textContent = formatTime(next);
            if (player && typeof player.setFallbackDuration === 'function') {
                player.setFallbackDuration(next);
            }
        }
        return masterDurationSec;
    };

    audioEl.addEventListener('loadedmetadata', resolveMasterDuration);
    audioEl.addEventListener('durationchange', resolveMasterDuration);
    if (audioEl && audioEl.readyState >= 1) {
        resolveMasterDuration();
    }

    // Playback time tracking — audio / player clock only (theme video is wallpaper).
    const onTimeTick = (cur, dur) => {
        const master = resolveMasterDuration();
        let safeDur = master > 0 ? master : (dur > 0 ? dur : 0);
        // Ignore wallpaper/theme-bed durations (e.g. 5–8s visualizer loops).
        if (dur > 0 && master > 0 && dur < master * 0.5) {
            safeDur = master;
        }

        const frontier = streamFrontierSeconds();
        if (frontier != null && cur >= frontier - 0.08) {
            if (!player.isPaused) {
                resumeWhenStreamAdvances = true;
                player.pause();
            }
            setStreamBanner('waiting');
            cur = Math.min(cur, Math.max(0, frontier - 0.05));
        }
        if (safeDur > 0) {
            cur = Math.max(0, Math.min(cur, safeDur));
        }
        if (!scrubber.matches(':active')) {
            scrubber.value = cur;
        }
        currentTimeDisplay.textContent = formatTime(cur);
        if (safeDur > 0 && Math.abs(Number(scrubber.max) - safeDur) > 0.01) {
            scrubber.max = safeDur;
            totalDurationDisplay.textContent = formatTime(safeDur);
        }
    };

    window.addEventListener('player-timeupdate', (e) => {
        onTimeTick(e.detail?.currentTime ?? player.currentTime, resolveMasterDuration());
    });
    audioEl.addEventListener('timeupdate', () => {
        onTimeTick(audioEl.currentTime, resolveMasterDuration());
    });

    // Play/Pause icon sync (ignore theme-video play/pause/loop events)
    window.addEventListener('player-play', () => {
        playIcon.className = 'bi bi-pause-fill fs-4';
    });
    window.addEventListener('player-pause', () => {
        playIcon.className = 'bi bi-play-fill fs-4';
    });
    audioEl.addEventListener('play', () => {
        playIcon.className = 'bi bi-pause-fill fs-4';
    });
    audioEl.addEventListener('pause', () => {
        playIcon.className = 'bi bi-play-fill fs-4';
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
        const landed = seekWithinStream(parseFloat(e.target.value));
        scrubber.value = landed;
    });

    // Replay / Forward 5s
    replay5Btn.addEventListener('click', () => {
        player.seekTo(Math.max(0, player.currentTime - 5));
    });
    forward5Btn.addEventListener('click', () => {
        seekWithinStream(player.currentTime + 5);
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

    function numOr(el, fallback) {
        if (!el) return fallback;
        const n = parseFloat(el.value);
        return Number.isFinite(n) ? n : fallback;
    }

    function syncEffectControlState() {
        const outlineOn = !styleOutlineEnabled || styleOutlineEnabled.checked;
        const shadowOn = !styleShadowEnabled || styleShadowEnabled.checked;
        const bevelOn = styleBevelEnabled && styleBevelEnabled.checked;
        document.getElementById('outlineControls')?.closest('.typo-effect-group')?.classList.toggle('is-disabled', !outlineOn);
        document.getElementById('shadowControls')?.closest('.typo-effect-group')?.classList.toggle('is-disabled', !shadowOn);
        document.getElementById('bevelControls')?.closest('.typo-effect-group')?.classList.toggle('is-disabled', !bevelOn);

        const setTxt = (id, text) => { const el = document.getElementById(id); if (el) el.textContent = text; };
        setTxt('outlineSizeDisplay', `${numOr(styleOutlineSize, 2)}px`);
        setTxt('outlineSoftnessDisplay', `${numOr(styleOutlineSoftness, 0)}px`);
        setTxt('shadowOpacityDisplay', `${Math.round(numOr(styleShadowOpacity, 70))}%`);
        setTxt('shadowDistanceDisplay', `${numOr(styleShadowDistance, 3)}px`);
        setTxt('shadowBlurDisplay', `${numOr(styleShadowBlur, 2)}px`);
        setTxt('shadowAngleDisplay', `${Math.round(numOr(styleShadowAngle, 45))}°`);
        setTxt('bevelSizeDisplay', `${numOr(styleBevelSize, 2)}px`);
        setTxt('bevelSoftnessDisplay', `${numOr(styleBevelSoftness, 1)}px`);
        setTxt('bevelAngleDisplay', `${Math.round(numOr(styleBevelAngle, 135))}°`);
        setTxt('bevelHighlightOpacityDisplay', `${Math.round(numOr(styleBevelHighlightOpacity, 55))}%`);
        setTxt('bevelShadowOpacityDisplay', `${Math.round(numOr(styleBevelShadowOpacity, 45))}%`);

        document.querySelectorAll('.style-color-hex').forEach((span) => {
            const input = document.getElementById(span.dataset.for);
            if (input) span.textContent = (input.value || '').toUpperCase();
        });

        if (shadowDirPad && styleShadowAngle) {
            const angle = Math.round(numOr(styleShadowAngle, 45));
            shadowDirPad.querySelectorAll('.typo-dir-btn').forEach((btn) => {
                btn.classList.toggle('is-active', Number(btn.dataset.angle) === angle);
            });
        }
    }

    function collectTextEffectStyleCamel() {
        return {
            outlineEnabled: styleOutlineEnabled ? styleOutlineEnabled.checked : true,
            outline: numOr(styleOutlineSize, 2),
            outlineColor: styleOutlineColor ? styleOutlineColor.value : '#000000',
            outlineSoftness: numOr(styleOutlineSoftness, 0),
            shadowEnabled: styleShadowEnabled ? styleShadowEnabled.checked : true,
            shadow: numOr(styleShadowDistance, 3),
            shadowColor: styleShadowColor ? styleShadowColor.value : '#000000',
            shadowOpacity: numOr(styleShadowOpacity, 70),
            shadowAngle: numOr(styleShadowAngle, 45),
            shadowBlur: numOr(styleShadowBlur, 2),
            bevelEnabled: styleBevelEnabled ? styleBevelEnabled.checked : false,
            bevelSize: numOr(styleBevelSize, 2),
            bevelSoftness: numOr(styleBevelSoftness, 1),
            bevelAngle: numOr(styleBevelAngle, 135),
            bevelHighlightColor: styleBevelHighlightColor ? styleBevelHighlightColor.value : '#FFFFFF',
            bevelHighlightOpacity: numOr(styleBevelHighlightOpacity, 55),
            bevelShadowColor: styleBevelShadowColor ? styleBevelShadowColor.value : '#000000',
            bevelShadowOpacity: numOr(styleBevelShadowOpacity, 45),
        };
    }

    function collectTextEffectStyleSnake() {
        const c = collectTextEffectStyleCamel();
        return {
            outline_enabled: c.outlineEnabled,
            outline: c.outline,
            outline_color: c.outlineColor,
            outline_softness: c.outlineSoftness,
            shadow_enabled: c.shadowEnabled,
            shadow: c.shadow,
            shadow_color: c.shadowColor,
            shadow_opacity: c.shadowOpacity,
            shadow_angle: c.shadowAngle,
            shadow_blur: c.shadowBlur,
            bevel_enabled: c.bevelEnabled,
            bevel_size: c.bevelSize,
            bevel_softness: c.bevelSoftness,
            bevel_angle: c.bevelAngle,
            bevel_highlight_color: c.bevelHighlightColor,
            bevel_highlight_opacity: c.bevelHighlightOpacity,
            bevel_shadow_color: c.bevelShadowColor,
            bevel_shadow_opacity: c.bevelShadowOpacity,
        };
    }

    function applyTextEffectsFromCanonical(s = {}) {
        const setCheck = (el, val, fallback = true) => {
            if (!el) return;
            el.checked = val === undefined || val === null ? fallback : !!val;
        };
        const setVal = (el, val, fallback) => {
            if (!el) return;
            el.value = val !== undefined && val !== null ? val : fallback;
        };

        setCheck(styleOutlineEnabled, s.outline_enabled, true);
        setVal(styleOutlineColor, s.outline_color, '#000000');
        setVal(styleOutlineSize, s.outline, 2);
        setVal(styleOutlineSoftness, s.outline_softness, 0);

        setCheck(styleShadowEnabled, s.shadow_enabled, true);
        setVal(styleShadowColor, s.shadow_color, '#000000');
        setVal(styleShadowOpacity, s.shadow_opacity, 70);
        // Prefer new distance key; fall back to legacy ASS `shadow` size
        setVal(styleShadowDistance, s.shadow_distance ?? s.shadow, 3);
        setVal(styleShadowBlur, s.shadow_blur, 2);
        setVal(styleShadowAngle, s.shadow_angle, 45);

        setCheck(styleBevelEnabled, s.bevel_enabled, false);
        setVal(styleBevelSize, s.bevel_size, 2);
        setVal(styleBevelSoftness, s.bevel_softness, 1);
        setVal(styleBevelAngle, s.bevel_angle, 135);
        setVal(styleBevelHighlightColor, s.bevel_highlight_color, '#FFFFFF');
        setVal(styleBevelHighlightOpacity, s.bevel_highlight_opacity, 55);
        setVal(styleBevelShadowColor, s.bevel_shadow_color, '#000000');
        setVal(styleBevelShadowOpacity, s.bevel_shadow_opacity, 45);
        syncEffectControlState();
    }

    function applyCurrentStyle() {
        const alignVal = getSelectedAlignment();
        const posVal = getSelectedPosition();
        const fontVal = styleFontFamily ? styleFontFamily.value : 'Caveat';
        const fontSizeVal = styleFontSize ? parseInt(styleFontSize.value) : 36;
        const lineHeightVal = styleLineHeight ? parseFloat(styleLineHeight.value) : 0.9;
        syncEffectControlState();

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
            effectStrength: styleEffectStrength ? parseFloat(styleEffectStrength.value) : 0.7,
            fontStyle: styleFontStyle ? styleFontStyle.value : 'normal',
            textCase: styleTextCase ? styleTextCase.value : 'as_is',
            ...collectTextEffectStyleCamel(),
        };
        player.setStyle(styleConfig);
        if (styleEffectStrength) applyEffectStrength(styleEffectStrength.value);
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

    function buildStylePayloadForSave() {
        // Canonical snake_case payload used by export / autosave / API.
        // Preview uses camelCase via applyCurrentStyle(); never send that to the server.
        syncEffectControlState();
        return {
            format: currentLyricsFormat,
            font: styleFontFamily ? styleFontFamily.value : 'Caveat',
            font_size: styleFontSize ? parseInt(styleFontSize.value) : 36,
            line_height: styleLineHeight ? parseFloat(styleLineHeight.value) : 0.9,
            letter_spacing: styleLetterSpacing ? parseFloat(styleLetterSpacing.value) : 0,
            font_weight: styleFontWeight ? parseInt(styleFontWeight.value) : 600,
            effect: styleEffect ? styleEffect.value : 'none',
            effect_strength: styleEffectStrength ? parseFloat(styleEffectStrength.value) : 0.7,
            font_style: styleFontStyle ? styleFontStyle.value : 'normal',
            text_case: styleTextCase ? styleTextCase.value : 'as_is',
            primary_color: stylePrimaryColor ? stylePrimaryColor.value : '#FFFFFF',
            highlight_color: styleHighlightColor ? styleHighlightColor.value : '#10B981',
            position: getSelectedPosition(),
            text_align: getSelectedAlignment(),
            mode: styleMode ? styleMode.value : 'karaoke',
            ...collectTextEffectStyleSnake(),
        };
    }

    let autoSaveTimer = null;
    function scheduleAutoSaveStyle() {
        if (autoSaveTimer) clearTimeout(autoSaveTimer);
        autoSaveTimer = setTimeout(async () => {
            try {
                const styleConfig = buildStylePayloadForSave();
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

    const textEffectInputs = [
        styleOutlineEnabled, styleOutlineColor, styleOutlineSize, styleOutlineSoftness,
        styleShadowEnabled, styleShadowColor, styleShadowOpacity, styleShadowDistance,
        styleShadowBlur, styleShadowAngle,
        styleBevelEnabled, styleBevelSize, styleBevelSoftness, styleBevelAngle,
        styleBevelHighlightColor, styleBevelHighlightOpacity, styleBevelShadowColor, styleBevelShadowOpacity,
    ];
    textEffectInputs.forEach((el) => {
        if (!el) return;
        const evt = el.type === 'checkbox' ? 'change' : 'input';
        el.addEventListener(evt, () => applyCurrentStyle());
    });
    shadowDirPad?.querySelectorAll('.typo-dir-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            if (!styleShadowAngle) return;
            styleShadowAngle.value = btn.dataset.angle || '45';
            applyCurrentStyle();
        });
    });
    syncEffectControlState();
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
    const effectCardGrid = document.getElementById('effectCardGrid');
    const styleEffectStrength = document.getElementById('styleEffectStrength');
    const effectStrengthDisplay = document.getElementById('effectStrengthDisplay');

    function syncEffectCards(effect) {
        const value = effect || 'none';
        const grid = document.getElementById('effectCardGrid');
        if (styleEffect && styleEffect.value !== value) styleEffect.value = value;
        if (!grid) return;
        grid.querySelectorAll('.effect-card').forEach((card) => {
            const active = card.dataset.effect === value;
            card.classList.toggle('active', active);
            card.setAttribute('aria-selected', active ? 'true' : 'false');
            if (active) {
                const preview = card.querySelector('.effect-preview-text');
                if (preview && value !== 'none') {
                    preview.style.animation = 'none';
                    void preview.offsetWidth;
                    preview.style.animation = '';
                }
            }
        });
    }

    function applyEffectStrength(strength) {
        const value = Math.max(0.2, Math.min(1.5, Number(strength) || 0.7));
        const activeTextEl = document.getElementById('displayActiveText');
        const grid = document.getElementById('effectCardGrid');
        const strengthLabel = document.getElementById('effectStrengthDisplay');
        if (videoContainer) videoContainer.style.setProperty('--lyric-effect-strength', String(value));
        if (activeTextEl) activeTextEl.style.setProperty('--lyric-effect-strength', String(value));
        if (grid) grid.style.setProperty('--lyric-effect-strength', String(value));
        if (strengthLabel) strengthLabel.textContent = `${Math.round(value * 100)}%`;
        if (player?.style) {
            player.style.effectStrength = value;
            player.renderActiveFrame(player.currentTime);
        }
    }

    syncEffectCards(window.__pendingLyricEffect || (styleEffect ? styleEffect.value : 'none'));
    if (window.__pendingEffectStrength != null && styleEffectStrength) {
        styleEffectStrength.value = window.__pendingEffectStrength;
    }
    applyEffectStrength(styleEffectStrength ? styleEffectStrength.value : 0.7);
    delete window.__pendingLyricEffect;
    delete window.__pendingEffectStrength;

    if (effectCardGrid) {
        effectCardGrid.querySelectorAll('.effect-card').forEach((card) => {
            card.addEventListener('click', () => {
                const effect = card.dataset.effect || 'none';
                syncEffectCards(effect);
                applyCurrentStyle();
                applyEffectToAllLines(effect);
            });
        });
    }

    if (styleEffect) styleEffect.addEventListener('change', () => {
        syncEffectCards(styleEffect.value);
        applyCurrentStyle();
        applyEffectToAllLines(styleEffect.value);
    });

    if (styleEffectStrength) {
        styleEffectStrength.addEventListener('input', (e) => {
            applyEffectStrength(e.target.value);
        });
    }

    if (styleFontStyle) styleFontStyle.addEventListener('change', () => applyCurrentStyle());
    if (styleTextCase) styleTextCase.addEventListener('change', () => applyCurrentStyle());

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
        exportIdleLabel = `Export ${aspect} Video`;
        if (exportBtnLabel && !exportInProgress) exportBtnLabel.textContent = exportIdleLabel;

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
                const styleConfig = buildStylePayloadForSave();
                await LyricSyncAPI.updateStyle(projectId, styleConfig, { aspect_ratio: aspect });
                const res = await LyricSyncAPI.updateBackgroundTemplate(projectId, selectedBackgroundTemplate, aspect);
                if (res.success && res.video_url) {
                    await applyBackgroundResponse(res);
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
        document.querySelectorAll('.template-visual-card').forEach((card) => {
            card.classList.toggle('active', card.getAttribute('data-template-id') === templateId);
        });
    }

    function themeMatchesFilters(theme) {
        if (activeMood !== 'all' && !(theme.moods || []).includes(activeMood)) return false;
        if (activeMediaFilter === 'video' && !theme.is_video) return false;
        if (activeMediaFilter === 'image' && theme.is_video) return false;
        if (themeSearchQuery) {
            const hay = `${theme.name} ${theme.tagline} ${(theme.moods || []).join(' ')}`.toLowerCase();
            if (!hay.includes(themeSearchQuery)) return false;
        }
        return true;
    }

    function renderThemeMoodChips(moods) {
        if (!themeMoodChips) return;
        themeMoodChips.innerHTML = '';
        (moods || ['all']).forEach((mood) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = `theme-mood-chip${mood === activeMood ? ' active' : ''}`;
            btn.dataset.mood = mood;
            btn.textContent = mood === 'all' ? 'All moods' : mood;
            btn.addEventListener('click', () => {
                activeMood = mood;
                themeMoodChips.querySelectorAll('.theme-mood-chip').forEach((el) => {
                    el.classList.toggle('active', el.dataset.mood === mood);
                });
                renderThemeGrid();
            });
            themeMoodChips.appendChild(btn);
        });
    }

    function renderThemeGrid() {
        if (!drawerTemplatesList) return;
        const filtered = allThemes
            .filter(themeMatchesFilters)
            .sort((a, b) => Number(!!b.is_ai) - Number(!!a.is_ai));
        if (themeCountLabel) {
            themeCountLabel.textContent = `${filtered.length} theme${filtered.length === 1 ? '' : 's'}`
                + (activeMood !== 'all' ? ` · ${activeMood}` : '')
                + (activeMediaFilter !== 'all' ? ` · ${activeMediaFilter}` : '');
        }
        drawerTemplatesList.innerHTML = '';
        if (!filtered.length) {
            drawerTemplatesList.innerHTML = `<div class="col-12 text-secondary small py-3">No themes match that mood/search.</div>`;
            return;
        }
        filtered.forEach((theme) => {
            const col = document.createElement('div');
            col.className = 'col-6';
            const color = theme.preview_color || '#334155';
            const thumb = theme.thumbnail || `/api/projects/templates/preview/${theme.id}`;
            col.innerHTML = `
                <div class="template-visual-card p-1${theme.id === selectedBackgroundTemplate ? ' active' : ''}" data-template-id="${theme.id}">
                    <div class="template-thumb-box position-relative" style="background:${color};">
                        <img src="${thumb}" alt="${theme.name}" loading="lazy"
                             onerror="this.style.opacity=0">
                        ${theme.is_ai ? '<span class="theme-video-badge theme-ai-badge">AI</span>'
                            : theme.is_visualizer ? '<span class="theme-video-badge theme-viz-badge">Visualizer</span>'
                            : theme.is_video ? '<span class="theme-video-badge">Video</span>'
                            : theme.is_photo ? '<span class="theme-video-badge theme-photo-badge">Photo</span>' : ''}
                    </div>
                    <div class="p-1 text-center">
                        <div class="fw-bold small text-dark text-truncate" style="font-size: 0.74rem;">${theme.name}</div>
                        <div class="text-secondary text-truncate" style="font-size: 0.62rem;">${theme.is_ai ? 'From your lyrics' : (theme.moods || []).slice(0, 2).join(' · ')}</div>
                    </div>
                </div>`;
            const card = col.querySelector('.template-visual-card');
            card.addEventListener('click', () => applyThemeCard(card, theme.id));
            drawerTemplatesList.appendChild(col);
        });
    }

    async function applyBackgroundResponse(res) {
        const keepTime = (player.audio && !isNaN(player.audio.currentTime))
            ? player.audio.currentTime
            : player.currentTime;
        const wasPlaying = player.isPlaying;
        const isVideoBg = res.media_type === 'video' || res.is_image === false;
        const posterUrl = videoContainer?.getAttribute('data-bg-poster')
            || `/api/projects/templates/preview/${res.template || selectedBackgroundTemplate || 'burgundy_studio'}`;
        if (videoContainer) {
            videoContainer.setAttribute('data-has-video', isVideoBg ? 'true' : 'false');
            if (res.video_url) videoContainer.setAttribute('data-bg-stream', res.video_url);
            if (res.template) {
                videoContainer.setAttribute('data-bg-template', res.template);
                videoContainer.setAttribute('data-bg-poster', `/api/projects/templates/preview/${res.template}`);
            }
        }
        await player.setMediaMode({
            hasVideo: isVideoBg,
            videoSrc: isVideoBg ? res.video_url : undefined,
            imageSrc: isVideoBg ? posterUrl : res.video_url,
            preserveTime: keepTime,
        });
        player.seekTo(keepTime);
        if (wasPlaying) {
            player.play();
        } else {
            player.pause();
            player.renderActiveFrame(keepTime);
        }
        videoContainer.style.backgroundImage = '';
    }

    async function applyThemeCard(card, tid) {
        selectTemplate(tid);
        const isAiTheme = tid === 'ai_lyric_scene';
        const previewImage = card?.querySelector?.('img');
        if (previewImage && previewImage.src && !isAiTheme) {
            videoContainer.style.backgroundImage = `url("${previewImage.src}")`;
            videoContainer.classList.add('theme-preview-loading');
        } else {
            videoContainer.classList.add('theme-preview-loading');
        }
        if (themeApplyStatus) {
            themeApplyStatus.classList.remove('d-none', 'text-danger');
            themeApplyStatus.classList.add('text-success');
            themeApplyStatus.innerHTML = isAiTheme
                ? '<span class="spinner-border spinner-border-sm me-1"></span> Painting AI lyric scene from your song…'
                : '<span class="spinner-border spinner-border-sm me-1"></span> Applying theme...';
        }
        const aiPromptPreview = document.getElementById('aiThemePromptPreview');
        try {
            const res = await LyricSyncAPI.updateBackgroundTemplate(projectId, tid, currentAspectRatio);
            if (!res.success) {
                const fail = new Error(res.error?.message || 'Theme apply failed');
                fail.code = res.error?.code;
                fail.credits = res.error?.credits || res.credits;
                fail.error = res.error;
                throw fail;
            }
            if (res.video_url) {
                await applyBackgroundResponse(res);
            }
            if (isAiTheme && res.ai?.prompt && aiPromptPreview) {
                aiPromptPreview.classList.remove('d-none');
                aiPromptPreview.textContent = res.ai.prompt;
            }
            if (isAiTheme && res.credits) {
                syncAiCreditUi(res.credits);
            }
        } catch (err) {
            console.warn('Background update error:', err);
            const errCredits = err?.credits || err?.error?.credits;
            if (errCredits) syncAiCreditUi(errCredits);
            if (isAiTheme && (err?.code === 'IMAGE_CREDITS_EXHAUSTED' || err?.error?.code === 'IMAGE_CREDITS_EXHAUSTED')) {
                openPremiumUpgradeModal();
            }
            if (themeApplyStatus) {
                themeApplyStatus.classList.remove('text-success');
                themeApplyStatus.classList.add('text-danger');
                themeApplyStatus.textContent = err.message || 'Could not apply theme';
                setTimeout(() => themeApplyStatus.classList.add('d-none'), 5000);
                return;
            }
        } finally {
            videoContainer.classList.remove('theme-preview-loading');
            videoContainer.style.backgroundImage = '';
            if (themeApplyStatus && !themeApplyStatus.classList.contains('text-danger')) {
                themeApplyStatus.classList.add('d-none');
            }
        }
    }

    const generateAiThemeBtn = document.getElementById('generateAiThemeBtn');
    const aiCreditChip = document.getElementById('aiCreditChip');
    const aiThemeGenerateWrap = document.getElementById('aiThemeGenerateWrap');
    const aiThemeLockedState = document.getElementById('aiThemeLockedState');
    const aiThemeSignInLink = document.getElementById('aiThemeSignInLink');
    const upgradePremiumBtn = document.getElementById('upgradePremiumBtn');
    const payWithCardBtn = document.getElementById('payWithCardBtn');
    const premiumCheckoutHint = document.getElementById('premiumCheckoutHint');
    const premiumCheckoutStatus = document.getElementById('premiumCheckoutStatus');

    let imageCreditState = {
        authenticated: workspace.getAttribute('data-auth-required-ai') !== 'true',
        unlimited: workspace.getAttribute('data-image-unlimited') === 'true',
        can_generate: workspace.getAttribute('data-can-generate-ai') === 'true',
        image_credits: Number(workspace.getAttribute('data-image-credits') || 0),
        premium_price_label: workspace.getAttribute('data-premium-price') || '$5/month',
        premium_credits: Number(workspace.getAttribute('data-premium-credits') || 100),
        stripe_enabled: workspace.getAttribute('data-stripe-enabled') === 'true',
    };

    function syncAiCreditUi(credits) {
        if (!credits) return;
        imageCreditState = { ...imageCreditState, ...credits };
        const authenticated = !!imageCreditState.authenticated;
        const unlimited = !!imageCreditState.unlimited;
        const canGenerate = !!imageCreditState.can_generate;
        const remaining = Number(imageCreditState.image_credits ?? 0);

        if (aiCreditChip) {
            aiCreditChip.classList.toggle('is-empty', authenticated && !unlimited && remaining <= 0);
            if (unlimited) aiCreditChip.textContent = 'Unlimited';
            else if (!authenticated) aiCreditChip.textContent = 'Sign in';
            else aiCreditChip.textContent = `${Math.max(0, remaining)} left`;
        }

        const showLocked = !canGenerate;
        if (aiThemeGenerateWrap) aiThemeGenerateWrap.classList.toggle('d-none', showLocked);
        if (aiThemeLockedState) aiThemeLockedState.classList.toggle('d-none', !showLocked);
        if (aiThemeSignInLink) aiThemeSignInLink.classList.toggle('d-none', authenticated);
        if (upgradePremiumBtn) upgradePremiumBtn.classList.toggle('d-none', !authenticated);
        if (generateAiThemeBtn) {
            generateAiThemeBtn.disabled = showLocked;
        }
        if (premiumCheckoutHint && typeof imageCreditState.stripe_enabled === 'boolean') {
            premiumCheckoutHint.textContent = imageCreditState.stripe_enabled
                ? 'Secure checkout opens in Stripe. Credits are added automatically after payment.'
                : 'Card payments activate when Stripe keys are set on the server. Until then, contact the admin to upgrade manually.';
        }
    }

    syncAiCreditUi(imageCreditState);
    if (typeof LyricSyncAPI !== 'undefined' && LyricSyncAPI.getImageCredits) {
        LyricSyncAPI.getImageCredits().then((res) => {
            if (res?.success && res.credits) syncAiCreditUi(res.credits);
        }).catch(() => {});
    }

    function openPremiumUpgradeModal() {
        const modalEl = document.getElementById('premiumUpgradeModal');
        if (!modalEl || typeof bootstrap === 'undefined') return;
        bootstrap.Modal.getOrCreateInstance(modalEl).show();
    }

    async function startCardCheckout() {
        if (premiumCheckoutStatus) {
            premiumCheckoutStatus.classList.remove('d-none', 'text-success');
            premiumCheckoutStatus.classList.add('text-secondary');
            premiumCheckoutStatus.textContent = 'Starting secure checkout…';
        }
        try {
            const res = await LyricSyncAPI.startPremiumCheckout();
            if (res?.checkout_url) {
                window.location.href = res.checkout_url;
                return;
            }
            if (res?.skipped) {
                syncAiCreditUi(res.credits || imageCreditState);
                if (premiumCheckoutStatus) {
                    premiumCheckoutStatus.classList.remove('text-secondary');
                    premiumCheckoutStatus.classList.add('text-success');
                    premiumCheckoutStatus.textContent = res.message || 'Admin accounts are unlimited.';
                }
                return;
            }
            const msg = res?.error?.message || 'Could not start checkout.';
            if (premiumCheckoutStatus) {
                premiumCheckoutStatus.classList.remove('text-secondary');
                premiumCheckoutStatus.classList.add('text-danger');
                premiumCheckoutStatus.textContent = msg;
            }
        } catch (err) {
            if (premiumCheckoutStatus) {
                premiumCheckoutStatus.classList.remove('text-secondary');
                premiumCheckoutStatus.classList.add('text-danger');
                premiumCheckoutStatus.textContent = err.message || 'Checkout failed.';
            }
        }
    }

    if (generateAiThemeBtn) {
        generateAiThemeBtn.addEventListener('click', () => {
            if (!imageCreditState.can_generate) {
                if (!imageCreditState.authenticated) {
                    window.location.href = '/login';
                    return;
                }
                openPremiumUpgradeModal();
                return;
            }
            applyThemeCard(null, 'ai_lyric_scene');
        });
    }
    if (upgradePremiumBtn) {
        upgradePremiumBtn.addEventListener('click', openPremiumUpgradeModal);
    }
    if (payWithCardBtn) {
        payWithCardBtn.addEventListener('click', startCardCheckout);
    }

    // Custom video upload under Themes drawer
    const studioVideoDropzone = document.getElementById('studioVideoDropzone');
    const studioVideoFileInput = document.getElementById('studioVideoFileInput');
    const studioVideoLabel = document.getElementById('studioVideoLabel');
    const studioVideoFileInfo = document.getElementById('studioVideoFileInfo');
    const studioVideoFileName = document.getElementById('studioVideoFileName');
    const studioRemoveVideoBtn = document.getElementById('studioRemoveVideoBtn');
    const studioVideoUploadStatus = document.getElementById('studioVideoUploadStatus');

    function formatStudioBytes(bytes) {
        if (!bytes) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
    }

    async function uploadStudioCustomVideo(file) {
        if (!file) return;
        if (studioVideoUploadStatus) {
            studioVideoUploadStatus.classList.remove('d-none', 'text-danger');
            studioVideoUploadStatus.classList.add('text-secondary');
            studioVideoUploadStatus.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Uploading custom video…';
        }
        try {
            const res = await LyricSyncAPI.uploadCustomBackgroundVideo(projectId, file);
            if (!res.success || !res.video_url) {
                throw new Error(res.error?.message || 'Upload failed');
            }
            selectedBackgroundTemplate = 'custom_video';
            if (studioVideoLabel) studioVideoLabel.classList.add('d-none');
            if (studioVideoFileInfo) studioVideoFileInfo.classList.remove('d-none');
            if (studioVideoFileName) {
                studioVideoFileName.textContent = res.filename || file.name;
                studioVideoFileName.title = `${file.name} · ${formatStudioBytes(file.size)}`;
            }
            await applyBackgroundResponse(res);
            if (studioVideoUploadStatus) {
                studioVideoUploadStatus.classList.remove('text-secondary');
                studioVideoUploadStatus.classList.add('text-success');
                studioVideoUploadStatus.textContent = 'Custom video applied.';
            }
        } catch (err) {
            if (studioVideoUploadStatus) {
                studioVideoUploadStatus.classList.remove('text-secondary', 'text-success');
                studioVideoUploadStatus.classList.add('text-danger');
                studioVideoUploadStatus.textContent = err.message || 'Could not upload video.';
            }
        }
    }

    if (studioVideoDropzone && studioVideoFileInput) {
        studioVideoDropzone.addEventListener('click', (e) => {
            if (studioRemoveVideoBtn && (e.target === studioRemoveVideoBtn || studioRemoveVideoBtn.contains(e.target))) return;
            studioVideoFileInput.click();
        });
        studioVideoFileInput.addEventListener('change', (e) => uploadStudioCustomVideo(e.target.files?.[0]));
        studioVideoDropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            studioVideoDropzone.style.borderColor = 'var(--brand-burgundy)';
        });
        studioVideoDropzone.addEventListener('dragleave', () => {
            studioVideoDropzone.style.borderColor = '';
        });
        studioVideoDropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            studioVideoDropzone.style.borderColor = '';
            if (e.dataTransfer.files?.[0]) uploadStudioCustomVideo(e.dataTransfer.files[0]);
        });
    }

    if (studioRemoveVideoBtn) {
        studioRemoveVideoBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const fallbackTheme = (allThemes.find((t) => t.id === 'burgundy_studio') || allThemes[0] || {}).id || 'burgundy_studio';
            if (studioVideoUploadStatus) {
                studioVideoUploadStatus.classList.remove('d-none', 'text-danger', 'text-success');
                studioVideoUploadStatus.classList.add('text-secondary');
                studioVideoUploadStatus.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Restoring theme…';
            }
            try {
                const res = await LyricSyncAPI.updateBackgroundTemplate(projectId, fallbackTheme, currentAspectRatio);
                if (!res.success) throw new Error(res.error?.message || 'Could not restore theme');
                selectedBackgroundTemplate = fallbackTheme;
                selectTemplate(fallbackTheme);
                if (studioVideoFileInput) studioVideoFileInput.value = '';
                if (studioVideoLabel) studioVideoLabel.classList.remove('d-none');
                if (studioVideoFileInfo) studioVideoFileInfo.classList.add('d-none');
                await applyBackgroundResponse(res);
                if (studioVideoUploadStatus) {
                    studioVideoUploadStatus.classList.add('text-success');
                    studioVideoUploadStatus.textContent = 'Theme background restored.';
                }
            } catch (err) {
                if (studioVideoUploadStatus) {
                    studioVideoUploadStatus.classList.add('text-danger');
                    studioVideoUploadStatus.textContent = err.message || 'Could not restore theme.';
                }
            }
        });
    }

    async function loadThemeCatalog() {
        try {
            const res = await LyricSyncAPI.getBackgroundTemplates();
            if (!res.success) throw new Error('Failed to load themes');
            allThemes = res.templates || [];
            renderThemeMoodChips(res.moods || ['all']);
            renderThemeGrid();
            selectTemplate(selectedBackgroundTemplate);
        } catch (err) {
            console.warn('Theme catalog load failed', err);
            if (themeCountLabel) themeCountLabel.textContent = 'Could not load themes';
        }
    }

    themeSearchInput?.addEventListener('input', (e) => {
        themeSearchQuery = (e.target.value || '').trim().toLowerCase();
        renderThemeGrid();
    });
    document.querySelectorAll('.theme-media-filter').forEach((btn) => {
        btn.addEventListener('click', () => {
            activeMediaFilter = btn.dataset.media || 'all';
            document.querySelectorAll('.theme-media-filter').forEach((el) => {
                el.classList.toggle('active', el === btn);
            });
            renderThemeGrid();
        });
    });
    loadThemeCatalog();

    // ================= CUSTOM LYRICS IMPORT =================
    function showLyricsImportStatus(type, message) {
        if (!drawerLyricsAlert) return;
        const icons = {
            success: 'bi-check-circle-fill',
            warning: 'bi-exclamation-triangle-fill',
            danger: 'bi-x-circle-fill',
            info: 'bi-info-circle-fill',
        };
        const icon = icons[type] || icons.info;
        drawerLyricsAlert.className = `studio-status studio-status-${type}`;
        drawerLyricsAlert.innerHTML = `<i class="bi ${icon}" aria-hidden="true"></i><span>${message}</span>`;
        drawerLyricsAlert.classList.remove('d-none');
    }

    if (drawerImportLyricsBtn) {
        drawerImportLyricsBtn.addEventListener('click', async () => {
            const textVal = drawerLyricsTextarea ? drawerLyricsTextarea.value.trim() : '';
            const file = drawerLyricsFileInput && drawerLyricsFileInput.files ? drawerLyricsFileInput.files[0] : null;

            if (!textVal && !file) {
                showLyricsImportStatus('warning', 'Choose a .txt / .lrc file or paste lyrics text first.');
                return;
            }

            const origHtml = drawerImportLyricsBtn.innerHTML;
            drawerImportLyricsBtn.disabled = true;
            drawerImportLyricsBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span><span>Importing…</span>';

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

                    showLyricsImportStatus(
                        'success',
                        `Imported ${res.lyrics.length} custom lyric line${res.lyrics.length === 1 ? '' : 's'} successfully.`
                    );
                    if (drawerLyricsTextarea) drawerLyricsTextarea.value = '';
                    if (drawerLyricsFileInput) drawerLyricsFileInput.value = '';
                } else {
                    throw new Error(res.error?.message || "Failed to parse or import custom lyrics.");
                }
            } catch (err) {
                showLyricsImportStatus('danger', `Import failed: ${err.message || 'Unknown error'}`);
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
            const listening = activeStream?.partial;
            const until = formatTime(Number(activeStream?.transcribed_until) || 0);
            lyricsSheetList.innerHTML = listening ? `
                <div class="text-center py-5 text-secondary">
                    <div class="spinner-border spinner-border-sm mb-2" style="color: var(--brand-burgundy);"></div>
                    <p class="fw-bold mb-1 text-dark">Streaming opening preview</p>
                    <p class="small text-secondary mb-0">Language detection + first lines land soon. Audio is playable; lyrics fill in as each slice finishes${Number(activeStream?.transcribed_until) > 0 ? ` (ready to ${until})` : ''}.</p>
                </div>
            ` : `
                <div class="text-center py-5 text-secondary">
                    <i class="bi bi-music-note-beamed fs-1 d-block mb-2" style="color: #94A3B8; opacity: 0.4;"></i>
                    <p class="fw-bold mb-1 text-dark">No Lyrics Detected Yet</p>
                    <p class="small text-secondary mb-3">Transcribe audio to extract synchronized lyrics in the song's language.</p>
                    <button class="btn btn-outline-burgundy btn-sm px-3 py-1.5" onclick="document.getElementById('transcribeBtn').click()">
                        <i class="bi bi-stars me-1"></i> Transcribe AI
                    </button>
                </div>
            `;
            if (lyricsSheetLineCount) lyricsSheetLineCount.textContent = listening ? 'Syncing…' : '0 lines';
            return;
        }

        if (lyricsSheetLineCount) {
            lyricsSheetLineCount.textContent = activeStream?.partial ? `${lines.length} lines · still syncing` : `${lines.length} lines`;
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
                    seekWithinStream(line.start);
                    highlightLyricsSheetLine(line.originalIndex);
                });

                linesCol.appendChild(lineEl);
            });

            block.appendChild(linesCol);
            lyricsSheetList.appendChild(block);
        });

        if (activeStream?.partial) {
            const pending = document.createElement('div');
            pending.className = 'small text-secondary fst-italic px-2 py-2';
            pending.textContent = 'Still listening — more lines appear as this part finishes.';
            lyricsSheetList.appendChild(pending);
        }

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
        const styleConfig = buildStylePayloadForSave();
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
    function streamFrontierSeconds() {
        if (!activeStream?.partial) return null;
        const until = Number(activeStream.transcribed_until);
        if (!Number.isFinite(until) || until <= 0.2) return null;
        return until;
    }

    function seekWithinStream(seconds) {
        let time = Math.max(0, Number(seconds) || 0);
        const frontier = streamFrontierSeconds();
        if (frontier != null && time > frontier - 0.05) {
            time = Math.max(0, frontier - 0.05);
            resumeWhenStreamAdvances = false;
            setStreamBanner('blocked');
        }
        player.seekTo(time);
        return time;
    }

    function paintStreamScrubber() {
        if (!scrubber) return;
        const frontier = streamFrontierSeconds();
        const duration = Number(activeStream?.duration) || Number(scrubber.max) || 0;
        if (frontier == null || duration <= 0) {
            scrubber.classList.remove('stream-active');
            scrubber.style.removeProperty('--stream-track');
            return;
        }
        const pct = Math.max(0, Math.min(100, (frontier / duration) * 100));
        scrubber.classList.add('stream-active');
        scrubber.style.setProperty('--stream-track', `linear-gradient(90deg, rgba(122, 46, 62, 0.72) ${pct}%, #E5E7EB ${pct}%)`);
    }

    function setStreamBanner(mode) {
        const banner = document.getElementById('streamBanner');
        const text = document.getElementById('streamBannerText');
        const spinner = document.getElementById('streamBannerSpinner');
        const meter = document.getElementById('streamBannerMeterFill');
        const playPreviewBtn = document.getElementById('streamPlayPreviewBtn');
        if (!banner || !text) return;
        const name = activeStream?.language_name || 'Detecting language';
        const until = formatTime(Number(activeStream?.transcribed_until) || 0);
        const total = formatTime(Number(activeStream?.duration) || 0);
        const duration = Number(activeStream?.duration) || 0;
        const synced = Number(activeStream?.transcribed_until) || 0;
        const pct = duration > 0 ? Math.max(0, Math.min(100, (synced / duration) * 100)) : 0;
        banner.classList.remove('d-none');
        banner.classList.add('d-flex');
        if (spinner) spinner.classList.toggle('d-none', mode === 'done');
        if (meter) meter.style.width = `${pct}%`;
        if (playPreviewBtn) {
            const showPlay = mode !== 'done' && synced > 0.2 && player.isPaused;
            playPreviewBtn.classList.toggle('d-none', !showPlay);
        }
        if (mode === 'waiting') {
            text.textContent = `Paused at ${until}. Next lines are still streaming in.`;
        } else if (mode === 'blocked') {
            text.textContent = `Preview ends at ${until}. Scrub back or wait for more sync.`;
        } else if (mode === 'done') {
            text.textContent = activeStream?.language_name
                ? `Sync finished · ${activeStream.language_name}.`
                : 'Sync finished. The full song is ready.';
            if (meter) meter.style.width = '100%';
        } else if (synced > 0.2) {
            const chunkHint = activeStream?.chunk_index && activeStream?.chunk_count
                ? ` · slice ${activeStream.chunk_index}/${activeStream.chunk_count}`
                : '';
            text.textContent = `${name} preview · synced to ${until} of ${total}${chunkHint}. Play until the ready part, then it waits.`;
        } else {
            text.textContent = 'Listening for language + opening lines. Audio is ready — lyrics stream in as each slice finishes.';
        }
    }

    function hideStreamBanner() {
        const banner = document.getElementById('streamBanner');
        const playPreviewBtn = document.getElementById('streamPlayPreviewBtn');
        if (playPreviewBtn) playPreviewBtn.classList.add('d-none');
        if (!banner) return;
        banner.classList.add('d-none');
        banner.classList.remove('d-flex');
    }

    function applyStreamLyrics(lyrics, stream) {
        const partial = !!(stream && (stream.partial === true || stream.partial === 1));
        activeStream = stream ? { ...stream, partial, preview: partial || !!stream.preview } : null;
        if (!partial) streamCursor = -1;
        timeline.setLines(lyrics || []);
        player.setLyrics(lyrics || []);
        renderLyricsSheet(lyrics || []);
        renderConfidenceHeatmap(lyrics || []);
        paintStreamScrubber();
        if (partial) {
            setStreamBanner('playing');
            maybeResumeAfterStream();
        }
    }

    function maybeResumeAfterStream() {
        if (!resumeWhenStreamAdvances) return;
        const frontier = streamFrontierSeconds();
        if (frontier == null || frontier > player.currentTime + 0.45) {
            resumeWhenStreamAdvances = false;
            player.play();
        }
    }

    let partialWatchTimer = null;
    let lyricsEventSource = null;
    let autoPlayedPreview = false;

    function stopLyricsStreamWatch() {
        if (partialWatchTimer) {
            clearTimeout(partialWatchTimer);
            partialWatchTimer = null;
        }
        if (lyricsEventSource) {
            lyricsEventSource.close();
            lyricsEventSource = null;
        }
    }

    function watchPartialLyrics() {
        if (lyricsEventSource || partialWatchTimer) return;

        const handlePayload = (lyricsRes) => {
            if (!lyricsRes?.success) return;
            const until = Number(lyricsRes.stream?.transcribed_until) || 0;
            if (until !== streamCursor || !lyricsRes.stream?.partial) {
                streamCursor = until;
                applyStreamLyrics(lyricsRes.lyrics || [], lyricsRes.stream);
            }
            if (until > 0.2 && !autoPlayedPreview && player.isPaused && player.currentTime < 0.35) {
                autoPlayedPreview = true;
                player.play();
            }
            if (lyricsRes.stream && lyricsRes.stream.partial === false) {
                stopLyricsStreamWatch();
                setStreamBanner('done');
                setTimeout(hideStreamBanner, 2400);
            }
        };

        const live = LyricSyncAPI.watchLyricsStream(projectId, {
            onUpdate: handlePayload,
            onDone: () => {
                stopLyricsStreamWatch();
            },
            onError: () => {
                // Fall back to polling if SSE drops.
                if (lyricsEventSource) {
                    lyricsEventSource.close();
                    lyricsEventSource = null;
                }
                if (!partialWatchTimer && activeStream?.partial) {
                    startPartialPoll();
                }
            },
        });

        if (live.supported) {
            lyricsEventSource = live;
            return;
        }
        startPartialPoll();

        function startPartialPoll() {
            if (partialWatchTimer) return;
            const tick = async () => {
                partialWatchTimer = null;
                if (!activeStream?.partial) return;
                try {
                    const lyricsRes = await LyricSyncAPI.getLyrics(projectId);
                    handlePayload(lyricsRes);
                } catch (err) {
                    console.warn('Lyric stream refresh failed', err);
                }
                if (activeStream?.partial) partialWatchTimer = setTimeout(tick, 900);
            };
            partialWatchTimer = setTimeout(tick, 700);
        }
    }

    document.getElementById('streamPlayPreviewBtn')?.addEventListener('click', () => {
        const frontier = streamFrontierSeconds();
        if (frontier != null && player.currentTime >= frontier - 0.1) {
            seekWithinStream(Math.max(0, frontier - Math.min(4, frontier * 0.4)));
        }
        resumeWhenStreamAdvances = false;
        player.play();
        setStreamBanner('playing');
    });

    const transcribeModalEl = document.getElementById('transcribeModal');
    const transcribeModal = new bootstrap.Modal(transcribeModalEl);
    const transcribeStageText = document.getElementById('transcribeStageText');
    const transcribeProgressBar = document.getElementById('transcribeProgressBar');
    const transcribeProgressPct = document.getElementById('transcribeProgressPct');
    const transcribeSpinner = document.getElementById('transcribeSpinner');
    const transcribeSuccessIcon = document.getElementById('transcribeSuccessIcon');
    const transcribeErrorBox = document.getElementById('transcribeErrorBox');
    const transcribeModalFooter = document.getElementById('transcribeModalFooter');
    const transcribeSubText = document.getElementById('transcribeSubText');
    const transcribeRetryBtn = document.getElementById('transcribeRetryBtn');

    // Streamed sync: unlock the studio on the first playable slice; keep loading the rest.
    transcribeBtn.addEventListener('click', async () => {
        stopLyricsStreamWatch();
        autoPlayedPreview = false;
        transcribeSpinner.classList.remove('d-none');
        transcribeSuccessIcon.classList.add('d-none');
        transcribeErrorBox.classList.add('d-none');
        if (transcribeRetryBtn) transcribeRetryBtn.classList.add('d-none');
        if (transcribeModalFooter) transcribeModalFooter.classList.remove('d-none');

        let currentPct = 6;
        let studioUnlocked = false;
        transcribeProgressBar.style.width = '6%';
        transcribeProgressPct.textContent = '6%';
        transcribeStageText.textContent = 'Checking if this song is already known…';
        if (transcribeSubText) {
            transcribeSubText.textContent = 'If the track is recognized, published lyrics load instantly. Otherwise AI transcribes a short opening preview first.';
        }
        transcribeModal.show();
        streamCursor = -1;
        resumeWhenStreamAdvances = false;

        const unlockStudio = () => {
            if (studioUnlocked) return;
            studioUnlocked = true;
            transcribeModal.hide();
            setStreamBanner('playing');
        };

        const progressHandler = async (e) => {
            const job = e.detail;
            if (!job) return;
            if (typeof job.progress === 'number' && job.progress > currentPct) {
                currentPct = job.progress;
                transcribeProgressBar.style.width = `${currentPct}%`;
                transcribeProgressPct.textContent = `${currentPct}%`;
            }
            if (job.stage) transcribeStageText.textContent = friendlyStage(job.stage);
            const until = Number(job.stream?.transcribed_until) || 0;
            if (job.stream) {
                activeStream = { ...(activeStream || {}), ...job.stream, partial: job.stream.partial !== false };
                setStreamBanner(until > 0.2 ? 'playing' : 'playing');
            }
            const streamMoved = job.stream && (until !== streamCursor || job.stream.partial === false);
            if (!streamMoved || (until <= 0 && job.stream?.partial !== false)) return;
            try {
                const lyricsRes = await LyricSyncAPI.getLyrics(projectId);
                if (!lyricsRes.success) return;
                streamCursor = Number(lyricsRes.stream?.transcribed_until) || until;
                applyStreamLyrics(lyricsRes.lyrics || [], lyricsRes.stream || job.stream);
                if (streamCursor > 0.2) unlockStudio();
            } catch (err) {
                console.warn('Could not load partial lyrics', err);
            }
        };

        try {
            const languageSelect = document.getElementById('transcribeLanguage');
            const language = languageSelect?.value || 'auto';
            localStorage.setItem('lyricsync_language', language);
            const res = await LyricSyncAPI.triggerTranscription(projectId, language);
            if (!res.success) throw new Error(res.error?.message || "Failed to trigger transcription");

            window.addEventListener('job-progress', progressHandler);
            activeStream = {
                partial: true,
                preview: true,
                transcribed_until: 0,
                duration: Number(scrubber.max) || 0,
                language_name: language !== 'auto' ? (languageSelect?.selectedOptions?.[0]?.text || '') : '',
                language: language === 'auto' ? '' : language,
            };
            setStreamBanner('playing');
            watchPartialLyrics();

            // Don't trap the user behind the modal — studio stays usable while syncing.
            setTimeout(() => {
                if (!studioUnlocked) {
                    unlockStudio();
                }
            }, 1800);

            await LyricSyncAPI.pollJob(res.job_id);
            window.removeEventListener('job-progress', progressHandler);
            stopLyricsStreamWatch();

            const lyricsRes = await LyricSyncAPI.getLyrics(projectId);
            if (lyricsRes.success) {
                applyStreamLyrics(lyricsRes.lyrics || [], { ...(lyricsRes.stream || {}), partial: false, preview: false });
                const revEl = document.getElementById('revisionDisplay') || document.getElementById('revisionBadge');
                if (revEl) revEl.textContent = `Rev ${lyricsRes.revision}`;
            }
            const knownArtist = lyricsRes?.stream?.artist || lyricsRes?.stream?.title;
            const knownLabel = lyricsRes?.stream?.artist && lyricsRes?.stream?.title
                ? `${lyricsRes.stream.artist} — ${lyricsRes.stream.title}`
                : (lyricsRes?.stream?.title || lyricsRes?.stream?.language_name || '');
            setStreamBanner('done');
            if (lyricsRes?.stream?.source === 'lrclib' || lyricsRes?.stream?.source === 'catalog') {
                const bannerText = document.getElementById('streamBannerText');
                if (bannerText) {
                    bannerText.textContent = knownLabel
                        ? `Known lyrics loaded · ${knownLabel}${lyricsRes.stream.synced ? ' (timed)' : ''}.`
                        : 'Known lyrics loaded from the catalog.';
                }
            }
            setTimeout(hideStreamBanner, 2800);
            paintStreamScrubber();

            transcribeSpinner.classList.add('d-none');
            transcribeSuccessIcon.classList.remove('d-none');
            transcribeProgressBar.style.width = '100%';
            transcribeProgressPct.textContent = '100%';
            transcribeStageText.textContent = (lyricsRes?.stream?.source === 'lrclib' || lyricsRes?.stream?.source === 'catalog')
                ? (knownLabel ? `Done · ${knownLabel}` : 'Done · known lyrics loaded')
                : (lyricsRes?.stream?.language_name
                    ? `Done · ${lyricsRes.stream.language_name}`
                    : 'Done. The full song is synced.');
            if (knownArtist) {
                const nameInput = document.getElementById('editorProjectName');
                if (nameInput && lyricsRes.stream?.artist && lyricsRes.stream?.title) {
                    const nextName = `${lyricsRes.stream.artist} - ${lyricsRes.stream.title}`;
                    if (!nameInput.value || /untitled/i.test(nameInput.value) || nameInput.value.trim().length < 3) {
                        nameInput.value = nextName;
                    }
                }
            }
        } catch (err) {
            window.removeEventListener('job-progress', progressHandler);
            stopLyricsStreamWatch();
            transcribeSpinner.classList.add('d-none');
            const isTimeout = err.message?.toLowerCase().includes('took longer') || err.message?.toLowerCase().includes('timeout');
            transcribeErrorBox.innerHTML = isTimeout
                ? `<strong>Sync is taking longer than expected.</strong><br><span class="small">Lines already on screen stay. Retry to continue, or keep playing the synced part.</span>`
                : (err.message || "An error occurred during transcription.");
            transcribeErrorBox.classList.remove('d-none');
            if (transcribeRetryBtn) transcribeRetryBtn.classList.remove('d-none');
            if (transcribeModalFooter) transcribeModalFooter.classList.remove('d-none');
            if (studioUnlocked) transcribeModal.show();
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

    function syncExportTierSelected() {
        const checked = document.querySelector('input[name="exportResolutionTier"]:checked');
        const value = checked?.value || selectedExportResolution || '720';
        selectedExportResolution = value;
        exportTierLabel720?.classList.toggle('is-selected', value === '720');
        exportTierLabel1080?.classList.toggle('is-selected', value === '1080');
    }

    if (exportTierLabel720) {
        exportTierLabel720.addEventListener('click', () => {
            const radio = exportTierLabel720.querySelector('input[type="radio"]');
            if (radio) radio.checked = true;
            syncExportTierSelected();
        });
    }

    if (exportTierLabel1080) {
        exportTierLabel1080.addEventListener('click', () => {
            const radio = exportTierLabel1080.querySelector('input[type="radio"]');
            if (radio) radio.checked = true;
            syncExportTierSelected();
        });
    }
    syncExportTierSelected();

    function showExportDockExpanded() {
        if (!exportJobDock) return;
        exportJobDock.classList.remove('d-none');
        if (exportDockCard) exportDockCard.classList.remove('d-none');
        if (exportDockCollapsed) exportDockCollapsed.classList.add('d-none');
    }

    function minimizeExportDock() {
        if (!exportJobDock) return;
        exportJobDock.classList.remove('d-none');
        if (exportDockCard) exportDockCard.classList.add('d-none');
        if (exportDockCollapsed) exportDockCollapsed.classList.remove('d-none');
    }

    function hideExportDock() {
        if (!exportJobDock) return;
        exportJobDock.classList.add('d-none');
        if (exportDockCard) exportDockCard.classList.add('d-none');
        if (exportDockCollapsed) exportDockCollapsed.classList.add('d-none');
    }

    function dismissExportModal() {
        try {
            const instance = bootstrap.Modal.getInstance(exportModalEl) || exportModal;
            instance?.hide();
        } catch (_) { /* ignore */ }
        // Ensure a mid-animation modal can't leave a blocking backdrop behind
        requestAnimationFrame(() => {
            if (!exportModalEl) return;
            exportModalEl.classList.remove('show');
            exportModalEl.style.display = 'none';
            exportModalEl.setAttribute('aria-hidden', 'true');
            document.body.classList.remove('modal-open');
            document.body.style.removeProperty('overflow');
            document.body.style.removeProperty('padding-right');
            document.querySelectorAll('.modal-backdrop').forEach((el) => el.remove());
        });
    }

    function setExportBusy(busy) {
        exportInProgress = busy;
        if (exportVideoBtn) {
            exportVideoBtn.classList.toggle('is-exporting', busy);
            exportVideoBtn.title = busy ? 'Export running — click to show progress' : 'Export lyric video';
        }
        if (exportBtnLabel) {
            if (!busy && exportBtnLabel.textContent && !exportBtnLabel.textContent.includes('Exporting')) {
                exportIdleLabel = exportBtnLabel.textContent;
            }
            exportBtnLabel.textContent = busy ? 'Exporting…' : (exportIdleLabel || 'Export');
        }
        if (exportDockCollapsed) {
            exportDockCollapsed.classList.toggle('is-complete', !busy);
        }
    }

    function updateExportProgress(pct, stage) {
        const safePct = Math.max(0, Math.min(100, Number(pct) || 0));
        if (exportProgressBar) exportProgressBar.style.width = `${safePct}%`;
        if (exportProgressPct) exportProgressPct.textContent = `${safePct}%`;
        if (exportDockPillPct) exportDockPillPct.textContent = `${safePct}%`;
        if (stage && exportStageText) exportStageText.textContent = stage;
        if (exportDockPillText) {
            exportDockPillText.textContent = safePct >= 100 ? 'Export ready' : 'Exporting…';
        }
    }

    minimizeExportDockBtn?.addEventListener('click', minimizeExportDock);
    hideExportDockBtn?.addEventListener('click', minimizeExportDock);
    dismissExportDockBtn?.addEventListener('click', () => {
        // Hide the card; keep pill if still rendering so status remains visible.
        if (exportInProgress) minimizeExportDock();
        else hideExportDock();
    });
    exportDockCollapsed?.addEventListener('click', showExportDockExpanded);

    // Open Export Modal in Quality Selection View
    exportVideoBtn.addEventListener('click', () => {
        if (exportInProgress) {
            showExportDockExpanded();
            return;
        }
        if (exportSelectView) exportSelectView.classList.remove('d-none');
        if (startExportActionBtn) {
            startExportActionBtn.classList.remove('d-none');
            startExportActionBtn.disabled = false;
        }
        if (exportErrorBox) exportErrorBox.classList.add('d-none');
        exportModal.show();
    });


    // Start render, then keep working — progress lives in the background dock
    if (startExportActionBtn) {
        startExportActionBtn.addEventListener('click', async () => {
            const chosenRes = document.querySelector('input[name="exportResolutionTier"]:checked')?.value || selectedExportResolution || '720';
            const qualityLabel = chosenRes === '720'
                ? (isAdmin ? '720p Fast Draft MP4' : '720p Fast Draft Video')
                : (isAdmin ? '1080p Studio Master MP4' : '1080p Full HD Video');

            if (exportQualityBadgeText) exportQualityBadgeText.textContent = qualityLabel;
            if (exportErrorBox) exportErrorBox.classList.add('d-none');
            if (downloadFinalVideoBtn) downloadFinalVideoBtn.classList.add('d-none');
            if (exportSpinner) exportSpinner.classList.remove('d-none');
            if (exportSubText) {
                exportSubText.textContent = isAdmin
                    ? 'Burning exact word-level timings via libass into progressive streaming MP4.'
                    : 'Creating your synchronized high-definition lyric video.';
            }

            updateExportProgress(12, isAdmin ? 'Queueing FFmpeg render job...' : 'Preparing high quality lyric video...');
            setExportBusy(true);
            dismissExportModal();
            showExportDockExpanded();
            startExportActionBtn.disabled = true;

            try {
                const styleConfig = buildStylePayloadForSave();
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

                const progressHandler = (e) => {
                    const job = e.detail;
                    updateExportProgress(job.progress, job.stage ? friendlyStage(job.stage) : null);
                };
                window.addEventListener('job-progress', progressHandler);

                await LyricSyncAPI.pollJob(jobId);
                window.removeEventListener('job-progress', progressHandler);

                if (exportSpinner) exportSpinner.classList.add('d-none');
                updateExportProgress(100, 'Video render complete');
                if (exportSubText) exportSubText.textContent = 'Your lyric video is ready to download.';
                setExportBusy(false);
                showExportDockExpanded();

                const downloadUrl = `/api/projects/${projectId}/download`;
                if (downloadFinalVideoBtn) {
                    downloadFinalVideoBtn.href = downloadUrl;
                    downloadFinalVideoBtn.classList.remove('d-none');
                }
                if (downloadHeaderBtn) {
                    downloadHeaderBtn.href = downloadUrl;
                    downloadHeaderBtn.classList.remove('d-none');
                    downloadHeaderBtn.classList.add('d-flex');
                }
            } catch (err) {
                if (exportSpinner) exportSpinner.classList.add('d-none');
                if (exportStageText) exportStageText.textContent = 'Rendering failed';
                if (exportSubText) exportSubText.textContent = 'You can keep editing, then try exporting again.';
                if (exportErrorBox) {
                    exportErrorBox.textContent = err.message || 'Export failed';
                    exportErrorBox.classList.remove('d-none');
                }
                if (exportDockPillText) exportDockPillText.textContent = 'Export failed';
                setExportBusy(false);
                showExportDockExpanded();
                startExportActionBtn.disabled = false;
            }
        });
    }
});
