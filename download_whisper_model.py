"""
预先下载 Whisper 模型
避免首次启动时等待下载
"""

import os
# 设置 Hugging Face 镜像（加速国内下载）
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from faster_whisper import WhisperModel

def download_model(model_size="tiny", device="cpu", compute_type="int8"):
    """
    下载指定的 Whisper 模型
    
    model_size 选项:
    - tiny: 最小模型，速度最快，准确率较低 (~75MB)
    - base: 基础模型，平衡速度和准确率 (~142MB)
    - small: 小型模型，较好准确率 (~466MB)
    - medium: 中型模型，高准确率，速度较慢 (~1.5GB)
    - large: 大型模型，最高准确率，速度最慢 (~2.9GB)
    """
    print("=" * 60)
    print(f"  下载 Whisper 模型: {model_size}")
    print("=" * 60)
    print(f"设备: {device}")
    print(f"计算类型: {compute_type}")
    print()
    
    try:
        # 定义本地模型保存路径
        project_root = os.path.dirname(os.path.abspath(__file__))
        models_dir = os.path.join(project_root, "models")
        
        print("开始下载模型，请耐心等待...")
        print(f"目标目录: {models_dir}")
        print()
        
        model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            download_root=models_dir  # 下载到项目内的 models 目录
        )
        
        print()
        print("✅ 模型下载成功！")
        print(f"✅ 模型 '{model_size}' 已保存到本地目录")
        print(f"📁 位置: {models_dir}")
        print()
        print("现在可以启动 main.py，将直接使用本地模型！")
        
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    
    # 默认下载 tiny 模型（最快，适合开发测试）
    model_size = "tiny"
    
    # 如果命令行指定了模型大小
    if len(sys.argv) > 1:
        model_size = sys.argv[1].lower()
    
    print()
    print("💡 提示：")
    print("  - tiny: 最快，75MB，适合开发测试")
    print("  - base: 平衡，142MB，日常使用推荐")
    print("  - small: 较好，466MB，中文识别更准确")
    print()
    print(f"当前将下载: {model_size}")
    print("如需其他模型，运行: python download_whisper_model.py <模型名>")
    print()
    
    download_model(model_size)
