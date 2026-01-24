#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简单测试 macro-correct"""

import os
import time

print("=" * 60)
print("  macro-correct 简单功能测试")
print("=" * 60)

# 测试1: 检查安装
print("\n1. 检查模块...")
try:
    import macro_correct
    print("✅ macro_correct 已导入")
except:
    print("❌ 导入失败")
    exit(1)

# 测试2: 尝试标点纠错
print("\n2. 测试标点纠错...")
try:
    os.environ["MACRO_CORRECT_FLAG_CSC_PUNCT"] = "1"
    from macro_correct.predict_csc_punct_zh import MacroCSC4Punct
    
    corrector = MacroCSC4Punct()
    
    test_text = "今天天气怎么样我们去哪里玩"
    print(f"   输入: {test_text}")
    
    start = time.time()
    result = corrector.func_csc_punct_batch([test_text])
    elapsed = time.time() - start
    
    print(f"   输出: {result[0]['target']}")
    print(f"   耗时: {elapsed:.2f} 秒")
    print("✅ 标点纠错成功")
    
except Exception as e:
    print(f"❌ 失败: {e}")
    import traceback
    traceback.print_exc()

# 测试3: 尝试拼写纠错
print("\n3. 测试拼写纠错...")
try:
    os.environ["MACRO_CORRECT_FLAG_CSC_TOKEN"] = "1"
    from macro_correct.predict_csc_token_zh import MacroCSC4Token
    
    corrector = MacroCSC4Token()
    
    test_text = "少先队员因该为老人让坐"
    print(f"   输入: {test_text}")
    
    start = time.time()
    result = corrector.func_csc_token_batch([test_text])
    elapsed = time.time() - start
    
    print(f"   输出: {result[0]['target']}")
    print(f"   耗时: {elapsed:.2f} 秒")
    print("✅ 拼写纠错成功")
    
except Exception as e:
    print(f"❌ 失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
