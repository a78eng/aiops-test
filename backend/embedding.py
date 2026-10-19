import threading
from sentence_transformers import SentenceTransformer
from config import settings
_model = None
_lock = threading.Lock()
def get_model():
    """懒加载 + 双检锁：首次调用才加载模型（1-3 分钟）"""
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                print("[Embedding] 加载 bge-m3（CPU 模式），首次启动需 1-3 分钟…")
                _model = SentenceTransformer(settings.EMBEDDING_MODEL, device="cpu")
                print("[Embedding] 加载完成")
    return _model
def encode(texts):
    """文本向量化，返回值约定：
    - 传入 str（单条查询）  → 一维 list，长度 1024，供 pgvector cosine_distance 使用  ★关键修复
    - 传入 list（批量入库）  → 二维 list，每个元素是一维向量，供批量 INSERT 使用
    """
    single = isinstance(texts, str)
    if single:
        texts = [texts]
    if not texts:
        return [] if single else [[]]
    # bge-m3 官方推荐检索指令前缀，提升中文检索效果
    texts = ["为这个句子生成表示以用于检索相关文章：" + t for t in texts]
    vecs = get_model().encode(texts, normalize_embeddings=True).tolist()
    # ★ 核心修复：单条文本直接返回 vecs[0]（一维），不再返回 [[...]]（二维）
    return vecs[0] if single else vecs
