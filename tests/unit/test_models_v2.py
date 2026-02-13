"""
Unit tests for models_v2.py - New data structures

Test strategy:
1. Verify data self-containment (no dict mapping)
2. Verify backward compatibility
3. Verify validation logic
4. Verify type safety
"""

import pytest
from datetime import datetime

from core.models_v2 import (
    ProcessingMode,
    Modes,
    RuntimeType,
    Event,
    EventType,
    Request,
    Response,
    ProcessingContext,
    RoutingDecision,
    ProcessingModeEnum,
    create_context,
)


# ========== ProcessingMode Tests ==========

class TestProcessingMode:
    """測試新的 ProcessingMode 數據結構"""
    
    def test_mode_is_frozen(self):
        """驗證 ProcessingMode 是不可變的"""
        mode = Modes.CHAT
        with pytest.raises(Exception):  # FrozenInstanceError
            mode.name = "modified"
    
    def test_mode_has_self_contained_data(self):
        """驗證數據自包含（無字典映射）"""
        mode = Modes.CHAT
        
        # 直接訪問屬性，無需字典映射
        assert mode.name == "chat"
        assert mode.cognitive_level == "system1"
        assert mode.runtime_type == RuntimeType.MODEL
        assert mode.description
    
    def test_chat_mode_attributes(self):
        """測試 CHAT mode 的所有屬性"""
        assert Modes.CHAT.name == "chat"
        assert Modes.CHAT.cognitive_level == "system1"
        assert Modes.CHAT.runtime_type == RuntimeType.MODEL
        assert Modes.CHAT.default_temperature == 0.7
        assert Modes.CHAT.default_max_tokens == 4000
        assert "chat" in Modes.CHAT.keywords or "聊天" in Modes.CHAT.keywords
    
    def test_search_mode_is_system2(self):
        """測試 SEARCH mode 屬於 system2"""
        assert Modes.SEARCH.cognitive_level == "system2"
        assert Modes.SEARCH.runtime_type == RuntimeType.MODEL
    
    def test_deep_research_is_agent(self):
        """測試 DEEP_RESEARCH mode 屬於 agent"""
        assert Modes.DEEP_RESEARCH.cognitive_level == "agent"
        assert Modes.DEEP_RESEARCH.runtime_type == RuntimeType.AGENT
    
    def test_all_modes_have_required_fields(self):
        """測試所有 mode 都有必需字段"""
        for mode in Modes.all():
            assert mode.name
            assert mode.cognitive_level in ["system1", "system2", "agent"]
            assert isinstance(mode.runtime_type, RuntimeType)
            assert mode.description
            assert 0.0 <= mode.default_temperature <= 2.0
            assert mode.default_max_tokens > 0
    
    def test_mode_equality_with_string(self):
        """測試 mode 可以與字符串比較"""
        assert Modes.CHAT == "chat"
        assert Modes.SEARCH == "search"
        assert not (Modes.CHAT == "search")
    
    def test_mode_equality_with_mode(self):
        """測試 mode 之間的比較"""
        chat1 = Modes.CHAT
        chat2 = Modes.from_name("chat")
        assert chat1 == chat2
        assert not (chat1 == Modes.SEARCH)
    
    def test_mode_hashable(self):
        """測試 mode 可以作為字典鍵"""
        mode_dict = {Modes.CHAT: "value1", Modes.SEARCH: "value2"}
        assert mode_dict[Modes.CHAT] == "value1"


class TestModesRegistry:
    """測試 Modes 常量註冊表"""
    
    def test_from_name_lowercase(self):
        """測試 from_name 支持小寫"""
        assert Modes.from_name("chat") == Modes.CHAT
        assert Modes.from_name("search") == Modes.SEARCH
    
    def test_from_name_case_insensitive(self):
        """測試 from_name 不區分大小寫"""
        assert Modes.from_name("CHAT") == Modes.CHAT
        assert Modes.from_name("Search") == Modes.SEARCH
    
    def test_from_name_unknown_returns_default(self):
        """測試未知 name 返回默認值"""
        assert Modes.from_name("unknown") == Modes.CHAT
    
    def test_all_returns_non_auto_modes(self):
        """測試 all() 不包含 AUTO"""
        modes = Modes.all()
        assert len(modes) == 6
        assert Modes.AUTO not in modes
        assert Modes.CHAT in modes


# ========== Event Tests ==========

class TestEvent:
    """測試統一事件模型"""
    
    def test_event_creation(self):
        """測試事件創建"""
        event = Event(type=EventType.INFO, data={"message": "test"})
        assert event.type == EventType.INFO
        assert event.data == {"message": "test"}
        assert isinstance(event.timestamp, datetime)
    
    def test_event_to_dict(self):
        """測試事件轉字典"""
        event = Event(
            type=EventType.MESSAGE,
            data="Hello",
            trace_id="trace-123",
            step="step1"
        )
        d = event.to_dict()
        
        assert d["type"] == "message"
        assert d["data"] == "Hello"
        assert d["trace_id"] == "trace-123"
        assert d["step"] == "step1"
        assert "timestamp" in d
    
    def test_event_to_sse(self):
        """測試 SSE 格式轉換"""
        event = Event(type=EventType.TOKEN, data="word")
        sse = event.to_sse()
        
        assert sse.startswith("data: ")
        assert sse.endswith("\n\n")
        assert "token" in sse
        assert "word" in sse


# ========== Request Tests ==========

class TestRequest:
    """測試新的 Request 模型"""
    
    def test_request_basic_creation(self):
        """測試基本請求創建"""
        req = Request(query="test query")
        assert req.query == "test query"
        assert req.mode == Modes.AUTO
        assert req.context_id
        assert req.trace_id
    
    def test_request_strips_whitespace(self):
        """測試自動去除空白"""
        req = Request(query="  test  ")
        assert req.query == "test"
    
    def test_request_empty_query_raises(self):
        """測試空查詢拋出異常"""
        with pytest.raises(ValueError, match="empty"):
            Request(query="")
        
        with pytest.raises(ValueError, match="empty"):
            Request(query="   ")
    
    def test_request_too_long_raises(self):
        """測試過長查詢拋出異常"""
        long_query = "x" * 50001
        with pytest.raises(ValueError, match="too long"):
            Request(query=long_query)
    
    def test_request_string_mode_converted(self):
        """測試字符串 mode 自動轉換"""
        req = Request(query="test", mode="chat")
        assert req.mode == Modes.CHAT
        assert isinstance(req.mode, ProcessingMode)
    
    def test_request_uses_mode_defaults(self):
        """測試使用 mode 的默認值"""
        req = Request(query="test", mode=Modes.CHAT)
        assert req.temperature == Modes.CHAT.default_temperature
        assert req.max_tokens == Modes.CHAT.default_max_tokens
    
    def test_request_override_defaults(self):
        """測試覆蓋默認值"""
        req = Request(
            query="test",
            mode=Modes.CHAT,
            temperature=0.9,
            max_tokens=2000
        )
        assert req.temperature == 0.9
        assert req.max_tokens == 2000
    
    def test_request_invalid_temperature_raises(self):
        """測試無效溫度拋出異常"""
        with pytest.raises(ValueError, match="Temperature"):
            Request(query="test", temperature=3.0)
        
        with pytest.raises(ValueError, match="Temperature"):
            Request(query="test", temperature=-0.1)


# ========== Response Tests ==========

class TestResponse:
    """測試新的 Response 模型"""
    
    def test_response_add_event(self):
        """測試添加事件"""
        resp = Response(result="test", mode=Modes.CHAT, trace_id="t1")
        resp.add_event(EventType.INFO, {"msg": "hello"})
        
        assert len(resp.events) == 1
        assert resp.events[0].type == EventType.INFO
        assert resp.events[0].data == {"msg": "hello"}
        assert resp.events[0].trace_id == "t1"
    
    def test_response_get_events_by_type(self):
        """測試按類型獲取事件"""
        resp = Response(result="test", mode=Modes.CHAT, trace_id="t1")
        resp.add_event(EventType.INFO, "info1")
        resp.add_event(EventType.TOKEN, "token1")
        resp.add_event(EventType.INFO, "info2")
        
        info_events = resp.get_events_by_type(EventType.INFO)
        assert len(info_events) == 2
        assert info_events[0].data == "info1"
        assert info_events[1].data == "info2"


# ========== ProcessingContext Tests ==========

class TestProcessingContext:
    """測試簡化的 ProcessingContext"""
    
    def test_context_creation(self):
        """測試上下文創建"""
        req = Request(query="test")
        resp = Response(result="", mode=req.mode, trace_id=req.trace_id)
        ctx = ProcessingContext(request=req, response=resp)
        
        assert ctx.request == req
        assert ctx.response == resp
        assert ctx.total_tokens == 0
        assert ctx.current_step == ""
    
    def test_step_tracking(self):
        """測試步驟追蹤"""
        ctx = create_context(Request(query="test"))
        
        ctx.set_current_step("step1")
        assert ctx.current_step == "step1"
        
        ctx.mark_step_complete("step1")
        assert "step1" in ctx.steps_completed
        assert ctx.current_step == ""
    
    def test_elapsed_time(self):
        """測試時間統計"""
        import time
        ctx = create_context(Request(query="test"))
        time.sleep(0.1)
        elapsed = ctx.get_elapsed_time()
        assert elapsed >= 100  # At least 100ms


# ========== Backward Compatibility Tests ==========

class TestBackwardCompatibility:
    """測試向後兼容性"""
    
    def test_legacy_enum_still_works(self):
        """測試舊的 Enum 仍然可用"""
        mode = ProcessingModeEnum.CHAT
        assert mode.value == "chat"
    
    def test_legacy_enum_cognitive_level(self):
        """測試舊的 cognitive_level 屬性"""
        assert ProcessingModeEnum.CHAT.cognitive_level == "system1"
        assert ProcessingModeEnum.SEARCH.cognitive_level == "system2"
        assert ProcessingModeEnum.DEEP_RESEARCH.cognitive_level == "agent"
    
    def test_legacy_enum_to_v2_conversion(self):
        """測試轉換到 V2"""
        legacy_mode = ProcessingModeEnum.CHAT
        v2_mode = legacy_mode.to_v2()
        assert v2_mode == Modes.CHAT
        assert v2_mode.cognitive_level == "system1"


# ========== Integration Tests ==========

class TestModelsV2Integration:
    """測試模型間的集成"""
    
    def test_request_response_context_flow(self):
        """測試完整的請求-響應-上下文流程"""
        # Create request
        req = Request(
            query="What is Python?",
            mode=Modes.CHAT,
            temperature=0.8
        )
        
        # Create context
        ctx = create_context(req)
        assert ctx.request.query == "What is Python?"
        assert ctx.response.mode == Modes.CHAT
        
        # Process (simulate)
        ctx.set_current_step("llm_call")
        ctx.total_tokens = 150
        ctx.response.result = "Python is a programming language"
        ctx.response.add_event(EventType.MESSAGE, "Processing...")
        ctx.mark_step_complete("llm_call")
        
        # Verify
        assert ctx.total_tokens == 150
        assert ctx.response.result
        assert len(ctx.response.events) == 1
        assert "llm_call" in ctx.steps_completed
    
    def test_routing_decision_with_modes(self):
        """測試路由決策使用新 Modes"""
        decision = RoutingDecision(
            mode=Modes.SEARCH,
            confidence=0.92,
            reason="Query contains '搜尋' keyword"
        )
        
        assert decision.mode == Modes.SEARCH
        assert decision.cognitive_level == "system2"
        assert decision.runtime_type == RuntimeType.MODEL
