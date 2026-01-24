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
    from config import (ASR_MODEL_SIZE, ASR_COMPUTE_TYPE, ASR_BEAM_SIZE, ASR_VAD_FILTER,
                        TEXT_CORRECTION_ENABLED, TEXT_CORRECTION_MODEL, 
                        TEXT_CORRECTION_MAX_TOKENS, TEXT_CORRECTION_TEMPERATURE, TEXT_CORRECTION_TIMEOUT)
    USE_CONFIG = True
except ImportError:
    # 如果没有 config.py，使用默认值
    ASR_MODEL_SIZE = "small"
    ASR_COMPUTE_TYPE = "int8"
    ASR_BEAM_SIZE = 5
    ASR_VAD_FILTER = True
    TEXT_CORRECTION_ENABLED = False
    USE_CONFIG = False

# 尝试导入真实ASR库
# 检测可用的ASR引擎
ASR_ENGINE_TYPE = os.getenv("ASR_ENGINE", "whisper")  # whisper 或 sherpa

try:
    if ASR_ENGINE_TYPE == "sherpa":
        from src.asr_sherpa import ParaformerModel as ASRModel
        REAL_ASR = True
        print("[ASR] 使用 Sherpa-ONNX Paraformer 引擎")
    else:
        from faster_whisper import WhisperModel as ASRModel
        REAL_ASR = True
        print("[ASR] 使用 faster-whisper 引擎")
        if USE_CONFIG:
            print(f"[ASR] 从配置文件加载: model={ASR_MODEL_SIZE}, compute={ASR_COMPUTE_TYPE}")
except ImportError as e:
    REAL_ASR = False
    ASRModel = None
    print(f"[ASR警告] {ASR_ENGINE_TYPE} 未安装: {e}")
    print("[ASR警告] 将使用模拟模式")

class ASREngine:
    """ASR转写引擎（支持真实和模拟模式 + 文本纠错）"""
    
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
        
        # 初始化文本纠错模块
        self.text_corrector = None
        if TEXT_CORRECTION_ENABLED:
            try:
                from src.text_corrector import get_text_corrector
                # 使用新的双引擎架构，自动从环境变量读取引擎类型
                self.text_corrector = get_text_corrector()
                print(f"[ASR] 文本纠错功能已启用，引擎: {os.getenv('TEXT_CORRECTOR_ENGINE', 'macro-correct')}")
            except Exception as e:
                print(f"[ASR警告] 文本纠错初始化失败: {e}, 将跳过纠错")
                import traceback
                traceback.print_exc()
                self.text_corrector = None
        else:
            print("[ASR] 文本纠错功能未启用")
        
        if REAL_ASR:
            print(f"[ASR] 加载模型: {self.model_size} ({self.device}, {self.compute_type})")
            print("[ASR] 首次加载可能需要下载模型，请稍候...")
            
            # 设置使用国内镜像
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
            
            # 检查本地 models 目录
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            try:
                if ASR_ENGINE_TYPE == "sherpa":
                    # Paraformer 模型路径
                    model_path = os.path.join(project_root, "models", "sherpa", "paraformer")
                    if not os.path.exists(model_path):
                        print(f"[ASR警告] Paraformer 模型不存在: {model_path}")
                        print(f"[ASR] 请先下载并解压模型到该目录")
                        raise FileNotFoundError(f"模型目录不存在: {model_path}")
                    
                    self.model = ASRModel(
                        model_path=model_path,
                        device=self.device,
                        compute_type=self.compute_type
                    )
                    print(f"[ASR] Paraformer 模型加载完成: {model_path}")
                else:
                    # Whisper 模型路径
                    local_models_dir = os.path.join(project_root, "models")
                    download_root = None
                    
                    if os.path.exists(local_models_dir):
                        print(f"[ASR] 检测到本地模型目录: {local_models_dir}")
                        download_root = local_models_dir
                    
                    self.model = ASRModel(
                        self.model_size, 
                        device=self.device, 
                        compute_type=self.compute_type,
                        download_root=download_root,
                        local_files_only=False  # 允许使用缓存的模型
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
        流式转写（实时转录场景，跳过文本纠错以提升速度）
        audio_chunks: 音频数据块列表 [[samples], [samples], ...]
        callback: 进度回调函数 callback(progress, partial_text)
        返回: 完整转写文本
        """
        if REAL_ASR and self.model:
            return self._real_transcribe(audio_chunks, callback, skip_correction=True)
        else:
            return self._mock_transcribe(audio_chunks, callback)
    
    def _real_transcribe(self, audio_chunks, callback=None, skip_correction=False):
        """真实的Whisper转写"""
        print("[ASR] 开始真实转写...")
        
        try:
            # 处理音频输入：支持列表或numpy数组
            if isinstance(audio_chunks, np.ndarray):
                # 直接是numpy数组
                audio_np = audio_chunks.astype(np.float32)
                if audio_np.max() > 1.0 or audio_np.min() < -1.0:
                    # 需要归一化
                    audio_np = audio_np / 32768.0  # int16 -> float32
                print(f"[ASR] 音频数据（numpy）: {len(audio_np)} 采样点 ({len(audio_np)/16000:.1f}秒)")
                
            elif isinstance(audio_chunks, list) and len(audio_chunks) > 0:
                # 合并音频块列表
                audio_data = []
                for chunk in audio_chunks:
                    if isinstance(chunk, list):
                        audio_data.extend(chunk)
                    elif isinstance(chunk, np.ndarray):
                        audio_data.extend(chunk.tolist())
                    elif hasattr(chunk, 'tolist'):
                        # 其他类数组对象
                        audio_data.extend(chunk.tolist())
                    else:
                        # 单个数值，跳过
                        print(f"[ASR警告] 跳过非数组类型: {type(chunk)}")
                        continue
                
                # 转换为numpy数组并归一化到 [-1, 1]
                audio_np = np.array(audio_data, dtype=np.float32)
                audio_np = audio_np / 32768.0  # int16 -> float32
                
                print(f"[ASR] 音频数据（列表）: {len(audio_np)} 采样点 ({len(audio_np)/16000:.1f}秒)")
            else:
                print("[ASR警告] 音频数据为空或格式错误")
                return ""
            
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
            
            # 文本纠错（如果启用且不跳过）
            if self.text_corrector is not None and not skip_correction:
                print("[ASR] 开始文本纠错...")
                try:
                    correction_result = self.text_corrector.correct(result)
                    
                    if correction_result['success'] and correction_result['changed']:
                        print(f"[ASR] 纠错完成: {correction_result['time_ms']}ms")
                        print(f"[ASR] 原文: {result}")
                        print(f"[ASR] 纠正: {correction_result['corrected']}")
                        print(f"[ASR] 变化: {correction_result['changes']}")
                        
                        # 返回带纠错信息的结果
                        return {
                            "text": correction_result['corrected'],
                            "text_original": result,
                            "correction_enabled": True,
                            "correction_changes": correction_result['changes'],
                            "correction_time_ms": correction_result['time_ms']
                        }
                    else:
                        print(f"[ASR] 纠错无变化或失败")
                except Exception as e:
                    print(f"[ASR警告] 纠错过程异常: {e}, 返回原文")
            
            # 返回普通结果
            return result
                
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
        import sys
        if REAL_ASR and self.model:
            print(f"[ASR] 转写文件: {audio_path}", file=sys.stderr, flush=True)
            try:
                segments, info = self.model.transcribe(
                    audio_path, 
                    language="zh",
                    initial_prompt="以下是普通话的句子，包含标点符号："
                )
                result = "".join([seg.text for seg in segments])
                print(f"[ASR] 文件转写完成: {len(result)} 字符", file=sys.stderr, flush=True)
                return {"text": result, "segments": len(list(segments))}
            except Exception as e:
                print(f"[ASR错误] 文件转写失败: {e}", file=sys.stderr, flush=True)
                import traceback
                traceback.print_exc(file=sys.stderr)
                return {"text": f"[转写错误: {e}]", "error": str(e)}
        else:
            print(f"[模拟ASR] 模拟转写文件: {audio_path}", file=sys.stderr, flush=True)
            time.sleep(1)
            return {"text": "这是模拟的文件转写结果。请安装 faster-whisper 以启用真实转写。"}
