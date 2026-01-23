#!/usr/bin/env python3
import requests

r = requests.post('http://localhost:5000/api/correct_text', json={'text': '今天天气怎么样 我们去哪里玩'})
print(r.json())
