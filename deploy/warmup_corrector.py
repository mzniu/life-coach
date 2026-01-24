#!/usr/bin/env python3
"""
文本纠错器预热脚本

在部署时预先下载 macro-correct 模型，避免首次请求超时
"""

import os
import sys

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def warmup_macro_correct():
    """预热 macro-correct 引擎，下载模型"""
    print("=" * 60)
    print("预热 macro-correct 文本纠错器")
    print("=" * 60)
    
    try:
        print("\n[1/3] 检查环境...")
        
        # 检查是否安装了必要的包
        try:
            import torch
            print(f"  ✓ PyTorch 已安装: {torch.__version__}")
        except ImportError:
            print("  ✗ PyTorch 未安装")
            print("    安装命令: pip install torch --index-url https://download.pytorch.org/whl/cpu")
            return False
        
        try:
            import transformers
            print(f"  ✓ transformers 已安装: {transformers.__version__}")
            if not transformers.__version__.startswith('4.30'):
                print(f"    ⚠️ 警告: transformers 版本应为 4.30.2 (当前 {transformers.__version__})")
        except ImportError:
            print("  ✗ transformers 未安装")
            print("    安装命令: pip install transformers==4.30.2")
            return False
        
        try:
            import macro_correct
            print(f"  ✓ macro-correct 已安装")
        except ImportError:
            print("  ✗ macro-correct 未安装")
            print("    安装命令: pip install macro-correct")
            return False
        
        print("\n[2/3] 初始化 macro-correct 引擎...")
        print("  注意: 首次运行会从 Hugging Face 下载模型 (~380MB)")
        print("  下载地址: https://huggingface.co/Macropodus/macbert4mdcspell_v2")
        
        # 设置环境变量：启用错别字纠正
        os.environ["MACRO_CORRECT_FLAG_CSC_TOKEN"] = "1"
        
        # 导入并初始化（使用官方推荐的 correct() 函数）
        from macro_correct import correct
        
        print("  正在下载/加载模型...")
        corrector = correct
        
        print("\n[3/3] 测试推理...")
        
        # 测试1: 标点符号补全
        test_text_punct = "今天天气怎么样"
        print(f"  测试1 (标点符号):")
        print(f"    输入: {test_text_punct}")
        
        import time
        start = time.time()
        results = corrector([test_text_punct])
        elapsed = time.time() - start
        
        if results and len(results) > 0:
            result = results[0]
            corrected = result.get('target', test_text_punct)
            errors = result.get('errors', [])
            
            print(f"    输出: {corrected}")
            print(f"    耗时: {elapsed:.2f} 秒")
            print(f"    修改: {len(errors)} 处")
        
        # 测试2: 错别字纠正
        test_text_typo = "今天天汽怎么样我想去那里玩"
        print(f"\n  测试2 (错别字纠正):")
        print(f"    输入: {test_text_typo}")
        
        start = time.time()
        results = corrector([test_text_typo])
        elapsed = time.time() - start
        
        if results and len(results) > 0:
            result = results[0]
            corrected = result.get('target', test_text_typo)
            errors = result.get('errors', [])
            
            print(f"    输出: {corrected}")
            print(f"    耗时: {elapsed:.2f} 秒")
            print(f"    修改: {len(errors)} 处")
        
        print("\n" + "=" * 60)
        print("✓ macro-correct 预热成功！")
        print("=" * 60)
        
        return True
    
    except Exception as e:
        print(f"\n✗ 预热失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("文本纠错器预热脚本")
    print("用途: 在部署时预先下载模型，避免首次请求超时\n")
    
    # 检查是否应该使用 macro-correct
    engine_type = os.getenv("TEXT_CORRECTOR_ENGINE", "macro-correct")
    
    if engine_type != "macro-correct":
        print(f"当前配置使用 {engine_type} 引擎，跳过 macro-correct 预热")
        return True
    
    # 预热
    success = warmup_macro_correct()
    
    if success:
        print("\n提示: 后续启动服务时，文本纠错功能将立即可用")
        return True
    else:
        print("\n警告: 预热失败，首次纠错请求可能会超时")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
