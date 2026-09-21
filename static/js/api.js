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

    pollJob(jobId, intervalMs = 1000) {
        return new Promise((resolve, reject) => {
            const timer = setInterval(async () => {
                try {
                    const res = await LyricSyncAPI.getJobStatus(jobId);
                    if (!res.success) {
                        clearInterval(timer);
                        return reject(new Error(res.error?.message || "Failed to poll job status"));
                    }
                    const job = res.job;
                    window.dispatchEvent(new CustomEvent('job-progress', { detail: job }));

                    if (job.status === 'completed') {
                        clearInterval(timer);
                        resolve(job);
                    } else if (job.status === 'failed' || job.status === 'cancelled') {
                        clearInterval(timer);
                        reject(new Error(job.error_message || "Job execution failed"));
                    }
                } catch (err) {
                    clearInterval(timer);
                    reject(err);
                }
            }, intervalMs);
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
