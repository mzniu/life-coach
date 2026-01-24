#!/usr/bin/env python3
"""测试 macro-correct 官方示例"""

import os
os.environ["MACRO_CORRECT_FLAG_CSC_TOKEN"] = "1"
from macro_correct import correct

# 官方示例
text_list = ["真麻烦你了。希望你们好好的跳无",
             "少先队员因该为老人让坐",
             "机七学习是人工智能领遇最能体现智能的一个分知",
             "一只小鱼船浮在平净的河面上",
             "今天天汽怎么样",
             "他在北经工作",
             "我喜欢吃平果"
             ]

print("测试 macro-correct 官方示例")
print("=" * 60)

text_csc = correct(text_list)
for res_i in text_csc:
    source = res_i.get('source', '')
    target = res_i.get('target', '')
    errors = res_i.get('errors', [])
    
    print(f"\n输入: {source}")
    print(f"输出: {target}")
    if errors:
        print(f"修改: {len(errors)} 处")
        for err in errors:
            print(f"  - 位置{err[2]}: '{err[0]}' → '{err[1]}' (置信度: {err[3]:.4f})")
    else:
        print("修改: 无")

print("\n" + "=" * 60)
