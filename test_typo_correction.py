#!/usr/bin/env python3
"""测试 macro-correct 错别字纠正能力"""

import requests
import json

test_cases = [
    {'text': '今天天气怎么样', 'desc': '只需要加标点'},
    {'text': '今天天汽怎么样', 'desc': '错别字：汽→气'},
    {'text': '我想去那里玩', 'desc': '错别字：那→哪'},
    {'text': '这个产品真的很好用', 'desc': '只需要加标点'},
    {'text': '这个产品真的很好勇', 'desc': '错别字：勇→用'},
    {'text': '他在北经工作', 'desc': '错别字：经→京'},
    {'text': '我喜欢吃平果', 'desc': '错别字：平→苹'},
]

print('测试 macro-correct 错别字纠正能力')
print('=' * 60)

for i, case in enumerate(test_cases, 1):
    text = case['text']
    desc = case['desc']
    
    print(f'\n测试 {i}: {desc}')
    print(f'输入: {text}')
    
    try:
        r = requests.post(
            'http://localhost:5000/api/correct_text',
            json={'text': text},
            timeout=30
        )
        
        if r.ok:
            result = r.json()
            if result.get('success'):
                corrected = result.get('corrected', '')
                changed = result.get('changed', False)
                changes = result.get('changes', [])
                
                print(f'输出: {corrected}')
                changed_text = '是' if changed else '否'
                print(f'修改: {changed_text}')
                
                if changed and isinstance(changes, list):
                    for change in changes:
                        desc_text = change.get('description', '')
                        print(f'  - {desc_text}')
            else:
                error_msg = result.get('error')
                print(f'错误: {error_msg}')
        else:
            print(f'HTTP错误: {r.status_code}')
            
    except Exception as e:
        print(f'异常: {e}')

print('\n' + '=' * 60)
