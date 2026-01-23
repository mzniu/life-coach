"""
Flask Web API 服务
提供 RESTful API 和 WebSocket 实时通信
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os
import sys

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

def broadcast_recording_complete(recording_id, word_count, duration):
    """广播录音完成"""
    socketio.emit('recording_complete', {
        'recording_id': recording_id,
        'word_count': word_count,
        'duration': duration
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
