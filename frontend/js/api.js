// API communication module

const API_BASE = '/api';

/**
 * Make an API request
 */
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;

    const config = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        ...options
    };

    // Don't set Content-Type for FormData
    if (options.body instanceof FormData) {
        delete config.headers['Content-Type'];
    }

    try {
        const response = await fetch(url, config);

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
            throw new Error(error.detail || `HTTP error ${response.status}`);
        }

        // Handle empty responses
        const text = await response.text();
        return text ? JSON.parse(text) : null;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

/**
 * Playlist API
 */
const PlaylistAPI = {
    /**
     * Upload a playlist file
     */
    async upload(file, onProgress) {
        const formData = new FormData();
        formData.append('file', file);

        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable && onProgress) {
                    onProgress(Math.round((e.loaded / e.total) * 100));
                }
            });

            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve(JSON.parse(xhr.responseText));
                } else {
                    const error = JSON.parse(xhr.responseText);
                    reject(new Error(error.detail || 'Upload failed'));
                }
            });

            xhr.addEventListener('error', () => {
                reject(new Error('Upload failed'));
            });

            xhr.open('POST', `${API_BASE}/playlists/upload`);
            xhr.send(formData);
        });
    },

    /**
     * Get all playlists
     */
    async list() {
        return apiRequest('/playlists');
    },

    /**
     * Get a single playlist with channels
     */
    async get(id) {
        return apiRequest(`/playlists/${id}`);
    },

    /**
     * Download a playlist
     */
    async download(id) {
        const response = await fetch(`${API_BASE}/playlists/${id}/download`);
        if (!response.ok) throw new Error('Download failed');
        return response.blob();
    },

    /**
     * Delete a playlist
     */
    async delete(id) {
        return apiRequest(`/playlists/${id}`, { method: 'DELETE' });
    }
};

/**
 * Channel API
 */
const ChannelAPI = {
    /**
     * Get channels for a playlist
     */
    async list(playlistId, params = {}) {
        const queryParams = new URLSearchParams();
        if (params.search) queryParams.append('search', params.search);
        if (params.group) queryParams.append('group', params.group);

        const query = queryParams.toString();
        return apiRequest(`/playlists/${playlistId}/channels${query ? '?' + query : ''}`);
    },

    /**
     * Create a new channel
     */
    async create(playlistId, channelData) {
        return apiRequest(`/playlists/${playlistId}/channels`, {
            method: 'POST',
            body: JSON.stringify(channelData)
        });
    },

    /**
     * Update a channel
     */
    async update(playlistId, channelId, channelData) {
        return apiRequest(`/playlists/${playlistId}/channels/${channelId}`, {
            method: 'PUT',
            body: JSON.stringify(channelData)
        });
    },

    /**
     * Delete a channel
     */
    async delete(playlistId, channelId) {
        return apiRequest(`/playlists/${playlistId}/channels/${channelId}`, {
            method: 'DELETE'
        });
    },

    /**
     * Reorder channels
     */
    async reorder(playlistId, channelIds) {
        return apiRequest(`/playlists/${playlistId}/channels/reorder`, {
            method: 'PUT',
            body: JSON.stringify({ channel_ids: channelIds })
        });
    },

    /**
     * Bulk delete channels
     */
    async bulkDelete(playlistId, channelIds) {
        return apiRequest(`/playlists/${playlistId}/channels/bulk`, {
            method: 'DELETE',
            body: JSON.stringify({ channel_ids: channelIds })
        });
    },

    /**
     * Bulk move channels to a group
     */
    async bulkMove(playlistId, channelIds, groupTitle) {
        return apiRequest(`/playlists/${playlistId}/channels/bulk-move`, {
            method: 'PUT',
            body: JSON.stringify({ channel_ids: channelIds, group_title: groupTitle })
        });
    }
};
