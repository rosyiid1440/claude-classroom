class ClassroomManager {
    constructor() {
        this.socket = io();
        this.clients = new Map();
        this.selectedClient = null;
        this.remoteControlActive = false;
        this.fileManagerActive = false;

        this.initializeEventListeners();
        this.startTimeUpdate();
    }

    initializeEventListeners() {
        // Socket events
        this.socket.on('connect', () => {
            console.log('Connected to server');
        });

        this.socket.on('client_connected', (data) => {
            this.addClient(data.client_id, data.client_info);
        });

        this.socket.on('client_status_update', (data) => {
            this.updateClientStatus(data.client_id, data.status);
        });

        this.socket.on('screenshot_update', (data) => {
            this.updateScreenshot(data.client_id, data.thumbnail);
        });

        this.socket.on('client_list', (clients) => {
            this.clients.clear();
            clients.forEach(client => {
                this.addClient(client.id, client.info);
            });
        });

        this.socket.on('message_reply', (data) => {
            this.showNotification(`Reply from ${data.client_id}: ${data.message}`);
        });

        this.socket.on('program_result', (data) => {
            this.showProgramResult(data.client_id, data.result);
        });

        // UI event listeners
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.refreshClients();
        });

        document.getElementById('broadcastBtn').addEventListener('click', () => {
            this.showMessageModal('all');
        });

        document.getElementById('powerControlBtn').addEventListener('click', () => {
            this.showPowerControlModal();
        });

        document.getElementById('fileManagerBtn').addEventListener('click', () => {
            this.showFileManagerModal();
        });

        // Modal event listeners
        this.setupModalListeners();
    }

    setupModalListeners() {
        // Message modal
        const messageModal = document.getElementById('messageModal');
        const sendMessageBtn = document.getElementById('sendMessageBtn');
        const cancelMessageBtn = document.getElementById('cancelMessageBtn');

        sendMessageBtn.addEventListener('click', () => {
            this.sendMessage();
        });

        cancelMessageBtn.addEventListener('click', () => {
            this.hideModal('messageModal');
        });

        // Remote control modal
        const remoteControlModal = document.getElementById('remoteControlModal');
        const stopRemoteBtn = document.getElementById('stopRemoteBtn');
        const remoteScreen = document.getElementById('remoteScreen');

        stopRemoteBtn.addEventListener('click', () => {
            this.stopRemoteControl();
        });

        remoteScreen.addEventListener('click', (e) => {
            this.handleRemoteClick(e);
        });

        remoteScreen.addEventListener('keydown', (e) => {
            this.handleRemoteKeyboard(e);
        });

        // File manager modal
        const navigateBtn = document.getElementById('navigateBtn');
        const uploadFileBtn = document.getElementById('uploadFileBtn');
        const createFolderBtn = document.getElementById('createFolderBtn');
        const deleteFileBtn = document.getElementById('deleteFileBtn');

        navigateBtn.addEventListener('click', () => {
            this.navigateToPath();
        });

        uploadFileBtn.addEventListener('click', () => {
            this.uploadFile();
        });

        createFolderBtn.addEventListener('click', () => {
            this.createFolder();
        });

        deleteFileBtn.addEventListener('click', () => {
            this.deleteSelected();
        });

        // Close modal listeners
        document.querySelectorAll('.close').forEach(closeBtn => {
            closeBtn.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                modal.style.display = 'none';
            });
        });

        // Close modal on outside click
        window.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                e.target.style.display = 'none';
            }
        });
    }

    addClient(clientId, clientInfo) {
        this.clients.set(clientId, {
            id: clientId,
            info: clientInfo,
            status: 'online',
            screenshot: null
        });
        this.renderClients();
    }

    updateClientStatus(clientId, status) {
        if (this.clients.has(clientId)) {
            this.clients.get(clientId).status = status;
            this.renderClients();
        }
    }

    updateScreenshot(clientId, thumbnail) {
        if (this.clients.has(clientId)) {
            this.clients.get(clientId).screenshot = thumbnail;
            this.renderClients();
        }
    }

    renderClients() {
        const clientGrid = document.getElementById('clientGrid');
        const clientCount = document.getElementById('clientCount');

        clientGrid.innerHTML = '';
        clientCount.textContent = `${this.clients.size} clients connected`;

        this.clients.forEach((client, clientId) => {
            const clientCard = this.createClientCard(clientId, client);
            clientGrid.appendChild(clientCard);
        });
    }

    createClientCard(clientId, client) {
        const card = document.createElement('div');
        card.className = `client-card ${client.status}`;

        const screenshotSrc = client.screenshot
            ? `data:image/jpeg;base64,${client.screenshot}`
            : '/static/images/no-screenshot.png';

        card.innerHTML = `
            <div class="client-header">
                <div class="client-name">${client.info.hostname}</div>
                <div class="client-status ${client.status}">${client.status}</div>
            </div>
            <div class="client-screenshot">
                <img src="${screenshotSrc}" alt="Screenshot" 
                     onerror="this.src='/static/images/no-screenshot.png'">
            </div>
            <div class="client-info">
                <div>IP: ${client.info.ip_address}</div>
                <div>OS: ${client.info.system} ${client.info.release}</div>
                <div>User: ${client.info.processor}</div>
            </div>
            <div class="client-controls">
                <button onclick="classroomManager.showMessageModal('${clientId}')">💬 Message</button>
                <button onclick="classroomManager.startRemoteControl('${clientId}')">🖥️ Control</button>
                <button onclick="classroomManager.showClientFileManager('${clientId}')">📁 Files</button>
                <button onclick="classroomManager.showPowerMenu('${clientId}')">⚡ Power</button>
                <button onclick="classroomManager.executeProgram('${clientId}')">🚀 Execute</button>
            </div>
        `;

        return card;
    }

    showMessageModal(clientId) {
        this.selectedClient = clientId;
        const modal = document.getElementById('messageModal');
        modal.style.display = 'block';
        document.getElementById('messageText').focus();
    }

    sendMessage() {
        const messageText = document.getElementById('messageText').value;
        if (!messageText.trim()) return;

        this.socket.emit('send_message', {
            client_id: this.selectedClient,
            message: messageText
        });

        this.hideModal('messageModal');
        document.getElementById('messageText').value = '';

        this.showNotification('Message sent successfully');
    }

    startRemoteControl(clientId) {
        this.selectedClient = clientId;
        this.remoteControlActive = true;

        const modal = document.getElementById('remoteControlModal');
        const clientName = document.getElementById('remoteClientName');

        clientName.textContent = this.clients.get(clientId).info.hostname;
        modal.style.display = 'block';

        // Start remote control
        this.socket.emit('remote_control', {
            client_id: clientId,
            action: 'start'
        });

        // Make remote screen focusable for keyboard events
        document.getElementById('remoteScreen').setAttribute('tabindex', '0');
        document.getElementById('remoteScreen').focus();
    }

    stopRemoteControl() {
        if (!this.remoteControlActive) return;

        this.socket.emit('remote_control', {
            client_id: this.selectedClient,
            action: 'stop'
        });

        this.remoteControlActive = false;
        this.hideModal('remoteControlModal');
    }

    handleRemoteClick(e) {
        if (!this.remoteControlActive) return;

        const rect = e.target.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Calculate relative coordinates
        const relativeX = x / rect.width;
        const relativeY = y / rect.height;

        this.socket.emit('remote_input', {
            client_id: this.selectedClient,
            type: 'click',
            x: relativeX,
            y: relativeY,
            button: e.button
        });
    }

    handleRemoteKeyboard(e) {
        if (!this.remoteControlActive) return;

        e.preventDefault();

        this.socket.emit('remote_input', {
            client_id: this.selectedClient,
            type: 'key',
            key: e.key,
            keyCode: e.keyCode,
            ctrlKey: e.ctrlKey,
            altKey: e.altKey,
            shiftKey: e.shiftKey
        });
    }

    showClientFileManager(clientId) {
        this.selectedClient = clientId;
        this.fileManagerActive = true;

        const modal = document.getElementById('fileManagerModal');
        const clientName = document.getElementById('fileManagerClientName');

        clientName.textContent = this.clients.get(clientId).info.hostname;
        modal.style.display = 'block';

        // Load initial directory
        this.loadDirectory('C:\\');
    }

    loadDirectory(path) {
        document.getElementById('currentPath').value = path;

        this.socket.emit('file_operation', {
            client_id: this.selectedClient,
            operation: 'list',
            path: path
        });
    }

    showPowerMenu(clientId) {
        const actions = ['shutdown', 'restart', 'logoff', 'hibernate'];
        const action = prompt('Select power action:\n' + actions.join(', '));

        if (actions.includes(action)) {
            this.socket.emit('power_control', {
                client_id: clientId,
                action: action
            });
        }
    }

    executeProgram(clientId) {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.exe';

        input.onchange = (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    const base64Data = e.target.result.split(',')[1];

                    this.socket.emit('execute_program', {
                        client_id: clientId,
                        program_data: {
                            filename: file.name,
                            data: base64Data,
                            silent: confirm('Run silently?')
                        }
                    });
                };
                reader.readAsDataURL(file);
            }
        };

        input.click();
    }

    showPowerControlModal() {
        const action = prompt('Enter power action (shutdown/restart/logoff/hibernate):');
        if (action) {
            this.socket.emit('power_control', {
                client_id: 'all',
                action: action
            });
        }
    }

    showFileManagerModal() {
        alert('Select a specific client to access file manager');
    }

    refreshClients() {
        this.socket.emit('refresh_clients');
    }

    hideModal(modalId) {
        document.getElementById(modalId).style.display = 'none';
    }

    showNotification(message) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #4facfe;
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            z-index: 10000;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            animation: slideIn 0.3s ease-out;
        `;

        document.body.appendChild(notification);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    showProgramResult(clientId, result) {
        const message = `Program execution result from ${clientId}:\n${JSON.stringify(result, null, 2)}`;
        alert(message);
    }

    startTimeUpdate() {
        setInterval(() => {
            const now = new Date();
            document.getElementById('serverTime').textContent = now.toLocaleTimeString();
        }, 1000);
    }
}

// Initialize the classroom manager
const classroomManager = new ClassroomManager();

// Add CSS for slide-in animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`;
document.head.appendChild(style);