#!/usr/bin/env python3
import requests

r = requests.post('http://localhost:5000/api/correct_text', json={'text': '测试 测试 今天天气怎么样'})
print(r.json())
