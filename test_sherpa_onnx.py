"""
sherpa-onnx 测试脚本
对比 faster-whisper 和 sherpa-onnx 的性能

测试内容：
1. 安装验证
2. 模型下载
3. 识别准确度对比
4. 延迟对比
5. CPU/内存占用对比
"""

import sys
import time
import psutil
import numpy as np
from pathlib import Path

def check_dependencies():
    """检查依赖是否安装"""
    print("=" * 60)
    print("1. 检查依赖")
    print("=" * 60)
    
    # 检查 faster-whisper
    try:
        import faster_whisper
        print(f"✓ faster-whisper 已安装: {faster_whisper.__version__}")
    except ImportError:
        print("✗ faster-whisper 未安装")
        return False
    
    # 检查 sherpa-onnx
    try:
        import sherpa_onnx
        print(f"✓ sherpa-onnx 已安装")
    except ImportError:
        print("✗ sherpa-onnx 未安装")
        print("\n安装命令: pip install sherpa-onnx")
        return False
    
    print()
    return True


def download_sherpa_models():
    """下载 sherpa-onnx 中文模型"""
    print("=" * 60)
    print("2. 下载 sherpa-onnx 中文模型")
    print("=" * 60)
    
    models_dir = Path("models/sherpa")
    models_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n模型将保存到: {models_dir.absolute()}\n")
    
    # 推荐的中文流式模型
    models = [
        {
            "name": "Paraformer Streaming (中文)",
            "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-paraformer-bilingual-zh-en.tar.bz2",
            "size": "~50MB",
            "desc": "中英双语流式识别，适合实时场景"
        },
        {
            "name": "Zipformer Transducer (中文)",
            "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20.tar.bz2",
            "size": "~70MB",
            "desc": "双语流式识别，低延迟"
        }
    ]
    
    print("推荐模型：\n")
    for i, model in enumerate(models, 1):
        print(f"{i}. {model['name']}")
        print(f"   大小: {model['size']}")
        print(f"   说明: {model['desc']}")
        print(f"   下载: {model['url']}\n")
    
    print("请手动下载并解压到 models/sherpa/ 目录")
    print("或使用以下命令：")
    print(f"cd {models_dir}")
    print("wget <模型URL>")
    print("tar -xjf <模型文件>.tar.bz2")
    print()


def test_faster_whisper(audio_file):
    """测试 faster-whisper"""
    print("=" * 60)
    print("3. 测试 faster-whisper")
    print("=" * 60)
    
    try:
        from faster_whisper import WhisperModel
        
        print("加载 Whisper tiny 模型...")
        start_load = time.time()
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        load_time = time.time() - start_load
        print(f"✓ 模型加载耗时: {load_time:.2f}秒\n")
        
        # 如果有测试音频
        if audio_file and Path(audio_file).exists():
            print(f"识别音频: {audio_file}")
            
            # 记录资源使用
            process = psutil.Process()
            cpu_before = process.cpu_percent()
            mem_before = process.memory_info().rss / 1024 / 1024
            
            start_time = time.time()
            segments, info = model.transcribe(audio_file, language="zh")
            
            text = " ".join([seg.text for seg in segments])
            duration = time.time() - start_time
            
            cpu_after = process.cpu_percent()
            mem_after = process.memory_info().rss / 1024 / 1024
            
            print(f"✓ 识别结果: {text}")
            print(f"✓ 识别耗时: {duration:.2f}秒")
            print(f"✓ CPU使用: {cpu_after:.1f}%")
            print(f"✓ 内存使用: {mem_after:.0f}MB (增加 {mem_after-mem_before:.0f}MB)")
            
            return {
                "text": text,
                "duration": duration,
                "cpu": cpu_after,
                "memory": mem_after,
                "load_time": load_time
            }
        else:
            print("⚠ 未提供测试音频文件")
            return None
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return None


def test_sherpa_onnx(audio_file):
    """测试 sherpa-onnx"""
    print("\n" + "=" * 60)
    print("4. 测试 sherpa-onnx")
    print("=" * 60)
    
    try:
        import sherpa_onnx
        
        # 检查模型是否存在
        models_dir = Path("models/sherpa")
        
        # 查找可用模型
        model_dirs = list(models_dir.glob("sherpa-onnx-*"))
        
        if not model_dirs:
            print("✗ 未找到 sherpa-onnx 模型")
            print(f"  请先下载模型到: {models_dir.absolute()}")
            return None
        
        print(f"找到模型: {model_dirs[0].name}\n")
        
        # 配置识别器（这里需要根据实际模型调整）
        recognizer = sherpa_onnx.OnlineRecognizer.from_paraformer(
            encoder=str(model_dirs[0] / "encoder.onnx"),
            decoder=str(model_dirs[0] / "decoder.onnx"),
            tokens=str(model_dirs[0] / "tokens.txt"),
        )
        
        print("✓ 识别器创建成功\n")
        
        # 如果有测试音频
        if audio_file and Path(audio_file).exists():
            print(f"识别音频: {audio_file}")
            
            # TODO: 实现音频流式识别
            print("⚠ 流式识别测试待实现")
            
            return None
        else:
            print("⚠ 未提供测试音频文件")
            return None
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def compare_results(whisper_result, sherpa_result):
    """对比测试结果"""
    print("\n" + "=" * 60)
    print("5. 性能对比")
    print("=" * 60)
    
    if not whisper_result and not sherpa_result:
        print("⚠ 无测试结果可对比")
        return
    
    print("\n| 指标 | faster-whisper | sherpa-onnx | 优势 |")
    print("|------|----------------|-------------|------|")
    
    if whisper_result and sherpa_result:
        # 识别准确度
        print(f"| 识别结果 | {whisper_result['text'][:20]}... | {sherpa_result.get('text', 'N/A')[:20]}... | - |")
        
        # 延迟对比
        whisper_time = whisper_result['duration']
        sherpa_time = sherpa_result.get('duration', 0)
        if sherpa_time > 0:
            faster = "sherpa-onnx" if sherpa_time < whisper_time else "faster-whisper"
            print(f"| 识别延迟 | {whisper_time:.2f}s | {sherpa_time:.2f}s | {faster} |")
        
        # CPU使用
        whisper_cpu = whisper_result['cpu']
        sherpa_cpu = sherpa_result.get('cpu', 0)
        if sherpa_cpu > 0:
            lower = "sherpa-onnx" if sherpa_cpu < whisper_cpu else "faster-whisper"
            print(f"| CPU使用 | {whisper_cpu:.1f}% | {sherpa_cpu:.1f}% | {lower} |")
        
        # 内存使用
        whisper_mem = whisper_result['memory']
        sherpa_mem = sherpa_result.get('memory', 0)
        if sherpa_mem > 0:
            lower = "sherpa-onnx" if sherpa_mem < whisper_mem else "faster-whisper"
            print(f"| 内存使用 | {whisper_mem:.0f}MB | {sherpa_mem:.0f}MB | {lower} |")
    
    elif whisper_result:
        print(f"| 识别结果 | {whisper_result['text'][:30]}... | - | - |")
        print(f"| 识别延迟 | {whisper_result['duration']:.2f}s | - | - |")
        print(f"| CPU使用 | {whisper_result['cpu']:.1f}% | - | - |")
        print(f"| 内存使用 | {whisper_result['memory']:.0f}MB | - | - |")
    
    print()


def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("sherpa-onnx vs. faster-whisper 性能测试")
    print("=" * 60 + "\n")
    
    # 1. 检查依赖
    if not check_dependencies():
        print("\n请先安装依赖：pip install sherpa-onnx")
        return
    
    # 2. 下载模型说明
    download_sherpa_models()
    
    # 3. 准备测试音频
    test_audio = None
    if len(sys.argv) > 1:
        test_audio = sys.argv[1]
        if not Path(test_audio).exists():
            print(f"⚠ 音频文件不存在: {test_audio}")
            test_audio = None
    
    if not test_audio:
        print("提示: 可以指定测试音频文件")
        print("用法: python test_sherpa_onnx.py <音频文件.wav>")
        print("\n将只测试模型加载...\n")
    
    # 4. 测试 faster-whisper
    whisper_result = test_faster_whisper(test_audio)
    
    # 5. 测试 sherpa-onnx
    sherpa_result = test_sherpa_onnx(test_audio)
    
    # 6. 对比结果
    compare_results(whisper_result, sherpa_result)
    
    # 总结建议
    print("=" * 60)
    print("测试总结与建议")
    print("=" * 60)
    print("""
下一步行动：

1. [P0] 安装 sherpa-onnx
   pip install sherpa-onnx

2. [P0] 下载中文流式模型
   推荐: Paraformer Streaming (双语, ~50MB)
   下载地址见上方输出

3. [P1] 重新运行此脚本并提供测试音频
   python test_sherpa_onnx.py test_audio.wav

4. [P1] 在 Raspberry Pi 上测试
   scp test_sherpa_onnx.py pi:~/LifeCoach/
   ssh pi "cd LifeCoach && python test_sherpa_onnx.py"

5. [P2] 根据测试结果决定：
   - 如果 sherpa-onnx 性能更好 → 完全替换
   - 如果只有 VAD 更好 → 只用 silero-vad
   - 如果差不多 → 保持现状

关键评估指标：
- 识别准确度（最重要）
- 端到端延迟（<2秒为佳）
- Pi 上 CPU 占用（<50%为佳）
- 内存占用（<500MB为佳）
""")


if __name__ == "__main__":
    main()
