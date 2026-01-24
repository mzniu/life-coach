#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 macro-correct 在树莓派上的可行性
分步骤验证: 依赖安装 -> 功能测试 -> 性能测试
"""

import sys
import time
import traceback
import subprocess


def print_section(title):
    """打印分段标题"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")


def check_pytorch():
    """检查 PyTorch 是否已安装"""
    print_section("步骤 1: 检查 PyTorch")
    try:
        import torch
        print(f"✅ PyTorch 已安装")
        print(f"   版本: {torch.__version__}")
        print(f"   CUDA 可用: {torch.cuda.is_available()}")
        return True
    except ImportError:
        print("❌ PyTorch 未安装")
        return False


def install_pytorch():
    """尝试安装 PyTorch"""
    print_section("步骤 2: 安装 PyTorch (ARM CPU 版本)")
    print("正在尝试安装 PyTorch...")
    print("⚠️  这可能需要 5-15 分钟，请耐心等待...")
    
    try:
        # 使用 CPU 版本的 PyTorch
        cmd = [
            sys.executable, "-m", "pip", "install",
            "torch", "torchvision", "torchaudio",
            "--index-url", "https://download.pytorch.org/whl/cpu",
            "--timeout", "300"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        
        if result.returncode == 0:
            print("✅ PyTorch 安装成功")
            # 验证安装
            import torch
            print(f"   版本: {torch.__version__}")
            return True
        else:
            print("❌ PyTorch 安装失败")
            print(f"   错误: {result.stderr[:500]}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ 安装超时 (>15分钟)")
        return False
    except Exception as e:
        print(f"❌ 安装出错: {e}")
        return False


def check_macro_correct():
    """检查 macro-correct 是否已安装"""
    print_section("步骤 3: 检查 macro-correct")
    try:
        import macro_correct
        print(f"✅ macro-correct 已安装")
        return True
    except ImportError:
        print("❌ macro-correct 未安装")
        return False


def install_macro_correct():
    """安装 macro-correct"""
    print_section("步骤 4: 安装 macro-correct")
    print("正在安装 macro-correct...")
    
    try:
        cmd = [
            sys.executable, "-m", "pip", "install",
            "macro-correct",
            "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
            "--timeout", "120"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ macro-correct 安装成功")
            return True
        else:
            print("❌ macro-correct 安装失败")
            print(f"   错误: {result.stderr[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ 安装出错: {e}")
        return False


def test_punct_correction():
    """测试标点纠错功能"""
    print_section("步骤 5: 功能测试 - 标点纠错")
    
    try:
        import os
        os.environ["MACRO_CORRECT_FLAG_CSC_PUNCT"] = "1"
        from macro_correct import correct_punct
        
        # 测试样例
        test_cases = [
            "今天天气怎么样我们去哪里玩",
            "山不在高有仙则名水不在深有龙则灵",
            "少先队员应该为老人让座",
            "你好吗我很好谢谢",
        ]
        
        print("测试用例:")
        for i, text in enumerate(test_cases, 1):
            print(f"  {i}. {text}")
        
        print("\n开始纠错...\n")
        
        results = correct_punct(test_cases)
        
        print("纠错结果:")
        for res in results:
            print(f"\n  原文: {res['source']}")
            print(f"  修正: {res['target']}")
            if res['errors']:
                print(f"  改动: {res['errors']}")
        
        print("\n✅ 标点纠错功能正常")
        return True, results
        
    except Exception as e:
        print(f"❌ 标点纠错测试失败")
        print(f"   错误: {e}")
        traceback.print_exc()
        return False, None


def test_csc_correction():
    """测试拼写纠错功能"""
    print_section("步骤 6: 功能测试 - 拼写纠错")
    
    try:
        import os
        os.environ["MACRO_CORRECT_FLAG_CSC_TOKEN"] = "1"
        from macro_correct import correct
        
        # 测试样例
        test_cases = [
            "少先队员因该为老人让坐",
            "真麻烦你了。希望你们好好的跳无",
        ]
        
        print("测试用例:")
        for i, text in enumerate(test_cases, 1):
            print(f"  {i}. {text}")
        
        print("\n开始纠错...\n")
        
        results = correct(test_cases)
        
        print("纠错结果:")
        for res in results:
            print(f"\n  原文: {res['source']}")
            print(f"  修正: {res['target']}")
            if res['errors']:
                print(f"  改动: {res['errors']}")
        
        print("\n✅ 拼写纠错功能正常")
        return True, results
        
    except Exception as e:
        print(f"❌ 拼写纠错测试失败")
        print(f"   错误: {e}")
        traceback.print_exc()
        return False, None


def test_performance():
    """性能测试"""
    print_section("步骤 7: 性能测试")
    
    try:
        import os
        os.environ["MACRO_CORRECT_FLAG_CSC_PUNCT"] = "1"
        from macro_correct import correct_punct
        
        # 批量测试
        test_text = "今天天气怎么样我们去哪里玩"
        batch_sizes = [1, 5, 10]
        
        print("性能基准测试:")
        print(f"  测试文本: {test_text}")
        print(f"  文本长度: {len(test_text)} 字符\n")
        
        for batch_size in batch_sizes:
            texts = [test_text] * batch_size
            
            start_time = time.time()
            results = correct_punct(texts)
            elapsed = time.time() - start_time
            
            avg_time = elapsed / batch_size
            
            print(f"  批次大小: {batch_size:2d} 条")
            print(f"    总耗时: {elapsed:.2f} 秒")
            print(f"    平均: {avg_time:.2f} 秒/条")
            print(f"    速率: {1/avg_time:.2f} 条/秒\n")
        
        # 内存占用估算
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            print(f"  当前内存占用: {memory_mb:.0f} MB\n")
        except:
            print("  (无法获取内存信息，需安装 psutil)\n")
        
        print("✅ 性能测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 性能测试失败: {e}")
        traceback.print_exc()
        return False


def generate_report(results):
    """生成测试报告"""
    print_section("测试总结报告")
    
    print("📊 测试结果汇总:\n")
    
    for step, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {step}: {status}")
    
    print("\n" + "="*60)
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 所有测试通过！macro-correct 可以在此环境运行")
        print("\n建议:")
        print("  1. 性能若 <15秒/条，可以考虑集成到项目")
        print("  2. 内存占用若 <1.5GB，可以替代 Qwen2.5-0.5B")
        print("  3. 否则保持使用 llama-cpp-python + Qwen2.5-0.5B")
    else:
        print("\n❌ 部分测试失败，macro-correct 不适合此环境")
        print("\n建议:")
        print("  继续使用 llama-cpp-python + Qwen2.5-0.5B 方案")
    
    print("\n" + "="*60 + "\n")


def main():
    """主测试流程"""
    print("="*60)
    print("  macro-correct 树莓派适配性测试")
    print("  目标: 验证能否替代 Qwen2.5-0.5B 用于标点纠错")
    print("="*60)
    
    results = {}
    
    # 1. 检查 PyTorch
    has_pytorch = check_pytorch()
    
    # 2. 如果没有，尝试安装
    if not has_pytorch:
        print("\n⚠️  PyTorch 是 macro-correct 的必需依赖")
        response = input("是否尝试安装 PyTorch? (这可能需要 15 分钟) [y/N]: ")
        
        if response.lower() in ['y', 'yes']:
            has_pytorch = install_pytorch()
        else:
            print("\n❌ 跳过安装，测试终止")
            print("   建议: 保持使用 llama-cpp-python + Qwen2.5-0.5B")
            return
    
    results['PyTorch 安装'] = has_pytorch
    if not has_pytorch:
        generate_report(results)
        return
    
    # 3. 检查 macro-correct
    has_macro = check_macro_correct()
    
    # 4. 如果没有，尝试安装
    if not has_macro:
        has_macro = install_macro_correct()
    
    results['macro-correct 安装'] = has_macro
    if not has_macro:
        generate_report(results)
        return
    
    # 5. 功能测试 - 标点纠错
    punct_ok, _ = test_punct_correction()
    results['标点纠错功能'] = punct_ok
    
    # 6. 功能测试 - 拼写纠错 (可选)
    csc_ok, _ = test_csc_correction()
    results['拼写纠错功能'] = csc_ok
    
    # 7. 性能测试
    if punct_ok:
        perf_ok = test_performance()
        results['性能测试'] = perf_ok
    
    # 8. 生成报告
    generate_report(results)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生未预期的错误:")
        print(f"   {e}")
        traceback.print_exc()
        sys.exit(1)
