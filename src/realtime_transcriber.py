"""
实时转录管理器
负责异步处理音频分段的转录任务，避免阻塞录音线程
"""

import threading
import queue
import time
from typing import Callable, Optional, Dict, Any


class RealtimeTranscriber:
    """实时转录管理器 - 异步处理音频分段转录"""
    
    def __init__(self, asr_engine, callback: Callable[[str, Dict], None]):
        """
        初始化实时转录器
        
        Args:
            asr_engine: ASR引擎实例（支持transcribe_stream方法）
            callback: 转录结果回调函数 callback(text: str, metadata: dict)
                     metadata包含: segment_index, duration, transcribe_time等
        """
        self.asr_engine = asr_engine
        self.callback = callback
        
        # 转录队列和线程
        self.segment_queue = queue.Queue(maxsize=10)  # 限制队列大小避免内存溢出
        self.is_running = False
        self.worker_thread = None
        
        # 性能统计
        self.stats = {
            'segments_count': 0,          # 已转录分段数
            'total_transcribe_time': 0,   # 总转录耗时
            'avg_transcribe_time': 0,     # 平均转录耗时
            'queue_size': 0,              # 当前队列大小
            'longest_delay': 0,           # 最长延迟
            'dropped_segments': 0,        # 因队列满丢弃的分段数
        }
        
        # 分段计数
        self.segment_index = 0
        
        print("[实时转录] 初始化完成")
        
    def start(self):
        """启动转录工作线程"""
        if self.is_running:
            print("[实时转录] 已经在运行中")
            return
            
        self.is_running = True
        self.segment_index = 0
        
        # 启动后台工作线程
        self.worker_thread = threading.Thread(
            target=self._transcribe_worker,
            daemon=True,
            name="RealtimeTranscriberWorker"
        )
        self.worker_thread.start()
        print("[实时转录] 工作线程已启动")
        
    def stop(self):
        """停止转录（等待队列处理完成）"""
        if not self.is_running:
            return
            
        print("[实时转录] 停止中，等待队列处理完成...")
        self.is_running = False
        
        # 等待工作线程结束（最多等待5秒）
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
            
        # 清空队列
        while not self.segment_queue.empty():
            try:
                self.segment_queue.get_nowait()
            except queue.Empty:
                break
                
        print(f"[实时转录] 已停止，共处理 {self.stats['segments_count']} 个分段")
        
    def add_segment(self, audio_segment, metadata: Optional[Dict] = None):
        """
        添加音频分段到转录队列
        
        Args:
            audio_segment: 音频数据（numpy数组或列表）
            metadata: 分段元数据（如时间戳、时长等）
        """
        if not self.is_running:
            print("[实时转录警告] 转录器未运行，分段被忽略")
            return False
            
        try:
            # 非阻塞添加，如果队列满则丢弃
            self.segment_queue.put_nowait({
                'audio': audio_segment,
                'metadata': metadata or {},
                'enqueue_time': time.time(),
                'segment_index': self.segment_index
            })
            self.segment_index += 1
            self.stats['queue_size'] = self.segment_queue.qsize()
            return True
            
        except queue.Full:
            # 队列满，丢弃此分段
            self.stats['dropped_segments'] += 1
            print(f"[实时转录警告] 队列已满({self.segment_queue.maxsize})，丢弃分段 #{self.segment_index}")
            self.segment_index += 1
            return False
            
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        stats = self.stats.copy()
        stats['queue_size'] = self.segment_queue.qsize()
        stats['is_running'] = self.is_running
        return stats
        
    def _transcribe_worker(self):
        """转录工作线程（后台运行）"""
        print("[实时转录] 工作线程开始处理...")
        
        while self.is_running:
            try:
                # 从队列获取音频段（超时0.5秒避免阻塞）
                segment_data = self.segment_queue.get(timeout=0.5)
                
                audio_segment = segment_data['audio']
                metadata = segment_data['metadata']
                enqueue_time = segment_data['enqueue_time']
                segment_idx = segment_data['segment_index']
                
                # 计算排队延迟
                queue_delay = time.time() - enqueue_time
                if queue_delay > self.stats['longest_delay']:
                    self.stats['longest_delay'] = queue_delay
                
                # 音频质量检查
                import numpy as np
                if isinstance(audio_segment, np.ndarray):
                    rms = np.sqrt(np.mean(audio_segment ** 2))
                    if rms < 0.001:
                        print(f"[实时转录] 分段 #{segment_idx} 音量过低 (RMS={rms:.4f})，跳过")
                        continue
                
                # 开始转录
                start_time = time.time()
                print(f"[实时转录] 开始转录分段 #{segment_idx}（排队: {queue_delay:.2f}秒）")
                
                try:
                    # 调用ASR引擎转录（启用上下文）
                    if hasattr(self.asr_engine, 'context_history'):
                        result = self.asr_engine.transcribe_stream(audio_segment, use_context=True)
                    else:
                        result = self.asr_engine.transcribe_stream(audio_segment)
                    transcribe_time = time.time() - start_time
                    
                    # 提取文本
                    if result and 'text' in result:
                        text = result['text'].strip()
                    elif isinstance(result, str):
                        text = result.strip()
                    else:
                        text = ""
                    
                    # 更新统计
                    self.stats['segments_count'] += 1
                    self.stats['total_transcribe_time'] += transcribe_time
                    self.stats['avg_transcribe_time'] = (
                        self.stats['total_transcribe_time'] / self.stats['segments_count']
                    )
                    
                    # 如果有文本则回调
                    if text:
                        print(f"[实时转录] 完成 #{segment_idx}（{transcribe_time:.2f}秒）: {text[:50]}...")
                        
                        # 构建回调元数据
                        callback_metadata = {
                            'segment_index': segment_idx,
                            'transcribe_time': transcribe_time,
                            'queue_delay': queue_delay,
                            'total_segments': self.stats['segments_count'],
                            **metadata  # 合并原始元数据
                        }
                        
                        # 调用用户回调
                        try:
                            self.callback(text, callback_metadata)
                        except Exception as e:
                            print(f"[实时转录错误] 回调函数异常: {e}")
                    else:
                        print(f"[实时转录] 完成 #{segment_idx}（{transcribe_time:.2f}秒）: [空文本]")
                        
                except Exception as e:
                    print(f"[实时转录错误] 转录失败: {e}")
                    import traceback
                    traceback.print_exc()
                    
            except queue.Empty:
                # 队列为空，继续等待
                continue
                
            except Exception as e:
                print(f"[实时转录错误] 工作线程异常: {e}")
                import traceback
                traceback.print_exc()
                
        print("[实时转录] 工作线程已退出")
        
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'segments_count': 0,
            'total_transcribe_time': 0,
            'avg_transcribe_time': 0,
            'queue_size': 0,
            'longest_delay': 0,
            'dropped_segments': 0,
        }
        print("[实时转录] 统计信息已重置")
