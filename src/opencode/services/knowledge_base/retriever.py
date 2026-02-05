"""
Retriever - Hybrid Search (向量 + BM25) + Cohere Rerank

特點：
1. 語義搜尋 (Cohere/OpenAI Embedding + Qdrant)
2. 全文檢索 (BM25)
3. 混合排序 (RRF - Reciprocal Rank Fusion)
4. Cohere Rerank 重排序 (可選)
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

# 使用統一的路徑工具載入環境變數
from opencode.core.utils import load_env
load_env()

logger = logging.getLogger(__name__)

# 全域實例
_retriever_instance = None


class BM25Index:
    """
    簡易 BM25 索引
    
    用於全文關鍵字檢索，補充語義搜尋的不足
    特別適用於：
    - 專有名詞 (如 BERT, GPT, RNN)
    - 縮寫 (如 NLP, CV, RL)
    - 精確匹配需求
    """
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents = []       # [(doc_id, text, metadata), ...]
        self.doc_freqs = defaultdict(int)  # term -> document frequency
        self.doc_lens = []        # document lengths
        self.avg_doc_len = 0
        self.vocab = set()
        self._tokenized_docs = []
        self._initialized = False
    
    def _tokenize(self, text: str) -> List[str]:
        """簡單分詞 (支援中英文)"""
        import re
        
        # 英文：按空格和標點分詞，轉小寫
        # 中文：按字符分詞
        tokens = []
        
        # 先提取英文單詞
        words = re.findall(r'[a-zA-Z0-9]+', text.lower())
        tokens.extend(words)
        
        # 提取中文字符
        chinese = re.findall(r'[\u4e00-\u9fff]+', text)
        for word in chinese:
            # 中文按 2-gram 分詞
            for i in range(len(word) - 1):
                tokens.append(word[i:i+2])
            if len(word) == 1:
                tokens.append(word)
        
        return tokens
    
    def build_index(self, documents: List[Tuple[str, str, Dict]]):
        """
        建立 BM25 索引
        
        Args:
            documents: [(doc_id, text, metadata), ...]
        """
        self.documents = documents
        self._tokenized_docs = []
        self.doc_freqs = defaultdict(int)
        self.doc_lens = []
        self.vocab = set()
        
        # 分詞並統計
        for doc_id, text, metadata in documents:
            tokens = self._tokenize(text)
            self._tokenized_docs.append(tokens)
            self.doc_lens.append(len(tokens))
            
            # 更新詞頻
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.doc_freqs[token] += 1
                self.vocab.add(token)
        
        self.avg_doc_len = sum(self.doc_lens) / len(self.doc_lens) if self.doc_lens else 0
        self._initialized = True
        
        logger.info(f"📚 [BM25] 索引建立完成: {len(documents)} 文檔, {len(self.vocab)} 詞彙")
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """
        BM25 搜尋
        
        Returns:
            [(doc_index, score), ...] 按分數降序
        """
        if not self._initialized or not self.documents:
            return []
        
        query_tokens = self._tokenize(query)
        scores = []
        n_docs = len(self.documents)
        
        for doc_idx, doc_tokens in enumerate(self._tokenized_docs):
            score = 0.0
            doc_len = self.doc_lens[doc_idx]
            
            # 計算每個 query term 的 BM25 分數
            token_counts = defaultdict(int)
            for t in doc_tokens:
                token_counts[t] += 1
            
            for term in query_tokens:
                if term not in self.vocab:
                    continue
                
                tf = token_counts.get(term, 0)
                df = self.doc_freqs.get(term, 0)
                
                if tf == 0 or df == 0:
                    continue
                
                # IDF
                idf = max(0, (n_docs - df + 0.5) / (df + 0.5))
                import math
                idf = math.log(1 + idf)
                
                # TF normalization
                tf_norm = (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len))
                
                score += idf * tf_norm
            
            if score > 0:
                scores.append((doc_idx, score))
        
        # 按分數排序
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class HybridRetriever:
    """
    混合檢索器
    
    結合語義搜尋和 BM25 全文檢索：
    1. 語義搜尋：捕捉語義相似性
    2. BM25 搜尋：捕捉關鍵字匹配
    3. RRF 融合：合併兩種結果
    4. Cohere Rerank：進一步優化排序 (可選)
    
    重要：Cohere 查詢時必須使用 input_type="search_query"
    """
    
    def __init__(
        self,
        collection_name: str = "rag_knowledge_base",
        qdrant_url: str = "http://localhost:6333",
        use_rerank: bool = True
    ):
        self.collection_name = collection_name
        self.qdrant_url = qdrant_url
        self.use_rerank = use_rerank
        
        # API clients
        self.cohere_client = None
        self.openai_client = None
        self.qdrant_client = None
        
        # Embedding 設定
        self.embed_provider = None
        self.embed_model = None
        
        # BM25 索引
        self.bm25_index = BM25Index()
        self._bm25_docs_cache = {}  # file_name -> docs
        
        self._initialize()
    
    def _initialize(self):
        """初始化 clients"""
        # 確保環境變數已載入
        load_env()
        
        cohere_key = os.getenv("COHERE_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        # 優先使用 Cohere
        if cohere_key:
            try:
                import cohere
                self.cohere_client = cohere.Client(api_key=cohere_key)
                self.embed_provider = "cohere"
                self.embed_model = os.getenv("COHERE_EMBED_MODEL", "embed-multilingual-v3.0")
                logger.info(f"✅ [HybridRetriever] 使用 Cohere embedding: {self.embed_model}")
                
                # 檢查是否有 rerank 模型
                if self.use_rerank:
                    logger.info(f"✅ [HybridRetriever] Rerank 已啟用 (rerank-multilingual-v3.0)")
            except ImportError:
                logger.warning("⚠️ [HybridRetriever] cohere 套件未安裝")
            except Exception as e:
                logger.error(f"❌ [HybridRetriever] Cohere 初始化失敗: {e}")
        
        # 備用：OpenAI
        if not self.cohere_client and openai_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=openai_key)
                self.embed_provider = "openai"
                self.embed_model = "text-embedding-3-small"
                self.use_rerank = False  # OpenAI 沒有 rerank
                logger.info(f"✅ [HybridRetriever] 使用 OpenAI embedding: {self.embed_model}")
            except ImportError:
                logger.warning("⚠️ [HybridRetriever] openai 套件未安裝")
            except Exception as e:
                logger.error(f"❌ [HybridRetriever] OpenAI 初始化失敗: {e}")
        
        if not self.cohere_client and not self.openai_client:
            logger.error("❌ [HybridRetriever] 沒有可用的 embedding provider！")
            raise ValueError("需要設定 COHERE_API_KEY 或 OPENAI_API_KEY")
        
        # 初始化 Qdrant
        self._init_qdrant()
    
    def _init_qdrant(self):
        """初始化 Qdrant client"""
        try:
            from qdrant_client import QdrantClient
            self.qdrant_client = QdrantClient(url=self.qdrant_url)
            logger.info(f"✅ [HybridRetriever] Qdrant 連接成功: {self.qdrant_url}")
        except Exception as e:
            logger.error(f"❌ [HybridRetriever] Qdrant 初始化失敗: {e}")
            raise
    
    def _build_bm25_index_from_qdrant(self, filters: Optional[Dict[str, Any]] = None):
        """從 Qdrant 載入文檔並建立 BM25 索引"""
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            # 建構過濾條件
            search_filter = None
            cache_key = str(filters) if filters else "all"
            
            # 檢查快取
            if cache_key in self._bm25_docs_cache:
                logger.info(f"📚 [BM25] 使用快取索引: {cache_key}")
                return
            
            if filters:
                conditions = []
                for key, value in filters.items():
                    if isinstance(value, list):
                        conditions.append(Filter(should=[
                            FieldCondition(key=key, match=MatchValue(value=v))
                            for v in value
                        ]))
                    else:
                        conditions.append(
                            FieldCondition(key=key, match=MatchValue(value=value))
                        )
                if conditions:
                    search_filter = Filter(must=conditions)
            
            # 從 Qdrant 載入文檔
            # 注意：這裡只載入前 1000 個文檔，避免記憶體問題
            points, _ = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                scroll_filter=search_filter,
                limit=1000,
                with_payload=True,
                with_vectors=False
            )
            
            # 建立索引
            documents = [
                (str(p.id), p.payload.get("text", ""), p.payload)
                for p in points
            ]
            
            self.bm25_index.build_index(documents)
            self._bm25_docs_cache[cache_key] = documents
            
        except Exception as e:
            logger.warning(f"⚠️ [BM25] 索引建立失敗: {e}，將只使用語義搜尋")
    
    def get_query_embedding(self, query: str) -> List[float]:
        """取得查詢的 embedding 向量"""
        if self.cohere_client:
            return self._get_cohere_embedding(query)
        else:
            return self._get_openai_embedding(query)
    
    def _get_cohere_embedding(self, text: str) -> List[float]:
        """使用 Cohere 取得查詢 embedding"""
        try:
            response = self.cohere_client.embed(
                texts=[text],
                model=self.embed_model,
                input_type="search_query"
            )
            return response.embeddings[0]
        except Exception as e:
            logger.error(f"❌ [HybridRetriever] Cohere embedding 失敗: {e}")
            raise
    
    def _get_openai_embedding(self, text: str) -> List[float]:
        """使用 OpenAI 取得 embedding"""
        try:
            response = self.openai_client.embeddings.create(
                model=self.embed_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"❌ [HybridRetriever] OpenAI embedding 失敗: {e}")
            raise
    
    def _vector_search(
        self,
        query: str,
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """純向量語義搜尋"""
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        query_vector = self.get_query_embedding(query)
        
        # 建構過濾條件
        search_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                if isinstance(value, list):
                    conditions.append(Filter(should=[
                        FieldCondition(key=key, match=MatchValue(value=v))
                        for v in value
                    ]))
                else:
                    conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )
            if conditions:
                search_filter = Filter(must=conditions)
        
        results = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=search_filter,
            limit=top_k,
            with_payload=True
        )
        
        return [
            {
                "id": str(p.id),
                "text": p.payload.get("text", ""),
                "file_name": p.payload.get("file_name", "unknown"),
                "page_label": p.payload.get("page_label", "?"),
                "score": p.score,
                "metadata": p.payload,
                "source": "vector"
            }
            for p in results.points
        ]
    
    def _bm25_search(
        self,
        query: str,
        top_k: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """BM25 關鍵字搜尋"""
        # 建立/更新 BM25 索引
        self._build_bm25_index_from_qdrant(filters)
        
        cache_key = str(filters) if filters else "all"
        if cache_key not in self._bm25_docs_cache:
            return []
        
        documents = self._bm25_docs_cache[cache_key]
        results = self.bm25_index.search(query, top_k=top_k)
        
        return [
            {
                "id": documents[idx][0],
                "text": documents[idx][1],
                "file_name": documents[idx][2].get("file_name", "unknown"),
                "page_label": documents[idx][2].get("page_label", "?"),
                "score": score,
                "metadata": documents[idx][2],
                "source": "bm25"
            }
            for idx, score in results
        ]
    
    def _rrf_fusion(
        self,
        vector_results: List[Dict],
        bm25_results: List[Dict],
        k: int = 60
    ) -> List[Dict]:
        """
        Reciprocal Rank Fusion (RRF)
        
        合併向量搜尋和 BM25 結果
        RRF score = 1 / (k + rank)
        """
        scores = defaultdict(float)
        docs = {}
        
        # 處理向量搜尋結果
        for rank, doc in enumerate(vector_results):
            doc_id = doc["text"][:100]  # 用前 100 字符作為 ID
            scores[doc_id] += 1.0 / (k + rank + 1)
            if doc_id not in docs:
                docs[doc_id] = doc.copy()
                docs[doc_id]["vector_rank"] = rank + 1
                docs[doc_id]["bm25_rank"] = None
        
        # 處理 BM25 結果
        for rank, doc in enumerate(bm25_results):
            doc_id = doc["text"][:100]
            scores[doc_id] += 1.0 / (k + rank + 1)
            if doc_id not in docs:
                docs[doc_id] = doc.copy()
                docs[doc_id]["vector_rank"] = None
                docs[doc_id]["bm25_rank"] = rank + 1
            else:
                docs[doc_id]["bm25_rank"] = rank + 1
        
        # 按 RRF 分數排序
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        results = []
        for doc_id in sorted_ids:
            doc = docs[doc_id]
            doc["rrf_score"] = scores[doc_id]
            results.append(doc)
        
        return results
    
    def _cohere_rerank(
        self,
        query: str,
        documents: List[Dict],
        top_k: int = 10
    ) -> List[Dict]:
        """
        使用 Cohere Rerank 重排序
        
        Rerank 模型會根據 query 和 document 的相關性重新打分
        特別擅長處理複雜的語義關係
        """
        if not self.cohere_client or not self.use_rerank:
            return documents[:top_k]
        
        if not documents:
            return []
        
        try:
            # 準備文檔
            texts = [doc["text"] for doc in documents]
            
            # 調用 Cohere Rerank
            response = self.cohere_client.rerank(
                model="rerank-multilingual-v3.0",
                query=query,
                documents=texts,
                top_n=top_k
            )
            
            # 重新排序
            reranked = []
            for item in response.results:
                doc = documents[item.index].copy()
                doc["rerank_score"] = item.relevance_score
                doc["original_index"] = item.index
                reranked.append(doc)
            
            logger.info(f"✅ [Rerank] 重排序完成，返回 top {len(reranked)}")
            return reranked
            
        except Exception as e:
            logger.warning(f"⚠️ [Rerank] 失敗: {e}，使用原始排序")
            return documents[:top_k]
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        use_hybrid: bool = True,
        use_rerank: bool = None
    ) -> List[Dict[str, Any]]:
        """
        混合搜尋
        
        Args:
            query: 搜尋查詢
            top_k: 返回結果數量
            filters: 過濾條件
            use_hybrid: 是否使用混合搜尋 (向量 + BM25)
            use_rerank: 是否使用 Rerank (None 表示使用預設設定)
            
        Returns:
            搜尋結果列表
        """
        logger.info(f"🔍 [HybridRetriever] ====== 開始搜尋 ======")
        logger.info(f"🔍 Query: {query[:50]}...")
        logger.info(f"🔍 Top-K: {top_k}, Hybrid: {use_hybrid}, Rerank: {use_rerank}")
        logger.info(f"🔍 Filters: {filters}")
        
        try:
            # 1. 向量搜尋 (擴大搜尋範圍給 rerank 用)
            search_k = top_k * 4 if (use_rerank or self.use_rerank) else top_k * 2
            vector_results = self._vector_search(query, top_k=search_k, filters=filters)
            logger.info(f"✅ 向量搜尋: {len(vector_results)} 結果")
            
            if use_hybrid:
                # 2. BM25 搜尋
                bm25_results = self._bm25_search(query, top_k=search_k, filters=filters)
                logger.info(f"✅ BM25 搜尋: {len(bm25_results)} 結果")
                
                # 3. RRF 融合
                fused_results = self._rrf_fusion(vector_results, bm25_results)
                logger.info(f"✅ RRF 融合: {len(fused_results)} 結果")
            else:
                fused_results = vector_results
            
            # 4. Rerank (可選)
            should_rerank = use_rerank if use_rerank is not None else self.use_rerank
            if should_rerank and self.cohere_client:
                final_results = self._cohere_rerank(query, fused_results, top_k=top_k)
            else:
                final_results = fused_results[:top_k]
            
            # 轉換為標準格式
            results = [
                {
                    "text": r["text"],
                    "file_name": r["file_name"],
                    "page_label": r["page_label"],
                    "score": r.get("rerank_score", r.get("rrf_score", r.get("score", 0))),
                    "metadata": r.get("metadata", {}),
                    "search_info": {
                        "vector_rank": r.get("vector_rank"),
                        "bm25_rank": r.get("bm25_rank"),
                        "rrf_score": r.get("rrf_score"),
                        "rerank_score": r.get("rerank_score"),
                        "source": r.get("source", "hybrid")
                    }
                }
                for r in final_results
            ]
            
            logger.info(f"✅ [HybridRetriever] 最終返回 {len(results)} 結果")
            for i, r in enumerate(results[:3]):
                logger.info(f"  [{i+1}] score={r['score']:.4f}, file={r['file_name']}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ [HybridRetriever] 搜尋失敗: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def search_multiple(
        self,
        queries: List[str],
        top_k: int = 3,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """多查詢搜尋"""
        logger.info(f"🔍 [HybridRetriever] 多查詢搜尋: {len(queries)} 個查詢")
        
        all_results = []
        seen_texts = set()
        
        for query in queries:
            results = self.search(query, top_k=top_k, filters=filters)
            
            for r in results:
                text_key = r["text"][:100] if r["text"] else ""
                if text_key and text_key not in seen_texts:
                    seen_texts.add(text_key)
                    all_results.append(r)
        
        # 按分數排序
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        logger.info(f"✅ [HybridRetriever] 多查詢搜尋完成: {len(all_results)} 個不重複結果")
        
        return {
            "queries": queries,
            "results": all_results,
            "total": len(all_results)
        }


# 向後兼容的別名
Retriever = HybridRetriever


def get_retriever() -> HybridRetriever:
    """取得全域 Retriever 實例"""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = HybridRetriever()
    return _retriever_instance


def reset_retriever():
    """重置全域 Retriever 實例"""
    global _retriever_instance
    _retriever_instance = None
