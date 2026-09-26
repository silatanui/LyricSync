/**
 * LyricSync API Client Module
 */
const lyricSyncProjectsUrl = document.querySelector('meta[name="lyricsync-api-root"]')?.content || '/api/projects';
const lyricSyncApiBase = lyricSyncProjectsUrl.endsWith('/projects')
    ? lyricSyncProjectsUrl.slice(0, -'/projects'.length)
    : '/api';
const lyricSyncApiUrl = (path) => `${lyricSyncApiBase}${path}`;

const LyricSyncAPI = {
    createProject(formData, onProgress = null) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open('POST', lyricSyncProjectsUrl);

            if (onProgress && xhr.upload) {
                xhr.upload.onprogress = (e) => {
                    if (e.lengthComputable) {
                        const pct = Math.round((e.loaded / e.total) * 100);
                        onProgress(pct, e.loaded, e.total);
                    }
                };
            }

            xhr.onload = () => {
                try {
                    const data = JSON.parse(xhr.responseText);
                    resolve(data);
                } catch (err) {
                    const message = xhr.status === 504
                        ? 'The server timed out while preparing the background video. Please try again with a shorter audio file.'
                        : xhr.status >= 500
                            ? 'The server could not finish preparing this project. Please try again.'
                            : `Server response error (${xhr.status})`;
                    reject(new Error(message));
                }
            };

            xhr.onerror = () => reject(new Error('Network error during project creation.'));
            xhr.ontimeout = () => reject(new Error('Project creation timed out.'));

            xhr.send(formData);
        });
    },

    async getProject(projectId) {
        const response = await fetch(`${lyricSyncProjectsUrl}/${projectId}`);
        return await response.json();
    },

    async deleteProject(projectId) {
        const response = await fetch(`${lyricSyncProjectsUrl}/${projectId}`, {
            method: 'DELETE',
        });
        return await response.json();
    },

    async updateProject(projectId, projectData) {
        const response = await fetch(`${lyricSyncProjectsUrl}/${projectId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(projectData),
        });
        return await response.json();
    },

    async triggerTranscription(projectId) {
        const response = await fetch(`${lyricSyncProjectsUrl}/${projectId}/transcribe`, {
            method: 'POST',
        });
        return await response.json();
    },

    async getLyrics(projectId) {
        const response = await fetch(`${lyricSyncProjectsUrl}/${projectId}/lyrics`);
        return await response.json();
    },

    async saveLyrics(projectId, lyrics) {
        const response = await fetch(`${lyricSyncProjectsUrl}/${projectId}/lyrics`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lyrics }),
        });
        return await response.json();
    },

    async updateStyle(projectId, styleData, renderData) {
        const response = await fetch(`${lyricSyncProjectsUrl}/${projectId}/style`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ style: styleData, render: renderData }),
        });
        return await response.json();
    },

    async queueRender(projectId, options = {}) {
        const response = await fetch(`${lyricSyncProjectsUrl}/${projectId}/render`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(options),
        });
        return await response.json();
    },

    async getJobStatus(jobId) {
        const response = await fetch(lyricSyncApiUrl(`/jobs/${jobId}`));
        return await response.json();
    },

    pollJob(jobId, intervalMs = 1500, timeoutMs = 600000) {
        // timeoutMs = 10 minutes — Whisper-1 can take up to 5-6 min for long songs
        // intervalMs starts at 1.5s, increases gradually to avoid hammering the server
        return new Promise((resolve, reject) => {
            const startedAt = Date.now();
            let currentInterval = intervalMs;
            let failCount = 0;
            const MAX_CONSECUTIVE_FAILS = 8;

            const poll = async () => {
                const elapsed = Date.now() - startedAt;

                if (elapsed >= timeoutMs) {
                    return reject(new Error('The transcription took longer than expected. The server is still processing — please click Retry to check if it completed.'));
                }

                // Adaptive interval: slow down after 90s to reduce server pressure
                if (elapsed > 90000 && currentInterval < 4000) {
                    currentInterval = 4000;
                } else if (elapsed > 30000 && currentInterval < 2500) {
                    currentInterval = 2500;
                }

                try {
                    const res = await LyricSyncAPI.getJobStatus(jobId);
                    failCount = 0;

                    if (!res.success) {
                        if (res.error?.retryable) {
                            setTimeout(poll, currentInterval);
                            return;
                        }
                        return reject(new Error(res.error?.message || "Failed to poll job status"));
                    }

                    const job = res.job;
                    window.dispatchEvent(new CustomEvent('job-progress', { detail: job }));

                    if (job.status === 'completed') {
                        resolve(job);
                    } else if (job.status === 'failed' || job.status === 'cancelled') {
                        reject(new Error(job.error_message || "Job execution failed"));
                    } else {
                        // Still running — poll again
                        setTimeout(poll, currentInterval);
                    }
                } catch (err) {
                    // Network hiccup — retry a few times before giving up
                    failCount++;
                    if (failCount >= MAX_CONSECUTIVE_FAILS) {
                        return reject(new Error('Connection lost. The server may still be processing — please retry.'));
                    }
                    // Exponential backoff on network errors
                    const backoffMs = Math.min(currentInterval * Math.pow(1.5, failCount), 12000);
                    setTimeout(poll, backoffMs);
                }
            };

            // Start polling immediately
            setTimeout(poll, 800);
        });
    },

    async getBackgroundTemplates() {
        const response = await fetch(`${lyricSyncProjectsUrl}/templates`);
        return await response.json();
    },

    async updateBackgroundTemplate(projectId, template, aspectRatio = null) {
        const payload = { template };
        if (aspectRatio) payload.aspect_ratio = aspectRatio;
        const response = await fetch(`${lyricSyncProjectsUrl}/${projectId}/background`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        return await response.json();
    },

    async importCustomLyrics(projectId, input) {
        let options = { method: 'POST' };
        if (input instanceof FormData) {
            options.body = input;
        } else {
            options.headers = { 'Content-Type': 'application/json' };
            options.body = JSON.stringify({ lyrics_text: input });
        }
        const response = await fetch(`${lyricSyncProjectsUrl}/${projectId}/lyrics/custom`, options);
        return await response.json();
    }
};

window.LyricSyncAPI = LyricSyncAPI;
