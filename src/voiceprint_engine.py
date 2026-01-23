"""
声纹识别模块 - 使用轻量级方案实现声纹识别
基于音频特征提取和余弦相似度对比
"""

import os
import numpy as np
import pickle
from pathlib import Path

# 尝试导入音频处理库
try:
    import librosa
    LIBROSA_AVAILABLE = True
    print("[声纹] 使用 librosa 特征提取")
except ImportError:
    LIBROSA_AVAILABLE = False
    print("[声纹警告] librosa 未安装，声纹识别功能不可用")
    print("[声纹警告] 安装方法: pip install librosa")

class VoiceprintEngine:
    """声纹识别引擎 - 基于MFCC特征"""
    
    def __init__(self, data_dir="voiceprints"):
        """
        初始化声纹引擎
        data_dir: 声纹数据存储目录
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        if LIBROSA_AVAILABLE:
            self.available = True
            print(f"[声纹] 引擎初始化完成，数据目录: {self.data_dir}")
        else:
            self.available = False
        
        # 加载已注册的声纹
        self.voiceprints = self._load_voiceprints()
    
    def _extract_features(self, audio_data, sample_rate=16000):
        """
        提取音频特征（MFCC + 统计特征）
        返回特征向量
        """
        if not LIBROSA_AVAILABLE:
            return None
        
        try:
            # 归一化音频
            if isinstance(audio_data, list):
                audio_np = np.array(audio_data, dtype=np.float32)
            else:
                audio_np = audio_data.astype(np.float32)
            
            if audio_np.dtype == np.int16 or np.abs(audio_np).max() > 1:
                audio_np = audio_np / 32768.0
            
            # 提取MFCC特征（梅尔频率倒谱系数）
            mfccs = librosa.feature.mfcc(
                y=audio_np,
                sr=sample_rate,
                n_mfcc=20,  # 20个MFCC系数
                n_fft=2048,
                hop_length=512
            )
            
            # 计算统计特征（均值和标准差）
            mfcc_mean = np.mean(mfccs, axis=1)
            mfcc_std = np.std(mfccs, axis=1)
            
            # 提取音高特征
            pitches, magnitudes = librosa.piptrack(
                y=audio_np,
                sr=sample_rate,
                n_fft=2048,
                hop_length=512
            )
            pitch_mean = np.mean(pitches[pitches > 0]) if np.any(pitches > 0) else 0
            pitch_std = np.std(pitches[pitches > 0]) if np.any(pitches > 0) else 0
            
            # 提取谱质心（音色特征）
            spectral_centroids = librosa.feature.spectral_centroid(
                y=audio_np,
                sr=sample_rate
            )
            centroid_mean = np.mean(spectral_centroids)
            centroid_std = np.std(spectral_centroids)
            
            # 组合所有特征
            feature_vector = np.concatenate([
                mfcc_mean,      # 20维
                mfcc_std,       # 20维
                [pitch_mean, pitch_std],  # 2维
                [centroid_mean, centroid_std]  # 2维
            ])  # 总共44维特征向量
            
            # 归一化特征向量
            feature_vector = feature_vector / (np.linalg.norm(feature_vector) + 1e-8)
            
            return feature_vector
            
        except Exception as e:
            print(f"[声纹错误] 特征提取失败: {e}")
            return None
    
    def _load_voiceprints(self):
        """加载所有已注册的声纹"""
        voiceprints = {}
        if not self.available:
            return voiceprints
        
        voiceprint_file = self.data_dir / "voiceprints.pkl"
        if voiceprint_file.exists():
            try:
                with open(voiceprint_file, 'rb') as f:
                    voiceprints = pickle.load(f)
                print(f"[声纹] 已加载 {len(voiceprints)} 个声纹")
            except Exception as e:
                print(f"[声纹错误] 加载声纹失败: {e}")
        
        return voiceprints
    
    def _save_voiceprints(self):
        """保存声纹数据"""
        voiceprint_file = self.data_dir / "voiceprints.pkl"
        try:
            with open(voiceprint_file, 'wb') as f:
                pickle.dump(self.voiceprints, f)
            print(f"[声纹] 已保存 {len(self.voiceprints)} 个声纹")
        except Exception as e:
            print(f"[声纹错误] 保存声纹失败: {e}")
    
    def register_voiceprint(self, user_name, audio_samples, sample_rate=16000):
        """
        注册声纹
        user_name: 用户名称
        audio_samples: 音频样本列表 [[samples], [samples], ...]，建议3-5段，每段3-10秒
        sample_rate: 采样率
        返回: {"success": bool, "message": str, "embedding_count": int}
        """
        if not self.available:
            return {
                "success": False,
                "message": "声纹识别功能不可用，请安装 librosa"
            }
        
        if not audio_samples or len(audio_samples) < 2:
            return {
                "success": False,
                "message": "至少需要2段音频样本"
            }
        
        try:
            feature_vectors = []
            
            for i, audio_data in enumerate(audio_samples):
                # 提取特征
                features = self._extract_features(audio_data, sample_rate)
                
                if features is None:
                    return {
                        "success": False,
                        "message": f"样本 {i+1} 特征提取失败"
                    }
                
                feature_vectors.append(features)
                print(f"[声纹] 处理样本 {i+1}/{len(audio_samples)}")
            
            # 计算平均特征向量（增强鲁棒性）
            avg_features = np.mean(feature_vectors, axis=0)
            avg_features = avg_features / (np.linalg.norm(avg_features) + 1e-8)
            
            # 保存声纹
            self.voiceprints[user_name] = {
                "features": avg_features,
                "sample_count": len(feature_vectors),
                "all_features": feature_vectors  # 保留所有样本用于后续优化
            }
            
            self._save_voiceprints()
            
            return {
                "success": True,
                "message": f"声纹注册成功: {user_name}",
                "embedding_count": len(feature_vectors)
            }
            
        except Exception as e:
            print(f"[声纹错误] 注册失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"注册失败: {e}"
            }
    
    def identify_speaker(self, audio_data, sample_rate=16000, threshold=0.75):
        """
        识别说话人
        audio_data: 音频数据
        sample_rate: 采样率
        threshold: 相似度阈值（0-1），越高越严格
        返回: {"speaker": str, "confidence": float, "is_registered": bool}
        """
        if not self.available:
            return {
                "speaker": "未知",
                "confidence": 0.0,
                "is_registered": False,
                "message": "声纹识别功能不可用"
            }
        
        if not self.voiceprints:
            return {
                "speaker": "未知",
                "confidence": 0.0,
                "is_registered": False,
                "message": "无已注册声纹"
            }
        
        try:
            # 提取特征
            features = self._extract_features(audio_data, sample_rate)
            
            if features is None:
                return {
                    "speaker": "未知",
                    "confidence": 0.0,
                    "is_registered": False,
                    "message": "特征提取失败"
                }
            
            # 与所有已注册声纹对比
            best_match = None
            best_similarity = 0.0
            
            for name, voiceprint in self.voiceprints.items():
                # 计算余弦相似度
                similarity = np.dot(features, voiceprint["features"])
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = name
            
            # 判断是否超过阈值
            if best_similarity >= threshold:
                return {
                    "speaker": best_match,
                    "confidence": float(best_similarity),
                    "is_registered": True
                }
            else:
                return {
                    "speaker": "未知",
                    "confidence": float(best_similarity),
                    "is_registered": False
                }
                
        except Exception as e:
            print(f"[声纹错误] 识别失败: {e}")
            return {
                "speaker": "未知",
                "confidence": 0.0,
                "is_registered": False,
                "message": f"识别失败: {e}"
            }
    
    def delete_voiceprint(self, user_name):
        """删除声纹"""
        if user_name in self.voiceprints:
            del self.voiceprints[user_name]
            self._save_voiceprints()
            return {"success": True, "message": f"已删除声纹: {user_name}"}
        else:
            return {"success": False, "message": f"声纹不存在: {user_name}"}
    
    def list_voiceprints(self):
        """列出所有已注册的声纹"""
        return [
            {
                "name": name,
                "sample_count": data["sample_count"]
            }
            for name, data in self.voiceprints.items()
        ]
    
    def get_status(self):
        """获取声纹引擎状态"""
        return {
            "available": self.available,
            "registered_count": len(self.voiceprints),
            "data_dir": str(self.data_dir)
        }


# 模拟模式（用于测试）
class MockVoiceprintEngine:
    """模拟声纹引擎（用于开发测试）"""
    
    def __init__(self, data_dir="voiceprints"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.voiceprints = {}
        print("[声纹] 使用模拟模式")
    
    def register_voiceprint(self, user_name, audio_samples, sample_rate=16000):
        self.voiceprints[user_name] = True
        return {
            "success": True,
            "message": f"[模拟] 声纹注册成功: {user_name}",
            "embedding_count": len(audio_samples)
        }
    
    def identify_speaker(self, audio_data, sample_rate=16000, threshold=0.75):
        # 模拟识别：随机返回第一个注册用户或未知
        if self.voiceprints:
            import random
            if random.random() > 0.3:  # 70% 概率识别为注册用户
                return {
                    "speaker": list(self.voiceprints.keys())[0],
                    "confidence": 0.85,
                    "is_registered": True
                }
        
        return {
            "speaker": "未知",
            "confidence": 0.45,
            "is_registered": False
        }
    
    def delete_voiceprint(self, user_name):
        if user_name in self.voiceprints:
            del self.voiceprints[user_name]
            return {"success": True, "message": f"已删除声纹: {user_name}"}
        return {"success": False, "message": "声纹不存在"}
    
    def list_voiceprints(self):
        return [{"name": name, "sample_count": 3} for name in self.voiceprints]
    
    def get_status(self):
        return {
            "available": True,
            "registered_count": len(self.voiceprints),
            "data_dir": str(self.data_dir),
            "mode": "mock"
        }
