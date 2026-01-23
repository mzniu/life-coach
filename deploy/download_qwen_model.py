#!/usr/bin/env python3
"""
Qwen2.5-0.5B 模型下载脚本
从 HuggingFace 镜像下载 GGUF 格式模型
支持断点续传和 SHA256 校验
"""

import os
import sys
import hashlib
import requests
from tqdm import tqdm
from pathlib import Path

# 模型配置
MODEL_NAME = "qwen2.5-0.5b-instruct-q4_k_m.gguf"
MODEL_URL = "https://hf-mirror.com/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
MODEL_SHA256 = None  # 如果有校验和可以填写

# 默认下载目录
DEFAULT_OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "LifeCoach", "models", "qwen2.5-0.5b")


def calculate_sha256(file_path, chunk_size=8192):
    """计算文件 SHA256 校验和"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()


def download_file(url, output_path, resume=True):
    """
    下载文件，支持断点续传
    
    Args:
        url: 下载链接
        output_path: 输出文件路径
        resume: 是否支持断点续传
    """
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 检查文件是否已存在
    headers = {}
    if resume and os.path.exists(output_path):
        existing_size = os.path.getsize(output_path)
        headers['Range'] = f'bytes={existing_size}-'
        print(f"检测到已下载 {existing_size / 1024 / 1024:.1f} MB，继续下载...")
    else:
        existing_size = 0
    
    try:
        # 发起请求
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        
        # 检查是否支持断点续传
        if response.status_code == 206:
            mode = 'ab'  # 追加模式
            print("服务器支持断点续传")
        elif response.status_code == 200:
            mode = 'wb'  # 覆写模式
            existing_size = 0
            print("从头开始下载")
        else:
            print(f"错误: HTTP {response.status_code}")
            return False
        
        # 获取文件总大小
        total_size = int(response.headers.get('content-length', 0)) + existing_size
        
        print(f"文件大小: {total_size / 1024 / 1024:.1f} MB")
        print(f"下载到: {output_path}")
        
        # 下载文件
        with open(output_path, mode) as f:
            with tqdm(total=total_size, initial=existing_size, 
                     unit='B', unit_scale=True, unit_divisor=1024) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        
        print("✓ 下载完成!")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"下载失败: {e}")
        return False
    except KeyboardInterrupt:
        print("\n下载已中断，下次运行时将继续")
        return False


def verify_file(file_path, expected_sha256):
    """验证文件 SHA256 校验和"""
    if not expected_sha256:
        print("跳过校验（未提供校验和）")
        return True
    
    print("正在验证文件完整性...")
    actual_sha256 = calculate_sha256(file_path)
    
    if actual_sha256 == expected_sha256:
        print("✓ 文件校验通过")
        return True
    else:
        print(f"✗ 文件校验失败!")
        print(f"  期望: {expected_sha256}")
        print(f"  实际: {actual_sha256}")
        return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='下载 Qwen2.5-0.5B GGUF 模型')
    parser.add_argument('-o', '--output', default=DEFAULT_OUTPUT_DIR,
                       help=f'输出目录 (默认: {DEFAULT_OUTPUT_DIR})')
    parser.add_argument('--no-resume', action='store_true',
                       help='禁用断点续传，从头下载')
    parser.add_argument('--verify', action='store_true',
                       help='下载后验证文件完整性')
    
    args = parser.parse_args()
    
    # 输出路径
    output_path = os.path.join(args.output, MODEL_NAME)
    
    print("=" * 60)
    print("Qwen2.5-0.5B GGUF 模型下载器")
    print("=" * 60)
    print(f"模型: {MODEL_NAME}")
    print(f"来源: HuggingFace 镜像")
    print(f"大小: ~330 MB")
    print("=" * 60)
    print()
    
    # 检查文件是否已存在且完整
    if os.path.exists(output_path) and not args.no_resume:
        file_size = os.path.getsize(output_path)
        print(f"文件已存在: {output_path}")
        print(f"大小: {file_size / 1024 / 1024:.1f} MB")
        
        # 如果文件大小合理（>300MB），询问是否跳过
        if file_size > 300 * 1024 * 1024:
            response = input("文件可能已完整下载，是否跳过下载? (y/N): ")
            if response.lower() == 'y':
                if args.verify and MODEL_SHA256:
                    verify_file(output_path, MODEL_SHA256)
                print("\n使用现有文件。")
                return 0
    
    # 下载文件
    success = download_file(MODEL_URL, output_path, resume=not args.no_resume)
    
    if not success:
        print("\n下载失败，请稍后重试")
        return 1
    
    # 验证文件
    if args.verify and MODEL_SHA256:
        if not verify_file(output_path, MODEL_SHA256):
            print("\n警告: 文件可能已损坏，建议重新下载")
            return 1
    
    print("\n" + "=" * 60)
    print("✓ 模型下载成功!")
    print("=" * 60)
    print(f"文件路径: {output_path}")
    print()
    print("使用说明:")
    print("1. 在 .env 文件中设置: TEXT_CORRECTION_ENABLED=true")
    print(f"2. 确保模型路径正确: TEXT_CORRECTION_MODEL={output_path}")
    print("3. 重启 Life Coach 服务")
    print()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
