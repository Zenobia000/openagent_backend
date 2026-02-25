# 深度研究報告品質審計與 Prompt 缺口分析

**審計對象**: `logs/reports/e363dd46_20260223_155301/report.md`
**對標基準**: McKinsey, BCG, Bain, Deloitte, RAND Corporation, Gartner
**範圍**: 報告品質診斷 + `prompts.py` 與 `_build_academic_report_prompt()` 缺口分析
**日期**: 2026-02-23

---

> **⚠️ v3.3 更新 (2026-02-25)**: 本文件中建議的多項修改已在 v3.3 Pipeline Reengineering 中做出**反向決策**。
>
> 本文建議加入更多制式規則（競爭分析章節、Bull/Base/Bear 情境分析、推論句式多樣性控制、表格完整性禁令等）。
> 經實際測試，**過多的制式規則正是機械化輸出的根源**（如 "這意味著" 52 次重複即源自 So-What 範例句式模板）。
>
> v3.3 採取相反策略：**從 23 條規則簡化為 10 條靈活指引，信任 LLM 推理能力**。
>
> 本文仍保留作為歷史參考和品質審計記錄，但以下建議狀態已更新：
> - ~~P0-3: 表格計算完整性禁令~~ → 移除（讓 LLM 自行判斷）
> - ~~P0-3: 推論句式多樣性要求~~ → 移除（移除 So-What 範例即可）
> - ~~P0-3: 競爭格局分析必備~~ → 移除（不是每個主題都需要）
> - ~~P1-8: Bull/Base/Bear 情境分析~~ → 移除（不是每個主題都適用）
> - ~~P2-10: 圖表位置校驗器~~ → 移除（整個 chart pipeline 已移除）
> - P0-1: 搜尋 query 品質導向 → **保留待實作**（上游品質仍是真問題）
> - P0-2: 來源可信度標注 → **保留待實作**
> - P1-5: synthesis 追蹤 evidence_quality → **保留待實作**
> - P1-9: 方法論章節 → **已實作**（v3.3 報告 prompt rule #9）

---

## 一、總體判斷

這份報告穿上了諮詢報告的外衣，骨架像、標籤對、節次分明，但掀開衣服看肌肉 — 證據薄弱、分析公式化、關鍵表格沒算完。用一句話概括：**形似而神不似**。

綜合評分 4.7/10，高於多數 AI 生成報告，但離 McKinsey 標準（9.0）還差得遠。

| 維度 | 分數 | 說明 |
|------|:---:|------|
| 結構與組織 | 7.5 | MECE 標注齊全、Pyramid 原則有執行、18 節覆蓋完整 |
| 證據品質 | 3.5 | 全部引用偏弱，blog 與新聞聚合站佔絕大多數 |
| 分析嚴謹度 | 5.0 | CEI 模式跑了但像填表，So-What 變成複製貼上 |
| 量化水準 | 4.5 | 有數字但缺交叉驗證，Table 1 加權得分居然寫 "=?" |
| 可操作性 | 6.5 | 分了董事會/CTO/PM 三層，可惜缺具體交付物 |
| 視覺分析 | 5.0 | 2 張圖放錯位置，編號還倒過來 |
| 來源可信度 | 3.0 | 24 篇引用零一級來源 |
| 競爭分析 | 1.0 | 完全空白，報告裡沒出現過任何一個競爭者名字 |
| 情境分析 | 2.0 | 無 Bull/Base/Bear，風險矩陣有但缺量化情境 |

---

## 二、做得好的地方

不能全盤否定。結構層面確實比絕大多數 AI 報告強：

MECE 執行到位 — 18 大節從市場到概念到技術到商業到實施路線圖，每層不重疊、每段有明確職責分工。Executive Summary 放在最前方，4 條核心結論先行、證據隨後展開，符合 Pyramid Principle。

CEI（Claim-Evidence-Implication）三段式貫穿全文，引用 `[1][5][9]` 穿插段中而非堆在段尾。4 張分析表格的類型選擇正確 — 比較得分矩陣、交叉表、成本分解瀑布、風險象限 — 每張附有 So-What 解讀段落。Section 18 的行動建議按角色分層，附帶量化 KPI 門檻（OTA 成功率 ≥98%、回滾時間 ≤1hr、LTV/CAC ≥3）。

這些「骨架」層面的表現說明 `_build_academic_report_prompt()` 中已有的 16 條指令確實發揮了作用。問題出在骨架之外的地方。

---

## 三、致命缺陷

### 3.1 證據全線潰敗 — 在沙上蓋大樓

這是整份報告最根本的問題，其他缺陷都是它的下游症狀。

頂級諮詢報告的來源結構長這樣：最核心的數字來自政府統計、央行數據、上市公司財報（Tier 1）；次核心的分析來自 Gartner、IDC、McKinsey 自有研究（Tier 2）；背景敘事來自 FT、WSJ、Economist 等品質媒體（Tier 3）；Blog 和社群媒體只在沒有替代來源時才用（Tier 4-5），而且會明確標註。

本報告 24 篇引用的實際分布：Tier 1 零篇，Tier 2 零篇。Intel 和 Arm 的白皮書看似權威，實則是廠商行銷材料，不算獨立研究。引用量最高的 [9]（雲界數位白皮書，被引 29 次）是一家邊緣運算廠商的產品推廣文章。引用 [4] 直接來自思科台灣的 Facebook 貼文。[24] 是 Yahoo 奇摩新聞。[23] 和 [27] 是 Sl886 博客上關於優藍國際的企業公關稿。

報告中最核心的定量主張 — TAM 約 $1,200B、CAGR 8-12%、SaaP 可服務市場 $120-240B — 全部源自這些企業公關文章，沒有任何一個數字能追溯到獨立市場研究機構。McKinsey 的基本規矩是每個核心數字至少要兩個獨立來源交叉印證。這份報告一個都沒做到。

追根溯源，問題出在 `get_serp_queries_prompt()` — 它只要求「SHORT keyword phrase (3-8 words) optimized for search engines」，從不指導模型去搜尋高品質來源。下游的 `get_search_result_prompt()` 要求提取 learnings，但不要求評估來源可信度。模型自然把 Gartner 報告和 Facebook 貼文一視同仁。

### 3.2 Table 1 沒算完 — 公信力瞬間崩塌

Table 1（三種路徑的比較得分矩陣）最後一欄赫然寫著：

```
| 加權得分 |
| (5*0.2 + 3*0.2 + 5*0.2)=? |
```

公式寫出來了但沒有計算結果。讀者翻到這裡，前面讀的所有分析都會打折扣 — 連基本的乘加都沒做完，其他複雜推論還能信嗎？

更深一層，公式本身的邏輯也是錯的。它把三個不同路徑的分數混在同一行做加法，應該是每列（每條路徑）各行分數乘以對應權重後加總，得出三條路徑各自的總加權得分。表格設計與計算雙雙失敗。

`_build_academic_report_prompt()` 的 16 條指令裡沒有一條說「表格中所有數學計算必須完成，禁止留空、禁止寫 '=?' 或 'TBD'」。這條規則太基本了，以至於沒人想到要寫。但 LLM 不是人，你不講它就不做。

### 3.3 「這意味著」52 次 — So-What 退化成噪音

搜了一下全文，「這意味著」出現 52 次，平均每節 2.9 次。幾乎每段末尾都是同一個開頭：

> ...這意味著企業若不轉型，將面臨效率與競爭力下降的較高風險。
> ...這意味著投資重點須向邊緣工程與運維能力傾斜...
> ...這意味著財務團隊與法律團隊必須從早期試點階段即介入...

一開始讀者會覺得「分析有推論、不錯」，讀到第十次就麻木了，讀到第五十次已經像機器在跑迴圈。McKinsey 或 BCG 的報告會依語境變換措辭：「戰略含義在於...」、「對 CIO 而言，這重新定義了投資優先序」、「此發現挑戰了傳統假設」、「淨效應是單位利潤壓縮 15-20%」、「董事會應將此視為一個訊號」。

根因在 prompt：指令原文是 "So-What: 'This means...' or 'The implication is...'"，直接給了固定句式模板。LLM 收到範例就會重複使用，這是語言模型的天性。

### 3.4 競爭格局完全空白

18 個 section 裡找不到任何一節分析現有玩家。優藍國際被引為資料來源，但從未被當作競爭者分析。直聘、58 同城、Recruit、Randstad、Manpower — 報告一個名字都沒提。護城河在哪？進入壁壘是什麼？價值鏈哪些環節已被佔據？全部空白。

任何市場分析報告，不論 McKinsey 還是 Bain，都會把競爭格局放在核心位置。缺了這一塊，報告的策略建議就像在真空裡做決定 — 不知道對手在做什麼，怎麼決定自己該做什麼？

`_build_academic_report_prompt()` 的 16 條要求沒有一條提到競爭分析或任何策略框架（Porter's Five Forces, Value Chain, SWOT）。

### 3.5 數字有但經不起追問

| 核心主張 | 來源 | 交叉驗證 |
|----------|------|:--------:|
| TAM ~$1,200B | [23] 優藍國際 blog | 無 |
| CAGR 8-12% | [23][29] 同一家公司兩篇文 | 自引自 |
| SaaP-TP $120-240B | [23][29][22] | 按比例假設，無獨立來源 |
| MVP 預算 $0.5-1M | [27][23] | blog 估算 |
| 試點成本 $1.85M/場 | Computed Analysis | 模型輸入未經驗證 |

每個核心數字都只有一個來源，而且那個來源本身就不夠硬。McKinsey 做市場規模估算時，bottom-up（從客戶數 × 客單價推）和 top-down（從產業總值 × 滲透率推）兩條路必須交叉、差距要能解釋。這份報告連一條路都沒走完整。

prompt 雖然寫了 "Every market claim must include specific numbers"，但「有數字」和「數字可信」是兩件事。缺的是三角驗證指令和假設聲明要求。

### 3.6 圖表放錯地方

兩張 Figure 都堆在 Section 12 的段落後方。Figure 2 出現在 Figure 1 前面 — 編號順序都反了。Prompt 明確寫了 "Reference figures INLINE within the relevant analysis section"，但模型沒遵守。這類指令 LLM 經常選擇性忽略，光靠 prompt 文字不夠，後處理需要加一道校驗。

### 3.7 缺情境分析與方法論說明

報告給了風險矩陣和觸發門檻，但沒有 Bull/Base/Bear 情境預測。決策者不知道最好情況和最壞情況的量化範圍，也無法評估投資的上行與下行空間。BCG/Bain 任何涉及投資建議的報告都會附情境分析。

同時，報告沒有方法論章節 — 搜了什麼、篩了什麼、排除了什麼、數據有什麼局限。RAND Corporation 的每份研究報告都有方法論段落，讓讀者自行判斷結論的可靠程度。本報告幾乎全是中文來源，英文一級研究完全缺席，但這個偏差從未被揭露。

---

## 四、對標六大組織

把上述發現放到各組織的核心紀律框架下看，差距的脈絡更清晰：

McKinsey 的鐵律是 "Source or it didn't happen" — 每個數字必須追到原始出處。這份報告的數字追到頭都是 blog。BCG 的招牌是 scenario-based decision framework，讓決策者看見上行/下行空間。報告完全沒做。Bain 把 competitive benchmarking 視為標準配備，不分析競爭者的策略報告在 Bain 過不了內審。Deloitte 強調 methodology transparency，讀者有權知道研究是怎麼做的。RAND Corporation 要求 explicit uncertainty quantification，不確定的地方要明說而非用自信語氣掩蓋。Gartner 區分 fact、opinion 與 hype，三者不能混為一談。

報告在結構紀律上和這些組織接軌了（MECE、Pyramid、CEI、角色化建議），但在證據紀律、競爭紀律和不確定性紀律上全線失守。

| 組織 | 核心紀律 | 本報告缺口 |
|------|----------|-----------|
| McKinsey | 每個數字追到原始來源 | 核心數字全靠 blog |
| BCG | 情境化決策框架 | 無 Bull/Base/Bear |
| Bain | 競爭對標是標準動作 | 零競爭分析 |
| Deloitte | 方法論透明 | 無方法論說明 |
| RAND | 明確量化不確定性 | 語氣過度自信 |
| Gartner | 區分事實、觀點與炒作 | 不區分來源層級 |

---

## 五、Prompt 系統缺口分析

問題不只在最後一步的報告生成 prompt。沿著 pipeline 從上游往下追，每個環節都有盲區。

### 5.1 架構層問題：兩套報告 prompt 並存

`prompts.py` 裡的 `get_final_report_prompt()`（L380）和 `processor.py` 裡的 `_build_academic_report_prompt()`（L1489）是兩套完全獨立的報告生成指令。前者品質低得多 — "aim for 5 pages or more, the more the better, include ALL the learnings"，鼓勵資料傾倒、無結構約束。後者有 16 條 McKinsey 級指令。

如果任何路徑意外呼叫了 `prompts.py` 版本，報告品質會瞬間倒退。兩套並存本身就是架構債。

### 5.2 上游：搜尋查詢不導向高品質來源

`get_serp_queries_prompt()`（L224-240）只管搜尋引擎命中率 — "SHORT keyword phrase optimized for search engines"。它不會指導模型加入 "Gartner report"、"IDC forecast"、"academic paper"、"government statistics" 這類定向關鍵字。結果就是搜尋結果被 blog 和新聞聚合站淹沒。

同樣地，所有 query 都是中文，沒有一條英文 query 去取全球性的一級研究。這直接決定了來源品質的天花板。

### 5.3 中游：學習提取不評估可信度

`get_search_result_prompt()` 和 `get_query_result_prompt()`（L243-297）要求模型提取 learnings，但從不要求判斷來源層級。Gartner 季度報告裡的產業規模估算和 Facebook 貼文裡的隨口一提，在 pipeline 裡權重完全相同。

`get_intermediate_synthesis_prompt()`（L651-698）輸出 synthesis、section_coverage、knowledge_gaps、cross_domain_links — 唯獨不追蹤各 section 的證據品質分布。Pipeline 永遠不知道「這個 section 覆蓋了，但全靠弱來源撐著」。

### 5.4 品質關卡形同虛設

`get_completeness_review_prompt()`（L701-738）判斷 `is_sufficient` 的唯一標準是覆蓋率 — overall_coverage ≥ 70、no section below 40。一個 section 可以 coverage 100% 但來源全是 blog，依然通過關卡。

`get_review_prompt()`（L327-356）的 follow-up 邏輯只看「知識缺口」不看「證據品質缺口」。即使所有 section 都覆蓋了，核心數字只靠一篇 blog 支撐，pipeline 也不會自動發起更高品質的搜尋。

### 5.5 深度研究 mode extension 過於抽象

`_MODE_EXTENSIONS["deep_research"]`（prompts.py L54-58）只有 4 條高階指令，其中 "Maintain a clear evidence hierarchy: primary sources over secondary" 方向正確但缺定義 — 什麼算 primary？什麼算 secondary？不具體就等於沒說。

### 5.6 報告生成 prompt 的遺漏清單

`_build_academic_report_prompt()` 已有的 16 條指令解決了結構問題，但以下項目完全缺失：

**表格計算完整性** — 沒有說「表格每一格都必須填入計算結果，禁止 '=?' 或 'TBD'」。結果 Table 1 直接留空。

**推論句式多樣性** — 給了 "這意味著" 當範例，模型就重複 52 次。需要明確禁止同一句式超過 5 次，並要求依語境變換表達。

**競爭格局** — 16 條指令沒有一條要求分析競爭者、應用策略框架。

**來源品質意識** — 沒有要求優先引用一級來源、標注弱來源、或對單一來源的核心主張提出警告。

**情境分析** — 涉及投資建議時，缺 Bull/Base/Bear 情境的量化範圍要求。

**方法論透明** — 不要求說明研究範圍、來源篩選標準和分析局限。

**圖表順序規則** — 雖然有 inline 嵌入指令，但缺少「Figure 編號必須遞增、必須出現在首次引用之前或同段」的硬性約束。

---

## 六、缺陷溯源對照

每個報告問題都能追溯到 prompt 系統中的具體位置：

| 報告缺陷 | 嚴重度 | Prompt 根因 | 修改位置 |
|----------|:------:|------------|---------|
| 零一級來源 | 致命 | 搜尋 query 不導向高品質來源 | prompts.py `get_serp_queries_prompt()` |
| 來源可信度未評估 | 致命 | learning 提取不含可信度判斷 | prompts.py `get_search_result_prompt()` |
| Table 1 "=?" | 致命 | 無表格計算完整性指令 | processor.py `_build_academic_report_prompt()` |
| 52 次同句式 | 中等 | 範例句式被當模板複製 | processor.py `_build_academic_report_prompt()` |
| 無競爭分析 | 嚴重 | 16 條指令不含競爭格局要求 | processor.py `_build_academic_report_prompt()` |
| 無情境分析 | 嚴重 | 不含 Bull/Base/Bear 要求 | processor.py `_build_academic_report_prompt()` |
| 無策略框架 | 嚴重 | 不含 Porter's/SWOT 等框架要求 | processor.py `_build_academic_report_prompt()` |
| 圖表位置錯 | 中等 | 指令存在但未強制執行，缺後處理校驗 | processor.py post-process |
| 無方法論章節 | 中等 | 不含方法論透明度要求 | processor.py `_build_academic_report_prompt()` |
| 綜合不追蹤證據品質 | 高 | synthesis prompt 不含品質欄位 | prompts.py `get_intermediate_synthesis_prompt()` |
| 完整性關卡忽略來源品質 | 高 | 只看覆蓋率不看來源層級 | prompts.py `get_completeness_review_prompt()` |
| Follow-up 不追求更好來源 | 高 | 只填知識缺口不填品質缺口 | prompts.py `get_review_prompt()` |
| 兩套報告 prompt 並存 | 架構 | 品質標準分裂 | prompts.py + processor.py |

---

## 七、修改優先序

### P0 — 純 Prompt 文字修改，零風險，立即生效

1. `get_serp_queries_prompt()` 加入來源品質導向 — 至少 30% query 含 "Gartner"、"IDC"、"academic paper" 等定向詞，至少 2 條英文 query
2. `get_search_result_prompt()` 和 `get_query_result_prompt()` 加入來源可信度標注（PRIMARY / SECONDARY / WEAK）
3. `_build_academic_report_prompt()` 追加：表格計算完整性禁令、推論句式多樣性要求（同句式上限 5 次）、競爭格局分析必備章節
4. `_MODE_EXTENSIONS["deep_research"]` 擴充為具體的證據層級定義

### P1 — Prompt 調整 + 輕量邏輯變動

5. `get_intermediate_synthesis_prompt()` JSON schema 加入 evidence_quality 欄位
6. `get_completeness_review_prompt()` 增加來源品質作為 sufficiency 判斷條件
7. `get_review_prompt()` follow-up 邏輯兼顧品質缺口
8. `_build_academic_report_prompt()` 追加：情境分析要求（Bull/Base/Bear）、策略框架應用要求

### P2 — 架構調整與後處理

9. 統一 `get_final_report_prompt()` 和 `_build_academic_report_prompt()` 為單一來源
10. 增加圖表位置與編號的後處理校驗器
11. 追加方法論章節要求

---

## 八、預期品質演進

| 指標 | 現狀 | P0 完成後 | P0+P1 完成後 | McKinsey 標準 |
|------|:----:|:---------:|:------------:|:------------:|
| 一/二級來源佔比 | 0% | 15-20% | 25-35% | 70%+ |
| 數據交叉驗證 | 無 | 有標注但未系統化 | 系統性執行 | 標準動作 |
| 表格完整性 | 有 "=?" | 全部計算完成 | 全部計算完成 | 基本要求 |
| 推論表述多樣性 | 52 次同句式 | 上限 5 次 | 依語境自然變化 | 自然流暢 |
| 競爭分析 | 空白 | 有基本章節 | 有框架支撐 | 標準配備 |
| 情境分析 | 空白 | 仍空白 | Bull/Base/Bear | 標準配備 |
| 綜合分數 | 4.7 | 6.0 | 7.5 | 9.0 |

天花板大約在 7.5-8.0。原因不在 prompt 而在搜尋引擎本身 — web search 很難穩定取得 Gartner/IDC 付費報告的完整內容。要突破 8.0 需要接入專業資料庫 API（Statista, PitchBook, JSTOR）。這是 pipeline 能力的結構性邊界，不是 prompt 能解的。

---

## 九、一句話收尾

報告的骨架到位了，問題出在血肉。Prompt 系統最大的盲區不在最後的報告生成環節，而在整條 pipeline 從頭到尾都沒有問過一個根本問題：**這個來源可信嗎？**

搜尋不導向好來源、提取不評估可信度、綜合不追蹤品質分布、關卡不攔弱來源、follow-up 不補強證據 — 五道工序全部放行了低品質來源，最後一步的報告 prompt 就算寫得再精緻，也只能在沙上蓋大樓。

修的順序很清楚：先堵上游（搜尋品質導向），再補中游（來源可信度標注與品質追蹤），最後細修下游（表格完整性、句式多樣性、競爭分析、情境分析）。P0 全是純文字修改，零風險、零架構變動、下一次跑報告就能看到效果。

---

*Cross-referencing: McKinsey, BCG, Bain, Deloitte, RAND Corporation, Gartner published quality standards*
*Scope: Report content audit + prompts.py + _build_academic_report_prompt() gap analysis*
