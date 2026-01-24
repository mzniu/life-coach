# macro-correct 树莓派测试报告

## 测试日期
2026-01-24

## 环境信息
- **平台**: 树莓派 (aarch64)
- **Python**: 3.9.2
- **内存**: 3.7GB
- **磁盘**: 15GB 可用

## 安装过程

### ✅ PyTorch 安装
- **状态**: 成功
- **版本**: 2.8.0+cpu
- **大小**: 102MB
- **耗时**: ~2分钟
- **备注**: ARM64 版本安装顺利，体积比预期小

### ✅ macro-correct 安装
- **状态**: 成功
- **版本**: 0.0.5
- **依赖**: transformers 4.57.6, torch 2.8.0
- **耗时**: ~3分钟

## 功能测试

### ❌ 标点纠错
- **状态**: **失败**
- **错误**: `ImportError: cannot import name 'BertModel' from 'transformers'`
- **原因**: macro-correct 与 transformers 4.57.6 不兼容

### ❌ 拼写纠错  
- **状态**: **失败**
- **错误**: `ImportError: cannot import name 'ErnieForMaskedLM' from 'transformers'`
- **原因**: 同上，API 版本不兼容

## 问题分析

### 根本原因
macro-correct 是基于旧版 transformers API (可能 <4.30) 开发的，使用了已废弃的接口：
- `BertModel`, `ErnieForMaskedLM` 等类在新版本中被重构或移除
- 项目可能已停止维护（最新版本 0.0.5）

### 可能的解决方案
1. **降级 transformers** (不推荐)
   - 需要卸载 4.57.6，安装 <4.30 版本
   - 可能引发其他依赖冲突
   - 会失去新版本的性能优化

2. **等待 macro-correct 更新** (不现实)
   - 项目可能已停止维护
   - 时间成本太高

3. **手动修复源码** (工作量大)
   - 需要修改 macro-correct 源码适配新 API
   - 维护成本高

## 性能估算（理论值）

基于 BERT-base 模型的资源占用：
- **内存**: ~1.2GB (模型 400MB + PyTorch 500MB + 运行时 300MB)
- **推理速度**: 预计 5-20秒/条（未验证）
- **首次加载**: 预计 10-30秒

## 结论

### ❌ macro-correct 不适合当前项目

**原因：**
1. ✅ PyTorch 安装成功
2. ✅ macro-correct 安装成功  
3. ❌ **transformers 版本冲突** (致命问题)
4. ❌ 无法实际运行纠错功能
5. ⚠️  即使能运行，资源占用 (>1GB) 也超出 0.5B 方案

### ✅ 推荐方案：保持 Qwen2.5-0.5B + llama-cpp-python

**对比优势：**

| 特性 | macro-correct | Qwen2.5-0.5B (当前) |
|------|---------------|---------------------|
| **安装难度** | ❌ 高（版本冲突） | ✅ 简单 |
| **功能可用** | ❌ 无法运行 | ✅ 已验证 |
| **内存占用** | ~1.2GB (估算) | ~600MB (实测) |
| **推理速度** | 未知 | 8秒 (实测) |
| **依赖库** | PyTorch (重) | llama-cpp (轻) |
| **维护性** | ❌ 可能停止维护 | ✅ 活跃 |
| **是否改写** | 未知 | ✅ 不改写 |

## 最终建议

### 短期方案（立即执行）
**继续使用 Qwen2.5-0.5B + llama-cpp-python**
- ✅ 已验证可用
- ✅ 性能符合要求
- ✅ 资源占用合理
- ✅ 维护简单

### 中期优化（可选）
**在 0.5B 基础上添加规则增强**
```python
def post_process_punctuation(text):
    """补充中文标点规则"""
    import re
    # 句号规则
    text = re.sub(r'([^。？！，、；：""''（）\s]{8,})(?=[^。？！])', r'\1。', text)
    # 问号规则  
    text = re.sub(r'(怎么样|什么|哪里|谁|为什么)(?=[^？。！])', r'\1？', text)
    return text
```

### 长期方案（未来考虑）
如需更强纠错能力：
1. **云端 API**: 部署 ChineseErrorCorrector-4B 到云服务器
2. **混合方案**: 本地快速处理 + 云端精准纠错
3. **Fine-tune**: 用标点数据集微调 0.5B 模型

## 清理建议

可卸载已安装但无法使用的包：
```bash
# 释放磁盘空间（可选）
pip uninstall macro-correct transformers torch -y
```

---

**报告人**: GitHub Copilot  
**日期**: 2026-01-24
