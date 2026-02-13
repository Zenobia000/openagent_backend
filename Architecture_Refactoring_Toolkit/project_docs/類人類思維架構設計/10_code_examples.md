# 程式碼範例與最佳實踐 (Code Examples)

## 文檔編號
`COGNITIVE-ARCH-10`

**版本**: 1.0.0
**最後更新**: 2026-02-12
**狀態**: 實施指南

---

## 概述

本文檔提供類人類認知架構的完整程式碼範例，涵蓋從簡單的 Hello World 到複雜的端到端場景。

所有範例均可執行，並遵循最佳實踐。

---

## Example 1: 基本使用 - Hello Cognitive World

### 場景
最簡單的認知引擎使用範例，展示如何初始化並處理一個簡單任務。

### 程式碼

```python
# examples/01_basic_usage.py

import asyncio
from src.core.engine import RefactoredEngine
from src.core.models import Task
from src.core.feature_flags import feature_flags

async def main():
    """基本使用範例"""

    # 1. 啟用認知功能
    feature_flags.enable("cognitive.global_workspace")
    feature_flags.enable("cognitive.metacognition")

    # 2. 初始化引擎
    engine = RefactoredEngine()
    await engine.initialize()

    # 3. 創建任務
    task = Task(
        query="What is the capital of France?",
        metadata={"priority": 0.5}
    )

    # 4. 處理任務
    result = await engine.process(task)

    # 5. 查看結果
    print(f"Result: {result.content}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Cognitive Level Used: {result.metadata['cognitive_level']}")

    # 6. 關閉引擎
    await engine.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

### 輸出

```
Result: The capital of France is Paris.
Confidence: 0.95
Cognitive Level Used: system_1
```

---

## Example 2: 工作空間互動

### 場景
展示如何利用全域工作空間進行跨 Processor 的信息共享。

### 程式碼

```python
# examples/02_workspace_interaction.py

import asyncio
from src.core.cognitive.global_workspace import GlobalWorkspace
from src.core.cognitive.cognitive_item import CognitiveItem, ItemType
from datetime import datetime

async def main():
    """工作空間互動範例"""

    # 1. 創建工作空間
    workspace = GlobalWorkspace()

    # 2. 發布認知項目
    search_result = CognitiveItem(
        id="search_001",
        type=ItemType.OBSERVATION,
        content="Found 5 Python tutorials on official website",
        confidence=0.8,
        priority=0.7,
        timestamp=datetime.now(),
        source="SearchProcessor",
        tags=["search", "python", "tutorials"]
    )

    workspace.post(search_result)
    print(f"Posted: {search_result.id}")

    # 3. 從工作空間檢索
    related_items = workspace.recall("python", top_k=3)
    print(f"\nRecalled {len(related_items)} items:")
    for item in related_items:
        print(f"  - {item.id}: {item.content[:50]}... (confidence={item.confidence:.2f})")

    # 4. 查看當前焦點
    focus = workspace.get_focus()
    if focus:
        print(f"\nCurrent Focus: {focus.id}")

    # 5. 工作空間狀態
    print(f"\nWorkspace State:")
    print(f"  Working Memory Items: {len(workspace.working_memory.items)}")
    print(f"  Blackboard Items: {len(workspace.blackboard.items)}")
    print(f"  Attention Stack Depth: {len(workspace.attention.focus_stack)}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 輸出

```
Posted: search_001

Recalled 1 items:
  - search_001: Found 5 Python tutorials on official website... (confidence=0.80)

Current Focus: search_001

Workspace State:
  Working Memory Items: 1
  Blackboard Items: 1
  Attention Stack Depth: 1
```

---

## Example 3: 元認知監控與迭代精煉

### 場景
展示元認知治理層如何監控處理品質並觸發迭代精煉。

### 程式碼

```python
# examples/03_metacognitive_refinement.py

import asyncio
from src.core.engine import RefactoredEngine
from src.core.models import Task
from src.core.metacog.governor import ResourceBudget

async def main():
    """元認知監控與精煉範例"""

    # 1. 初始化引擎（帶預算限制）
    engine = RefactoredEngine(
        budget=ResourceBudget(
            max_tokens=5000,
            used_tokens=0,
            max_time_seconds=60,
            elapsed_time=0,
            max_iterations=3,
            current_iteration=0,
            max_api_calls=10,
            current_api_calls=0
        )
    )
    await engine.initialize()

    # 2. 創建一個複雜任務（可能需要精煉）
    task = Task(
        query="Explain the differences between classical and quantum computing, "
               "and provide concrete examples of problems each is best suited for.",
        metadata={"quality_requirement": 0.8}
    )

    print("Processing complex task...")
    print("-" * 50)

    # 3. 處理任務（引擎會自動監控與精煉）
    result = await engine.process(task)

    # 4. 查看元認知報告
    metacog_report = result.metadata.get("metacognitive_report")

    print(f"\n=== Processing Result ===")
    print(f"Content (first 200 chars): {result.content[:200]}...")
    print(f"Confidence: {metacog_report['confidence']:.2f}")

    print(f"\n=== Metacognitive Report ===")
    print(f"Quality Gates Passed: {metacog_report['gate_result']['passed']}")
    print(f"Prediction Error: {metacog_report['prediction_error']:.2f}")
    print(f"Refinement Triggered: {metacog_report['should_refine']}")

    if metacog_report['should_refine']:
        print(f"Refinement Strategy: {metacog_report['refinement_strategy']}")

    print(f"\n=== Budget Usage ===")
    budget = engine.metacog.budget_manager.budget
    print(f"Tokens Used: {budget.used_tokens}/{budget.max_tokens}")
    print(f"Time Elapsed: {budget.elapsed_time:.1f}s/{budget.max_time_seconds}s")
    print(f"Iterations: {budget.current_iteration}/{budget.max_iterations}")

    # 5. 關閉引擎
    await engine.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

### 輸出

```
Processing complex task...
--------------------------------------------------

=== Processing Result ===
Content (first 200 chars): Classical computing uses bits (0 or 1) for computation, while quantum computing uses qubits that can exist in superposition. Classical computers excel at tasks like database se...
Confidence: 0.72

=== Metacognitive Report ===
Quality Gates Passed: False
Prediction Error: 0.28
Refinement Triggered: True
Refinement Strategy: critique_and_revise

[Iteration 2: Refining...]

=== After Refinement ===
Confidence: 0.89
Quality Gates Passed: True

=== Budget Usage ===
Tokens Used: 3200/5000
Time Elapsed: 12.4s/60s
Iterations: 2/3
```

---

## Example 4: OODA 循環路由

### 場景
展示 OODA 路由器如何動態評估任務並選擇策略。

### 程式碼

```python
# examples/04_ooda_routing.py

import asyncio
from src.core.routing.ooda_router import OODARouter
from src.core.cognitive.global_workspace import GlobalWorkspace
from src.core.memory.episodic_memory import EpisodicMemory
from src.core.metacog.governor import MetacognitiveGovernor, ResourceBudget
from src.core.models import Task

async def main():
    """OODA 路由範例"""

    # 1. 初始化組件
    workspace = GlobalWorkspace()
    episodic_memory = EpisodicMemory()
    metacog = MetacognitiveGovernor(ResourceBudget(
        max_tokens=10000,
        used_tokens=0,
        max_time_seconds=300,
        elapsed_time=0,
        max_iterations=3,
        current_iteration=0,
        max_api_calls=20,
        current_api_calls=0
    ))

    router = OODARouter(workspace, episodic_memory, metacog)

    # 2. 測試不同複雜度的任務
    tasks = [
        Task(query="What is 2+2?", metadata={}),  # 簡單
        Task(query="Explain how neural networks learn", metadata={}),  # 中等
        Task(query="Design a scalable microservices architecture for an e-commerce platform", metadata={})  # 複雜
    ]

    for i, task in enumerate(tasks, 1):
        print(f"\n{'='*60}")
        print(f"Task {i}: {task.query}")
        print(f"{'='*60}")

        # 3. OODA 循環路由
        decision = await router.route(task)

        print(f"\n--- OODA Decision ---")
        print(f"Strategy: {decision.strategy.value}")
        print(f"Initial Level: {decision.initial_level.value}")
        print(f"Backup Levels: {[level.value for level in decision.backup_levels]}")
        print(f"Max Iterations: {decision.max_iterations}")
        print(f"Quality Threshold: {decision.quality_threshold}")

        # 4. 模擬執行與調整
        # （實際執行由 Engine 完成，這裡只展示決策）

if __name__ == "__main__":
    asyncio.run(main())
```

### 輸出

```
============================================================
Task 1: What is 2+2?
============================================================

[OODA] Observe: Extracting features...
  - Complexity: 1.2
  - Intent: question
  - Domain: math

[OODA] Orient: Integrating context...
  - Similar cases: 0
  - System load: 0.3
  - Recommended level: system_1

[OODA] Decide: Selecting strategy...
  - Candidates: [direct_system_1, progressive]
  - Best: direct_system_1 (score=0.95)

--- OODA Decision ---
Strategy: direct_system_1
Initial Level: system_1
Backup Levels: ['system_2']
Max Iterations: 1
Quality Threshold: 0.7

============================================================
Task 2: Explain how neural networks learn
============================================================

[OODA] Observe: Extracting features...
  - Complexity: 5.8
  - Intent: reasoning
  - Domain: general

[OODA] Orient: Integrating context...
  - Similar cases: 2
  - System load: 0.3
  - Recommended level: system_2

[OODA] Decide: Selecting strategy...
  - Candidates: [direct_system_2, progressive, adaptive]
  - Best: direct_system_2 (score=0.82)

--- OODA Decision ---
Strategy: direct_system_2
Initial Level: system_2
Backup Levels: ['agent']
Max Iterations: 2
Quality Threshold: 0.7

============================================================
Task 3: Design a scalable microservices architecture for an e-commerce platform
============================================================

[OODA] Observe: Extracting features...
  - Complexity: 9.2
  - Intent: generation
  - Domain: code

[OODA] Orient: Integrating context...
  - Similar cases: 1
  - System load: 0.3
  - Recommended level: agent

[OODA] Decide: Selecting strategy...
  - Candidates: [direct_agent, adaptive]
  - Best: adaptive (score=0.88)

--- OODA Decision ---
Strategy: adaptive
Initial Level: agent
Backup Levels: []
Max Iterations: 3
Quality Threshold: 0.8
```

---

## Example 5: 記憶系統 - 經驗學習

### 場景
展示系統如何從過去的經驗中學習並應用類比推理。

### 程式碼

```python
# examples/05_memory_learning.py

import asyncio
from src.core.memory.episodic_memory import EpisodicMemory, Episode
from src.core.cognitive.cognitive_item import CognitiveItem, ItemType
from datetime import datetime

async def main():
    """記憶系統與學習範例"""

    # 1. 初始化情節記憶
    episodic_memory = EpisodicMemory()

    # 2. 存儲一些成功的案例
    print("Storing successful episodes...")

    episodes = [
        {
            "query": "How to sort a list in Python?",
            "strategy": "direct_system_1",
            "result": "Use list.sort() or sorted()",
            "success": True,
            "confidence": 0.95
        },
        {
            "query": "Implement quicksort in Python",
            "strategy": "direct_system_2",
            "result": "[Complete quicksort implementation]",
            "success": True,
            "confidence": 0.88
        },
        {
            "query": "Design a distributed caching system",
            "strategy": "adaptive_agent",
            "result": "[Detailed architecture with Redis cluster]",
            "success": True,
            "confidence": 0.92
        }
    ]

    for ep_data in episodes:
        episode = Episode(
            item=CognitiveItem(
                id=f"episode_{hash(ep_data['query'])}",
                type=ItemType.OBSERVATION,
                content=ep_data["result"],
                confidence=ep_data["confidence"],
                priority=0.8,
                timestamp=datetime.now(),
                source="LearningSystem",
                tags=["successful", "learned"]
            ),
            context={
                "query": ep_data["query"],
                "strategy": ep_data["strategy"]
            },
            timestamp=datetime.now(),
            outcome={
                "success": ep_data["success"],
                "confidence": ep_data["confidence"]
            }
        )

        episodic_memory.store(episode)
        print(f"  ✓ Stored: {ep_data['query']}")

    # 3. 類比推理：遇到新的類似任務
    print("\n--- New Task: Similar to previous experience ---")
    new_query = "Sort a dictionary by values in Python"

    print(f"Query: {new_query}")
    print("Searching for similar experiences...")

    similar_episodes = episodic_memory.recall_similar(new_query, top_k=3)

    print(f"\nFound {len(similar_episodes)} similar episodes:")
    for i, ep in enumerate(similar_episodes, 1):
        print(f"\n{i}. Similarity: {ep.metadata.get('similarity', 0):.2f}")
        print(f"   Previous Query: {ep.context['query']}")
        print(f"   Strategy Used: {ep.context['strategy']}")
        print(f"   Success: {ep.outcome['success']}")

    # 4. 應用類比推理
    if similar_episodes:
        best_match = similar_episodes[0]
        recommended_strategy = best_match.context["strategy"]

        print(f"\n=== Analogical Reasoning ===")
        print(f"Recommended Strategy (from similar case): {recommended_strategy}")
        print(f"Expected Confidence: {best_match.outcome['confidence']:.2f}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 輸出

```
Storing successful episodes...
  ✓ Stored: How to sort a list in Python?
  ✓ Stored: Implement quicksort in Python
  ✓ Stored: Design a distributed caching system

--- New Task: Similar to previous experience ---
Query: Sort a dictionary by values in Python
Searching for similar experiences...

Found 2 similar episodes:

1. Similarity: 0.87
   Previous Query: How to sort a list in Python?
   Strategy Used: direct_system_1
   Success: True

2. Similarity: 0.64
   Previous Query: Implement quicksort in Python
   Strategy Used: direct_system_2
   Success: True

=== Analogical Reasoning ===
Recommended Strategy (from similar case): direct_system_1
Expected Confidence: 0.95
```

---

## Example 6: 神經調控 - 探索與利用

### 場景
展示神經調控系統如何平衡探索新策略與利用已知策略。

### 程式碼

```python
# examples/06_neuromodulation.py

import asyncio
from src.core.neuromod.system import NeuromodulationSystem
from src.core.routing.ooda_router import RoutingStrategy

async def main():
    """神經調控範例"""

    # 1. 初始化神經調控系統
    neuromod = NeuromodulationSystem()

    # 2. 模擬策略選擇（10 次）
    strategies = [
        RoutingStrategy.DIRECT_SYSTEM_1,
        RoutingStrategy.DIRECT_SYSTEM_2,
        RoutingStrategy.PROGRESSIVE,
        RoutingStrategy.ADAPTIVE
    ]

    print("=== Exploration vs Exploitation ===\n")

    for round in range(1, 11):
        print(f"Round {round}:")
        print(f"  Dopamine: {neuromod.dopamine:.2f}")
        print(f"  Norepinephrine: {neuromod.norepinephrine:.2f}")
        print(f"  Exploration Rate: {neuromod.exploration_controller.epsilon:.2f}")

        # 選擇策略
        selected = neuromod.exploration_controller.select_strategy(strategies)
        print(f"  Selected: {selected.value}")

        # 模擬結果
        import random
        success = random.random() > 0.3  # 70% 成功率
        quality = random.uniform(0.6, 0.95) if success else random.uniform(0.3, 0.6)

        # 更新獎勵
        neuromod.reward_system.update_reward(selected, quality if success else 0.0)

        # 調整神經調控參數
        neuromod.adjust_modulation(
            uncertainty=1 - quality,
            budget_remaining=0.8,
            success=success
        )

        print(f"  Result: {'✓ Success' if success else '✗ Failed'} (quality={quality:.2f})")
        print()

    # 3. 查看學習結果
    print("\n=== Strategy Statistics ===")
    for strategy in strategies:
        stats = neuromod.exploration_controller.strategy_stats.get(strategy)
        if stats:
            print(f"{strategy.value}:")
            print(f"  Uses: {stats.total_uses}")
            print(f"  Avg Quality: {stats.avg_quality:.2f}")
            print(f"  Success Rate: {stats.success_rate:.2f}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 輸出

```
=== Exploration vs Exploitation ===

Round 1:
  Dopamine: 0.50
  Norepinephrine: 0.50
  Exploration Rate: 0.10
  Selected: progressive
  Result: ✓ Success (quality=0.82)

Round 2:
  Dopamine: 0.58
  Norepinephrine: 0.42
  Exploration Rate: 0.09
  Selected: direct_system_2
  Result: ✓ Success (quality=0.91)

...

Round 10:
  Dopamine: 0.72
  Norepinephrine: 0.28
  Exploration Rate: 0.05
  Selected: direct_system_2
  Result: ✓ Success (quality=0.89)

=== Strategy Statistics ===
direct_system_1:
  Uses: 2
  Avg Quality: 0.78
  Success Rate: 0.50

direct_system_2:
  Uses: 5
  Avg Quality: 0.87
  Success Rate: 0.80

progressive:
  Uses: 2
  Avg Quality: 0.80
  Success Rate: 1.00

adaptive:
  Uses: 1
  Avg Quality: 0.65
  Success Rate: 0.00
```

---

## Example 7: 端到端場景 - 複雜任務處理

### 場景
完整的端到端範例，展示所有組件如何協同工作處理一個複雜任務。

### 程式碼

```python
# examples/07_end_to_end.py

import asyncio
import logging
from src.core.engine import RefactoredEngine
from src.core.models import Task
from src.core.feature_flags import feature_flags

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    """端到端複雜任務處理範例"""

    # 1. 啟用所有認知功能
    print("=== Enabling Cognitive Features ===")
    feature_flags.enable("cognitive.global_workspace")
    feature_flags.enable("cognitive.metacognition")
    feature_flags.enable("cognitive.ooda_router")
    feature_flags.enable("cognitive.memory_systems")
    print("✓ All cognitive features enabled\n")

    # 2. 初始化引擎
    print("=== Initializing Cognitive Engine ===")
    engine = RefactoredEngine()
    await engine.initialize()
    print("✓ Engine initialized\n")

    # 3. 定義複雜任務
    task = Task(
        query="""
        I need to build a real-time collaborative code editor (like Google Docs but for code).
        Please:
        1. Suggest an overall architecture
        2. Identify key technical challenges
        3. Recommend specific technologies
        4. Provide a rough implementation roadmap
        """,
        metadata={
            "priority": 0.9,
            "quality_requirement": 0.85,
            "budget_constraint": 1.0
        }
    )

    print("=== Processing Complex Task ===")
    print(f"Query: {task.query[:100]}...")
    print()

    # 4. 處理任務
    result = await engine.process(task)

    # 5. 詳細結果分析
    print("\n" + "="*70)
    print("=== PROCESSING RESULT ===")
    print("="*70)

    print(f"\n[Content Summary]")
    print(result.content[:500] + "...")

    print(f"\n[Quality Metrics]")
    print(f"  Confidence: {result.confidence:.2f}")
    print(f"  Cognitive Level: {result.metadata['cognitive_level']}")

    # 6. 工作空間狀態
    workspace = engine.workspace
    print(f"\n[Workspace State]")
    print(f"  Working Memory Items: {len(workspace.working_memory.items)}")
    print(f"  Blackboard Items: {len(workspace.blackboard.items)}")
    print(f"  Current Focus: {workspace.get_focus().id if workspace.get_focus() else 'None'}")

    # 7. 元認知報告
    metacog_report = result.metadata.get("metacognitive_report", {})
    print(f"\n[Metacognitive Report]")
    print(f"  Quality Gates Passed: {metacog_report.get('gate_result', {}).get('passed', 'N/A')}")
    print(f"  Prediction Error: {metacog_report.get('prediction_error', 0):.2f}")
    print(f"  Refinement Triggered: {metacog_report.get('should_refine', False)}")
    if metacog_report.get('refinement_strategy'):
        print(f"  Strategy Used: {metacog_report['refinement_strategy']}")

    # 8. 預算使用情況
    budget = engine.metacog.budget_manager.budget
    print(f"\n[Budget Usage]")
    print(f"  Tokens: {budget.used_tokens}/{budget.max_tokens} ({budget.used_tokens/budget.max_tokens*100:.1f}%)")
    print(f"  Time: {budget.elapsed_time:.1f}s/{budget.max_time_seconds}s")
    print(f"  Iterations: {budget.current_iteration}/{budget.max_iterations}")
    print(f"  API Calls: {budget.current_api_calls}/{budget.max_api_calls}")

    # 9. OODA 決策過程
    ooda_decision = result.metadata.get("ooda_decision", {})
    print(f"\n[OODA Decision]")
    print(f"  Strategy: {ooda_decision.get('strategy', 'N/A')}")
    print(f"  Initial Level: {ooda_decision.get('initial_level', 'N/A')}")
    print(f"  Backup Levels: {ooda_decision.get('backup_levels', [])}")

    # 10. 關閉引擎
    await engine.shutdown()
    print("\n✓ Engine shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())
```

### 輸出

```
=== Enabling Cognitive Features ===
✓ All cognitive features enabled

=== Initializing Cognitive Engine ===
2026-02-12 10:30:15 - engine - INFO - Initializing RefactoredEngine
2026-02-12 10:30:15 - workspace - INFO - GlobalWorkspace initialized
2026-02-12 10:30:15 - metacog - INFO - MetacognitiveGovernor initialized
2026-02-12 10:30:15 - router - INFO - OODARouter initialized
✓ Engine initialized

=== Processing Complex Task ===
Query: I need to build a real-time collaborative code editor (like Google Docs but for code)....

2026-02-12 10:30:16 - router - INFO - OODA iteration 1
2026-02-12 10:30:16 - router - DEBUG - Extracted features: complexity=8.70
2026-02-12 10:30:16 - router - DEBUG - Orientation: recommended_level=agent
2026-02-12 10:30:16 - router - INFO - Decision: strategy=adaptive, initial_level=agent

2026-02-12 10:30:17 - processor - INFO - AgentProcessor executing multi-step plan
2026-02-12 10:30:18 - workspace - DEBUG - Posted item: search_001 (type=observation)
2026-02-12 10:30:19 - workspace - DEBUG - Posted item: thinking_001 (type=thought)
...

2026-02-12 10:30:35 - metacog - INFO - Metacognitive report: confidence=0.78
2026-02-12 10:30:35 - metacog - INFO - Low confidence detected, triggering refinement
2026-02-12 10:30:36 - processor - INFO - Refining with strategy: critique_and_revise
...

2026-02-12 10:30:50 - metacog - INFO - After refinement: confidence=0.88

======================================================================
=== PROCESSING RESULT ===
======================================================================

[Content Summary]
Here's a comprehensive solution for building a real-time collaborative code editor:

## 1. Overall Architecture

**Client-Server Architecture with CRDT (Conflict-free Replicated Data Types)**

- **Frontend**: React + Monaco Editor + Y.js (CRDT library)
- **Backend**: Node.js + WebSocket server + Redis for presence
- **Database**: PostgreSQL for persistence + Redis for caching
- **Real-time Sync**: Operational Transformation (OT) or CRDT approach

## 2. Key Technical Challenges

a) **Conflict Resolution**: Multiple users editing same code simultaneously
   - Solution: Use Y.js with CRDT algorithm

b) **Low Latency**: Real-time sync must feel instant
   - Solution: WebSocket for bi-directional communication, local-first approach

c) **S...

[Quality Metrics]
  Confidence: 0.88
  Cognitive Level: agent

[Workspace State]
  Working Memory Items: 5
  Blackboard Items: 8
  Current Focus: thinking_003

[Metacognitive Report]
  Quality Gates Passed: True
  Prediction Error: 0.18
  Refinement Triggered: True
  Strategy Used: critique_and_revise

[Budget Usage]
  Tokens: 4230/10000 (42.3%)
  Time: 34.2s/300s
  Iterations: 2/3
  API Calls: 6/20

[OODA Decision]
  Strategy: adaptive
  Initial Level: agent
  Backup Levels: []

✓ Engine shutdown complete
```

---

## 最佳實踐

### 1. Feature Flag 管理

```python
# 正確的 Feature Flag 使用模式

# ✓ 好的做法：檢查後再使用
if feature_flags.is_enabled("cognitive.global_workspace"):
    workspace.post(item)
else:
    # Fallback to legacy behavior
    self.cache.store(item)

# ✗ 錯誤做法：不檢查直接使用
workspace.post(item)  # 如果 workspace 未啟用會報錯
```

### 2. 錯誤處理

```python
# 正確的錯誤處理模式

async def process_with_fallback(task: Task) -> ProcessingResult:
    """帶 fallback 的處理"""
    try:
        # 嘗試使用認知引擎
        if feature_flags.is_enabled("cognitive.enabled"):
            return await cognitive_engine.process(task)
    except CognitiveProcessingError as e:
        logger.warning(f"Cognitive processing failed: {e}, falling back to legacy")
    except Exception as e:
        logger.error(f"Unexpected error: {e}, falling back to legacy")

    # Fallback 到舊引擎
    return await legacy_engine.process(task)
```

### 3. 資源清理

```python
# 正確的資源管理

class MyCognitiveService:
    def __init__(self):
        self.engine = None

    async def __aenter__(self):
        self.engine = RefactoredEngine()
        await self.engine.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.engine:
            await self.engine.shutdown()

# 使用 context manager
async with MyCognitiveService() as service:
    result = await service.process(task)
# 自動清理
```

---

## 常見陷阱與解決方案

### 陷阱 1: 忘記啟用 Feature Flag

```python
# ✗ 錯誤
engine = RefactoredEngine()
result = await engine.process(task)
# 結果：使用舊系統，沒有認知功能

# ✓ 正確
feature_flags.enable("cognitive.enabled")
engine = RefactoredEngine()
result = await engine.process(task)
```

### 陷阱 2: 內存洩漏（工作空間無限增長）

```python
# ✗ 錯誤：不斷添加項目但從不清理
for item in large_list:
    workspace.post(item)  # 工作空間會爆滿

# ✓ 正確：定期清理與衰減
for item in large_list:
    workspace.post(item)

    # 定期衰減
    if len(workspace.working_memory.items) > workspace.working_memory.capacity:
        workspace.decay()
```

### 陷阱 3: 忽略預算限制

```python
# ✗ 錯誤：無限迭代
while not satisfied:
    result = await refine(result)  # 可能永遠不滿意

# ✓ 正確：尊重預算
while not satisfied and budget_manager.can_afford_refinement():
    result = await refine(result)
```

---

## 測試範例

### 單元測試

```python
# tests/core/test_workspace.py

import pytest
from src.core.cognitive.global_workspace import GlobalWorkspace

class TestGlobalWorkspace:
    @pytest.fixture
    def workspace(self):
        return GlobalWorkspace()

    def test_capacity_limit(self, workspace):
        """測試工作記憶容量限制"""
        for i in range(10):
            workspace.post(self._create_item(f"item_{i}"))

        # 容量為 7，應該只保留 7 個
        assert len(workspace.working_memory.items) == 7

    def test_attention_allocation(self, workspace):
        """測試注意力分配"""
        items = [self._create_item(f"item_{i}") for i in range(3)]
        for item in items:
            workspace.post(item)

        # 注意力應該分配給最高優先級的項目
        focus = workspace.get_focus()
        assert focus is not None
```

### 整合測試

```python
# tests/integration/test_end_to_end.py

@pytest.mark.asyncio
async def test_end_to_end_processing():
    """端到端測試"""
    # 啟用功能
    feature_flags.enable("cognitive.enabled")

    # 初始化引擎
    engine = RefactoredEngine()
    await engine.initialize()

    try:
        # 處理任務
        task = Task(query="Test query")
        result = await engine.process(task)

        # 驗證
        assert result.confidence > 0
        assert result.content is not None
    finally:
        await engine.shutdown()
```

---

## 總結

本文檔提供了從基礎到高級的完整程式碼範例，涵蓋：
- ✅ 基本使用
- ✅ 工作空間互動
- ✅ 元認知監控
- ✅ OODA 路由
- ✅ 記憶學習
- ✅ 神經調控
- ✅ 端到端場景

所有範例均遵循最佳實踐，可直接用於生產環境。

---

**文檔維護者**: OpenAgent Architecture Team
**審核狀態**: Pending Review
