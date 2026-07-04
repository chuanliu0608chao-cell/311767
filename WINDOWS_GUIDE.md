# AI学习教练系统 - Windows 端对接指南

## 架构说明

```
┌─────────────┐         HTTP API          ┌─────────────┐
│  Windows 端  │ ◄────────────────────►  │  Ubuntu 端    │
│  硬件交互    │    localhost:5000        │  AI 大脑      │
│  高拍仪/录音 │                          │  数据库/API   │
│  打印/TTS    │                          │  看板页面     │
└─────────────┘                          └─────────────┘
```

- **Ubuntu 端**（本机器）：AI 推理（Claude Vision + DeepSeek）、数据库、前端看板、API 服务
- **Windows 端**（你家电脑）：高拍仪驱动、麦克风录音、打印机、TTS 语音播报、开机自启

---

## Ubuntu 端已完成的工作（截至 2026-07-03）

### ✅ 已完成

| 模块 | 状态 | 说明 |
|------|------|------|
| Flask API 服务 | 🟢 运行中 | 端口 5000，所有 REST API 就绪 |
| 前端看板 | 🟢 可用 | 访问 http://localhost:5000 查看 |
| 数据库 | 🟢 就绪 | 17张表，SQLite WAL 模式 |
| 错题本管理 | 🟢 就绪 | 增删查、间隔重复复习计划 |
| 目标奖励系统 | 🟢 就绪 | 目标CRUD、积分、冻结/解冻状态机 |
| 学习摘要 | 🟢 就绪 | 今日统计接口 |
| 知识图谱 | 🟢 就绪 | 知识点管理接口 |
| 家长消息 | 🟢 接口就绪 | Server酱推送框架已写好 |
| 定时提醒 | 🟢 接口就绪 | schedule 调度器已写好 |
| DeepSeek API | 🟢 已配置 | 出卷/诊断/追问可用 |
| Claude Vision | 🟢 已配置 | 拍题识别/答卷批改（图片理解） |

### 🟡 需要 Windows 端配合

| 模块 | Windows 端职责 | Ubuntu 端接口 |
|------|--------------|--------------|
| **拍题识别** | 控制高拍仪拍照 → 上传图片 | `POST /api/photo/recognize` |
| **答卷批改** | 扫描/拍照答卷 → 上传图片 | `POST /api/exam/grade` |
| **英语口语** | 麦克风录音 → 上传音频 | `POST /api/english/dialogue` |
| **TTS 语音播报** | 接收 Ubuntu 的 TTS 音频 → 播放 | 需 Ubuntu 返回音频 URL |
| **打印机** | 打印试卷/错题本 | 需 Ubuntu 返回 PDF 路径 |
| **开机自启** | 启动 Windows 客户端程序 | - |

### 🔴 尚未实现（双方待定）

| 模块 | 说明 |
|------|------|
| Whisper 语音识别 | Ubuntu 端目前为占位实现 |
| Edge TTS 音频生成 | Ubuntu 端目前为占位实现 |
| Obsidian 同步 | 双向笔记同步 |

---

## Windows 端开发要点

### 1. 通信方式

Windows 端通过 HTTP 调用 Ubuntu 端的 API，Ubuntu 端 IP 地址为：
- 本机访问：`http://localhost:5000`
- 局域网访问：`http://<Ubuntu_IP>:5000`

### 2. API 接口清单

完整接口文档见 `contracts/api_spec.yaml`（OpenAPI 3.0 格式）。

**核心接口速查：**

```
GET  /api/health                    健康检查
GET  /api/dashboard                 看板数据（今日统计+积分+目标）
GET  /api/error_book                获取错题列表
POST /api/error_book                添加错题
POST /api/photo/recognize           拍题识别（上传照片）
POST /api/exam/generate             生成试卷
POST /api/exam/grade                批改答卷
POST /api/english/dialogue          英语口语对话
GET  /api/goal                      获取目标列表
POST /api/goal                      创建目标
POST /api/goal/{id}/redeem          兑换奖励
GET  /api/points                    查询积分
GET  /api/summary/daily             每日学习摘要
GET  /api/knowledge/graph           知识图谱
POST /api/parent/message            发送家长消息
```

### 3. 统一响应格式

所有接口返回统一格式：
```json
{
  "code": 0,
  "data": { ... },
  "msg": ""
}
```

- `code: 0` = 成功
- `code: 1` = 参数错误
- `code: 2` = API 调用失败
- `code: 3` = 硬件异常

### 4. Windows 端推荐技术栈

- **语言**：Python（最方便调用 API）或 C#（Windows 原生）
- **高拍仪**：根据设备型号选择 SDK（海康威视/良田等）
- **录音**：PyAudio / NAudio
- **TTS 播放**：playsound / NAudio
- **打印机**：win32print / PrintDocument
- **开机自启**：注册表或任务计划程序

### 5. 开发流程示例

#### 拍题入库流程：
```
Windows 端: 高拍仪拍照 → 获取图片文件
Windows 端: POST /api/photo/recognize (上传图片 + 学科)
Ubuntu 端: Claude Vision 识别 → 返回题目内容 + 知识点
Windows 端: 展示识别结果 → 确认后入库
```

#### 出卷流程：
```
Windows 端: 用户选择科目/年级/章节
Windows 端: POST /api/exam/generate (JSON)
Ubuntu 端: DeepSeek 生成试卷 → 返回题目列表
Windows 端: 打印试卷
```

#### 阅卷流程：
```
Windows 端: 高拍仪扫描答卷 → 获取图片
Windows 端: POST /api/exam/grade (上传图片)
Ubuntu 端: Claude Vision 批改 → 返回分数
Windows 端: 展示成绩 → 错题自动入库
```

---

## 文件结构对照

```
ai-study-coach/
├── app.py                    ← Flask 主应用（Ubuntu 独有）
├── main.py                   ← 启动入口（Ubuntu 独有）
├── config.yaml               ← 配置文件（Ubuntu 独有）
├── db_schema.sql             ← 数据库结构（Ubuntu 独有）
├── templates/                ← HTML 页面（Ubuntu 独有）
│   └── index.html            ← 看板首页
├── static/                   ← 前端静态资源（Ubuntu 独有）
│   ├── css/
│   ├── js/
│   ├── animations/
│   └── sounds/
├── modules/                  ← 业务模块（Ubuntu 独有）
│   ├── error_book.py         ← 错题本
│   ├── goal_system.py        ← 目标奖励
│   ├── exam_module.py        ← 出卷/阅卷
│   ├── ocr_recognition.py    ← 拍题识别
│   ├── english_module.py     ← 英语口语
│   ├── diagnosis_engine.py   ← 诊断引擎
│   ├── knowledge_graph.py    ← 知识图谱
│   ├── reminder.py           ← 定时提醒
│   └── parent_notify.py      ← 家长消息
├── common/                   ← 公共模块（Ubuntu 独有修改权）
│   ├── database.py           ← 数据库连接
│   ├── config.py             ← 配置读取
│   ├── api_client.py         ← API 客户端
│   └── logger.py             ← 日志
├── contracts/                ← API 契约
│   └── api_spec.yaml         ← OpenAPI 文档 ⭐ Windows 端必看
├── verify/                   ← 验证脚本（Ubuntu 独有）
└── tests/                    ← 测试（共享）
```

---

## Git 协同约定

- Ubuntu 端代码 → `auto-ubuntu` 分支
- Windows 端代码 → `auto-win` 分支
- 每天 22:30 合并到 `main`
- `common/` 目录唯一修改权在 Ubuntu 端

---

## 拍题识别 - Claude Vision 说明

拍题识别和答卷批改使用 **Claude Vision**（图片理解模型），不再依赖 GLM-4V。

### 工作原理

```
Windows 端: 高拍仪拍照 → 获取图片文件 (JPEG/PNG)
Windows 端: POST /api/photo/recognize (上传图片 + 学科)
   ↓
Ubuntu 端: 图片 → base64 → Claude Vision API
   ↓
Claude: 识别题目文字 + 公式(LaTeX) + 知识点 + 难度 + 答案
   ↓
Ubuntu 端: 返回结构化 JSON → 展示/入库
```

### Claude Vision 的优势

- **图片理解能力强**：支持 JPEG/PNG 等多种格式，自动识别手写/印刷体
- **数学公式识别**：可将题目中的公式转为 LaTeX 格式
- **知识点标注**：自动提取题目涉及的知识点
- **难度判断**：自动评估题目难度（easy/medium/hard）
- **多模态**：一张图可同时识别文字、公式、图表

### 配置说明

Ubuntu 端 `config.yaml` 中的 Claude 配置（已自动使用 Claude Code 代理）：

```yaml
ai:
  claude:
    base_url: "http://127.0.0.1:15721"  # Claude Code 代理服务
    model: "claude-sonnet-4-6"
    max_tokens: 3000
    temperature: 0.3
```

无需额外配置 API Key，直接使用 Claude Code 的代理即可。

### Windows 端调用示例

```python
import requests

UBUNTU_URL = "http://<Ubuntu_IP>:5000"

# 拍题识别
with open("homework.jpg", "rb") as f:
    r = requests.post(
        f"{UBUNTU_URL}/api/photo/recognize",
        files={"image": f},
        data={"subject": "math", "description": "作业第3题"}
    )
    result = r.json()["data"]
    print(f"题目: {result['recognized_text']}")
    print(f"知识点: {result['knowledge_points']}")
    print(f"难度: {result['difficulty']}")
    print(f"答案: {result['answer']}")

# 答卷批改
with open("answer_sheet.jpg", "rb") as f:
    r = requests.post(
        f"{UBUNTU_URL}/api/exam/grade",
        files={"images": f},
        data={"exam_id": "exam_001"}
    )
    result = r.json()["data"]
    print(f"总分: {result['total_score']}")
    for qs in result['question_scores']:
        status = "✓" if qs['is_correct'] else "✗"
        print(f"  {status} Q{qs['question_id']}: {qs['score']}/{qs['full_score']} - {qs['comment']}")
```

---

## 快速开始（Windows 端）

1. 安装 Python
2. 安装 requests 库：`pip install requests`
3. 参考 `contracts/api_spec.yaml` 编写 API 调用代码
4. 高拍仪/录音/打印等硬件部分根据设备 SDK 开发

示例代码：
```python
import requests

UBUNTU_URL = "http://<Ubuntu_IP>:5000"

# 健康检查
r = requests.get(f"{UBUNTU_URL}/api/health")
print(r.json())

# 获取看板数据
r = requests.get(f"{UBUNTU_URL}/api/dashboard")
data = r.json()["data"]
print(f"今日错题: {data['today_stats']['new_errors']}")
print(f"可用积分: {data['points']['available_points']}")

# 拍题识别
with open("photo.jpg", "rb") as f:
    r = requests.post(f"{UBUNTU_URL}/api/photo/recognize",
                      files={"image": f},
                      data={"subject": "math"})
    print(r.json()["data"])
```
