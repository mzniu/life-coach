"""
真实的ASR转写引擎（支持Windows/Linux）
使用 faster-whisper 实现本地语音识别
"""

import time
import numpy as np
import sys
import os

# 添加项目根目录到路径，以便导入 config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import ASR_MODEL_SIZE, ASR_COMPUTE_TYPE, ASR_BEAM_SIZE, ASR_VAD_FILTER
    USE_CONFIG = True
except ImportError:
    # 如果没有 config.py，使用默认值
    ASR_MODEL_SIZE = "small"
    ASR_COMPUTE_TYPE = "int8"
    ASR_BEAM_SIZE = 5
    ASR_VAD_FILTER = True
    USE_CONFIG = False

# 尝试导入真实ASR库
try:
    from faster_whisper import WhisperModel
    REAL_ASR = True
    print("[ASR] 使用真实 faster-whisper 引擎")
    if USE_CONFIG:
        print(f"[ASR] 从配置文件加载: model={ASR_MODEL_SIZE}, compute={ASR_COMPUTE_TYPE}")
except ImportError:
    REAL_ASR = False
    print("[ASR警告] faster-whisper 未安装，将使用模拟模式")
    print("[ASR警告] 安装方法: pip install faster-whisper")

class ASREngine:
    """ASR转写引擎（支持真实和模拟模式）"""
    
    def __init__(self, model_size=None, device="cpu", compute_type=None):
        """
        初始化ASR引擎
        model_size: 模型大小 (tiny, base, small, medium, large), None 则使用配置文件
        device: 设备 (cpu, cuda)
        compute_type: 计算类型 (int8, float16, float32), None 则使用配置文件
        """
        global REAL_ASR
        
        # 使用配置文件中的值（如果参数为 None）
        self.model_size = model_size if model_size is not None else ASR_MODEL_SIZE
        self.device = device
        self.compute_type = compute_type if compute_type is not None else ASR_COMPUTE_TYPE
        
        if REAL_ASR:
            print(f"[ASR] 加载 Whisper 模型: {self.model_size} ({self.device}, {self.compute_type})")
            print("[ASR] 首次加载可能需要下载模型，请稍候...")
            
            # 检查本地 models 目录
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            local_models_dir = os.path.join(project_root, "models")
            download_root = None
            
            local_files_only = False
            if os.path.exists(local_models_dir):
                print(f"[ASR] 检测到本地模型目录: {local_models_dir}")
                download_root = local_models_dir
                local_files_only = True # 强制仅使用本地文件，防止联网卡死
                os.environ["HF_HUB_OFFLINE"] = "1" # 双重保险
            
            try:
                self.model = WhisperModel(
                    self.model_size, 
                    device=self.device, 
                    compute_type=self.compute_type,
                    download_root=download_root,
                    local_files_only=local_files_only
                )
                print("[ASR] Whisper 模型加载完成")
            except Exception as e:
                print(f"[ASR错误] 模型加载失败: {e}")
                print("[ASR] 降级到模拟模式")
                REAL_ASR = False
                self.model = None
        else:
            self.model = None
            print(f"[模拟ASR] 初始化模拟引擎: {model_size}")
    
    def transcribe_stream(self, audio_chunks, callback=None):
        """
        流式转写
        audio_chunks: 音频数据块列表 [[samples], [samples], ...]
        callback: 进度回调函数 callback(progress, partial_text)
        返回: 完整转写文本
        """
        if REAL_ASR and self.model:
            return self._real_transcribe(audio_chunks, callback)
        else:
            return self._mock_transcribe(audio_chunks, callback)
    
    def _real_transcribe(self, audio_chunks, callback=None):
        """真实的Whisper转写"""
        print("[ASR] 开始真实转写...")
        
        try:
            # 合并音频块
            if isinstance(audio_chunks, list) and len(audio_chunks) > 0:
                # 展平音频数据
                audio_data = []
                for chunk in audio_chunks:
                    if isinstance(chunk, list):
                        audio_data.extend(chunk)
                    else:
                        audio_data.extend(chunk.tolist())
                
                # 转换为numpy数组并归一化到 [-1, 1]
                audio_np = np.array(audio_data, dtype=np.float32)
                audio_np = audio_np / 32768.0  # int16 -> float32
                
                print(f"[ASR] 音频数据: {len(audio_np)} 采样点 ({len(audio_np)/16000:.1f}秒)")
                
                # 执行转写（使用配置的参数）
                # initial_prompt 提示模型输出标点符号和规范的中文
                segments, info = self.model.transcribe(
                    audio_np,
                    language="zh",  # 中文
                    beam_size=ASR_BEAM_SIZE,  # 使用配置的 beam size
                    vad_filter=ASR_VAD_FILTER,  # 使用配置的 VAD
                    initial_prompt="以下是普通话的句子，包含标点符号：",  # 提示输出标点
                )
                
                print(f"[ASR] 检测语言: {info.language} (概率: {info.language_probability:.2f})")
                
                # 收集转写结果 - 实时逐个处理segment
                full_text = []
                segment_count = 0
                
                # 直接遍历生成器，每处理一个segment就回调一次
                for segment in segments:
                    text = segment.text.strip()
                    full_text.append(text)
                    segment_count += 1
                    
                    # 实时回调进度（使用已处理的segment数量估算进度）
                    if callback:
                        # 由于无法预知总数，使用已处理的字数来估算进度
                        # 假设平均每秒产生10-15个字，根据音频长度估算
                        partial = "".join(full_text)
                        # 根据已转写的字数和音频时长估算进度
                        progress = min(95, int(len(partial) / max(1, info.duration * 10) * 100))
                        callback(progress, partial)
                        print(f"[ASR进度] {progress}% - 已转写 {len(partial)} 字")
                    
                    print(f"[ASR片段] [{segment.start:.1f}s -> {segment.end:.1f}s] {text}")
                
                # 最后回调100%
                result = "".join(full_text)
                if callback:
                    callback(100, result)
                
                print(f"[ASR] 转写完成: {len(result)} 字符")
                return result
                
            else:
                print("[ASR警告] 音频数据为空")
                return ""
                
        except Exception as e:
            print(f"[ASR错误] 转写失败: {e}")
            import traceback
            traceback.print_exc()
            return f"[转写错误: {e}]"
    
    def _mock_transcribe(self, audio_chunks, callback=None):
        """模拟转写（备用方案）"""
        import random
        print("[模拟ASR] 开始模拟转写")
        
        total_chunks = len(audio_chunks) if hasattr(audio_chunks, '__len__') else 10
        result_text = []
        
        for i in range(total_chunks):
            time.sleep(0.1)  # 模拟处理时间
            
            sample_words = [
                "今天我们讨论一下",
                "产品的MVP功能",
                "需要实现录音",
                "和实时转写",
                "还有AI整理功能"
            ]
            text = random.choice(sample_words)
            result_text.append(text)
            
            if callback:
                progress = int((i + 1) / total_chunks * 100)
                callback(progress, "".join(result_text))
        
        final_text = " ".join(result_text)
        print(f"[模拟ASR] 转写完成: {final_text}")
        return final_text
    
    def transcribe_file(self, audio_path):
        """批量转写音频文件"""
        if REAL_ASR and self.model:
            print(f"[ASR] 转写文件: {audio_path}")
            try:
                segments, info = self.model.transcribe(
                    audio_path, 
                    language="zh",
                    initial_prompt="以下是普通话的句子，包含标点符号："
                )
                result = "".join([seg.text for seg in segments])
                print(f"[ASR] 文件转写完成: {len(result)} 字符")
                return result
            except Exception as e:
                print(f"[ASR错误] 文件转写失败: {e}")
                return f"[转写错误: {e}]"
        else:
            print(f"[模拟ASR] 模拟转写文件: {audio_path}")
            time.sleep(1)
            return "这是模拟的文件转写结果。请安装 faster-whisper 以启用真实转写。"
