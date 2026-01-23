"""
Life Coach 主程序
整合硬件控制、Web服务、录音转写功能
"""

import os
import sys
import time
import threading
import argparse
from datetime import datetime

# 添加src目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.config import *
from src import api_server

class LifeCoachApp:
    """Life Coach 主应用管理器"""
    
    def __init__(self):
        self.state = AppState.IDLE
        self.recording_id = None
        self.recording_duration = 0
        self.word_count = 0
        
        # 初始化各模块
        self.display = None
        self.recorder = None
        self.asr = None
        self.buttons = None
        self.storage = None
        
        print("[主程序] Life Coach 初始化...")
        self._init_modules()
        
    def _init_modules(self):
        """初始化各功能模块"""
        try:
            from src.display_controller import DisplayController
            from src.button_handler import ButtonHandler
            from src.audio_recorder_real import AudioRecorder
            from src.asr_engine_real import ASREngine
            from src.file_storage import FileStorage
            from src.voiceprint_engine import VoiceprintEngine
            
            self.display = DisplayController()
            self.buttons = ButtonHandler()
            self.recorder = AudioRecorder()
            self.asr = ASREngine()
            self.storage = FileStorage()
            self.voiceprint = VoiceprintEngine()
            
            print("[主程序] 所有模块初始化完成")
            
        except Exception as e:
            print(f"[错误] 模块初始化失败: {e}")
            raise
    
    def get_status(self):
        """获取当前状态"""
        return {
            "status": self.state,
            "recording": {
                "duration": self.recording_duration,
                "recording_id": self.recording_id
            },
            "stats": {
                "today_count": self._get_today_count(),
                "storage_left_gb": self._get_storage_left()
            },
            "hardware": {
                "oled": True,
                "gpio": True
            }
        }
    
    def _get_today_count(self):
        if self.storage:
            return self.storage.get_today_count()
        return 0
    
    def _get_storage_left(self):
        if self.storage:
            info = self.storage.get_storage_info()
            return info['free_gb']
        return 0.0
    
    def start_recording(self):
        """开始录音"""
        if self.state != AppState.IDLE:
            return {
                "success": False,
                "error": {
                    "code": ErrorCode.INVALID_STATE,
                    "message": "当前状态不允许开始录音"
                }
            }
        
        try:
            now = datetime.now()
            self.recording_id = now.strftime("%Y-%m-%d/%H-%M")
            
            self.recorder.start()
            
            if self.display:
                self.display.show_status(AppState.RECORDING, "录音中...")
            
            self.state = AppState.RECORDING
            self.recording_duration = 0
            self.word_count = 0
            
            api_server.broadcast_status_update(self.state, "录音已开始")
            threading.Thread(target=self._recording_progress_loop, daemon=True).start()
            
            print(f"[录音] 开始录音: {self.recording_id}")
            return {
                "success": True,
                "message": "录音已开始",
                "recording_id": self.recording_id
            }
            
        except Exception as e:
            print(f"[错误] 启动录音失败: {e}")
            self.state = AppState.IDLE
            return {
                "success": False,
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR,
                    "message": str(e)
                }
            }
    
    def stop_recording(self):
        """停止录音并开始转写"""
        if self.state != AppState.RECORDING:
            return {
                "success": False,
                "error": {
                    "code": ErrorCode.INVALID_STATE,
                    "message": "当前未在录音"
                }
            }
        
        try:
            audio_data = self.recorder.stop()
            
            if self.display:
                self.display.show_status(AppState.PROCESSING, "转写中...")
            
            self.state = AppState.PROCESSING
            self.recording_duration = self.recorder.get_duration()
            
            api_server.broadcast_status_update(self.state, "正在转写...")
            threading.Thread(target=self._transcribe_recording, args=(audio_data,), daemon=True).start()
            
            print(f"[录音] 停止录音，开始转写")
            
            return {
                "success": True,
                "message": "录音已停止，开始转写",
                "recording_id": self.recording_id
            }
            
        except Exception as e:
            print(f"[错误] 停止录音失败: {e}")
            return {
                "success": False,
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR,
                    "message": str(e)
                }
            }
    
    def cancel_recording(self):
        """取消当前录音"""
        if self.state != AppState.RECORDING:
            return {
                "success": False,
                "error": {
                    "code": ErrorCode.INVALID_STATE,
                    "message": "当前未在录音"
                }
            }
        
        try:
            self.recorder.cancel()
            
            if self.display:
                self.display.show_status(AppState.IDLE, "已取消")
            
            self.state = AppState.IDLE
            self.recording_id = None
            
            api_server.broadcast_status_update(self.state, "录音已取消")
            
            print(f"[录音] 已取消")
            return {
                "success": True,
                "message": "录音已取消"
            }
            
        except Exception as e:
            print(f"[错误] 取消录音失败: {e}")
            return {
                "success": False,
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR,
                    "message": str(e)
                }
            }
    
    def _finish_recording(self, content, audio_data=None, correction_info=None):
        """完成录音"""
        metadata = {
            'duration': self.recording_duration,
            'word_count': self.word_count
        }
        
        self.storage.save(self.recording_id, content, metadata)
        
        # 保存音频文件
        if audio_data is not None:
            try:
                self.storage.save_audio(self.recording_id, audio_data, sample_rate=16000)
            except Exception as e:
                print(f"[错误] 保存音频文件失败: {e}")
        
        if self.display:
            self.display.show_status(AppState.DONE, f"已保存 {self.word_count}字")
        
        api_server.broadcast_recording_complete(
            self.recording_id,
            self.word_count,
            self.recording_duration,
            correction_info
        )
        
        self.state = AppState.DONE
        api_server.broadcast_status_update(self.state, f"已保存 共{self.word_count}字")
        
        # 3秒后自动重置为待机状态
        import time
        time.sleep(3)
        self.state = AppState.IDLE
        api_server.broadcast_status_update(self.state, "就绪")
        if self.display:
            self.display.show_status(AppState.IDLE, "就绪")
    
    def get_recordings(self, date=None, limit=10):
        """获取录音列表"""
        try:
            recordings = self.storage.query(date=date, limit=limit)
            return {
                "success": True,
                "count": len(recordings),
                "recordings": recordings
            }
        except Exception as e:
            print(f"[错误] 查询录音失败: {e}")
            return {
                "success": False,
                "error": {"code": ErrorCode.INTERNAL_ERROR, "message": str(e)}
            }
    
    def get_recording_detail(self, recording_id):
        """获取录音详情"""
        try:
            recording = self.storage.get(recording_id)
            if recording:
                return {
                    "success": True,
                    "recording": recording
                }
            else:
                return {
                    "success": False,
                    "error": {
                        "code": ErrorCode.RECORDING_NOT_FOUND,
                        "message": "录音不存在"
                    }
                }
        except Exception as e:
            print(f"[错误] 获取录音详情失败: {e}")
            return {
                "success": False,
                "error": {"code": ErrorCode.INTERNAL_ERROR, "message": str(e)}
            }
    
    def delete_recording(self, recording_id):
        """删除录音"""
        try:
            if self.storage.delete(recording_id):
                return {
                    "success": True,
                    "message": "录音已删除"
                }
            else:
                return {
                    "success": False,
                    "error": {
                        "code": ErrorCode.RECORDING_NOT_FOUND,
                        "message": "录音不存在"
                    }
                }
        except Exception as e:
            print(f"[错误] 删除录音失败: {e}")
            return {
                "success": False,
                "error": {"code": ErrorCode.INTERNAL_ERROR, "message": str(e)}
            }
    
    def _recording_progress_loop(self):
        """录音进度更新循环"""
        while self.state == AppState.RECORDING:
            self.recording_duration = int(self.recorder.get_duration())
            
            if self.display:
                self.display.update_timer(self.recording_duration)
            
            api_server.broadcast_recording_progress(
                self.recording_duration,
                self.recording_id
            )
            
            time.sleep(1)
    
    def _transcribe_recording(self, audio_data):
        """转写录音"""
        try:
            print(f"[转写] 开始转写...")
            
            def progress_callback(percent, text=""):
                if self.display:
                    self.display.update_progress(percent, "转写中")
                api_server.broadcast_processing_progress(percent, text)
            
            result = self.asr.transcribe_stream(audio_data, callback=progress_callback)
            
            # 处理返回结果：可能是字符串或字典（带纠错信息）
            correction_info = None
            if isinstance(result, dict):
                # 纠错模式返回的字典
                content = result.get('text', '')
                print(f"[转写] 完成（纠错模式）: 原文 {len(result.get('text_original', ''))} 字 → 纠正后 {len(content)} 字")
                if result.get('correction_changes'):
                    print(f"[转写] 纠正详情: {result['correction_changes']}")
                    correction_info = {
                        'applied': True,
                        'changes': result['correction_changes'],
                        'time_ms': result.get('correction_time_ms', 0)
                    }
            else:
                # 普通模式返回字符串
                content = result
                print(f"[转写] 完成，共 {len(content)} 字")
            
            self.word_count = len(content)
            self._finish_recording(content, audio_data, correction_info)
            
        except Exception as e:
            print(f"[错误] 转写失败: {e}")
            self.state = AppState.ERROR
            api_server.broadcast_error("转写失败", str(e))
            
            # 5秒后自动重置为待机状态
            import time
            time.sleep(5)
            self.state = AppState.IDLE
            api_server.broadcast_status_update(self.state, "就绪")
            if self.display:
                self.display.show_status(AppState.IDLE, "就绪")
    
    def shutdown(self):
        """关闭程序"""
        print("[主程序] 准备关闭...")
        
        if self.recorder:
            self.recorder.cleanup()
        if self.display:
            self.display.cleanup()
        if self.buttons:
            self.buttons.cleanup()
        
        print("[主程序] 已关闭")
        os._exit(0)
    
    def run(self):
        """启动主循环"""
        print("[主程序] 启动主循环...")
        
        try:
            while True:
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n[主程序] 收到中断信号")
            self.shutdown()


def main():
    """主入口"""
    parser = argparse.ArgumentParser(description='Life Coach 对话记录助手')
    parser.add_argument('--host', default=WEB_HOST, help='Web服务监听地址')
    parser.add_argument('--port', type=int, default=WEB_PORT, help='Web服务端口')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    args = parser.parse_args()
    
    print("=" * 50)
    print("  Life Coach - 对话记录助手")
    print("  阶段0: 最小MVP版本")
    print("=" * 50)
    
    app = LifeCoachApp()
    
    api_server.set_app_manager(app)
    
    # 使用配置文件中的DEBUG设置，除非命令行明确指定
    debug_mode = args.debug if args.debug else WEB_DEBUG
    
    web_thread = threading.Thread(
        target=api_server.run_server,
        args=(args.host, args.port, debug_mode),
        daemon=True
    )
    web_thread.start()
    
    print(f"\n[Web服务] 已启动: http://{args.host}:{args.port} (Debug: {debug_mode})")
    print(f"[提示] 在浏览器访问上述地址查看监控面板")
    print(f"[提示] 按 Ctrl+C 退出程序\n")
    
    app.run()


if __name__ == '__main__':
    main()
