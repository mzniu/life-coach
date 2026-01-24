"""
Flask Web API 服务
提供 RESTful API 和 WebSocket 实时通信
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os
import sys
import time

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import *

# 创建Flask应用
app = Flask(__name__, 
            static_folder='../static',
            static_url_path='/static')
# 从环境变量读取SECRET_KEY，如果未设置则使用默认值（开发环境）
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# 启用跨域支持（前端开发必需）
CORS(app, resources={r"/api/*": {"origins": CORS_ORIGINS}})

# 启用WebSocket - 配置实时通信参数
socketio = SocketIO(
    app, 
    cors_allowed_origins=CORS_ORIGINS,
    async_mode='threading',  # 使用线程模式支持实时推送
    logger=True,  # 启用日志便于调试
    engineio_logger=True,
    ping_timeout=60,  # 增加超时时间
    ping_interval=25  # 心跳间隔
)

# 全局状态管理器（将由main.py注入）
app_manager = None

def set_app_manager(manager):
    """设置应用管理器引用"""
    global app_manager
    app_manager = manager

# ==================== 静态页面路由 ====================
@app.route('/')
def index():
    """Web监控页面"""
    return send_from_directory('../static', 'index.html')

@app.route('/api/recordings/<path:recording_id>/audio', methods=['GET'])
def get_recording_audio(recording_id):
    """获取录音音频文件"""
    if not app_manager:
        return jsonify({"success": False, "error": "服务未初始化"}), 500
    
    try:
        recording = app_manager.storage.get(recording_id)
        if not recording:
            return jsonify({"success": False, "error": "录音不存在"}), 404
        
        audio_path = recording.get('audio_path')
        if not audio_path or not os.path.exists(audio_path):
            return jsonify({"success": False, "error": "音频文件不存在"}), 404
        
        # 返回音频文件
        from flask import send_file
        return send_file(audio_path, mimetype='audio/wav')
        
    except Exception as e:
        print(f"[API错误] 获取音频失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== API 路由 ====================

@app.route('/api/status', methods=['GET'])
def get_status():
    """获取系统状态"""
    if not app_manager:
        return jsonify({"success": False, "error": "服务未初始化"}), 500
    
    status = app_manager.get_status()
    return jsonify(status)

@app.route('/api/recording/start', methods=['POST'])
def start_recording():
    """开始录音"""
    if not app_manager:
        return jsonify({"success": False, "error": "服务未初始化"}), 500
    
    result = app_manager.start_recording()
    if result['success']:
        # 广播状态更新
        socketio.emit('status_update', {
            'status': AppState.RECORDING,
            'detail': '录音已开始'
        })
        return jsonify(result)
    else:
        return jsonify(result), 400

@app.route('/api/recording/stop', methods=['POST'])
def stop_recording():
    """停止录音"""
    if not app_manager:
        return jsonify({"success": False, "error": "服务未初始化"}), 500
    
    result = app_manager.stop_recording()
    if result['success']:
        # 广播状态更新
        socketio.emit('status_update', {
            'status': AppState.PROCESSING,
            'detail': '开始转写'
        })
        return jsonify(result)
    else:
        return jsonify(result), 400

@app.route('/api/recording/cancel', methods=['POST'])
def cancel_recording():
    """取消录音"""
    if not app_manager:
        return jsonify({"success": False, "error": "服务未初始化"}), 500
    
    result = app_manager.cancel_recording()
    return jsonify(result)

@app.route('/api/recordings', methods=['GET'])
def get_recordings():
    """获取录音列表"""
    if not app_manager:
        return jsonify({"success": False, "error": "服务未初始化"}), 500
    
    date = request.args.get('date', None)
    limit = int(request.args.get('limit', 20))
    
    result = app_manager.get_recordings(date=date, limit=limit)
    return jsonify(result)

@app.route('/api/recordings/<path:recording_id>', methods=['GET'])
def get_recording_detail(recording_id):
    """获取单条录音详情"""
    if not app_manager:
        return jsonify({"success": False, "error": "服务未初始化"}), 500
    
    result = app_manager.get_recording_detail(recording_id)
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 404

@app.route('/api/recordings/<path:recording_id>', methods=['DELETE'])
def delete_recording(recording_id):
    """删除录音"""
    if not app_manager:
        return jsonify({"success": False, "error": "服务未初始化"}), 500
    
    result = app_manager.delete_recording(recording_id)
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 404

@app.route('/api/recordings/<path:recording_id>/corrected', methods=['POST'])
def save_corrected_text(recording_id):
    """保存纠正后的文本"""
    if not app_manager:
        return jsonify({"success": False, "error": "服务未初始化"}), 500
    
    try:
        data = request.json
        corrected_text = data.get('corrected_text')
        changes = data.get('changes', '')
        
        if not corrected_text:
            return jsonify({"success": False, "error": "缺少corrected_text参数"}), 400
        
        # 保存纠正后文本
        path = app_manager.storage.save_corrected(recording_id, corrected_text, changes)
        
        return jsonify({
            "success": True,
            "message": "纠正文本已保存",
            "path": path
        })
    except Exception as e:
        print(f"[API错误] 保存纠正文本失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/recordings/<path:recording_id>/corrected', methods=['GET'])
def get_corrected_text(recording_id):
    """获取纠正后的文本"""
    if not app_manager:
        return jsonify({"success": False, "error": "服务未初始化"}), 500
    
    try:
        corrected_text = app_manager.storage.get_corrected(recording_id)
        
        if corrected_text:
            return jsonify({
                "success": True,
                "corrected_text": corrected_text
            })
        else:
            return jsonify({
                "success": False,
                "error": "未找到纠正后文本"
            }), 404
    except Exception as e:
        print(f"[API错误] 获取纠正文本失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/recordings/<path:recording_id>/retranscribe', methods=['POST'])
def retranscribe_recording(recording_id):
    """重新识别录音文件"""
    if not app_manager:
        return jsonify({"success": False, "error": "服务未初始化"}), 500
    
    try:
        import sys
        print(f"[重新识别] 开始重新识别: {recording_id}", file=sys.stderr, flush=True)
        
        # 获取录音详情
        recording = app_manager.storage.get(recording_id)
        if not recording:
            return jsonify({"success": False, "error": "录音不存在"}), 404
        
        # 构建音频文件路径
        date_str, time_str = recording_id.split('/')
        audio_path = app_manager.storage.base_path / date_str / f"{time_str}.wav"
        if not audio_path.exists():
            return jsonify({"success": False, "error": "音频文件不存在"}), 404
        
        audio_path_str = str(audio_path)
        print(f"[重新识别] 音频文件: {audio_path_str}", file=sys.stderr, flush=True)
        
        # 使用ASR引擎重新识别
        if not app_manager.asr:
            return jsonify({"success": False, "error": "ASR引擎未初始化"}), 500
        
        # 转写音频文件
        import time
        start_time = time.time()
        print(f"[重新识别] 调用ASR引擎...", file=sys.stderr, flush=True)
        
        try:
            result = app_manager.asr.transcribe_file(audio_path_str)
            elapsed = time.time() - start_time
            print(f"[重新识别] ASR返回结果: {result}", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[重新识别错误] ASR调用异常: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return jsonify({"success": False, "error": f"ASR引擎异常: {e}"}), 500
        
        if not result or 'text' not in result:
            print(f"[重新识别错误] 返回结果格式错误: {result}", file=sys.stderr, flush=True)
            return jsonify({"success": False, "error": "识别结果格式错误"}), 500
        
        new_text = result['text'].strip()
        print(f"[重新识别] 识别完成，耗时: {elapsed:.2f}秒，文本长度: {len(new_text)}", file=sys.stderr, flush=True)
        
        # 保存新的识别结果（更新original_content）
        app_manager.storage.update_transcription(recording_id, new_text)
        
        return jsonify({
            "success": True,
            "text": new_text,
            "time_ms": int(elapsed * 1000),
            "message": "重新识别完成"
        })
        
    except Exception as e:
        import traceback
        print(f"[重新识别错误] {e}", file=sys.stderr, flush=True)
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== 文本纠错 API ====================

@app.route('/api/correct_text', methods=['POST'])
def correct_text():
    """
    文本纠错 API
    
    请求体:
    {
        "text": "待纠错的文本"
    }
    
    响应:
    {
        "success": true,
        "original": "原始文本",
        "corrected": "纠正后的文本",
        "changed": true,
        "changes": [...],
        "time_ms": 3245
    }
    """
    try:
        # 检查服务是否初始化
        if not app_manager:
            return jsonify({"success": False, "error": "服务未初始化"}), 500
        
        # 获取请求数据
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({
                "success": False,
                "error": "缺少参数: text"
            }), 400
        
        text = data['text']
        
        # 检查文本长度
        if not text or len(text.strip()) == 0:
            return jsonify({
                "success": False,
                "error": "文本不能为空"
            }), 400
        
        if len(text) > 5000:
            return jsonify({
                "success": False,
                "error": "文本过长（最多 5000 字符）"
            }), 400
        
        # 检查纠错功能是否启用
        from src.config import TEXT_CORRECTION_ENABLED
        if not TEXT_CORRECTION_ENABLED:
            return jsonify({
                "success": False,
                "error": "文本纠错功能未启用",
                "hint": "请在 .env 中设置 TEXT_CORRECTION_ENABLED=true"
            }), 503
        
        # 获取纠错器实例
        if not hasattr(app_manager, 'asr') or not hasattr(app_manager.asr, 'text_corrector'):
            return jsonify({
                "success": False,
                "error": "文本纠错模块未初始化"
            }), 503
        
        corrector = app_manager.asr.text_corrector
        
        if corrector is None:
            return jsonify({
                "success": False,
                "error": "文本纠错模块不可用",
                "hint": "可能是模型文件不存在或加载失败"
            }), 503
        
        # 执行纠错
        import sys
        print(f"[纠错API] 开始纠错，输入长度: {len(text)} 字符", file=sys.stderr, flush=True)
        print(f"[纠错API] 输入文本: {text[:100]}..." if len(text) > 100 else f"[纠错API] 输入文本: {text}", file=sys.stderr, flush=True)
        
        result = corrector.correct(text)
        
        # 详细日志输出
        if result.get('success'):
            corrected = result.get('corrected', '')
            changed = result.get('changed', False)
            changes = result.get('changes', [])
            time_ms = result.get('time_ms', 0)
            from_cache = result.get('from_cache', False)
            
            print(f"[纠错API] 纠错完成: 耗时={time_ms}ms, 来源={'缓存' if from_cache else '模型'}, 修改={'是' if changed else '否'}", file=sys.stderr, flush=True)
            print(f"[纠错API] 输出文本: {corrected[:100]}..." if len(corrected) > 100 else f"[纠错API] 输出文本: {corrected}", file=sys.stderr, flush=True)
            
            if changed and isinstance(changes, list):
                print(f"[纠错API] 修改详情: 共 {len(changes)} 处", file=sys.stderr, flush=True)
                for i, change in enumerate(changes[:5], 1):  # 只打印前5处修改
                    if isinstance(change, dict):
                        pos = change.get('position', '?')
                        old = change.get('original', '?')
                        new = change.get('corrected', '?')
                        confidence = change.get('confidence', 0)
                        print(f"[纠错API]   {i}. 位置{pos}: '{old}' → '{new}' (置信度: {confidence:.4f})", file=sys.stderr, flush=True)
                if len(changes) > 5:
                    print(f"[纠错API]   ... 还有 {len(changes) - 5} 处修改", file=sys.stderr, flush=True)
        else:
            error = result.get('error', '未知错误')
            print(f"[纠错API] 纠错失败: {error}", file=sys.stderr, flush=True)
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"纠错失败: {str(e)}"
        }), 500

@app.route('/api/correct_text/stats', methods=['GET'])
def get_correction_stats():
    """
    获取文本纠错统计信息
    
    响应:
    {
        "success": true,
        "stats": {
            "is_loaded": true,
            "correction_count": 42,
            "cache_hits": 10,
            ...
        }
    }
    """
    try:
        if not app_manager:
            return jsonify({"success": False, "error": "服务未初始化"}), 500
        
        # 检查纠错模块是否存在
        if not hasattr(app_manager, 'asr') or not hasattr(app_manager.asr, 'text_corrector'):
            return jsonify({
                "success": False,
                "error": "文本纠错模块未初始化"
            }), 503
        
        corrector = app_manager.asr.text_corrector
        
        if corrector is None:
            return jsonify({
                "success": True,
                "stats": {
                    "is_loaded": False,
                    "enabled": False
                }
            })
        
        stats = corrector.get_stats()
        
        return jsonify({
            "success": True,
            "stats": stats
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"获取统计信息失败: {str(e)}"
        }), 500

# ==================== 系统控制 API ====================

@app.route('/api/system/shutdown', methods=['POST'])
def shutdown_system():
    """关闭程序"""
    data = request.get_json() or {}
    if not data.get('confirm'):
        return jsonify({
            "success": False,
            "error": "需要确认参数 confirm=true"
        }), 400
    
    if app_manager:
        app_manager.shutdown()
    
    return jsonify({
        "success": True,
        "message": "程序即将关闭"
    })

# ==================== 声纹识别 API ====================

@app.route('/api/voiceprint/status', methods=['GET'])
def get_voiceprint_status():
    """获取声纹引擎状态"""
    if not app_manager:
        return jsonify({"success": False, "error": "服务未初始化"}), 500
    
    if not app_manager.voiceprint:
        return jsonify({
            "success": False,
            "error": "声纹识别模块未启用"
        }), 500
    
    status = app_manager.voiceprint.get_status()
    voiceprints = app_manager.voiceprint.list_voiceprints()
    
    return jsonify({
        "success": True,
        "status": status,
        "voiceprints": voiceprints
    })

@app.route('/api/voiceprint/register', methods=['POST'])
def register_voiceprint():
    """
    注册声纹
    Body: {
        "user_name": "张三",
        "recording_ids": ["rec_20260122_001", "rec_20260122_002"]
    }
    """
    try:
        print(f"[声纹API] 收到注册请求")
        
        if not app_manager:
            print(f"[声纹API错误] 服务未初始化")
            return jsonify({"success": False, "error": "服务未初始化"}), 500
        
        if not app_manager.voiceprint:
            print(f"[声纹API错误] 声纹模块未启用")
            return jsonify({
                "success": False,
                "error": "声纹识别模块未启用"
            }), 500
        
        data = request.json
        print(f"[声纹API] 请求数据: {data}")
        
        user_name = data.get('user_name')
        recording_ids = data.get('recording_ids', [])
        
        if not user_name:
            print(f"[声纹API错误] 缺少user_name参数")
            return jsonify({"success": False, "error": "缺少user_name参数"}), 400
        
        if len(recording_ids) < 2:
            print(f"[声纹API错误] 录音样本不足: {len(recording_ids)}")
            return jsonify({
                "success": False,
                "error": "至少需要2段录音进行声纹注册"
            }), 400
        
        print(f"[声纹API] 开始加载 {len(recording_ids)} 段音频样本")
        
        # 加载音频样本
        audio_samples = []
        for i, rec_id in enumerate(recording_ids):
            print(f"[声纹API] 正在加载样本 {i+1}/{len(recording_ids)}: {rec_id}")
            
            recording = app_manager.storage.get(rec_id)
            if not recording:
                print(f"[声纹API错误] 录音不存在: {rec_id}")
                return jsonify({
                    "success": False,
                    "error": f"录音不存在: {rec_id}"
                }), 404
            
            # 读取音频文件
            audio_path = recording.get('audio_path')
            print(f"[声纹API] 音频路径: {audio_path}")
            
            if not audio_path or not os.path.exists(audio_path):
                print(f"[声纹API错误] 音频文件不存在: {audio_path}")
                error_msg = f"录音 {rec_id} 没有音频文件。请使用新录制的音频（系统已升级，旧录音不包含.wav文件）"
                return jsonify({
                    "success": False,
                    "error": error_msg
                }), 400
            
            # 加载音频数据
            try:
                import numpy as np
                import wave
                with wave.open(audio_path, 'rb') as wf:
                    frames = wf.readframes(wf.getnframes())
                    audio_data = np.frombuffer(frames, dtype=np.int16)
                    print(f"[声纹API] 成功加载音频: 长度={len(audio_data)}")
                    audio_samples.append(audio_data)
            except Exception as e:
                print(f"[声纹API错误] 读取音频失败: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({
                    "success": False,
                    "error": f"读取音频失败: {e}"
                }), 500
        
        print(f"[声纹API] 开始注册声纹: user_name={user_name}, samples={len(audio_samples)}")
        
        # 注册声纹
        result = app_manager.voiceprint.register_voiceprint(
            user_name=user_name,
            audio_samples=audio_samples,
            sample_rate=16000
        )
        
        print(f"[声纹API] 注册结果: {result}")
        return jsonify(result)
        
    except Exception as e:
        print(f"[声纹API异常] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"服务器内部错误: {e}"
        }), 500

@app.route('/api/voiceprint/identify', methods=['POST'])
def identify_voiceprint():
    """
    识别声纹
    Body: {
        "recording_id": "rec_20260122_003"
    }
    """
    try:
        print(f"[声纹API] 收到识别请求")
        
        if not app_manager:
            return jsonify({"success": False, "error": "服务未初始化"}), 500
        
        if not app_manager.voiceprint:
            return jsonify({
                "success": False,
                "error": "声纹识别模块未启用"
            }), 500
        
        data = request.json
        recording_id = data.get('recording_id')
        
        if not recording_id:
            return jsonify({"success": False, "error": "缺少recording_id参数"}), 400
        
        print(f"[声纹API] 识别录音: {recording_id}")
        
        # 获取录音
        recording = app_manager.storage.get(recording_id)
        if not recording:
            print(f"[声纹API错误] 录音不存在: {recording_id}")
            return jsonify({
                "success": False,
                "error": "录音不存在"
            }), 404
        
        # 读取音频
        audio_path = recording.get('audio_path')
        if not audio_path or not os.path.exists(audio_path):
            print(f"[声纹API错误] 音频文件不存在: {audio_path}")
            return jsonify({
                "success": False,
                "error": "音频文件不存在"
            }), 404
        
        try:
            import numpy as np
            import wave
            with wave.open(audio_path, 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                audio_data = np.frombuffer(frames, dtype=np.int16)
            print(f"[声纹API] 成功加载音频: 长度={len(audio_data)}")
        except Exception as e:
            print(f"[声纹API错误] 读取音频失败: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "success": False,
                "error": f"读取音频失败: {e}"
            }), 500
        
        # 识别声纹
        result = app_manager.voiceprint.identify_speaker(
            audio_data=audio_data,
            sample_rate=16000,
            threshold=0.75
        )
        
        print(f"[声纹API] 识别结果: {result}")
        
        return jsonify({
            "success": True,
            "result": result
        })
        
    except Exception as e:
        print(f"[声纹API异常] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"服务器内部错误: {e}"
        }), 500

@app.route('/api/voiceprint/delete', methods=['DELETE'])
def delete_voiceprint():
    """
    删除声纹
    Body: {
        "user_name": "张三"
    }
    """
    if not app_manager:
        return jsonify({"success": False, "error": "服务未初始化"}), 500
    
    if not app_manager.voiceprint:
        return jsonify({
            "success": False,
            "error": "声纹识别模块未启用"
        }), 500
    
    data = request.json
    user_name = data.get('user_name')
    
    if not user_name:
        return jsonify({"success": False, "error": "缺少user_name参数"}), 400
    
    result = app_manager.voiceprint.delete_voiceprint(user_name)
    return jsonify(result)

# ==================== WebSocket 事件 ====================

@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    print(f"[WebSocket] 客户端已连接: {request.sid}")
    if app_manager:
        # 发送当前状态
        status = app_manager.get_status()
        emit('status_update', {
            'status': status['status'],
            'detail': '已连接'
        })

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开"""
    print(f"[WebSocket] 客户端已断开: {request.sid}")

@socketio.on('request_status')
def handle_request_status():
    """客户端请求状态"""
    if app_manager:
        status = app_manager.get_status()
        emit('status_update', {
            'status': status['status'],
            'detail': f"当前状态: {status['status']}"
        })

# ==================== 全局事件广播函数 ====================
# 供 app_manager 调用，向所有客户端广播事件

def broadcast_status_update(status, detail=""):
    """广播状态更新"""
    socketio.emit('status_update', {
        'status': status,
        'detail': detail
    })

def broadcast_recording_progress(duration, word_count):
    """广播录音进度"""
    socketio.emit('recording_progress', {
        'duration': duration,
        'word_count': word_count
    })

def broadcast_processing_progress(progress, message=""):
    """广播转写进度"""
    print(f"[WebSocket] 广播转写进度: {progress}% - {len(message)} 字")
    socketio.emit('processing_progress', {
        'progress': progress,
        'message': message
    })
    socketio.sleep(0.01)  # 确保消息发送

def broadcast_recording_complete(recording_id, word_count, duration, correction_info=None):
    """广播录音完成"""
    payload = {
        'recording_id': recording_id,
        'word_count': word_count,
        'duration': duration
    }
    
    # 添加纠正信息
    if correction_info:
        payload['correction_applied'] = correction_info.get('applied', False)
        payload['correction_changes'] = correction_info.get('changes', '')
        payload['correction_time_ms'] = correction_info.get('time_ms', 0)
    
    socketio.emit('recording_complete', payload)

def broadcast_realtime_transcript(segment, full_text, segment_index, transcribe_time=0, total_segments=0):
    """广播实时转录结果"""
    socketio.emit('realtime_transcript', {
        'segment': segment,              # 本次识别的片段
        'full_text': full_text,           # 所有片段拼接的完整文本
        'segment_index': segment_index,   # 片段序号
        'transcribe_time': transcribe_time,  # 转录耗时（秒）
        'total_segments': total_segments, # 已转录总段数
        'is_final': False                 # 是否为最终结果（录音结束）
    })
    print(f"[WebSocket] 广播实时转录: 第{segment_index}段, {len(segment)}字")
def broadcast_log(message, level='info'):
    """广播日志消息到前端"""
    socketio.emit('log_message', {
        'message': message,
        'level': level,  # info, success, warning, error
        'timestamp': time.time()
    })
def broadcast_error(error_message, error_code):
    """广播错误"""
    socketio.emit('error_occurred', {
        'error': error_message,
        'code': error_code
    })

# ==================== 启动服务 ====================

def run_server(host=WEB_HOST, port=WEB_PORT, debug=WEB_DEBUG):
    """启动Flask服务"""
    print(f"[Web服务] 启动于 http://{host}:{port}")
    # 在线程中运行时禁用reloader，避免signal错误
    socketio.run(app, host=host, port=port, debug=debug, use_reloader=False, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    run_server()
