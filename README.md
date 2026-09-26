# 靛蓝纪要 · 手工扎染工坊产品开发会议系统

手工扎染工坊的产品开发会议需要被完整记录：手工艺人围坐染缸边讨论图案、配色、扎结手法与成本，
这些讨论必须沉淀成可执行的开发纪要，并同步给买手店。

本系统是一个前后端分离的全栈应用：

- **后端**（`backend/`，Flask）：接收会议录音，降噪后转写、区分说话人、提取工艺要素，
  生成系列主题与成本核算摘要，并把纪要邮件发给买手店。
- **前端**（`frontend/`，React + Ant Design）：会议处理中心、图案设计库、植物染料色谱、历史记录。

## 目录结构

```
.
├── backend/
│   ├── app.py              # Flask 应用与全部 HTTP 路由
│   ├── audio_processor.py  # librosa 降噪（染缸搅动声抑制）
│   ├── transcriber.py      # Whisper 转写 + pyannote 说话人区分 + 工艺要素提取
│   ├── summarizer.py       # OpenAI 摘要生成 + 成本核算
│   ├── email_sender.py     # 纪要邮件（HTML 正文 + 成本 CSV + 转写 TXT 附件）
│   ├── data_store.py       # JSON 文件存储（会议 / 图案库 / 染料库）
│   └── tests/              # pytest 测试
├── frontend/
│   └── src/
│       ├── App.js
│       ├── components/     # MeetingProcessor / PatternLibrary / DyeLibrary /
│       │                   # MeetingHistory / MeetingDetail
│       └── services/api.js
├── requirements.txt        # 后端依赖（轻量，可离线跑测试）
├── requirements-ml.txt     # Whisper / pyannote / librosa 等重型可选依赖
├── CLAUDE.md               # 本仓库的工程规则，动手前先读
└── README.md
```

## 运行方式

后端（Python 3.11+）：

```bash
pip install -r requirements.txt
cd backend && python app.py          # http://localhost:5000
```

前端（Node 18+）：

```bash
cd frontend && npm install && npm start   # http://localhost:3000，proxy 指向 5000
```

测试：

```bash
cd backend && python -m pytest -q
```

`requirements.txt` 只包含轻量依赖。Whisper / pyannote / librosa（见 `requirements-ml.txt`）与
`OPENAI_API_KEY` 都是**可选的**：未安装模型、未配置 Key 时，转写与摘要会走确定性的离线分支，
因此后端与测试可在无网络、无 GPU、不调用任何外部 API 的环境下跑通。

## HTTP 接口一览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/process-meeting` | 上传录音 + 设计数据，完整处理一条会议并落库 |
| GET | `/api/meetings` | 会议列表 |
| GET | `/api/meetings/<meeting_id>` | 会议详情 |
| POST | `/api/send-email/<meeting_id>` | 把纪要邮件发给指定收件人 |
| GET | `/api/patterns` | 图案设计库 |
| GET | `/api/dyes` | 植物染料色谱 |
| POST | `/api/cost-calculator` | 成本核算 |

`POST /api/process-meeting` 为 `multipart/form-data`：`audio` 是音频文件，`designData` 是 JSON 字符串
（含 `series_name` / `fabric_type` / `complexity` / `quantity` / `notes`）。

## 行为规格（验收标准）

本节是本次修复的验收依据，逐条以本节为准。

### A. 请求校验与错误响应

1. 所有接收 JSON 的接口在 body 缺失、不是合法 JSON、或字段类型/取值非法时，必须返回 `400`
   并带 JSON 错误信息；**不得**抛出 `KeyError` / `TypeError` / `ZeroDivisionError` 变成 `500`，
   也不得落到框架默认的 `415`。
2. `POST /api/process-meeting` 的 `designData` 如果不是合法 JSON 对象，必须返回 `400`
   （允许缺省，缺省按空对象处理）；缺少 `audio` 文件返回 `400`。
3. `POST /api/cost-calculator` 的校验规则：
   - `quantity`：必须是**正整数**（`>= 1`）。为 `0`、负数、非数值、布尔值时一律 `400`。
   - `fabric_type`：必须是 `cotton` / `linen` / `silk` / `wool` 之一，否则 `400`。
   - `complexity`：必须是 `simple` / `medium` / `complex` 之一，否则 `400`。
   - 缺省字段按规格默认值处理（`quantity=1`、`cotton`、`medium`）。
4. 资源不存在（如未知 `meeting_id`）必须返回 `404` + JSON 错误体。

### B. 成本核算口径

5. 单件成本构成必须与下列口径一致，且分项之和等于总成本：

   | 项目 | 计算式 |
   | --- | --- |
   | 面料成本 | `base_fabric(fabric_type) × quantity` |
   | 染料成本 | `15 × quantity × multiplier(complexity)` |
   | 人工成本 | `80 × quantity × multiplier(complexity)` |
   | 水电能耗 | `12 × quantity` |
   | 其他费用 | `8 × quantity` |
   | 总成本 | 上述五项之和 |
   | 建议零售价 | `总成本 × 2.8` |

   其中 `base_fabric`：`cotton=35, linen=55, silk=120, wool=80`；
   `multiplier`：`simple=1.0, medium=1.5, complex=2.2`。

6. 响应中每个分项的 `*_percentage` 必须是该分项占总成本的百分比（保留一位小数、带 `%`），
   分项占比之和应在合理舍入误差内接近 100%。`total_cost` 与 `suggested_retail` 保留两位小数。

### C. 外部服务失败不得伪装成功

7. `summarizer.generate_summary` 在**未配置 `OPENAI_API_KEY`**（服务不可用）时，允许返回确定性的
   离线摘要，但该结果必须可识别（带 mock 标记），不得伪装成真实模型产出。
8. 一旦**真的发起**了 OpenAI 调用但失败（网络错误、`429`、鉴权失败等），必须把异常向上抛出，
   由 `POST /api/process-meeting` 返回错误响应；**不得**改用模板摘要返回成功，也不得把模板内容
   作为正式纪要写入存储。
9. 同理，`transcriber.transcribe_meeting` 在模型已加载但推理失败时必须上抛；模型未安装/未加载
   属于服务不可用，走离线分支。

### D. 工艺要素提取

10. `transcriber.extract_patterns` 提取的 `tie_methods` 与 `color_mentions` 必须是**可复现的稳定顺序**
    （按在文本中首次出现的先后），同一条录音重复处理必须得到完全一致的顺序与内容；
    不得使用 `list(set(...))` 这类依赖哈希随机化的写法。
11. `dye_count_mentions` 统计"染色 N 次"这类表述的次数，`technique_count` 的口径为
    `len(tie_methods) + dye_count_mentions`，且与规格一致。

### E. 会议处理与资源清理

12. `POST /api/process-meeting` 处理结束后，**不得**在临时目录残留中间产物
    （如降噪生成的 `*_denoised*` 文件）。无论成功或失败，都必须清理本次处理产生的临时文件。
13. 一个会议下有多条录音时，合并与摘要的行为须符合规格（不得只取第一条、也不得重复拼接）。
14. 处理成功后，`GET /api/meetings` 与 `GET /api/meetings/<id>` 必须能查到该会议，
    且 `summary.series_theme`、`summary.cost_breakdown.total_cost`、`patterns.tie_methods`
    等前端渲染字段必须存在且非空。

### F. 邮件

15. `POST /api/send-email/<id>` 只有在**确实投递成功**时才返回成功；未配置邮件服务或投递失败时，
    必须返回错误状态码（`4xx`/`5xx`）+ JSON 错误信息，**不得**返回 `200` 配 `{"success": false}` 冒充成功。
16. 收件人为空时按规格处理（回退到配置的默认收件人；仍为空则报错）。

### G. 前端与后端契约

17. 前端各组件调用的接口路径与字段名必须与后端实际返回一致；页面不得因为引用未定义的标识符
    或读取不存在的字段而抛错（例如未引入 `message` 却调用 `message.success`）。
18. 不得通过删除功能来"修好"契约（不允许删掉按钮、删掉字段读取来回避问题）。

### H. 不得回归的既有正确行为

19. `GET /api/meetings`、`GET /api/meetings/<id>`、`GET /api/patterns`、`GET /api/dyes` 的正常查询，
    以及 `POST /api/cost-calculator` 的合法输入、`POST /api/process-meeting` 的顺利路径必须保持可用。
20. `data_store` 的 JSON 存储语义不变：会议按最新在前插入，图案库 / 染料库缺文件时按默认数据初始化。

## 变更说明

本次修复以「行为规格」为验收标准，逐条修正了以下缺陷（根因 → 修法）：

1. **请求校验缺失导致 500/415**
   - 根因：`process-meeting` 直接 `json.loads(designData)`，非法 JSON 抛 `JSONDecodeError` 变 500；
     `send-email` / `cost-calculator` 直接用 `request.json`，非法 body 落到框架默认 415 或 `AttributeError` 变 500。
   - 修法：新增 `_parse_json_body()` 统一解析（无 body 按 `{}`、非法 JSON/非对象返回 400）；
     `designData` 解析失败或不是 JSON 对象时返回 400；缺少 `audio` 文件返回 400；未知资源统一 404 + JSON 错误体。

2. **成本核算输入无边界**
   - 根因：`calculate_cost` 未校验入参，`quantity=0` 触发除零、负数算出负成本、非数值抛 `TypeError`，
     非法 `fabric_type` / `complexity` 被静默套用默认值。
   - 修法：新增 `validate_cost_params`（`quantity` 必须为正整数且排除布尔值，`fabric_type` / `complexity`
     必须落在支持取值内），非法输入抛 `ValueError` 并由路由转为 400；缺省字段按规格默认值
     （`quantity=1`、`cotton`、`medium`）处理；`process-meeting` 的 `designData` 复用同一校验。

3. **外部服务失败被伪装成成功**
   - 根因：`generate_summary` 用 `try/except` 吞掉真实 OpenAI 调用的失败并回落模板摘要，
     429/网络错误时接口照样 200，模板文本被当作正式纪要落库。
   - 修法：移除吞异常的回落逻辑，真实调用失败直接上抛，由 `process-meeting` 返回错误响应且不落库；
     未配置 `OPENAI_API_KEY` 的离线摘要保留，但返回结果带 `is_mock: true` 标记。
     `transcriber` 保持「模型未安装走离线分支、已加载但推理失败上抛」的语义不变。

4. **工艺提取结果不可复现**
   - 根因：`extract_patterns` 用 `list(set(...))` 去重，顺序依赖哈希随机化；
     `technique_count` 用的是去重前的列表长度；`dye_count_mentions` 的正则把「染色次数」这类名词也计入。
   - 修法：改用 `dict.fromkeys` 按首次出现顺序去重；`technique_count = len(tie_methods) + dye_count_mentions`
     （均为去重后口径）；「染色 N 次」必须带数字才计数。离线说话人划分中 `hash(str(...))` 同样依赖
     哈希随机化，已改为确定性计算。

5. **临时文件残留**
   - 根因：`process-meeting` 的 `finally` 只删除上传的原始临时文件，降噪生成的 `*_denoised*` 分片被遗漏。
   - 修法：统一登记本次处理产生的全部临时路径（原始 + 降噪），`finally` 中无论成功失败都清理。

6. **会议历史页「发送邮件」报错**
   - 根因：`MeetingHistory.js` 调用了 `message.success/error` 却未从 `antd` 引入 `message`，点击即 `ReferenceError`。
   - 修法：补上 `message` 引入；其余组件的接口路径与字段名已逐一核对，与后端返回一致。

7. **邮件未投递却返回成功**
   - 根因：`send_meeting_summary` 在未配置或投递失败时返回 `False`，路由照样 200 返回 `{"success": false}`。
   - 修法：未配置邮件服务 / 投递失败时抛 `RuntimeError`（路由转 502），收件人为空且无默认收件人时抛
     `ValueError`（路由转 400），只有确实投递成功才返回 200 + `{"success": true}`。

8. **多条录音只处理第一条**
   - 根因：`process-meeting` 只取 `request.files['audio']` 的第一个文件。
   - 修法：改用 `getlist('audio')` 逐条降噪、转写、说话人区分后合并（文本按序拼接、片段依次衔接），
     再统一提取工艺要素与生成摘要。

同时新增 `backend/tests/test_spec.py`，按 A–F 各节验收点补齐测试；未修复的实现上 26 个用例失败，修复后全部通过。

## 技术栈

- 后端：Flask 3、Flask-CORS；Whisper / pyannote / librosa / OpenAI 均为可选
- 前端：React 18、Ant Design 5、axios、react-router-dom 6
- 测试：pytest（`backend/tests`）

## 许可证

MIT License
