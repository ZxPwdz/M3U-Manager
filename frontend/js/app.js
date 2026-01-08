// Main application logic

function app() {
    return {
        // View state
        currentView: 'home',
        activeTab: 'library',
        loading: true,
        editorLoading: false,

        // Data
        playlists: [],
        currentPlaylist: null,
        channels: [],
        filteredChannels: [],
        groups: [],
        originalChannels: [], // For tracking changes

        // Upload state
        dragOver: false,
        uploading: false,
        uploadProgress: 0,

        // Editor state
        searchQuery: '',
        filterGroup: '',
        selectedChannels: [],
        expandedChannel: null,
        hasUnsavedChanges: false,
        saving: false,

        // Modal state
        deleteModal: false,
        deleteTarget: null,
        channelModal: false,
        editingChannel: null,
        bulkMoveModal: false,
        bulkMoveGroup: '',
        unsavedWarningModal: false,

        // Channel form
        channelForm: {
            name: '',
            stream_url: '',
            group_title: '',
            tvg_logo: '',
            tvg_id: ''
        },

        // Toast notifications
        toasts: [],

        // Initialize
        async init() {
            await this.loadPlaylists();
            // If there are playlists, show library tab
            if (this.playlists.length > 0) {
                this.activeTab = 'library';
            } else {
                this.activeTab = 'upload';
            }
        },

        // Toast notifications
        showToast(message, type = 'success') {
            const id = generateId();
            this.toasts.push({ id, message, type, visible: true });

            setTimeout(() => {
                const toast = this.toasts.find(t => t.id === id);
                if (toast) toast.visible = false;
                setTimeout(() => {
                    this.toasts = this.toasts.filter(t => t.id !== id);
                }, 200);
            }, 3000);
        },

        // Format helpers
        formatDate,
        formatFileSize,

        // Playlist management
        async loadPlaylists() {
            this.loading = true;
            try {
                this.playlists = await PlaylistAPI.list();
            } catch (error) {
                this.showToast(error.message, 'error');
            } finally {
                this.loading = false;
            }
        },

        async handleDrop(event) {
            this.dragOver = false;
            const files = event.dataTransfer.files;
            if (files.length > 0) {
                await this.uploadFile(files[0]);
            }
        },

        async handleFileSelect(event) {
            const files = event.target.files;
            if (files.length > 0) {
                await this.uploadFile(files[0]);
            }
            event.target.value = '';
        },

        async uploadFile(file) {
            const ext = file.name.split('.').pop().toLowerCase();
            if (!['m3u', 'm3u8'].includes(ext)) {
                this.showToast('Please upload a .m3u or .m3u8 file', 'error');
                return;
            }

            this.uploading = true;
            this.uploadProgress = 0;

            try {
                const result = await PlaylistAPI.upload(file, (progress) => {
                    this.uploadProgress = progress;
                });
                this.showToast(`Uploaded "${file.name}" with ${result.channels_count} channels`);
                await this.loadPlaylists();
                this.activeTab = 'library';
            } catch (error) {
                this.showToast(error.message, 'error');
            } finally {
                this.uploading = false;
                this.uploadProgress = 0;
            }
        },

        confirmDelete(playlist) {
            this.deleteTarget = playlist;
            this.deleteModal = true;
        },

        async deletePlaylist() {
            if (!this.deleteTarget) return;

            try {
                await PlaylistAPI.delete(this.deleteTarget.id);
                this.showToast('Playlist deleted');
                this.deleteModal = false;
                this.deleteTarget = null;
                await this.loadPlaylists();
            } catch (error) {
                this.showToast(error.message, 'error');
            }
        },

        async downloadPlaylist(id, filename) {
            try {
                const blob = await PlaylistAPI.download(id);
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                this.showToast('Download started');
            } catch (error) {
                this.showToast(error.message, 'error');
            }
        },

        copyDirectLink(id) {
            const directUrl = window.location.origin + '/api/playlists/stream/' + id + '.m3u';
            const textArea = document.createElement('textarea');
            textArea.value = directUrl;
            textArea.style.position = 'fixed';
            textArea.style.left = '-9999px';
            textArea.style.top = '-9999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            const success = document.execCommand('copy');
            document.body.removeChild(textArea);
            if (success) {
                this.showToast('Direct link copied to clipboard');
            } else {
                this.showToast('Failed to copy link', 'error');
            }
        },

        // Navigation with unsaved changes check
        goBack() {
            if (this.hasUnsavedChanges) {
                this.unsavedWarningModal = true;
            } else {
                this.exitEditor();
            }
        },

        async saveAndGoBack() {
            await this.savePlaylist();
            this.unsavedWarningModal = false;
            this.exitEditor();
        },

        discardAndGoBack() {
            this.hasUnsavedChanges = false;
            this.unsavedWarningModal = false;
            this.exitEditor();
        },

        exitEditor() {
            this.currentView = 'home';
            this.currentPlaylist = null;
            this.channels = [];
            this.originalChannels = [];
            this.hasUnsavedChanges = false;
            this.selectedChannels = [];
            this.loadPlaylists();
        },

        // Editor
        async openEditor(playlistId) {
            this.currentView = 'editor';
            this.editorLoading = true;
            this.selectedChannels = [];
            this.searchQuery = '';
            this.filterGroup = '';
            this.hasUnsavedChanges = false;

            try {
                this.currentPlaylist = await PlaylistAPI.get(playlistId);
                this.channels = this.currentPlaylist.channels || [];
                this.originalChannels = JSON.parse(JSON.stringify(this.channels));
                this.groups = this.currentPlaylist.groups || [];
                this.filterChannels();
            } catch (error) {
                this.showToast(error.message, 'error');
                this.currentView = 'home';
            } finally {
                this.editorLoading = false;
            }
        },

        filterChannels() {
            let filtered = [...this.channels];

            if (this.searchQuery) {
                const query = this.searchQuery.toLowerCase();
                filtered = filtered.filter(c =>
                    c.name.toLowerCase().includes(query) ||
                    (c.group_title && c.group_title.toLowerCase().includes(query)) ||
                    c.stream_url.toLowerCase().includes(query)
                );
            }

            if (this.filterGroup) {
                filtered = filtered.filter(c => c.group_title === this.filterGroup);
            }

            this.filteredChannels = filtered;
        },

        expandChannel(channel) {
            this.expandedChannel = this.expandedChannel === channel.id ? null : channel.id;
        },

        // Track changes
        markAsChanged() {
            this.hasUnsavedChanges = true;
        },

        // Channel selection
        toggleChannelSelection(channelId) {
            const index = this.selectedChannels.indexOf(channelId);
            if (index === -1) {
                this.selectedChannels.push(channelId);
            } else {
                this.selectedChannels.splice(index, 1);
            }
        },

        selectAllChannels() {
            this.selectedChannels = this.filteredChannels.map(c => c.id);
        },

        // Channel CRUD
        openAddModal() {
            this.editingChannel = null;
            this.channelForm = {
                name: '',
                stream_url: '',
                group_title: '',
                tvg_logo: '',
                tvg_id: ''
            };
            this.channelModal = true;
        },

        openEditModal(channel) {
            this.editingChannel = channel;
            this.channelForm = {
                name: channel.name,
                stream_url: channel.stream_url,
                group_title: channel.group_title || '',
                tvg_logo: channel.tvg_logo || '',
                tvg_id: channel.tvg_id || ''
            };
            this.channelModal = true;
        },

        async saveChannel() {
            if (!this.currentPlaylist) return;

            const data = {
                name: this.channelForm.name,
                stream_url: this.channelForm.stream_url,
                group_title: this.channelForm.group_title || null,
                tvg_logo: this.channelForm.tvg_logo || null,
                tvg_id: this.channelForm.tvg_id || null
            };

            try {
                if (this.editingChannel) {
                    const updated = await ChannelAPI.update(
                        this.currentPlaylist.id,
                        this.editingChannel.id,
                        data
                    );
                    const index = this.channels.findIndex(c => c.id === this.editingChannel.id);
                    if (index !== -1) {
                        this.channels[index] = updated;
                    }
                    this.showToast('Channel updated');
                } else {
                    const created = await ChannelAPI.create(this.currentPlaylist.id, data);
                    this.channels.push(created);
                    if (data.group_title && !this.groups.includes(data.group_title)) {
                        this.groups.push(data.group_title);
                        this.groups.sort();
                    }
                    this.showToast('Channel added');
                }

                this.markAsChanged();
                this.filterChannels();
                this.channelModal = false;
            } catch (error) {
                this.showToast(error.message, 'error');
            }
        },

        async deleteChannel(channelId) {
            if (!this.currentPlaylist) return;

            try {
                await ChannelAPI.delete(this.currentPlaylist.id, channelId);
                this.channels = this.channels.filter(c => c.id !== channelId);
                this.markAsChanged();
                this.filterChannels();
                this.showToast('Channel deleted');
            } catch (error) {
                this.showToast(error.message, 'error');
            }
        },

        // Bulk operations
        async bulkDeleteChannels() {
            if (!this.currentPlaylist || this.selectedChannels.length === 0) return;

            try {
                await ChannelAPI.bulkDelete(this.currentPlaylist.id, this.selectedChannels);
                this.channels = this.channels.filter(c => !this.selectedChannels.includes(c.id));
                this.showToast(`Deleted ${this.selectedChannels.length} channels`);
                this.selectedChannels = [];
                this.markAsChanged();
                this.filterChannels();
            } catch (error) {
                this.showToast(error.message, 'error');
            }
        },

        async bulkMoveChannels() {
            if (!this.currentPlaylist || this.selectedChannels.length === 0 || !this.bulkMoveGroup) return;

            try {
                await ChannelAPI.bulkMove(this.currentPlaylist.id, this.selectedChannels, this.bulkMoveGroup);

                this.channels.forEach(c => {
                    if (this.selectedChannels.includes(c.id)) {
                        c.group_title = this.bulkMoveGroup;
                    }
                });

                if (!this.groups.includes(this.bulkMoveGroup)) {
                    this.groups.push(this.bulkMoveGroup);
                    this.groups.sort();
                }

                this.showToast(`Moved ${this.selectedChannels.length} channels to "${this.bulkMoveGroup}"`);
                this.selectedChannels = [];
                this.bulkMoveModal = false;
                this.bulkMoveGroup = '';
                this.markAsChanged();
                this.filterChannels();
            } catch (error) {
                this.showToast(error.message, 'error');
            }
        },

        // Save playlist (mark as saved)
        async savePlaylist() {
            if (!this.currentPlaylist) return;

            this.saving = true;

            // Small delay to show saving state
            await new Promise(resolve => setTimeout(resolve, 500));

            this.hasUnsavedChanges = false;
            this.saving = false;
            this.showToast('Playlist saved successfully!');
        }
    };
}
