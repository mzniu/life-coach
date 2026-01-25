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

# 尝试导入psutil用于系统监控
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("[警告] psutil未安装，系统监控功能将被禁用")

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
        self.realtime_transcriber = None  # 实时转录管理器
        self.accumulated_text = ""  # 实时累积的文本
        
        # 统计信息
        self.today_count = 0  # 今日录音次数
        self.today_duration = 0  # 今日录音时长(秒)
        self.last_transcript = ""  # 最近一次转录内容
        
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
            from src.realtime_transcriber import RealtimeTranscriber
            
            self.display = DisplayController()
            self.buttons = ButtonHandler()
            # AudioRecorder启用实时分段和VAD
            self.recorder = AudioRecorder(
                realtime_transcribe=True,  # 启用VAD和实时分段
                segment_callback=self._on_audio_segment
            )
            self.asr = ASREngine()
            self.storage = FileStorage()
            self.voiceprint = VoiceprintEngine()
            
            # 创建实时转录器（不立即启动）
            self.realtime_transcriber = RealtimeTranscriber(
                asr_engine=self.asr,
                callback=self._on_segment_transcribed
            )
            
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
            
            # 启用实时转录（根据配置）
            realtime_enabled = getattr(sys.modules['src.config'], 'REALTIME_TRANSCRIBE_ENABLED', True)
            print(f"[调试] REALTIME_TRANSCRIBE_ENABLED = {realtime_enabled}")
            if realtime_enabled:
                print("[实时转录] 启用实时转录模式")
                self.recorder.realtime_transcribe = True
                print(f"[调试] realtime_transcriber 对象: {self.realtime_transcriber}")
                self.realtime_transcriber.start()
                print(f"[调试] realtime_transcriber.is_running = {self.realtime_transcriber.is_running}")
                self.accumulated_text = ""
            else:
                print("[实时转录] 已禁用实时转录")
                self.recorder.realtime_transcribe = False
            
            self.recorder.start()
            
            if self.display:
                self.display.update_status("录音中", recording=True)
            
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
            
            # 停止实时转录器
            has_realtime_text = False
            if self.realtime_transcriber and self.realtime_transcriber.is_running:
                print("[实时转录] 停止实时转录器...")
                self.realtime_transcriber.stop()
                has_realtime_text = len(self.accumulated_text) > 0
                print(f"[实时转录] 已累积文本: {len(self.accumulated_text)} 字")
            
            if self.display:
                self.display.update_status("处理中")
            
            self.state = AppState.PROCESSING
            self.recording_duration = self.recorder.get_duration()
            
            # 如果有实时转录结果，直接使用；否则需要转写整个音频
            if has_realtime_text:
                print(f"[录音] 停止录音，使用实时转录结果（跳过重新转写）")
                api_server.broadcast_status_update(self.state, "正在纠错...")
                threading.Thread(target=self._process_realtime_text, args=(audio_data,), daemon=True).start()
            else:
                print(f"[录音] 停止录音，开始完整转写")
                api_server.broadcast_status_update(self.state, "正在转写...")
                threading.Thread(target=self._transcribe_recording, args=(audio_data,), daemon=True).start()
            
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
                self.display.update_status("已取消")
            
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
            self.display.update_status("已完成", detail=f"已保存 {self.word_count}字")
        
        api_server.broadcast_recording_complete(
            self.recording_id,
            self.word_count,
            self.recording_duration,
            correction_info
        )
        
        self.state = AppState.DONE
        api_server.broadcast_status_update(self.state, f"已保存 共{self.word_count}字")
        
        # 更新今日统计和最近转录
        self.today_count += 1
        self.today_duration += self.recording_duration
        self.last_transcript = content[:50] if content else ""
        
        # 3秒后自动重置为待机状态
        import time
        time.sleep(3)
        self.state = AppState.IDLE
        api_server.broadcast_status_update(self.state, "就绪")
        if self.display:
            self.display.update_status("就绪")
            # 切换回仪表盘模式
            self.display.switch_to_dashboard_mode()
    
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
                self.display.update_status("录音中", recording=True, 
                    duration=self.recording_duration, word_count=self.word_count)
            
            api_server.broadcast_recording_progress(
                self.recording_duration,
                self.word_count  # 使用实时字数而不是recording_id
            )
            
            time.sleep(1)
    
    def _process_realtime_text(self, audio_data):
        """处理实时转录的文本（仅纠错）"""
        try:
            print(f"[处理] 使用实时转录文本，开始纠错...")
            
            # 使用累积的实时转录文本
            content = self.accumulated_text
            
            # 进行文本纠错
            correction_info = None
            if self.asr.text_corrector is not None:
                print(f"[纠错] 开始纠错实时转录文本...")
                try:
                    correction_result = self.asr.text_corrector.correct(content)
                    
                    if correction_result['success'] and correction_result['changed']:
                        print(f"[纠错] 完成: {correction_result['time_ms']}ms")
                        print(f"[纠错] 原文: {content}")
                        print(f"[纠错] 纠正: {correction_result['corrected']}")
                        content = correction_result['corrected']
                        correction_info = {
                            'applied': True,
                            'changes': correction_result['changes'],
                            'time_ms': correction_result['time_ms']
                        }
                    else:
                        print(f"[纠错] 无需修改")
                except Exception as e:
                    print(f"[纠错警告] 纠错失败: {e}")
            
            self.word_count = len(content)
            self._finish_recording(content, audio_data, correction_info)
            
        except Exception as e:
            print(f"[错误] 处理实时转录文本失败: {e}")
            self.state = AppState.ERROR
            api_server.broadcast_error("处理失败", str(e))
            
            import time
            time.sleep(5)
            self.state = AppState.IDLE
            api_server.broadcast_status_update(self.state, "就绪")
            if self.display:
                self.display.update_status("就绪")
    
    def _transcribe_recording(self, audio_data):
        """转写录音（完整音频转写）"""
        try:
            print(f"[转写] 开始完整转写...")
            
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
                self.display.update_status("就绪")
    
    def _on_audio_segment(self, audio_segment, metadata):
        """音频分段回调 - 将音频段添加到转录队列"""
        print(f"[调试] _on_audio_segment 被调用: realtime_transcriber={self.realtime_transcriber is not None}, is_running={self.realtime_transcriber.is_running if self.realtime_transcriber else 'N/A'}")
        if self.realtime_transcriber and self.realtime_transcriber.is_running:
            print(f"[实时转录] 收到音频段 {metadata.get('segment_index')}，长度: {len(audio_segment)} 样本")
            
            # 广播到前端
            api_server.broadcast_log(
                f"[VAD] 第 {metadata.get('segment_index')} 段已提交转录队列（时长: {metadata.get('duration', 0):.1f}秒）",
                'info'
            )
            
            self.realtime_transcriber.add_segment(audio_segment, metadata)
    
    def _on_segment_transcribed(self, text, metadata):
        """转录结果回调 - 通过WebSocket推送给前端"""
        try:
            self.accumulated_text += text
            self.word_count = len(self.accumulated_text)
            
            segment_idx = metadata.get('segment_index', 0)
            transcribe_time = metadata.get('transcribe_time', 0)
            
            print(f"[实时转录] 推送第 {segment_idx} 段: {text[:50]}... (耗时: {transcribe_time:.2f}秒)")
            
            # 广播日志
            api_server.broadcast_log(
                f"[转录完成] 第 {segment_idx} 段: \"{text[:20]}...\" ({transcribe_time:.2f}秒)",
                'success'
            )
            
            # 通过WebSocket推送实时转录结果
            api_server.broadcast_realtime_transcript(
                segment=text,
                full_text=self.accumulated_text,
                segment_index=segment_idx,
                transcribe_time=transcribe_time,
                total_segments=metadata.get('total_segments', 0)
            )
            
        except Exception as e:
            print(f"[实时转录错误] 回调异常: {e}")
            import traceback
            traceback.print_exc()
    
    def shutdown(self):
        """关闭程序"""
        print("[主程序] 准备关闭...")
        
        # 停止实时转录器
        if self.realtime_transcriber:
            self.realtime_transcriber.stop()
        
        if self.recorder:
            self.recorder.cleanup()
        if self.display:
            self.display.cleanup()
        if self.buttons:
            self.buttons.cleanup()
        
        print("[主程序] 已关闭")
        os._exit(0)
    
    def _get_system_stats(self):
        """获取系统统计信息"""
        stats = {
            'recording_status': '待机',
            'duration': 0,
            'word_count': 0,
            'cpu_temp': 0,
            'memory_usage': 0,
            'today_count': self.today_count,
            'today_duration': self.today_duration,
            'last_transcript': self.last_transcript
        }
        
        # 更新录音状态
        if self.state == AppState.RECORDING:
            stats['recording_status'] = '录音中'
            stats['duration'] = self.recording_duration
            stats['word_count'] = self.word_count
        elif self.state == AppState.PROCESSING:
            stats['recording_status'] = '处理中'
        elif self.state == AppState.DONE:
            stats['recording_status'] = '已完成'
            stats['word_count'] = self.word_count
        
        # CPU温度
        if PSUTIL_AVAILABLE:
            try:
                # 树莓派CPU温度
                if os.path.exists('/sys/class/thermal/thermal_zone0/temp'):
                    with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                        temp = int(f.read().strip()) / 1000
                        stats['cpu_temp'] = temp
                else:
                    # 其他系统尝试用psutil
                    temps = psutil.sensors_temperatures()
                    if temps:
                        for name, entries in temps.items():
                            if entries:
                                stats['cpu_temp'] = entries[0].current
                                break
            except Exception as e:
                pass
        
        # 内存使用率
        if PSUTIL_AVAILABLE:
            try:
                mem = psutil.virtual_memory()
                stats['memory_usage'] = mem.percent
            except Exception as e:
                pass
        
        return stats
    
    def _update_today_stats(self):
        """更新今日统计信息（从存储中读取）"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            recordings = self.storage.query(date=today, limit=100)
            
            self.today_count = len(recordings)
            self.today_duration = sum(r.get('duration', 0) for r in recordings)
            
            # 获取最近一次转录
            if recordings:
                latest = recordings[0]  # 假设按时间倒序
                self.last_transcript = latest.get('content', '')[:50]  # 截取前50字符
        except Exception as e:
            print(f"[统计] 更新今日统计失败: {e}")
    
    def run(self):
        """启动主循环"""
        print("[主程序] 启动主循环...")
        print("[按钮] K1=开始/停止录音, K4长按3秒=退出")
        
        # 初始更新统计信息
        self._update_today_stats()
        
        last_stats_update = 0  # 上次更新统计的时间
        
        try:
            while True:
                # 检测K1按钮 - 开始/停止录音
                if self.buttons.k1_pressed():
                    print(f"[按钮] K1触发，当前状态: {self.state}")
                    
                    if self.state == AppState.IDLE:
                        # 开始录音
                        print("[按钮] 触发开始录音")
                        try:
                            result = self.start_recording()
                            if result.get('success'):
                                print(f"[按钮] 录音已开始: {result.get('recording_id')}")
                        except Exception as e:
                            print(f"[按钮] 启动录音失败: {e}")
                    
                    elif self.state == AppState.RECORDING:
                        # 停止录音
                        print("[按钮] 触发停止录音")
                        try:
                            result = self.stop_recording()
                            if result.get('success'):
                                print(f"[按钮] 录音已停止")
                        except Exception as e:
                            print(f"[按钮] 停止录音失败: {e}")
                
                # 检测K4长按 - 退出程序
                if self.buttons.k4_long_pressed():
                    print("[按钮] K4长按触发，准备退出...")
                    self.shutdown()
                    break
                
                # 定期更新仪表盘统计信息 (每5秒)
                current_time = time.time()
                if current_time - last_stats_update >= 5:
                    last_stats_update = current_time
                    
                    # 重新加载今日统计（可能有新的录音）
                    self._update_today_stats()
                    
                    # 获取系统统计
                    stats = self._get_system_stats()
                    
                    # 更新仪表盘显示
                    if self.display and self.display.enabled:
                        self.display.update_dashboard(**stats)
                
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
