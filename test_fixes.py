#!/usr/bin/env python3
"""测试修复效果：1. 录音列表过滤 .corrected 文件  2. 纠错API详细日志"""

import requests
import json

API_BASE = "http://192.168.1.28:5000/api"

print("=" * 60)
print("测试1: 检查录音列表是否过滤了 .corrected 文件")
print("=" * 60)

resp = requests.get(f"{API_BASE}/recordings?limit=10")
if resp.ok:
    data = resp.json()
    recordings = data.get('recordings', [])
    
    print(f"\n获取到 {len(recordings)} 条录音记录:\n")
    
    has_corrected = False
    for rec in recordings:
        rec_id = rec.get('id', '')
        print(f"  - {rec_id}")
        
        if '.corrected' in rec_id:
            has_corrected = True
            print(f"    ⚠️ 发现 .corrected 文件！")
    
    if has_corrected:
        print("\n❌ 测试失败：列表中仍包含 .corrected 文件")
    else:
        print("\n✅ 测试通过：列表中不包含 .corrected 文件")
else:
    print(f"❌ 请求失败: {resp.status_code}")

print("\n" + "=" * 60)
print("测试2: 纠错API详细日志（请查看服务器日志）")
print("=" * 60)

test_text = "今天天汽怎么样我想去那里玩"
print(f"\n发送纠错请求: {test_text}\n")

resp = requests.post(
    f"{API_BASE}/correct_text",
    json={"text": test_text},
    timeout=30
)

if resp.ok:
    result = resp.json()
    print(f"✅ 纠错成功:")
    print(f"  - 原始: {result.get('original', '')}")
    print(f"  - 纠正: {result.get('corrected', '')}")
    print(f"  - 修改: {result.get('changed', False)}")
    print(f"  - 耗时: {result.get('time_ms', 0)}ms")
    print(f"  - 来源: {'缓存' if result.get('from_cache') else '模型'}")
    
    changes = result.get('changes', [])
    if changes:
        print(f"  - 修改详情: {len(changes)} 处")
else:
    print(f"❌ 请求失败: {resp.status_code}")

print("\n提示: 请查看服务器日志以验证详细日志输出")
print("命令: ssh cmit@192.168.1.28 \"sudo journalctl -u lifecoach -f --no-pager\"")
print("\n" + "=" * 60)
