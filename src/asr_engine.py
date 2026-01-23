"""
模拟的ASR转写引擎（用于本地开发测试）
在非树莓派环境下模拟Whisper转写行为
"""

import time
import random

class ASREngine:
    """模拟Whisper转写引擎"""
    
    def __init__(self):
        self.model_name = "tiny-simulated"
        print(f"[模拟ASR] 初始化Whisper模型: {self.model_name}")
        
    def transcribe_stream(self, audio_chunks, callback=None):
        """
        流式转写（模拟）
        audio_chunks: 音频数据
        callback: 进度回调函数
        """
        print("[模拟ASR] 开始流式转写（模拟）")
        
        # 模拟转写过程
        total_chunks = len(audio_chunks) if hasattr(audio_chunks, '__len__') else 10
        result_text = []
        
        for i in range(total_chunks):
            # 模拟每个音频块的转写时间
            time.sleep(0.1)
            
            # 生成模拟文字
            sample_words = [
                "今天我们讨论一下",
                "产品的MVP功能",
                "需要实现录音",
                "和实时转写",
                "还有AI整理功能"
            ]
            text = random.choice(sample_words)
            result_text.append(text)
            
            # 回调进度
            if callback:
                progress = int((i + 1) / total_chunks * 100)
                callback(progress, "".join(result_text))
                
        final_text = " ".join(result_text)
        print(f"[模拟ASR] 转写完成: {final_text}")
        return final_text
        
    def transcribe_file(self, audio_path):
        """批量转写音频文件（模拟）"""
        print(f"[模拟ASR] 转写文件: {audio_path}")
        time.sleep(1)  # 模拟处理时间
        
        # 生成模拟转写结果
        mock_text = """
        这是一段模拟的转写文本内容。
        在实际部署到树莓派后，这里会是真实的语音识别结果。
        当前为本地开发测试模式，使用模拟数据。
        您可以通过这个模拟版本验证整体流程是否正常。
        """.strip()
        
        return mock_text
        
    def cleanup(self):
        """清理资源"""
        print("[模拟ASR] 清理资源")
