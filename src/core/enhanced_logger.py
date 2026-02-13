"""
Enhanced Logging System with Long Content Support and Markdown Export
支援長內容分割記錄和 Markdown 輸出的增強日誌系統

DEPRECATION WARNING:
--------------------
This module is DEPRECATED and will be removed in a future version.

Please use src/core/logger.py (StructuredLogger) instead, which provides:
- Unified logging interface
- Better SSE event integration
- Simplified API
- Active maintenance and support

Migration Guide:
----------------
Old: enhanced_logger.log_long_content(...)
New: structured_logger.info(...) with automatic truncation

Old: enhanced_logger.save_response_as_markdown(...)
New: Markdown export is no longer part of core logging (use a separate service)

This logger remains available for backward compatibility but will not receive
new features or bug fixes.
"""

import warnings
import json
import logging
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
import textwrap

# Issue deprecation warning when this module is imported
warnings.warn(
    "enhanced_logger.py is deprecated. Use logger.py (StructuredLogger) instead.",
    DeprecationWarning,
    stacklevel=2
)


@dataclass
class ContentSegment:
    """內容分段"""
    segment_id: str
    segment_index: int
    total_segments: int
    content: str
    checksum: str


class EnhancedLogger:
    """增強型日誌系統 - 支援長內容處理"""

    # 單個日誌條目的最大字符數
    MAX_LOG_SIZE = 10000  # 10KB per log entry

    # Markdown 報告的最大 token 估算
    MAX_MARKDOWN_TOKENS = 100000  # 約 100K tokens

    def __init__(self, base_path: Path = None):
        self.base_path = base_path or Path.cwd() / "logs"
        self.base_path.mkdir(parents=True, exist_ok=True)

        # 創建子目錄
        self.segments_dir = self.base_path / "segments"
        self.segments_dir.mkdir(exist_ok=True)

        self.reports_dir = self.base_path / "reports"
        self.reports_dir.mkdir(exist_ok=True)

        # 設置基礎日誌
        self.setup_logging()

    def setup_logging(self):
        """設置日誌系統"""
        # 主日誌文件
        log_file = self.base_path / f"opencode_{datetime.now().strftime('%Y%m%d')}.log"

        # 配置格式
        formatter = logging.Formatter(
            '%(asctime)s %(levelname)-8s %(message)s',
            datefmt='%H:%M:%S'
        )

        # 文件處理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)

        # File-only logger — console output is handled by StructuredLogger
        self.logger = logging.getLogger('opencode.enhanced')
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.logger.addHandler(file_handler)

    def log_long_content(self,
                        level: str,
                        message: str,
                        content: str,
                        trace_id: str,
                        category: str = "application") -> List[str]:
        """
        記錄長內容，自動分割成多個段落

        Args:
            level: 日誌級別
            message: 簡短描述
            content: 長內容
            trace_id: 追蹤ID
            category: 日誌類別

        Returns:
            分段ID列表
        """
        # 如果內容不長，直接記錄
        if len(content) <= self.MAX_LOG_SIZE:
            self._log_single(level, f"{message}: {content[:200]}...", trace_id, category)
            return []

        # 計算需要分割的段數
        segments = self._split_content(content, self.MAX_LOG_SIZE)
        segment_ids = []

        # 生成內容哈希作為主ID
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:8]

        # 記錄主條目
        self._log_single(
            level,
            f"{message} [Long content: {len(content)} chars, {len(segments)} segments, ID: {content_hash}]",
            trace_id,
            category
        )

        # 記錄每個分段
        for i, segment in enumerate(segments):
            segment_id = f"{content_hash}_{i+1}of{len(segments)}"
            segment_ids.append(segment_id)

            # 保存分段到文件
            segment_file = self.segments_dir / f"{trace_id}_{segment_id}.json"
            segment_data = ContentSegment(
                segment_id=segment_id,
                segment_index=i + 1,
                total_segments=len(segments),
                content=segment,
                checksum=hashlib.md5(segment.encode()).hexdigest()
            )

            with open(segment_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(segment_data), f, ensure_ascii=False, indent=2)

            # 記錄分段信息
            self._log_single(
                "DEBUG",
                f"Content segment {i+1}/{len(segments)} saved: {segment_id} [{len(segment)} chars]",
                trace_id,
                category
            )

        return segment_ids

    def _split_content(self, content: str, max_size: int) -> List[str]:
        """智能分割內容"""
        if len(content) <= max_size:
            return [content]

        segments = []

        # 嘗試按段落分割
        paragraphs = content.split('\n\n')
        current_segment = ""

        for para in paragraphs:
            if len(current_segment) + len(para) + 2 <= max_size:
                if current_segment:
                    current_segment += "\n\n"
                current_segment += para
            else:
                if current_segment:
                    segments.append(current_segment)

                # 如果單個段落太長，強制分割
                if len(para) > max_size:
                    para_segments = textwrap.wrap(para, width=max_size)
                    segments.extend(para_segments[:-1])
                    current_segment = para_segments[-1]
                else:
                    current_segment = para

        if current_segment:
            segments.append(current_segment)

        return segments

    def _log_single(self, level: str, message: str, trace_id: str, category: str):
        """記錄單條日誌"""
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(f"🚀 {message} [{trace_id}]")

    def save_response_as_markdown(self,
                                 response: str,
                                 metadata: Dict[str, Any],
                                 trace_id: str) -> Path:
        """
        將回應保存為 Markdown 文件

        Args:
            response: 回應內容
            metadata: 元數據（包含查詢、模式、時間等）
            trace_id: 追蹤ID

        Returns:
            Markdown 文件路徑
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"response_{trace_id}_{timestamp}.md"
        filepath = self.reports_dir / filename

        # 構建 Markdown 內容
        markdown_content = self._build_markdown_report(response, metadata, trace_id)

        # 保存文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        # 如果內容太長，同時創建分段版本
        if len(response) > self.MAX_LOG_SIZE:
            self._save_segmented_markdown(response, metadata, trace_id, timestamp)

        self.logger.info(f"📝 Response saved to markdown: {filepath} [{trace_id}]")

        return filepath

    def _build_markdown_report(self,
                              response: str,
                              metadata: Dict[str, Any],
                              trace_id: str) -> str:
        """構建 Markdown 報告"""

        # 提取元數據
        query = metadata.get('query', 'N/A')
        mode = metadata.get('mode', 'N/A')
        model = metadata.get('model', 'N/A')
        tokens = metadata.get('tokens', {})
        duration = metadata.get('duration_ms', 0)
        timestamp = metadata.get('timestamp', datetime.now().isoformat())

        # 構建 Markdown
        markdown = f"""# OpenCode AI Response Report

## Metadata

| Field | Value |
|-------|-------|
| **Trace ID** | `{trace_id}` |
| **Timestamp** | {timestamp} |
| **Mode** | {mode} |
| **Model** | {model} |
| **Duration** | {duration}ms |
| **Input Tokens** | {tokens.get('prompt_tokens', 'N/A')} |
| **Output Tokens** | {tokens.get('completion_tokens', 'N/A')} |
| **Total Tokens** | {tokens.get('total_tokens', 'N/A')} |

## Query

```
{query}
```

## Response

{response}

---

### Processing Details

"""

        # 添加處理細節
        if 'stages' in metadata:
            markdown += "#### Stage Execution\n\n"
            for stage in metadata.get('stages', []):
                markdown += f"- **{stage['name']}**: {stage['duration']}ms - {stage['status']}\n"

        # 添加引用統計
        if 'citations' in metadata:
            citations = metadata['citations']
            markdown += f"\n#### Citation Statistics\n\n"
            markdown += f"- Cited References: {citations.get('cited_count', 0)}\n"
            markdown += f"- Uncited References: {citations.get('uncited_count', 0)}\n"
            markdown += f"- Total References: {citations.get('total_count', 0)}\n"
            markdown += f"- Citation Rate: {citations.get('citation_rate', 0):.1f}%\n"

        # 添加錯誤信息（如果有）
        if 'errors' in metadata and metadata['errors']:
            markdown += f"\n#### Errors\n\n"
            for error in metadata['errors']:
                markdown += f"- {error}\n"

        markdown += f"""

---

*Generated by OpenCode Platform v2.0*
*Report ID: {trace_id}*
*Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        return markdown

    def _save_segmented_markdown(self,
                                response: str,
                                metadata: Dict[str, Any],
                                trace_id: str,
                                timestamp: str):
        """保存分段的 Markdown 文件"""
        segments = self._split_content(response, self.MAX_LOG_SIZE)

        for i, segment in enumerate(segments):
            filename = f"response_{trace_id}_{timestamp}_part{i+1}of{len(segments)}.md"
            filepath = self.reports_dir / filename

            # 構建分段 Markdown
            part_metadata = metadata.copy()
            part_metadata['part'] = f"{i+1}/{len(segments)}"

            markdown_content = f"""# OpenCode AI Response Report - Part {i+1}/{len(segments)}

## Metadata

| Field | Value |
|-------|-------|
| **Trace ID** | `{trace_id}` |
| **Part** | {i+1} of {len(segments)} |
| **Segment Size** | {len(segment)} characters |

## Response (Part {i+1})

{segment}

---

*This is part {i+1} of {len(segments)} segments*
*Full response saved in segments due to length*
"""

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

    def load_segments(self, trace_id: str, content_hash: str) -> Optional[str]:
        """載入分段內容並重組"""
        segments = []
        segment_files = sorted(self.segments_dir.glob(f"{trace_id}_{content_hash}_*.json"))

        for segment_file in segment_files:
            with open(segment_file, 'r', encoding='utf-8') as f:
                segment_data = json.load(f)
                segments.append((segment_data['segment_index'], segment_data['content']))

        if not segments:
            return None

        # 按索引排序並合併
        segments.sort(key=lambda x: x[0])
        full_content = ''.join(seg[1] for seg in segments)

        return full_content

    def get_metrics(self) -> Dict[str, Any]:
        """獲取日誌指標"""
        log_files = list(self.base_path.glob("*.log"))
        segment_files = list(self.segments_dir.glob("*.json"))
        report_files = list(self.reports_dir.glob("*.md"))

        total_size = sum(f.stat().st_size for f in log_files)
        total_size += sum(f.stat().st_size for f in segment_files)
        total_size += sum(f.stat().st_size for f in report_files)

        return {
            "log_files": len(log_files),
            "segment_files": len(segment_files),
            "report_files": len(report_files),
            "total_size_mb": total_size / (1024 * 1024),
            "reports_dir": str(self.reports_dir)
        }


# 單例實例
_enhanced_logger = None

def get_enhanced_logger() -> EnhancedLogger:
    """獲取增強日誌器單例"""
    global _enhanced_logger
    if _enhanced_logger is None:
        _enhanced_logger = EnhancedLogger()
    return _enhanced_logger