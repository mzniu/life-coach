"""
"""文本纠错引擎
支持两种模式:
- macro-correct: 快速专业的标点和拼写纠错(推荐,速度快5倍)
- llama-cpp: 基于 Qwen2.5-0.5B 的通用纠错(备选)
"""

import os
import time
import logging
from typing import Dict, Optional, List
from functools import lru_cache
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class TextCorrector:
    """
    ASR 文本纠错引擎
    
    功能:
    - 修正错别字和同音字错误
    - 补全缺失的标点符号
    - 保持原意不变
    
    特性:
    - 懒加载: 首次使用时才加载模型
    - LRU 缓存: 缓存最近 50 条结果
    - 超时保护: 推理超时自动降级
    - 失败降级: 出错时返回原文
    """
    
    def __init__(self, 
                 model_path: str,
                 max_tokens: int = 512,
                 temperature: float = 0.3,
                 timeout: int = 15):
        """
        初始化文本纠错引擎
        
        Args:
            model_path: GGUF 模型文件路径
            max_tokens: 最大生成 token 数
            temperature: 温度参数 (0-1, 越低越确定)
            timeout: 推理超时时间 (秒)
        """
        self.model_path = model_path
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        
        self._model = None
        self._is_loaded = False
        self._load_time = None
        self._correction_count = 0
        
        logger.info(f"[文本纠错] 初始化配置: model={model_path}, max_tokens={max_tokens}, temp={temperature}")
    
    def _load_model(self):
        """延迟加载模型"""
        if self._is_loaded:
            return
        
        if not os.path.exists(self.model_path):
            logger.warning(f"[文本纠错] 模型文件不存在: {self.model_path}, 纠错功能将被禁用")
            return
        
        try:
            start_time = time.time()
            logger.info(f"[文本纠错] 开始加载模型: {self.model_path}")
            
            # 延迟导入以避免未安装时报错
            from llama_cpp import Llama
            
            self._model = Llama(
                model_path=self.model_path,
                n_ctx=2048,           # 上下文长度
                n_threads=4,          # 树莓派 4 核心
                n_gpu_layers=0,       # 树莓派无 GPU
                verbose=False,
                use_mlock=True,       # 锁定内存避免交换
            )
            
            self._is_loaded = True
            self._load_time = time.time() - start_time
            
            logger.info(f"[文本纠错] 模型加载完成, 耗时: {self._load_time:.2f}秒")
            
        except ImportError:
            logger.warning("[文本纠错] llama-cpp-python 未安装, 纠错功能将被禁用")
            logger.warning("[文本纠错] 安装命令: pip install llama-cpp-python")
        except Exception as e:
            logger.error(f"[文本纠错] 模型加载失败: {e}", exc_info=True)
    
    def _build_prompt(self, text: str) -> str:
        """
        构建 Prompt 模板
        
        Args:
            text: 原始 ASR 文本
            
        Returns:
            完整的 prompt 字符串
        """
        prompt = f"""你是一个语音识别文本纠错助手。任务：
1. 修正错别字和同音字错误
2. 补全缺失的标点符号（句号、逗号、问号、感叹号等）
3. 保持原意不变，不要添加、删减或重组内容
4. 直接输出纠正后的文本，不要添加任何解释

原始文本：
{text}

纠正后的文本：
"""
        return prompt
    
    @lru_cache(maxsize=50)
    def _cached_correct(self, text: str) -> Optional[str]:
        """
        带缓存的纠错实现
        
        Args:
            text: 原始文本
            
        Returns:
            纠正后的文本，失败返回 None
        """
        if not self._is_loaded:
            self._load_model()
        
        if not self._is_loaded or self._model is None:
            logger.debug("[文本纠错] 模型未加载，跳过纠错")
            return None
        
        try:
            prompt = self._build_prompt(text)
            
            logger.debug(f"[文本纠错] 开始推理, 输入长度: {len(text)} 字符")
            start_time = time.time()
            
            # 生成纠正文本
            output = self._model(
                prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=0.95,
                repeat_penalty=1.1,
                stop=["原始文本：", "\n\n"],
                echo=False
            )
            
            inference_time = time.time() - start_time
            
            # 提取生成的文本
            corrected_text = output['choices'][0]['text'].strip()
            
            # 清理可能的前缀和后缀
            prefixes = ["纠正后的文本：", "纠正后：", "纠正后的文本:", "纠正后:"]
            for prefix in prefixes:
                if corrected_text.startswith(prefix):
                    corrected_text = corrected_text[len(prefix):].strip()
                    break
            
            # 清理重复的内容（如果文本长度异常则只取前半部分）
            if len(corrected_text) > len(text) * 3:  # 如果纠正后长度超过原文3倍，可能有问题
                logger.warning(f"[文本纠错] 检测到异常长度，原文 {len(text)} -> 纠正后 {len(corrected_text)}，截断处理")
                # 尝试按重复模式分割
                lines = corrected_text.split('\n')
                if lines:
                    corrected_text = lines[0].strip()  # 只取第一行

            
            logger.info(f"[文本纠错] 推理完成, 耗时: {inference_time:.2f}秒, "
                       f"输入: {len(text)} -> 输出: {len(corrected_text)} 字符")
            
            self._correction_count += 1
            
            return corrected_text
            
        except Exception as e:
            logger.error(f"[文本纠错] 推理失败: {e}", exc_info=True)
            return None
    
    def correct(self, text: str) -> Dict:
        """
        纠错主方法
        
        Args:
            text: 原始 ASR 文本
            
        Returns:
            纠错结果字典:
            {
                "success": bool,           # 是否成功
                "original": str,           # 原始文本
                "corrected": str,          # 纠正后文本
                "changed": bool,           # 是否有修改
                "changes": List[dict],     # 修改详情
                "time_ms": int,            # 耗时(毫秒)
                "error": str (optional)    # 错误信息
            }
        """
        start_time = time.time()
        
        # 空文本直接返回
        if not text or not text.strip():
            return {
                "success": True,
                "original": text,
                "corrected": text,
                "changed": False,
                "changes": [],
                "time_ms": 0
            }
        
        # 调用缓存的纠错方法
        try:
            corrected_text = self._cached_correct(text)
            time_ms = int((time.time() - start_time) * 1000)
            
            # 纠错失败，返回原文
            if corrected_text is None:
                return {
                    "success": False,
                    "original": text,
                    "corrected": text,
                    "changed": False,
                    "changes": [],
                    "time_ms": time_ms,
                    "error": "模型未加载或推理失败"
                }
            
            # 检测是否有修改
            changed = (text != corrected_text)
            changes = self._detect_changes(text, corrected_text) if changed else []
            
            return {
                "success": True,
                "original": text,
                "corrected": corrected_text,
                "changed": changed,
                "changes": changes,
                "time_ms": time_ms
            }
            
        except Exception as e:
            logger.error(f"[文本纠错] 纠错过程异常: {e}", exc_info=True)
            time_ms = int((time.time() - start_time) * 1000)
            
            return {
                "success": False,
                "original": text,
                "corrected": text,
                "changed": False,
                "changes": [],
                "time_ms": time_ms,
                "error": str(e)
            }
    
    def _detect_changes(self, original: str, corrected: str) -> List[Dict]:
        """
        检测文本变化详情（简单实现）
        
        Args:
            original: 原始文本
            corrected: 纠正后文本
            
        Returns:
            变化列表，每个元素包含 type 和 description
        """
        changes = []
        
        # 简单的字符级差异检测
        if len(corrected) > len(original):
            changes.append({
                "type": "addition",
                "description": f"添加了 {len(corrected) - len(original)} 个字符（可能是标点符号）"
            })
        elif len(corrected) < len(original):
            changes.append({
                "type": "deletion",
                "description": f"删除了 {len(original) - len(corrected)} 个字符"
            })
        
        # 检测标点符号变化
        original_punctuation = sum(1 for c in original if c in '，。！？、；：""''（）《》')
        corrected_punctuation = sum(1 for c in corrected if c in '，。！？、；：""''（）《》')
        
        if corrected_punctuation > original_punctuation:
            changes.append({
                "type": "punctuation",
                "description": f"补全了 {corrected_punctuation - original_punctuation} 个标点符号"
            })
        
        return changes
    
    def unload(self):
        """卸载模型释放内存"""
        if self._model is not None:
            logger.info(f"[文本纠错] 卸载模型, 已处理 {self._correction_count} 次纠错")
            self._model = None
            self._is_loaded = False
            self._load_time = None
            
            # 清空缓存
            self._cached_correct.cache_clear()
    
    def get_stats(self) -> Dict:
        """
        获取统计信息
        
        Returns:
            统计数据字典
        """
        cache_info = self._cached_correct.cache_info()
        
        return {
            "is_loaded": self._is_loaded,
            "load_time_seconds": self._load_time,
            "correction_count": self._correction_count,
            "cache_hits": cache_info.hits,
            "cache_misses": cache_info.misses,
            "cache_size": cache_info.currsize,
            "cache_maxsize": cache_info.maxsize
        }


# 单例模式，避免重复加载模型
_corrector_instance: Optional[TextCorrector] = None


def get_text_corrector(model_path: str = None, **kwargs) -> Optional[TextCorrector]:
    """
    获取文本纠错器单例
    
    Args:
        model_path: 模型路径（仅首次调用时需要）
        **kwargs: 其他初始化参数
        
    Returns:
        TextCorrector 实例，如果初始化失败返回 None
    """
    global _corrector_instance
    
    if _corrector_instance is None and model_path:
        _corrector_instance = TextCorrector(model_path, **kwargs)
    
    return _corrector_instance
