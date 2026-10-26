| 这个作业属于哪个课程 | [计科 24 级 56 班](https://edu.cnblogs.com/campus/gdgy/Class56-Grade2024-CS/) |
|-------------------|-----------------|
| 这个作业要求在哪里 | [构建一个能说会做的智能体](https://edu.cnblogs.com/campus/gdgy/Class56-Grade2024-CS/homework/16760) |
| 这个作业的目标 | 实现一个能够理解自然语言、调用工具处理文件和执行命令，并记住多轮对话的编程与办公助手。 |
| 学号 | 3124004049（成员A）、3124004064（成员B） |

# 构建一个能说会做的智能体：Aria

[返回作业目录](../README.md) · [仓库首页](../../README.md)

## 1. 项目简介

Aria 是一个基于 Python 的终端 Coding Agent，面向编程与文件整理场景，能够通过自然语言理解用户任务，并调用文件、搜索、编辑和命令工具完成操作。

项目围绕“模型理解任务 → 调用工具 → 分析执行结果 → 回复用户”的循环设计，将模型接入、工具调度、权限审批、会话存储和终端界面划分为独立模块。用户既可以直接提问，也可以让智能体创建文件、修改内容和执行命令。

GitHub 仓库：[onychen/gdut-software-engineering-2026](https://github.com/onychen/gdut-software-engineering-2026)，项目目录：`3124004049/aria/`。

## 2. 需求描述

面向需要通过自然语言阅读、整理和修改项目文件的用户。用户给出任务后，智能体自行决定是否调用工具，把工具执行结果继续交给模型分析，最后说明完成情况。

| 需求 | 实现方式 | 对应代码 |
| --- | --- | --- |
| 自然语言对话（会说） | OpenAI-compatible 模型接口、流式回复与推理展示 | `src/core/openai_client.py`、`src/core/ui.py` |
| 执行操作（会做） | 文件列举、搜索、读取、创建、编辑和本地命令执行 | `src/core/tools/` |
| 多轮记忆 | JSONL 会话保存、历史恢复和上下文压缩 | `src/core/session.py`、`src/core/session_store.py`、`src/core/context.py` |
| 外部工具扩展 | 可选 stdio MCP 客户端，支持工具发现与调用 | `src/core/tools/mcp_stdio.py` |
| 简洁交互界面 | 全屏终端界面，显示 Markdown、工具执行和审批操作 | `src/core/screen.py`、`src/core/tool_approval.py` |
| 控制写入与执行 | 写文件、编辑文件和执行命令前请求用户确认 | `src/core/tools/permissions.py` |
| 语音输入/输出（加分项） | 使用 faster-whisper `base` 自动识别语言并转写；输入文本先进入可编辑草稿，Windows 下可朗读回复 | `src/core/voice.py`、`src/core/commands/voice_input.py`、`src/core/commands/voice_output.py` |

本项目提供终端界面、跨平台语音输入和 Windows 语音输出；没有实现网页或桌面图形界面，也没有内置天气或数据库服务。MCP 是可选扩展能力，基础文件任务不依赖额外 MCP Server。语音输入使用 `sounddevice` 录音并由 faster-whisper `base` 模型自动识别语言，Windows/macOS/Linux 均可使用；语音输出当前使用 Windows 自带的 `System.Speech`，Linux/macOS 下仍可使用完整的文本输入输出功能。

## 3. 业务流描述

```mermaid
flowchart TD
    A[用户输入自然语言任务] --> B[读取会话历史与项目指令]
    A0[语音输入 /listen] --> A
    B --> C[模型理解任务并生成回复或工具调用]
    C --> D{是否需要工具}
    D -- 否 --> J[展示回复]
    D -- 是 --> E[校验工具参数与工作区路径]
    E --> F{是否需要审批}
    F -- 是 --> G{用户是否批准}
    F -- 否 --> H[执行本地工具或 MCP 工具]
    G -- 是 --> H
    G -- 否 --> I[将拒绝原因返回模型]
    H --> K[记录工具结果和会话]
    K --> C
    I --> C
    J --> L{是否开启语音输出}
    L -- 是 --> M[Windows System.Speech朗读回复]
    L -- 否 --> N[保存会话]
    M --> N
```

例如，用户要求“把会议记录整理成待办清单”，模型先调用读取工具获取文件，再调用写入工具生成清单。用户批准写入后，执行结果返回模型，由模型说明输出文件位置。路径校验或工具执行失败时，错误同样会返回模型，支持后续纠正。

## 4. 实现说明

采用 Python 3.11+，主要依赖为 OpenAI Python SDK、prompt-toolkit 和 Pygments；测试使用 pytest 与 pytest-asyncio。完整依赖声明在 `pyproject.toml`，固定版本在 `uv.lock`。

```text
aria/
├── src/core/               # 模型、Agent 循环、会话、界面、命令与工具
│   ├── agent_loop.py       # 模型 → 工具 → 模型循环
│   ├── prompts/            # Agent 与上下文压缩提示词资源
│   ├── voice.py             # faster-whisper 输入与 Windows 语音输出适配
│   ├── tools/              # 本地工具、权限、MCP 接入
│   └── commands/           # /model、/compact、/mcp、/listen、/voice 等命令
├── tests/                  # 自动化测试
├── evaluation/             # 离线回归与可选真实模型评测
├── examples/               # 无真实密钥的配置模板与演示输入
├── evidence/               # 测试与功能验证结果
├── design/                 # 架构与模块设计资料
├── problems/、todo/        # 实验分析与待办记录
├── pyproject.toml
├── uv.lock
└── README.md               # 项目说明与使用文档
```

`main.py` 负责启动，`ui.py` 负责编排用户交互，`screen.py` 负责渲染，`agent_loop.py` 驱动模型与工具循环。工具通过统一注册表调度，权限判断与审批界面分离。会话和工具结果写入工作区的 `.aria/`，恢复时重新载入历史消息。

MCP 接入使用标准输入输出与外部 Server 通信，完成初始化、`tools/list` 工具发现和 `tools/call` 调用，再统一交给工具管理器调度。可选配置说明见 [MCP 示例](./examples/README.md)。

## 5. 安装与运行

需要 Python 3.11+、Git、uv 和 ripgrep（`rg` 命令，供文件搜索工具使用）。核心终端程序支持 Windows、macOS 和 Linux；命令工具在 Windows 使用 `cmd.exe`，在 macOS/Linux 使用 `/bin/sh`。PowerShell 命令可通过 `powershell -NoProfile -Command "..."` 显式执行。语音输入需要可用的麦克风；首次使用 faster-whisper 时还会自动下载 `base` 模型，模型缓存后可以离线识别。Windows 语音输出需要系统语音服务。

语音输入可以通过环境变量调整：`ARIA_WHISPER_MODEL` 默认为 `base`，`ARIA_WHISPER_DEVICE` 默认为 `cpu`，`ARIA_WHISPER_COMPUTE_TYPE` 默认为 `int8`，`ARIA_VOICE_RECORD_SECONDS` 默认为 `12`。如果系统默认录音设备不是目标麦克风，可设置 `ARIA_VOICE_INPUT_DEVICE` 为设备名称或编号。

SWE-bench 需要可用的 Linux Docker 引擎和官方评测镜像；已适配 Windows 宿主的容器启动与进程清理，但真实评测仍建议在 WSL2 中运行。`evaluation.big_task_single_goal` 实验还会挂载宿主的 Linux Node 工具链，需在 Linux/WSL2 环境运行。

Windows 可在 PowerShell 中安装 ripgrep，然后按常规方式同步依赖并启动：

```powershell
winget install --id BurntSushi.ripgrep.MSVC -e
uv sync --frozen
uv run aria
```

也可使用 Scoop 或 Chocolatey 安装 ripgrep。安装后需重新打开终端，使 `rg` 加入 `PATH`。

Ubuntu 可先安装搜索工具：

```bash
sudo apt-get update
sudo apt-get install ripgrep
rg --version
```

```bash
git clone https://github.com/onychen/gdut-software-engineering-2026.git
cd gdut-software-engineering-2026/3124004049/aria
uv sync --frozen
uv run aria
```

首次运行会引导选择模型服务商、填写 API Key 和模型名称，并将配置保存到用户目录 `~/.aria/settings.json`。目前支持 DeepSeek、OpenAI、Gemini、Moonshot、阿里云百炼、智谱和硅基流动，也可以手动填写兼容服务地址。Gemini 型号会从其 API 动态获取并筛选支持内容生成的模型；也可手动输入未列出的模型 ID。模型须支持工具调用；上下文窗口以实际模型配置为准。

也可复制 `examples/settings.example.json` 到项目 `.aria/settings.json`，填写真实配置后显式启动：

```bash
mkdir -p .aria
cp examples/settings.example.json .aria/settings.json
# 编辑 .aria/settings.json，填写服务地址、模型名称、API Key 和上下文窗口。
uv run aria --config .aria/settings.json
```

示例中的域名、模型名和密钥均为占位内容，不能直接连接模型。`.aria/` 已被忽略，勿将真实密钥写入示例文件。

常用操作：`Enter` 发送，`Ctrl+J` 换行，`Esc` 取消请求或停止录音，`Ctrl+D` 退出。输入 `/` 可以选择 `/model`、`/compact`、`/status`、`/mcp`、`/listen`、`/voice`、`/export` 等命令。Windows、macOS 或 Linux 下输入 `/listen` 开始录音，录音期间按 `Esc` 可结束采集并继续识别已录制音频，未手动停止时 12 秒后自动结束；Whisper 会自动检测中文或英文，结果会放入草稿，检查后按 `Enter` 发送。Windows 下输入 `/voice on` 开启回复朗读，输入 `/voice off` 关闭。写操作审批支持批准本次、批准本会话或拒绝。

## 6. 使用示例与功能演示

以下为可复现的演示步骤和预期结果；真实模型演示需要自行配置有效服务。自动化验证使用离线模型替身，实际验证结果见 [测试与功能验证记录](./evidence/README.md)。

### 示例一：自然语言创建文件

启动 Agent 后输入：

```text
请读取 examples/demo-workspace/meeting-notes.txt，把三个任务整理成 Markdown 复选框清单，写入 examples/demo-workspace/TODO.md。保留负责人和截止日期，完成后说明输出路径。
```

预期过程：读取会议记录 → 生成写入请求 → 用户批准 → 创建 `TODO.md` → 返回完成说明。可以直接打开文件核对三个任务及负责人、日期。生成的 `TODO.md` 已加入忽略规则。

### 示例二：多轮对话和修改文件

继续输入：

```text
把刚才清单中成员B负责的“执行测试与整理演示证据”标为已完成，其余任务保持不变，并读取修改后的文件确认。
```

预期过程：利用会话历史定位刚才的文件 → 读取与编辑 → 用户批准 → 再次读取确认。此过程同时展示对话记忆与工具执行。

### 示例三：退出后恢复

```bash
uv run aria resume
uv run aria resume <session-id>
```

不带 ID 时选择历史会话；带 ID 时恢复指定会话。退出时会显示恢复命令。恢复后可继续询问上一轮创建的清单。

### 示例四：执行命令

```text
请运行 python --version，并告诉我当前 Python 版本。
```

批准命令后，Agent 根据真实命令输出回答版本。需要演示 MCP 时，可按 `examples/README.md` 配置自己的 Server，再使用 `/mcp` 查看状态。

### 示例五：语音输入与输出

先连接麦克风，然后在 Aria 中输入：

```text
/voice on
/listen
```

对着麦克风说“请读取 examples/demo-workspace/meeting-notes.txt 并整理成待办清单”，说完后按 `Esc` 结束采集并等待识别。faster-whisper 会自动判断主要语言并转写，识别结果会回填到输入框，用户可以修改识别错误后按 `Enter` 发送；Windows 下模型完成回复后，Aria 使用系统默认语音朗读回复。Linux/macOS 下 `/voice on` 会提示语音输出不可用，但不影响文本对话。

## 7. 测试与验证

从本项目目录执行：

```bash
uv run --frozen pytest -q
uv run --frozen python -m evaluation.runner
uv run --frozen aria --help
```

离线评测覆盖多轮记忆、文件编辑、工具失败恢复、上下文压缩恢复、取消后的会话恢复和模型重试六种场景，不需要 API Key。默认输出到被忽略的 `evaluation-results/`。语音模块的单元测试通过替换录音设备和 Whisper 模型，不要求测试环境连接真实麦克风或扬声器。

Windows 原生环境最新验证为 923 项测试通过、0 项失败、3 项按环境条件跳过，六项离线评测场景全部通过。详细环境、测试方式与容器评测边界见 [Windows 验证记录](./evidence/windows-validation.md)；其他测试日志与评测报告保存在 [evidence/](./evidence/)。

## 8. 小组分工安排

按实际提交划分职责。成员 A 负责原有 Agent 核心能力，成员 B 负责 Windows 原生迁移以及本次新增的语音输入/输出；双方共同完成联调、测试检查、功能演示和博客整合。

| 模块 | 负责人 | 主要工作 | 对应代码 |
| --- | --- | --- | --- |
| Agent 核心能力 | 3124004049 成员A | 实现模型接入、Agent 主循环、会话记忆、上下文管理、配置异常处理、本地工具、权限、MCP 和终端界面 | `agent_loop.py`、`session*.py`、`context.py`、`tools/`、`screen.py`、`ui.py`、原有 `commands/` |
| Windows 原生支持 | 3124004064 成员B | 迁移命令执行、文件路径、会话存储、工作树和容器辅助逻辑，补充 Windows 环境测试与验证记录 | `tools/command_executor.py`、`tools/command_tool.py`、`tools/file_tools.py`、`session_store.py`、`worktree.py`、`evidence/windows-validation.md` |
| 语音输入/输出 | 3124004064 成员B | 接入 faster-whisper `base` 和 `sounddevice`；实现 `/listen` 自动语言识别、`/voice on|off` 开关、Windows 回复朗读、错误提示和无硬件单元测试 | `voice.py`、`commands/voice_input.py`、`commands/voice_output.py`、`ui.py`、`screen.py`、`tests/test_voice.py` |

表中 `src/core/` 下的代码路径均相对于该目录，`evidence/` 和 `tests/` 路径相对于项目根目录。模块测试由各自负责人编写与维护，双方交叉检查关键逻辑；整体联调、端到端测试、功能演示、博客整合和最终提交由两人共同完成。


## 9. 成员心得

### 3124004049 成员A

这次作业让我对智能体与普通聊天程序的区别有了更具体的理解。模型生成回复只是其中一步，还需要把工具调用解析出来、交给对应模块执行，再把执行结果传回模型，才能形成完整的任务处理流程。在梳理模型接入与 Agent 主循环时，我认识到每一层的职责需要清楚：模型负责理解和决策，工具负责执行，主循环负责衔接过程。这样处理后，模型接口、工具实现和界面就能分别调整，出错时也更容易定位。

会话记忆与上下文管理是另一个收获。保存聊天记录并不等于模型能够一直记住全部内容，还要考虑上下文窗口、历史消息的组织和压缩后的信息保留。会话恢复也需要依靠明确的存储结构，而不是只保留终端上显示的文字。配置校验、异常分类和请求重试这些看似辅助的部分，同样影响程序能否稳定运行。通过这次作业，我更重视模块边界和可验证的执行结果；与同伴对接工具和界面模块时，也体会到先约定好输入、输出和错误格式，可以减少后续联调中的反复修改。

### 3124004064 成员B

这次作业中我主要负责两部分工作。第一部分是原有 Agent 的 Windows 原生迁移：命令执行、路径处理、会话存储、工作树和容器辅助逻辑都依赖操作系统行为，不能只把 POSIX 命令替换成 Windows 命令，还要处理路径分隔符、进程启动、超时取消、工作目录和用户身份等差异。通过补充 Windows 环境测试和验证记录，我对跨平台软件的边界条件有了更具体的认识。

第二部分是语音输入和输出。我使用 `sounddevice` 录制麦克风音频，再通过 faster-whisper `base` 模型自动检测中文或英文并转写；识别结果会放回可编辑草稿，避免不准确的语音直接触发文件操作。Windows 下通过 `/voice on|off` 控制是否朗读模型的最终回复。实现时还需要处理模型首次下载、录音设备异常、没有识别到语音、CPU 推理速度和非 Windows 语音输出边界，并用替换录音设备和模型的单元测试验证语言检测、错误和命令行为。这个过程让我认识到，加分功能也应当服从已有的会话、审批和错误处理边界，而不是绕开 Agent 的主流程。
