"""文本纠错引擎
支持两种模式:
- macro-correct: 快速专业的标点和拼写纠错(推荐,速度快5倍)
- llama-cpp: 基于 Qwen2.5-0.5B 的通用纠错(备选)
"""

import os
import time
import logging
from typing import Dict, Optional, List
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseCorrectorEngine(ABC):
    """文本纠错引擎基类"""
    
    @abstractmethod
    def load(self):
        """加载模型"""
        pass
    
    @abstractmethod
    def correct_text(self, text: str) -> Optional[str]:
        """纠错文本"""
        pass
    
    @abstractmethod
    def unload(self):
        """卸载模型"""
        pass
    
    @abstractmethod
    def get_engine_stats(self) -> Dict:
        """获取引擎统计信息"""
        pass


class MacroCorrectEngine(BaseCorrectorEngine):
    """
    macro-correct 引擎(推荐)
    
    优势:
    - 速度快: 1.5秒/条 vs 8秒/条(快5倍)
    - 专业: 错别字纠正 + 标点符号补全
    - 精准: 每个修改都有置信度评分
    
    限制:
    - 内存: 1.4GB(比 llama-cpp 多 800MB)
    - 首次加载: 16秒(但仅一次)
    
    功能:
    - CSC_TOKEN: 错别字纠正 (例: "天汽"→"天气")
    - CSC_PUNCT: 标点符号补全 (例: 句末加问号、感叹号)
    """
    
    def __init__(self):
        self._corrector = None
        self._punct_corrector = None
        self._is_loaded = False
        self._load_time = None
        self._correction_count = 0
        
        # macro-correct.correct() 参数配置
        self._correct_params = {
            "threshold": 0.55,      # token阈值过滤，降低可减少误报
            "batch_size": 32,       # 批大小
            "max_len": 256,         # 最大长度，超过部分不参与纠错
            "rounded": 4,           # 保留置信度4位小数
            "flag_confusion": True, # 使用默认混淆词典
            "flag_prob": True,      # 返回纠错token处的概率
            "flag_cut": True,       # 切分长句，按标点切分后处理
        }
        
        logger.info("[macro-correct] 初始化引擎")
    
    def load(self):
        """加载 macro-correct 模型"""
        if self._is_loaded:
            return
        
        try:
            start_time = time.time()
            logger.info("[macro-correct] 开始加载模型...")
            
            # 设置环境变量：启用错别字纠正和标点补全（必须在 import 前设置）
            os.environ["MACRO_CORRECT_FLAG_CSC_TOKEN"] = "1"
            os.environ["MACRO_CORRECT_FLAG_CSC_PUNCT"] = "1"
            
            # 导入错别字纠正函数
            from macro_correct import correct
            self._corrector = correct
            
            # 导入标点符号补全类
            from macro_correct import MacroCSC4Punct
            self._punct_corrector = MacroCSC4Punct()
            
            self._is_loaded = True
            self._load_time = time.time() - start_time
            
            logger.info(f"[macro-correct] 模型加载完成,耗时: {self._load_time:.2f}秒")
            
        except ImportError as e:
            logger.warning(f"[macro-correct] 未安装,纠错功能将被禁用: {e}")
            logger.warning("[macro-correct] 安装命令: pip install macro-correct transformers==4.30.2")
        except Exception as e:
            logger.error(f"[macro-correct] 模型加载失败: {e}", exc_info=True)
    
    def correct_text(self, text: str) -> Optional[tuple]:
        """使用 macro-correct 纠错文本
        
        Returns:
            (corrected_text, errors) 或 None
            errors 格式: [[old_char, new_char, position, confidence], ...]
        """
        if not self._is_loaded:
            self.load()
        
        if not self._is_loaded or self._corrector is None:
            logger.debug("[macro-correct] 模型未加载,跳过纠错")
            return None
        
        try:
            logger.debug(f"[macro-correct] 开始推理,输入长度: {len(text)} 字符")
            start_time = time.time()
            
            all_errors = []
            
            # 步骤1: 纠正错别字（使用配置参数）
            results = self._corrector([text], **self._correct_params)
            
            if not results or len(results) == 0:
                logger.warning("[macro-correct] 错别字纠正返回空")
                return None
            
            result = results[0]
            corrected_text = result.get('target', text)
            token_errors = result.get('errors', [])
            all_errors.extend(token_errors)
            
            logger.debug(f"[macro-correct] 错别字纠正: 发现 {len(token_errors)} 处")
            
            # 步骤2: 添加标点符号（在已纠正错别字的文本上）
            if self._punct_corrector:
                punct_results = self._punct_corrector.func_csc_punct_batch([corrected_text])
                
                if punct_results and len(punct_results) > 0:
                    punct_result = punct_results[0]
                    final_text = punct_result.get('target', corrected_text)
                    punct_errors = punct_result.get('errors', [])
                    
                    # 合并标点错误（需要调整位置，因为标点是在已纠错文本上添加的）
                    all_errors.extend(punct_errors)
                    
                    logger.debug(f"[macro-correct] 标点补全: 添加 {len(punct_errors)} 处")
                    corrected_text = final_text
                else:
                    logger.debug("[macro-correct] 标点补全返回空，保持原纠错结果")
            
            inference_time = time.time() - start_time
            logger.info(f"[macro-correct] 推理完成,耗时: {inference_time:.2f}秒,"
                       f"总修改: {len(all_errors)} 处 (错别字:{len(token_errors)}, 标点:{len(all_errors)-len(token_errors)})")
            
            self._correction_count += 1
            return (corrected_text, all_errors)
                
        except Exception as e:
            logger.error(f"[macro-correct] 推理失败: {e}", exc_info=True)
            return None
    
    def unload(self):
        """卸载模型"""
        if self._corrector is not None:
            logger.info(f"[macro-correct] 卸载模型,已处理 {self._correction_count} 次纠错")
            self._corrector = None
            self._is_loaded = False
            self._load_time = None
    
    def get_engine_stats(self) -> Dict:
        """获取引擎统计信息"""
        return {
            "engine": "macro-correct",
            "is_loaded": self._is_loaded,
            "load_time_seconds": self._load_time,
            "correction_count": self._correction_count,
        }


class LlamaCppEngine(BaseCorrectorEngine):
    """
    llama-cpp 引擎(备选)
    
    基于 Qwen2.5-0.5B GGUF 模型的通用纠错
    
    优势:
    - 内存: 600MB(轻量)
    - 加载快: 3秒
    
    限制:
    - 速度慢: 8秒/条
    - 通用模型: 非专门针对纠错任务
    """
    
    def __init__(self, model_path: str, max_tokens: int = 512, 
                 temperature: float = 0.3, timeout: int = 15):
        self.model_path = model_path
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout
        
        self._model = None
        self._is_loaded = False
        self._load_time = None
        self._correction_count = 0
        
        logger.info(f"[llama-cpp] 初始化引擎: model={model_path}")
    
    def load(self):
        """加载 llama-cpp 模型"""
        if self._is_loaded:
            return
        
        if not os.path.exists(self.model_path):
            logger.warning(f"[llama-cpp] 模型文件不存在: {self.model_path}")
            return
        
        try:
            start_time = time.time()
            logger.info(f"[llama-cpp] 开始加载模型: {self.model_path}")
            
            from llama_cpp import Llama
            
            self._model = Llama(
                model_path=self.model_path,
                n_ctx=2048,
                n_threads=4,
                n_gpu_layers=0,
                verbose=False,
                use_mlock=True,
            )
            
            self._is_loaded = True
            self._load_time = time.time() - start_time
            
            logger.info(f"[llama-cpp] 模型加载完成,耗时: {self._load_time:.2f}秒")
            
        except ImportError:
            logger.warning("[llama-cpp] llama-cpp-python 未安装")
        except Exception as e:
            logger.error(f"[llama-cpp] 模型加载失败: {e}", exc_info=True)
    
    def correct_text(self, text: str) -> Optional[str]:
        """使用 llama-cpp 纠错文本"""
        if not self._is_loaded:
            self.load()
        
        if not self._is_loaded or self._model is None:
            logger.debug("[llama-cpp] 模型未加载,跳过纠错")
            return None
        
        try:
            prompt = f"""你是一个语音识别文本纠错助手。任务:
1. 修正错别字和同音字错误
2. 补全缺失的标点符号(句号、逗号、问号、感叹号等)
3. 保持原意不变,不要添加、删减或重组内容
4. 直接输出纠正后的文本,不要添加任何解释

原始文本:
{text}

纠正后的文本:
"""
            
            logger.debug(f"[llama-cpp] 开始推理,输入长度: {len(text)} 字符")
            start_time = time.time()
            
            output = self._model(
                prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=0.95,
                repeat_penalty=1.1,
                stop=["原始文本:", "\n\n"],
                echo=False
            )
            
            inference_time = time.time() - start_time
            
            corrected_text = output['choices'][0]['text'].strip()
            
            # 清理前缀
            prefixes = ["纠正后的文本:", "纠正后:", "纠正后的文本:", "纠正后:"]
            for prefix in prefixes:
                if corrected_text.startswith(prefix):
                    corrected_text = corrected_text[len(prefix):].strip()
                    break
            
            # 长度检查
            if len(corrected_text) > len(text) * 3:
                logger.warning(f"[llama-cpp] 异常长度,截断处理")
                lines = corrected_text.split('\n')
                if lines:
                    corrected_text = lines[0].strip()
            
            logger.info(f"[llama-cpp] 推理完成,耗时: {inference_time:.2f}秒")
            
            self._correction_count += 1
            return corrected_text
            
        except Exception as e:
            logger.error(f"[llama-cpp] 推理失败: {e}", exc_info=True)
            return None
    
    def unload(self):
        """卸载模型"""
        if self._model is not None:
            logger.info(f"[llama-cpp] 卸载模型,已处理 {self._correction_count} 次纠错")
            self._model = None
            self._is_loaded = False
            self._load_time = None
    
    def get_engine_stats(self) -> Dict:
        """获取引擎统计信息"""
        return {
            "engine": "llama-cpp",
            "is_loaded": self._is_loaded,
            "load_time_seconds": self._load_time,
            "correction_count": self._correction_count,
        }


class TextCorrector:
    """
    文本纠错器统一接口
    
    支持多种引擎:
    - macro-correct: 快速专业(推荐)
    - llama-cpp: 通用轻量(备选)
    
    特性:
    - 懒加载: 首次使用时才加载模型
    - 自动降级: 失败时返回原文
    - 统一接口: 对外屏蔽引擎差异
    """
    
    def __init__(self, 
                 engine_type: str = "macro-correct",
                 model_path: str = None,
                 **kwargs):
        """
        初始化文本纠错器
        
        Args:
            engine_type: 引擎类型 ("macro-correct" 或 "llama-cpp")
            model_path: 模型路径 (llama-cpp 需要)
            **kwargs: 其他引擎参数
        """
        self.engine_type = engine_type
        self._engine: Optional[BaseCorrectorEngine] = None
        
        # 根据类型创建引擎
        if engine_type == "macro-correct":
            self._engine = MacroCorrectEngine()
        elif engine_type == "llama-cpp":
            if not model_path:
                raise ValueError("llama-cpp 引擎需要提供 model_path")
            self._engine = LlamaCppEngine(model_path, **kwargs)
        else:
            raise ValueError(f"不支持的引擎类型: {engine_type}")
        
        logger.info(f"[文本纠错] 初始化: engine={engine_type}")
    
    def correct(self, text: str) -> Dict:
        """
        纠正文本中的错误
        
        Args:
            text: 待纠正的文本
        
        Returns:
            {
                "success": bool,           # 是否成功
                "original": str,           # 原始文本
                "corrected": str,          # 纠正后的文本
                "changed": bool,           # 是否有改变
                "changes": List[Dict],     # 改变列表
                "time_ms": int,            # 耗时(毫秒)
                "engine": str,             # 使用的引擎
                "error": str (optional)    # 错误信息
            }
        """
        start_time = time.time()
        
        result = {
            "success": False,
            "original": text,
            "corrected": text,
            "changed": False,
            "changes": [],
            "time_ms": 0,
            "engine": self.engine_type,
        }
        
        try:
            # 调用引擎纠错
            engine_result = self._engine.correct_text(text)
            
            # 处理结果
            if engine_result:
                # macro-correct 返回 (corrected_text, errors) 元组
                if isinstance(engine_result, tuple) and len(engine_result) == 2:
                    corrected_text, errors = engine_result
                    
                    result["success"] = True
                    result["corrected"] = corrected_text
                    result["changed"] = (text != corrected_text)
                    
                    # 使用引擎提供的 errors 列表
                    if result["changed"] and errors:
                        # 转换 macro-correct 格式 [old, new, pos, conf] 到标准格式
                        changes = []
                        for error in errors:
                            if len(error) >= 4:
                                old_char, new_char, position, confidence = error[:4]
                                changes.append({
                                    "position": position,
                                    "original": old_char,
                                    "corrected": new_char,
                                    "confidence": confidence
                                })
                        result["changes"] = changes
                        logger.info(f"[文本纠错] 检测到 {len(changes)} 处改变")
                else:
                    # 兼容旧引擎，只返回 corrected_text 字符串
                    corrected_text = engine_result
                    result["success"] = True
                    result["corrected"] = corrected_text
                    result["changed"] = (text != corrected_text)
                    
                    # 使用 difflib 检测改变
                    if result["changed"]:
                        changes = self._detect_changes(text, corrected_text)
                        result["changes"] = changes
                        logger.info(f"[文本纠错] 检测到 {len(changes)} 处改变")
            else:
                # 引擎失败,返回原文
                result["success"] = True
                result["corrected"] = text
                logger.debug("[文本纠错] 引擎返回空,使用原文")
        
        except Exception as e:
            logger.error(f"[文本纠错] 处理失败: {e}", exc_info=True)
            result["error"] = str(e)
        
        finally:
            elapsed = time.time() - start_time
            result["time_ms"] = int(elapsed * 1000)
        
        return result
    
    def _detect_changes(self, original: str, corrected: str) -> List[Dict]:
        """
        检测文本改变
        
        简单实现,检测:
        - 添加的标点符号
        - 删除的内容
        - 替换的字符
        """
        changes = []
        
        # 简单实现: 逐字对比
        import difflib
        
        diff = list(difflib.ndiff(original, corrected))
        
        for i, item in enumerate(diff):
            if item[0] == '+':
                # 添加
                char = item[2]
                changes.append({
                    "type": "addition",
                    "char": char,
                    "position": i,
                })
            elif item[0] == '-':
                # 删除
                char = item[2]
                changes.append({
                    "type": "deletion",
                    "char": char,
                    "position": i,
                })
        
        return changes
    
    def unload(self):
        """卸载模型释放内存"""
        if self._engine:
            self._engine.unload()
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        if self._engine:
            return self._engine.get_engine_stats()
        return {}


# 全局单例
_corrector_instance: Optional[TextCorrector] = None


def get_text_corrector(engine_type: str = None, **kwargs) -> TextCorrector:
    """
    获取文本纠错器单例
    
    Args:
        engine_type: 引擎类型,默认从环境变量读取
        **kwargs: 其他参数
    
    Returns:
        TextCorrector 实例
    """
    global _corrector_instance
    
    # 从环境变量读取配置
    if engine_type is None:
        engine_type = os.getenv("TEXT_CORRECTOR_ENGINE", "macro-correct")
    
    # 创建或返回单例
    if _corrector_instance is None:
        # 构建参数
        params = {"engine_type": engine_type}
        
        # llama-cpp 需要模型路径
        if engine_type == "llama-cpp":
            model_path = os.getenv("TEXT_CORRECTOR_MODEL_PATH")
            if not model_path:
                logger.error("[文本纠错] llama-cpp 引擎需要设置 TEXT_CORRECTOR_MODEL_PATH")
                raise ValueError("llama-cpp 需要设置 TEXT_CORRECTOR_MODEL_PATH")
            params["model_path"] = model_path
        
        params.update(kwargs)
        _corrector_instance = TextCorrector(**params)
    
    return _corrector_instance
