"""
PDF 解析器 - 使用 LlamaIndex + Docling
支援高品質的 PDF 文字提取和結構化解析
"""

import os
import logging
from typing import List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class PDFParser:
    """
    使用 LlamaIndex 的 DoclingReader 解析 PDF
    
    DoclingReader 優勢：
    1. 更好的表格識別
    2. 保留文件結構
    3. 支援多種文件格式
    """
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._reader = None
        self._init_reader()
    
    def _init_reader(self):
        """初始化 DoclingReader"""
        try:
            from llama_index.readers.docling import DoclingReader
            self._reader = DoclingReader()
            logger.info("✅ [Parser] DoclingReader 初始化成功")
        except ImportError as e:
            logger.warning(f"⚠️ [Parser] DoclingReader 不可用: {e}")
            logger.info("🔄 [Parser] 將使用 PyMuPDF 備用方案")
            self._reader = None
        except Exception as e:
            logger.warning(f"⚠️ [Parser] DoclingReader 初始化失敗: {e}")
            self._reader = None
    
    def parse(self, file_path: str) -> List[Dict[str, Any]]:
        """
        解析 PDF 檔案
        
        Args:
            file_path: PDF 檔案路徑
            
        Returns:
            解析後的文件列表，每個元素包含 text 和 metadata
        """
        logger.info(f"📄 [Parser] ====== 開始解析 PDF ======")
        logger.info(f"📄 [Parser] 檔案: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"❌ [Parser] 檔案不存在: {file_path}")
            return []
        
        # 優先使用 DoclingReader
        if self._reader:
            result = self._parse_with_docling(file_path)
            if result:
                return result
        
        # 備用方案：PyMuPDF
        return self._parse_with_pymupdf(file_path)
    
    def _parse_with_docling(self, file_path: str) -> List[Dict[str, Any]]:
        """使用 DoclingReader 解析"""
        try:
            logger.info("📖 [Parser] 使用 DoclingReader 解析...")
            
            # DoclingReader 返回 LlamaIndex Document 物件
            documents = self._reader.load_data(file_path)
            
            parsed_data = []
            file_name = os.path.basename(file_path)
            
            for i, doc in enumerate(documents):
                text = doc.text.strip() if hasattr(doc, 'text') else str(doc).strip()
                
                logger.info(f"📖 [Parser] Document {i+1}: {len(text)} 字符")
                
                if not text or len(text) < 50:
                    logger.debug(f"⏭️ [Parser] 跳過過短的內容 (長度: {len(text)})")
                    continue
                
                # 取得 metadata
                metadata = doc.metadata if hasattr(doc, 'metadata') else {}
                page_label = metadata.get('page_label', metadata.get('page', str(i + 1)))
                
                # 切分成適當大小的 chunks
                chunks = self._split_text(text)
                logger.info(f"📖 [Parser] 分成 {len(chunks)} 個 chunks")
                
                for chunk_idx, chunk in enumerate(chunks):
                    if len(chunk) > 50:
                        parsed_data.append({
                            "text": chunk,
                            "metadata": {
                                "file_name": file_name,
                                "page_label": str(page_label),
                                "chunk_index": chunk_idx,
                                "source": "docling"
                            }
                        })
            
            logger.info(f"✅ [Parser] DoclingReader 解析完成，共 {len(parsed_data)} 個 chunks")
            return parsed_data
            
        except Exception as e:
            logger.error(f"❌ [Parser] DoclingReader 解析失敗: {e}")
            logger.info("🔄 [Parser] 嘗試使用 PyMuPDF 備用方案")
            return []
    
    def _parse_with_pymupdf(self, file_path: str) -> List[Dict[str, Any]]:
        """使用 PyMuPDF 作為備用方案"""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.error("❌ [Parser] PyMuPDF 未安裝，請執行: pip install pymupdf")
            return []
        
        try:
            logger.info("📖 [Parser] 使用 PyMuPDF 解析...")
            
            doc = fitz.open(file_path)
            parsed_data = []
            file_name = os.path.basename(file_path)
            total_pages = len(doc)
            
            logger.info(f"📖 [Parser] PDF 共 {total_pages} 頁")
            
            for page_num in range(total_pages):
                page = doc[page_num]
                text = page.get_text("text").strip()
                
                logger.info(f"📖 [Parser] 第 {page_num + 1} 頁: {len(text)} 字符")
                
                if not text or len(text) < 50:
                    logger.debug(f"⏭️ [Parser] 第 {page_num + 1} 頁內容過短，跳過")
                    continue
                
                # 切分成適當大小的 chunks
                chunks = self._split_text(text)
                logger.info(f"📖 [Parser] 第 {page_num + 1} 頁分成 {len(chunks)} 個 chunks")
                
                for chunk_idx, chunk in enumerate(chunks):
                    if len(chunk) > 50:
                        parsed_data.append({
                            "text": chunk,
                            "metadata": {
                                "file_name": file_name,
                                "page_label": str(page_num + 1),
                                "chunk_index": chunk_idx,
                                "source": "pymupdf"
                            }
                        })
            
            doc.close()
            logger.info(f"✅ [Parser] PyMuPDF 解析完成，共 {len(parsed_data)} 個 chunks")
            return parsed_data
            
        except Exception as e:
            logger.error(f"❌ [Parser] PyMuPDF 解析失敗: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _split_text(self, text: str) -> List[str]:
        """
        將文字切分成適當大小的 chunks
        
        Args:
            text: 原始文字
            
        Returns:
            切分後的文字列表
        """
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # 嘗試在句子邊界分割
            if end < len(text):
                # 尋找最近的句號或換行
                for sep in ['\n\n', '\n', '。', '.', '！', '!', '？', '?', '；', ';']:
                    last_sep = text.rfind(sep, start, end)
                    if last_sep > start + self.chunk_size // 2:  # 確保不會太短
                        end = last_sep + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # 下一塊從 overlap 位置開始
            start = end - self.chunk_overlap if end < len(text) else end
        
        return chunks
