"""
文件存储管理模块
负责录音文件的保存、查询、删除
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
import src.config as config

class FileStorage:
    """文件存储管理器"""
    
    def __init__(self):
        # 每次从config读取，而不是缓存路径
        print(f"[文件存储] 初始化存储路径: {config.STORAGE_BASE}")
    
    @property
    def base_path(self):
        """动态获取存储路径"""
        path = Path(config.STORAGE_BASE)
        path.mkdir(parents=True, exist_ok=True)
        return path
        
    def save(self, recording_id, content, metadata=None):
        """
        保存录音记录
        recording_id: 格式为 "2026-01-21/15-30"
        content: 转写文本内容
        metadata: 额外元数据（时长、字数等）
        """
        date_str, time_str = recording_id.split('/')
        date_dir = self.base_path / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = date_dir / f"{time_str}.txt"
        
        # 如果文件已存在，添加后缀
        counter = 2
        while file_path.exists():
            file_path = date_dir / f"{time_str}_{counter}.txt"
            counter += 1
        
        # 构建文件内容
        now = datetime.now()
        header = f"""=== Life Coach 对话记录 ===
录音时间: {date_str} {time_str.replace('-', ':')}
录音时长: {metadata.get('duration', 0) if metadata else 0}秒
文字长度: {len(content)}字
---
"""
        footer = f"\n---\n保存时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        full_content = header + content + footer
        
        # 保存文件
        file_path.write_text(full_content, encoding='utf-8')
        print(f"[文件存储] 已保存: {file_path}")
        
        return str(file_path)
    
    def save_audio(self, recording_id, audio_data, sample_rate=16000):
        """
        保存音频文件
        recording_id: 格式为 "2026-01-21/15-30"
        audio_data: numpy数组或字节数据
        sample_rate: 采样率
        """
        import numpy as np
        import wave
        
        date_str, time_str = recording_id.split('/')
        date_dir = self.base_path / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # 使用与txt文件相同的命名规则
        audio_path = date_dir / f"{time_str}.wav"
        
        # 如果文件已存在，添加后缀
        counter = 2
        while audio_path.exists():
            audio_path = date_dir / f"{time_str}_{counter}.wav"
            counter += 1
        
        # 合并音频数据并确保为int16格式
        if isinstance(audio_data, list):
            # 检查第一个元素的类型
            if len(audio_data) > 0:
                if isinstance(audio_data[0], np.ndarray):
                    # 已经是numpy数组列表，直接合并
                    audio_data = np.concatenate(audio_data)
                else:
                    # 是普通list，需要flatten并转换
                    flat_data = []
                    for chunk in audio_data:
                        if isinstance(chunk, list):
                            flat_data.extend(chunk)
                        else:
                            flat_data.extend(chunk.tolist())
                    audio_data = np.array(flat_data, dtype=np.int16)
            else:
                audio_data = np.array([], dtype=np.int16)
        
        # 检查数据类型并转换（仅当数据是float时才需要缩放）
        if audio_data.dtype == np.float32 or audio_data.dtype == np.float64:
            # float数据范围是-1.0到1.0，需要转换为int16范围
            audio_data = (audio_data * 32767).astype(np.int16)
        elif audio_data.dtype != np.int16:
            # 其他类型直接转换
            audio_data = audio_data.astype(np.int16)
        
        # 保存WAV文件
        with wave.open(str(audio_path), 'wb') as wf:
            wf.setnchannels(1)  # 单声道
            wf.setsampwidth(2)   # 16bit = 2 bytes
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())
        
        print(f"[文件存储] 已保存音频: {audio_path}")
        return str(audio_path)
    
    def save_corrected(self, recording_id, corrected_text, changes):
        """
        保存纠正后的文本
        recording_id: 格式为 "2026-01-21/15-30"
        corrected_text: 纠正后的文本
        changes: 修改详情
        """
        date_str, time_str = recording_id.split('/')
        date_dir = self.base_path / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存为 .corrected.txt 文件
        corrected_path = date_dir / f"{time_str}.corrected.txt"
        
        # 构建文件内容
        now = datetime.now()
        header = f"""=== 文本纠错结果 ===
纠错时间: {now.strftime('%Y-%m-%d %H:%M:%S')}
修改详情: {changes}
---
"""
        footer = f"\n---\n保存时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        full_content = header + corrected_text + footer
        
        # 保存文件
        corrected_path.write_text(full_content, encoding='utf-8')
        print(f"[文件存储] 已保存纠正文本: {corrected_path}")
        return str(corrected_path)
    
    def get_corrected(self, recording_id):
        """
        获取纠正后的文本
        recording_id: 格式为 "2026-01-21/15-30"
        """
        date_str, time_str = recording_id.split('/')
        date_dir = self.base_path / date_str
        corrected_path = date_dir / f"{time_str}.corrected.txt"
        
        if not corrected_path.exists():
            return None
        
        try:
            content = corrected_path.read_text(encoding='utf-8')
            # 提取纯文本内容
            content_start = content.find('---\n') + 4
            content_end = content.rfind('\n---')
            text_content = content[content_start:content_end].strip() if content_end > content_start else content
            return text_content
        except Exception as e:
            print(f"[文件存储] 读取纠正文本失败: {e}")
            return None
    
    def update_transcription(self, recording_id, new_text):
        """
        更新录音的转写文本（重新识别后使用）
        recording_id: 格式为 "2026-01-21/15-30"
        new_text: 新的转写文本
        """
        date_str, time_str = recording_id.split('/')
        date_dir = self.base_path / date_str
        file_path = date_dir / f"{time_str}.txt"
        
        if not file_path.exists():
            print(f"[文件存储] 录音文件不存在: {file_path}")
            return False
        
        try:
            # 读取现有文件获取元数据
            content = file_path.read_text(encoding='utf-8')
            
            # 提取头部元数据（保留原有的录音时间等信息）
            header_end = content.find('---\n')
            if header_end > 0:
                header = content[:header_end + 4]
            else:
                # 如果没有找到分隔符，保留前3行
                lines = content.split('\n', 3)
                header = '\n'.join(lines[:3]) + '\n---\n'
            
            # 构建新内容
            now = datetime.now()
            footer = f"\n---\n更新时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
            new_content = header + new_text + footer
            
            # 保存文件
            file_path.write_text(new_content, encoding='utf-8')
            print(f"[文件存储] 已更新转写文本: {file_path}")
            
            # 删除旧的纠正文本（如果存在）
            corrected_path = date_dir / f"{time_str}.corrected.txt"
            if corrected_path.exists():
                corrected_path.unlink()
                print(f"[文件存储] 已删除旧的纠正文本: {corrected_path}")
            
            return True
        except Exception as e:
            print(f"[文件存储] 更新转写文本失败: {e}")
            return False

    def query(self, date=None, limit=20):
        """
        查询录音列表
        date: 日期过滤（格式：2026-01-21）
        limit: 返回数量限制
        """
        recordings = []
        
        if date:
            # 查询指定日期
            date_dir = self.base_path / date
            if date_dir.exists():
                recordings.extend(self._scan_directory(date_dir, date))
        else:
            # 查询所有日期
            for date_dir in sorted(self.base_path.iterdir(), reverse=True):
                if date_dir.is_dir():
                    recordings.extend(self._scan_directory(date_dir, date_dir.name))
                    if len(recordings) >= limit:
                        break
        
        # 按时间倒序排序
        recordings.sort(key=lambda x: x['date'] + ' ' + x['time'], reverse=True)
        
        return recordings[:limit]
        
    def _scan_directory(self, directory, date_str):
        """扫描目录中的录音文件"""
        recordings = []
        
        for file_path in directory.glob("*.txt"):
            # 跳过纠正后的文本文件（.corrected.txt）
            if '.corrected' in file_path.stem:
                continue
            
            try:
                # 读取文件内容
                content = file_path.read_text(encoding='utf-8')
                
                # 解析文件名（格式：15-30.txt 或 15-30_2.txt）
                filename = file_path.stem
                time_str = filename.split('_')[0]  # 去掉后缀
                
                # 提取元数据
                lines = content.split('\n')
                duration = 0.0
                word_count = len(content)
                
                for line in lines:
                    if line.startswith('录音时长:'):
                        duration = float(line.split(':')[1].replace('秒', '').strip())
                    elif line.startswith('文字长度:'):
                        word_count = int(line.split(':')[1].replace('字', '').strip())
                
                # 提取内容预览（前50字）和完整文本
                content_start = content.find('---\n') + 4
                content_end = content.rfind('\n---')
                if content_start > 3 and content_end > content_start:
                    text_content = content[content_start:content_end].strip()
                    preview = text_content[:50] + '...' if len(text_content) > 50 else text_content
                    full_text = text_content  # 完整文本
                else:
                    preview = "无内容"
                    full_text = ""
                
                recordings.append({
                    'id': f"{date_str}/{time_str}",
                    'date': date_str,
                    'time': time_str.replace('-', ':'),
                    'duration': duration,
                    'word_count': word_count,
                    'preview': preview,
                    'full_text': full_text,  # 添加完整文本
                    'file_path': str(file_path)
                })
                
            except Exception as e:
                print(f"[文件存储] 解析文件失败: {file_path}, 错误: {e}")
                continue
        
        return recordings
        
    def get(self, recording_id):
        """
        获取单条录音详情
        recording_id: 格式为 "2026-01-21/15-30"
        
        返回字段说明:
        - original_content: 原始ASR识别文本（来自 .txt 文件）
        - corrected_content: 纠错后文本（来自 .corrected.txt 文件，如果存在）
        - content: 向后兼容字段，优先返回纠错后文本
        """
        date_str, time_str = recording_id.split('/')
        date_dir = self.base_path / date_str
        
        # 查找原始文件
        original_file = date_dir / f"{time_str}.txt"
        if not original_file.exists():
            return None
        
        try:
            # 读取原始文本
            original_content = original_file.read_text(encoding='utf-8')
            content_start = original_content.find('---\n') + 4
            content_end = original_content.rfind('\n---')
            original_text = original_content[content_start:content_end].strip() if content_end > content_start else original_content
            
            # 解析元数据
            lines = original_content.split('\n')
            duration = 0.0
            
            for line in lines:
                if line.startswith('录音时长:'):
                    duration = float(line.split(':')[1].replace('秒', '').strip())
            
            # 查找纠错后的文本
            corrected_file = date_dir / f"{time_str}.corrected.txt"
            corrected_text = None
            if corrected_file.exists():
                try:
                    corrected_content = corrected_file.read_text(encoding='utf-8')
                    content_start = corrected_content.find('---\n') + 4
                    content_end = corrected_content.rfind('\n---')
                    corrected_text = corrected_content[content_start:content_end].strip() if content_end > content_start else corrected_content
                except Exception as e:
                    print(f"[文件存储] 读取纠错文件失败: {corrected_file}, 错误: {e}")
            
            # 查找对应的音频文件
            audio_path = None
            audio_file = date_dir / f"{time_str}.wav"
            if audio_file.exists():
                audio_path = str(audio_file)
            
            # 返回结果
            return {
                'id': recording_id,
                'date': date_str,
                'time': time_str.replace('-', ':'),
                'duration': duration,
                'word_count': len(original_text),
                'original_content': original_text,  # 新增：原始文本
                'corrected_content': corrected_text,  # 新增：纠错后文本（可能为None）
                'content': corrected_text if corrected_text else original_text,  # 向后兼容：优先返回纠错后文本
                'audio_path': audio_path
            }
            
        except Exception as e:
            print(f"[文件存储] 读取文件失败: {original_file}, 错误: {e}")
            return None
        
    def delete(self, recording_id):
        """
        删除录音
        recording_id: 格式为 "2026-01-21/15-30"
        """
        date_str, time_str = recording_id.split('/')
        date_dir = self.base_path / date_str
        
        # 查找文件
        file_path = date_dir / f"{time_str}.txt"
        if not file_path.exists():
            for candidate in date_dir.glob(f"{time_str}*.txt"):
                file_path = candidate
                break
        
        if file_path.exists():
            file_path.unlink()
            print(f"[文件存储] 已删除: {file_path}")
            
            # 如果目录为空，删除日期目录
            if not any(date_dir.iterdir()):
                date_dir.rmdir()
                print(f"[文件存储] 删除空目录: {date_dir}")
            
            return True
        else:
            print(f"[文件存储] 文件不存在: {recording_id}")
            return False
        
    def get_today_count(self):
        """获取今日录音数量"""
        today = datetime.now().strftime("%Y-%m-%d")
        date_dir = self.base_path / today
        
        if date_dir.exists():
            return len(list(date_dir.glob("*.txt")))
        return 0
        
    def get_storage_info(self):
        """获取存储信息"""
        try:
            total, used, free = shutil.disk_usage(self.base_path)
            return {
                'total_gb': total / (1024**3),
                'used_gb': used / (1024**3),
                'free_gb': free / (1024**3)
            }
        except:
            return {'total_gb': 0, 'used_gb': 0, 'free_gb': 0}
        
    def cleanup(self):
        """清理资源"""
        print("[文件存储] 清理资源")
