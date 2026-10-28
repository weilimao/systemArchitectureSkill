# Architecture Guardian (架构守护者)

> 解决工程化项目迭代中“功能越加越多、越写越庞大、AI 遗忘全局架构、代码腐化”的 Antigravity 架构守护 Skill。

---

## 📖 设计背景与解决痛点

在基于 AI 辅助软件研发的工程化项目中，常见以下架构劣化过程：
1. **上下文注意力衰减 (Context Decay)**：迭代轮次增多后，AI 无法在上下文里完整保留最初的架构图与分层约定。
2. **架构文档滞后 (Doc Rot)**：代码一直在加，但文档停留在立项之初，导致新业务功能无处可查、重构困难。
3. **分层破坏与重复建设**：AI 不知道项目中已经存在某些公共组件或已有业务域，导致重复造轮子或产生跨模块私有调用的“屎山代码”。
4. **多模块文档通读耗时**：当工程模块增多后，AI 逐篇通读分析极为缓慢。

**Architecture Guardian** 通过强约束的**双向闭环机制（事前查架构/秒级定位、事中遵规范、事后同架构）**，强制将每次新增业务功能点固化在标准化的项目架构目录中。

---

## 🏗️ 架构文档标准骨架

在目标工程中，本 Skill 将维护一套分层且模块化的架构知识库：

```text
<项目根目录>/docs/architecture/
├── ARCHITECTURE.md                  # 【主索引文件】全局分层拓扑、模块索引表、变更时序流
├── decisions/                        # 【架构决策记录 (ADR)】技术选型与重大设计决策
│   └── 0001-template.md
└── modules/                          # 【业务模块子目录】垂直业务域拆分
    ├── auth/                         # 示例模块：认证中心
    │   └── README.md                 # 业务逻辑、时序流、已实现功能清单、关键类与对外接口
    ├── order/                        # 示例模块：订单中心
    │   └── README.md
    └── ...
```

---

## 🚀 安装与启用方式

### 方式一：作为全局插件安装（推荐，所有项目生效）
将本项目目录作为插件复制到用户全局配置路径：
```bash
# 复制至全局插件目录
xcopy "e:\GPT\systemArchitectureSkill" "%USERPROFILE%\.gemini\config\plugins\architecture-guardian-plugin" /E /I /H /Y
```
安装后，所有由 Antigravity 驱动的项目在开发新功能时，均可自动识别并执行本 Skill。

### 方式二：作为项目专属技能启用
将 `skills/architecture-guardian` 目录直接拷贝至目标工程的 `.agents/skills/` 目录下即可：
```text
<目标项目根目录>/
└── .agents/
    └── skills/
        └── architecture-guardian/
            ├── SKILL.md
            ├── scripts/arch_guardian.py
            └── resources/templates/...
```

---

## 🌐 分布式多工程协同与架构目录指针 (.arch-guardian.json)

在分布式或微服务架构中，多个子服务（如 `order-service`、`user-service`、`gateway`）通常各为一个独立 Git 仓库。为实现多人协同开发与全局架构集中追踪，可通过**架构指针**将各子工程统一指向一个共享架构仓库：

### 1. 配置方式：子工程根目录 `.arch-guardian.json`
在子工程根目录下创建 `.arch-guardian.json`（支持相对路径与绝对路径）：
```json
{
  "arch_dir": "../central-architecture/docs/architecture"
}
```

### 2. 命令行一键初始化与自动持久化
在微服务工程根目录下执行初始化时传入 `--arch-dir`，脚本会自动持久化生成 `.arch-guardian.json` 并配置工程 `GEMINI.md`：
```bash
python scripts/arch_guardian.py --workspace "<子工程路径>" init --name "<平台总名称>" --arch-dir "../central-architecture/docs/architecture"
```
后续 AI 在该子工程下执行 `locate`、`new-module`、`sync-feature`、`verify` 时，将自动路由并更新共享架构库，无需再手动传递路径参数！

### 3. 解析优先级
1. **CLI 显式参数**：`--arch-dir / -a`（最高优先级）
2. **工程配置文件**：当前工程根目录的 `.arch-guardian.json`
3. **默认回退**：`<当前工程根目录>/docs/architecture`

---

## 🛠️ CLI 辅助工具命令行指南

本 Skill 内置了零外部依赖的跨平台辅助工具 `arch_guardian.py`，AI 或开发者可直接调用：

### 1. 初始化目标项目的架构骨架与常驻硬门禁
```bash
python scripts/arch_guardian.py --workspace "<项目绝对路径>" init --name "<项目名称>" --desc "<系统定位描述>"
```
> **自动注入硬门禁**：执行初始化时，工具会自动在目标工程根目录下建立或增补 `GEMINI.md` 常驻规则，确保项目后续的每一次日常业务代码修改均被强制要求同步业务文档。

### 2. ⚡ 秒级定位业务说明与章节路径 (事前首选)
当文档较多时，无需一个个文档分析，直接输入关键词获取命中模块与精确章节行号：
```bash
python scripts/arch_guardian.py --workspace "<项目绝对路径>" locate <业务关键词/类名/接口/状态枚举...>
```
输出包含：所属业务模块、章节面包屑路径（如 `modules/order/README.md > ## 3. 核心业务流程 > ### 3.2 订单超时退款 [L85]`）以及关键文本摘要与行号直链。

### 3. 创建并自动登记新的业务模块
```bash
python scripts/arch_guardian.py --workspace "<项目绝对路径>" new-module order --title "订单中心" --domain "交易与履约域" --desc "管理订单生命周期、状态机流转与履约支付"
```

### 4. 同步业务功能点（自动更新模块文档与主索引）
```bash
python scripts/arch_guardian.py --workspace "<项目绝对路径>" sync-feature order --title "超时自动关单" --desc "基于延迟队列实现30分钟未支付订单自动关闭并回滚库存" --code-ref "src/order/OrderAutoCancelService.java"
```

### 5. 全域文档影响面检索 (事后同步前必查)
扫描架构库中受某关键词影响的所有历史文档，防止更新遗漏：
```bash
python scripts/arch_guardian.py --workspace "<项目绝对路径>" search-docs <keywords...>
```

### 6. 记录重大架构决策 (ADR)
```bash
python scripts/arch_guardian.py --workspace "<项目绝对路径>" add-adr 0001 --title "引入分库分表与ShardingSphere中间件"
```

### 7. 校验架构文档完整性（检测坏链与未登记模块）
```bash
python scripts/arch_guardian.py --workspace "<项目绝对路径>" verify
```

---

## 🧪 自动化测试与验证

本项目自带完备的单元测试与端到端集成测试，具备严格的环境沙箱隔离机制（Teardown 确保零脏数据残留）：
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```
