#!/usr/bin/env python3
"""
测试修复后的"重新纠正"功能
验证使用 original_content 而不是 content
"""

import requests
import json
import sys

API_BASE = "http://192.168.1.28:5000/api"

def test_get_recording_detail():
    """测试获取录音详情是否返回 original_content 字段"""
    print("\n=== 测试1: 获取录音详情 ===")
    
    # 获取最近录音
    resp = requests.get(f"{API_BASE}/recordings?limit=1")
    if not resp.ok:
        print(f"❌ 获取录音列表失败: {resp.status_code}")
        return None
    
    recordings = resp.json().get('recordings', [])
    if not recordings:
        print("⚠️ 没有录音记录")
        return None
    
    recording_id = recordings[0]['id']
    print(f"📝 录音ID: {recording_id}")
    
    # 获取详情
    resp = requests.get(f"{API_BASE}/recordings/{recording_id}")
    if not resp.ok:
        print(f"❌ 获取详情失败: {resp.status_code}")
        return None
    
    data = resp.json()
    recording = data.get('recording', {})
    
    # 检查字段
    has_original = 'original_content' in recording
    has_corrected = 'corrected_content' in recording
    has_content = 'content' in recording
    
    print(f"✓ 包含 original_content: {has_original}")
    print(f"✓ 包含 corrected_content: {has_corrected}")
    print(f"✓ 包含 content (兼容): {has_content}")
    
    if not has_original:
        print("❌ 缺少 original_content 字段！")
        return None
    
    # 显示内容（前50字符）
    original = recording.get('original_content', '')
    corrected = recording.get('corrected_content')
    content = recording.get('content', '')
    
    print(f"\n原始内容: {original[:50]}...")
    if corrected:
        print(f"纠正内容: {corrected[:50]}...")
    else:
        print("纠正内容: (无)")
    print(f"兼容字段: {content[:50]}...")
    
    return recording_id

def test_recorrection(recording_id):
    """测试重新纠正功能"""
    print(f"\n=== 测试2: 重新纠正功能 ===")
    
    if not recording_id:
        print("⚠️ 跳过测试（没有录音ID）")
        return
    
    # 获取详情
    resp = requests.get(f"{API_BASE}/recordings/{recording_id}")
    recording = resp.json().get('recording', {})
    
    original_text = recording.get('original_content')
    if not original_text:
        print("❌ 没有 original_content，无法测试")
        return
    
    print(f"📝 使用原始文本纠正（前50字）: {original_text[:50]}...")
    
    # 调用纠正API
    resp = requests.post(
        f"{API_BASE}/correct_text",
        json={"text": original_text},
        timeout=30
    )
    
    if not resp.ok:
        print(f"❌ 纠正失败: {resp.status_code}")
        print(resp.text)
        return
    
    result = resp.json()
    
    if not result.get('success'):
        print(f"❌ 纠正失败: {result.get('error')}")
        return
    
    corrected = result.get('corrected', '')
    changed = result.get('changed', False)
    time_ms = result.get('time_ms', 0)
    from_cache = result.get('from_cache', False)
    
    print(f"✓ 纠正成功")
    print(f"  - 有修改: {changed}")
    print(f"  - 耗时: {time_ms}ms")
    print(f"  - 来源: {'缓存' if from_cache else '模型'}")
    print(f"  - 纠正后文本（前50字）: {corrected[:50]}...")
    
    # 验证纠正后文本不是重复标点符号
    if corrected.startswith('；；；；') or corrected.startswith(';;;;'):
        print("❌ 检测到Bug！纠正后文本是重复标点符号")
        return False
    
    print("✓ 纠正结果正常（不是重复标点符号）")
    
    # 保存纠正结果
    resp = requests.post(
        f"{API_BASE}/recordings/{recording_id}/corrected",
        json={
            "corrected_text": corrected,
            "changes": result.get('changes', '')
        }
    )
    
    if resp.ok:
        print(f"✓ 纠正结果已保存")
    else:
        print(f"⚠️ 保存失败: {resp.status_code}")
    
    return True

def main():
    print("=" * 60)
    print("测试修复后的'重新纠正'功能")
    print("=" * 60)
    
    try:
        # 测试1: 获取录音详情
        recording_id = test_get_recording_detail()
        
        # 测试2: 重新纠正
        if recording_id:
            success = test_recorrection(recording_id)
            
            print("\n" + "=" * 60)
            if success:
                print("✅ 所有测试通过！")
                print("=" * 60)
                sys.exit(0)
            else:
                print("❌ 测试失败")
                print("=" * 60)
                sys.exit(1)
        else:
            print("\n⚠️ 无法完成测试（没有录音记录）")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
