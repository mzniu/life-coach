// Life Coach 前端逻辑
// WebSocket 实时通信 + API 调用

// 获取树莓派IP（自动检测当前访问地址）
const API_BASE = window.location.origin + '/api';
const socket = io(window.location.origin);

// 状态变量
let currentState = 'idle';
let recordingStartTime = null;
let timerInterval = null;
let correctionEnabled = true;  // 默认启用纠正
let correctionAvailable = false;

// ==================== WebSocket 事件监听 ====================

socket.on('connect', () => {
    console.log('[WebSocket] 已连接');
    updateWSStatus('connected');
    socket.emit('request_status');
});

socket.on('disconnect', () => {
    console.log('[WebSocket] 已断开');
    updateWSStatus('disconnected');
});

socket.on('status_update', (data) => {
    console.log('[状态更新]', data);
    currentState = data.status;
    updateStatusDisplay(data.status, data.detail || '');
});

socket.on('recording_progress', (data) => {
    console.log('[录音进度]', data);
    updateRecordingProgress(data.duration, data.word_count);
});

socket.on('processing_progress', (data) => {
    console.log('[转写进度]', data);
    updateProcessingProgress(data.progress, data.message);
});

socket.on('recording_complete', (data) => {
    console.log('[录音完成]', data);
    showRecordingComplete(data);
    refreshRecordings();
    refreshSystemStatus();
    
    // 如果有纠正信息，在控制台输出
    if (data.correction_applied) {
        console.log('[文本纠错] 已应用', data.correction_changes);
    }
});

socket.on('error_occurred', (data) => {
    console.error('[错误]', data);
    showError(data.error);
});

// ==================== 初始化 ====================

window.addEventListener('DOMContentLoaded', () => {
    console.log('[页面加载] 初始化...');
    refreshSystemStatus();
    refreshRecordings();
    checkCorrectionStatus();
    
    // 定期刷新状态（每10秒）
    setInterval(refreshSystemStatus, 10000);
});

// ==================== API 调用 ====================

async function apiCall(endpoint, method = 'GET', body = null) {
    try {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        if (body) {
            options.body = JSON.stringify(body);
        }
        
        const response = await fetch(API_BASE + endpoint, options);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error?.message || '请求失败');
        }
        
        return data;
    } catch (error) {
        console.error('[API错误]', error);
        showError(error.message);
        throw error;
    }
}

// ==================== 录音控制 ====================

async function startRecording() {
    console.log('[操作] 开始录音');
    try {
        const result = await apiCall('/recording/start', 'POST');
        console.log('[录音开始]', result);
        
        // 更新按钮状态
        document.getElementById('btn-start').disabled = true;
        document.getElementById('btn-stop').disabled = false;
        document.getElementById('btn-cancel').disabled = false;
        
        // 开始计时
        recordingStartTime = Date.now();
        startTimer();
        
    } catch (error) {
        console.error('[录音失败]', error);
    }
}

async function stopRecording() {
    console.log('[操作] 停止录音');
    try {
        const result = await apiCall('/recording/stop', 'POST');
        console.log('[录音停止]', result);
        
        // 更新按钮状态
        document.getElementById('btn-start').disabled = true;
        document.getElementById('btn-stop').disabled = true;
        document.getElementById('btn-cancel').disabled = true;
        
        // 停止计时
        stopTimer();
        
        // 显示进度条
        showProgressBar();
        
        // 记录转写开始时间
        window.transcribeStartTime = Date.now();
        
        // 重置转写内容显示
        document.getElementById('transcribe-content').textContent = '';
        
    } catch (error) {
        console.error('[停止失败]', error);
    }
}

async function cancelRecording() {
    if (!confirm('确认取消当前录音？')) {
        return;
    }
    
    console.log('[操作] 取消录音');
    try {
        const result = await apiCall('/recording/cancel', 'POST');
        console.log('[录音取消]', result);
        
        // 重置按钮状态
        resetControls();
        stopTimer();
        hideProgressBar();
        
    } catch (error) {
        console.error('[取消失败]', error);
    }
}

// ==================== 录音列表 ====================

async function refreshRecordings() {
    console.log('[刷新] 录音列表');
    try {
        const result = await apiCall('/recordings?limit=10');
        displayRecordings(result.recordings || []);
    } catch (error) {
        console.error('[刷新失败]', error);
    }
}

function displayRecordings(recordings) {
    const container = document.getElementById('recordings-list');
    
    if (recordings.length === 0) {
        container.innerHTML = '<p class="loading">暂无录音记录</p>';
        return;
    }
    
    container.innerHTML = recordings.map(rec => {
        const hasCorrectedText = rec.text_corrected && rec.text_corrected !== rec.text_original;
        const displayText = hasCorrectedText ? rec.text_corrected : (rec.preview || '');
        
        return `
        <div class="recording-item" id="rec-${rec.id}">
            <div class="recording-info">
                <div class="recording-title">${rec.date} ${rec.time}</div>
                <div class="recording-meta">
                    时长: ${formatDuration(rec.duration)} | 字数: ${rec.word_count}字
                    ${hasCorrectedText ? '<span class="correction-badge">已纠错</span>' : ''}
                </div>
                <div class="recording-text">${displayText}</div>
                ${hasCorrectedText ? `<details class="recording-original"><summary>查看原始文本</summary><div class="original-text">${rec.text_original || rec.preview}</div></details>` : ''}
                <div id="correction-result-${rec.id}" class="correction-result" style="display:none;"></div>
            </div>
            <div class="recording-actions">
                <button class="btn btn-small" onclick="playRecording('${rec.id}')" title="播放录音">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M3 2v12l10-6z"></path>
                    </svg>
                </button>
                <button class="btn btn-small btn-warning" onclick="recorrectRecording('${rec.id}')" title="重新纠正">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M13.5 2l-7.5 7.5-3.5-3.5-2.5 2.5 6 6 10-10z"></path>
                    </svg>
                </button>
                <button class="btn btn-small btn-secondary" onclick="viewCorrectedText('${rec.id}')" title="查看纠正后文本">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M2 3h12v2H2zm0 4h12v2H2zm0 4h8v2H2z"></path>
                    </svg>
                </button>
                <button class="btn btn-small btn-primary" onclick="viewRecording('${rec.id}')" title="查看详情">
                    查看
                </button>
                <button class="btn btn-small btn-danger" onclick="deleteRecording('${rec.id}')" title="删除">
                    删除
                </button>
            </div>
        </div>
    `;
    }).join('');
}

async function playRecording(recordingId) {
    console.log('[播放录音]', recordingId);
    
    // 创建或获取全局音频播放器
    let audioPlayer = document.getElementById('global-audio-player');
    if (!audioPlayer) {
        audioPlayer = document.createElement('audio');
        audioPlayer.id = 'global-audio-player';
        audioPlayer.controls = true;
        audioPlayer.style.cssText = 'position:fixed;bottom:20px;left:50%;transform:translateX(-50%);z-index:1000;box-shadow:0 4px 20px rgba(0,255,0,0.3);border:2px solid #00ff00;background:#000;';
        document.body.appendChild(audioPlayer);
    }
    
    // 设置音频源并播放
    const audioUrl = `${API_BASE}/recordings/${recordingId}/audio`;
    audioPlayer.src = audioUrl;
    audioPlayer.play().catch(err => {
        console.error('[播放失败]', err);
        showModal('播放失败', '无法播放音频文件，可能该录音没有保存音频数据');
    });
}

async function viewRecording(recordingId) {
    console.log('[查看录音]', recordingId);
    try {
        const result = await apiCall(`/recordings/${recordingId}`);
        const rec = result.recording;
        
        // 使用Modal显示
        const details = `时间: ${rec.date} ${rec.time}\n时长: ${formatDuration(rec.duration)}\n字数: ${rec.word_count}字\n\n内容:\n${rec.content}`;
        showModal('录音详情', details);
    } catch (error) {
        console.error('[查看失败]', error);
    }
}

async function deleteRecording(recordingId) {
    if (!confirm('确认删除此录音？')) {
        return;
    }
    
    console.log('[删除录音]', recordingId);
    try {
        await apiCall(`/recordings/${recordingId}`, 'DELETE');
        refreshRecordings();
        showSuccess('录音已删除');
    } catch (error) {
        console.error('[删除失败]', error);
    }
}

// ==================== 系统状态刷新 ====================

async function refreshSystemStatus() {
    try {
        const status = await apiCall('/status');
        
        // 更新统计信息
        document.getElementById('today-count').textContent = status.stats.today_count;
        document.getElementById('storage-left').textContent = (status.stats.storage_left_gb || 0).toFixed(1) + ' GB';
        
        // 更新硬件状态
        updateHardwareStatus('mic', status.hardware.mic_connected || true);
        updateHardwareStatus('oled-left', status.hardware.oled || true);
        updateHardwareStatus('oled-right', status.hardware.oled || true);
        
    } catch (error) {
        console.error('[状态刷新失败]', error);
    }
}

// ==================== UI 更新函数 ====================

function updateStatusDisplay(status, detail) {
    const iconMap = {
        'idle': '⏸️',
        'recording': '🔴',
        'processing': '⚙️',
        'done': '✅',
        'error': '❌'
    };
    
    const textMap = {
        'idle': '待机中',
        'recording': '录音中',
        'processing': '转写中',
        'done': '已完成',
        'error': '错误'
    };
    
    document.getElementById('status-icon').textContent = iconMap[status] || '❓';
    document.getElementById('status-text').textContent = textMap[status] || status;
    document.getElementById('status-detail').textContent = detail;
    
    // 根据状态更新按钮
    if (status === 'idle' || status === 'done') {
        resetControls();
    }
}

function updateRecordingProgress(duration, wordCount) {
    document.getElementById('recording-duration').textContent = formatDuration(duration);
    document.getElementById('word-count').textContent = wordCount;
}

function updateProcessingProgress(progress, message) {
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const transcribeContent = document.getElementById('transcribe-content');
    
    // 更新进度条
    progressBar.style.width = progress + '%';
    progressText.textContent = `转写中 ${progress}%`;
    
    // 显示实时转写内容
    if (message) {
        transcribeContent.textContent = message;
    }
}

function showProgressBar() {
    document.getElementById('progress-section').style.display = 'block';
    document.getElementById('progress-bar').style.width = '0%';
}

function hideProgressBar() {
    document.getElementById('progress-section').style.display = 'none';
}

function showRecordingComplete(data) {
    // 计算转写耗时
    let transcribeTimeText = '';
    if (window.transcribeStartTime) {
        const transcribeTime = (Date.now() - window.transcribeStartTime) / 1000;
        transcribeTimeText = `，转写耗时 ${transcribeTime.toFixed(1)}秒`;
        window.transcribeStartTime = null;
    }
    
    // 纠正信息
    let correctionText = '';
    if (data.correction_applied && data.correction_changes) {
        // 格式化changes
        let changesDisplay = '';
        if (typeof data.correction_changes === 'string') {
            changesDisplay = data.correction_changes;
        } else if (Array.isArray(data.correction_changes)) {
            changesDisplay = data.correction_changes.map(c => c.description).join('；');
        } else {
            changesDisplay = JSON.stringify(data.correction_changes);
        }
        correctionText = `\n✓ 文本纠错: ${changesDisplay}`;
    } else if (correctionEnabled && !data.correction_applied) {
        correctionText = '\n○ 文本纠错: 无需修改';
    }
    
    hideProgressBar();
    showSuccess(`录音完成！共 ${data.word_count} 字，时长 ${formatDuration(data.duration)}${transcribeTimeText}${correctionText}`);
}

function resetControls() {
    document.getElementById('btn-start').disabled = false;
    document.getElementById('btn-stop').disabled = true;
    document.getElementById('btn-cancel').disabled = true;
    document.getElementById('recording-duration').textContent = '00:00';
    document.getElementById('word-count').textContent = '0';
}

function updateHardwareStatus(device, connected) {
    const element = document.getElementById('hw-' + device);
    if (connected) {
        element.textContent = '✅ 正常';
        element.className = 'status-badge status-connected';
    } else {
        element.textContent = '❌ 断开';
        element.className = 'status-badge status-disconnected';
    }
}

function updateWSStatus(status) {
    const element = document.getElementById('ws-status');
    const statusMap = {
        'connected': { text: '✅ 已连接', class: 'status-connected' },
        'disconnected': { text: '❌ 已断开', class: 'status-disconnected' },
        'connecting': { text: '🔄 连接中...', class: 'status-connecting' }
    };
    
    const info = statusMap[status] || statusMap.connecting;
    element.textContent = info.text;
    element.className = 'status-badge ' + info.class;
}

// ==================== 计时器 ====================

function startTimer() {
    timerInterval = setInterval(() => {
        if (recordingStartTime) {
            const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
            document.getElementById('recording-duration').textContent = formatDuration(elapsed);
        }
    }, 1000);
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
    recordingStartTime = null;
}

// ==================== 工具函数 ====================

function formatDuration(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function showModal(title, body) {
    const modal = document.getElementById('messageModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalBody = document.getElementById('modalBody');
    
    modalTitle.textContent = title;
    modalBody.textContent = body;
    modal.style.display = 'block';
    
    // 点击modal外部关闭
    modal.onclick = function(event) {
        if (event.target === modal) {
            closeModal();
        }
    }
}

function closeModal() {
    document.getElementById('messageModal').style.display = 'none';
}

function showSuccess(message) {
    showModal('成功', '✅ ' + message);
}

function showError(message) {
    showModal('错误', '❌ ' + message);
}

// ==================== 文本纠错功能 ====================

async function checkCorrectionStatus() {
    try {
        const result = await apiCall('/correct_text/stats');
        correctionAvailable = result.model_loaded !== false;
        updateCorrectionUI();
        console.log('[纠错状态]', correctionAvailable ? '可用' : '不可用');
    } catch (error) {
        console.log('[纠错功能] 未启用或不可用');
        correctionAvailable = false;
        updateCorrectionUI();
    }
}

function toggleCorrection() {
    const checkbox = document.getElementById('correction-enabled');
    correctionEnabled = checkbox.checked;
    updateCorrectionUI();
    console.log('[纠错开关]', correctionEnabled ? '已启用' : '已禁用');
}

function updateCorrectionUI() {
    const checkbox = document.getElementById('correction-enabled');
    const status = document.getElementById('correction-status');
    
    if (!correctionAvailable) {
        checkbox.disabled = true;
        checkbox.checked = false;
        correctionEnabled = false;
        status.textContent = '(模型未加载)';
        status.className = 'correction-status unavailable';
    } else {
        checkbox.disabled = false;
        if (correctionEnabled) {
            status.textContent = '✓ 已启用';
            status.className = 'correction-status enabled';
        } else {
            status.textContent = '';
            status.className = 'correction-status';
        }
    }
}

// ==================== 日志功能 ====================

function addLog(message, type = 'info') {
    const logContent = document.getElementById('log-content');
    const timestamp = new Date().toLocaleTimeString('zh-CN', { hour12: false });
    
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry log-${type}`;
    logEntry.innerHTML = `<span class="log-timestamp">[${timestamp}]</span>${message}`;
    
    logContent.appendChild(logEntry);
    logContent.scrollTop = logContent.scrollHeight;
    
    // 限制日志条数
    const maxLogs = 500;
    while (logContent.children.length > maxLogs) {
        logContent.removeChild(logContent.firstChild);
    }
}

function clearLogs() {
    const logContent = document.getElementById('log-content');
    logContent.innerHTML = '';
    addLog('日志已清空', 'info');
}

// 拦截console.log并显示到日志窗口
const originalConsoleLog = console.log;
console.log = function(...args) {
    originalConsoleLog.apply(console, args);
    const message = args.map(arg => 
        typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
    ).join(' ');
    addLog(message, 'info');
};

const originalConsoleError = console.error;
console.error = function(...args) {
    originalConsoleError.apply(console, args);
    const message = args.map(arg => 
        typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
    ).join(' ');
    addLog(message, 'error');
};

// ==================== 重新纠正功能 ====================

async function recorrectRecording(recordingId) {
    addLog(`开始重新纠正录音: ${recordingId}`, 'info');
    
    try {
        // 获取录音详情
        const recResult = await apiCall(`/recordings/${recordingId}`);
        const recording = recResult.recording;
        
        if (!recording || !recording.content) {
            addLog('无法获取录音内容', 'error');
            showModal('错误', '无法获取录音内容');
            return;
        }
        
        const originalText = recording.content;
        addLog(`原始文本: ${originalText.substring(0, 50)}...`, 'info');
        
        // 调用纠正API
        addLog('调用文本纠正API...', 'info');
        const correctionResult = await apiCall('/correct_text', 'POST', { text: originalText });
        
        if (!correctionResult.success) {
            addLog(`纠正失败: ${correctionResult.error}`, 'error');
            showModal('纠正失败', correctionResult.error || '未知错误');
            return;
        }
        
        const correctedText = correctionResult.corrected;
        const changed = correctionResult.changed;
        const changes = correctionResult.changes;
        
        // 格式化changes为易读文本
        let changesText = '';
        if (Array.isArray(changes)) {
            changesText = changes.map(change => change.description).join('；');
        } else if (typeof changes === 'string') {
            changesText = changes;
        } else {
            changesText = JSON.stringify(changes);
        }
        
        // 保存纠正后文本到文件
        if (changed) {
            try {
                await apiCall(`/recordings/${recordingId}/corrected`, 'POST', {
                    corrected_text: correctedText,
                    changes: changesText
                });
                addLog(`✓ 纠正文本已保存: ${recordingId}.corrected.txt`, 'success');
            } catch (error) {
                addLog(`⚠ 保存纠正文本失败: ${error.message}`, 'warning');
            }
        }
        
        // 显示结果
        const resultDiv = document.getElementById(`correction-result-${recordingId}`);
        if (resultDiv) {
            if (changed) {
                resultDiv.innerHTML = `
                    <div style="margin-top: 8px; padding: 8px; background: #0a3a0a; border-left: 2px solid #00ff00;">
                        <strong>✓ 纠正详情:</strong> ${changesText}<br>
                        <strong>纠正后文本:</strong> ${correctedText}<br>
                        <small style="color: #888;">⏱ 耗时: ${correctionResult.time_ms}ms | 来源: ${correctionResult.from_cache ? '🔄 缓存' : '🤖 模型'}</small>
                    </div>
                `;
                resultDiv.style.display = 'block';
                addLog(`✓ 纠正完成: ${changesText}`, 'success');
            } else {
                resultDiv.innerHTML = `
                    <div style="margin-top: 8px; padding: 8px; background: #3a3a0a; border-left: 2px solid #ffff00;">
                        <strong>纠正结果:</strong> 文本无需修改<br>
                        <small style="color: #888;">耗时: ${correctionResult.time_ms}ms</small>
                    </div>
                `;
                resultDiv.style.display = 'block';
                addLog('纠正完成: 文本无需修改', 'info');
            }
        }
        
        showSuccess(`纠正完成！${changed ? '已发现并修正问题' : '文本无需修改'}`);
        
    } catch (error) {
        addLog(`纠正失败: ${error.message}`, 'error');
        console.error('[重新纠正失败]', error);
        showModal('纠正失败', error.message || '网络请求失败');
    }
}

// 查看纠正后文本
async function viewCorrectedText(recordingId) {
    addLog(`查看纠正后文本: ${recordingId}`, 'info');
    
    try {
        const result = await apiCall(`/recordings/${recordingId}/corrected`);
        
        if (result.success) {
            showModal('纠正后文本', result.corrected_text);
            addLog('✓ 成功加载纠正后文本', 'success');
        } else {
            showModal('提示', '该录音暂无纠正后文本。请先点击“重新纠正”按钮进行纠错。');
            addLog('⚠ 未找到纠正后文本', 'warning');
        }
    } catch (error) {
        addLog(`✗ 获取纠正文本失败: ${error.message}`, 'error');
        showModal('错误', '无法加载纠正后文本');
    }
}

// 初始化时添加欢迎日志
addLog('Life Coach 监控面板已加载', 'success');
addLog('WebSocket 连接中...', 'info');
