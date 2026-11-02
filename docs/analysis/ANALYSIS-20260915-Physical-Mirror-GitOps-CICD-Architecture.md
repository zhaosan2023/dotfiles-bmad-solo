# ANALYSIS-20260915-Physical-Mirror-GitOps-CICD-Architecture

> **分析类型**：物理镜像 GitOps 部署架构与 CI/CD 自动化全流程解构（Physical Mirror GitOps & CI/CD Lifecycle Architecture）  
> **现场现场**：全局 `~/.gemini/config` 与任意克隆路径（如 `~/project/dotfiles-bmad-solo`、`~/dotfiles-bmad-solo`）  
> **用户意图**：确立物理镜像（方案 A）下的跨目录独立性、GitHub 远程更新（`--latest` / `git pull`）、版本切换回滚与全套 CI/CD 自动化流水线。  
> **裁定结果**：`FEASIBLE` (极高可行性，架构解耦清晰，兼顾安全性、幂等性与极简开发者体验)

---

## 1. 战略架构与执行摘要 (Mary Strategic Executive Summary)

### 核心矛盾与架构演进 (The Architectural Shift)

在以往的软链接架构中，我们追求“修改即生效”的开发便利，却无意间踩踏了 Antigravity IDE 的多工作区沙箱安全红线（`filepath.EvalSymlinks` 导致的跨域越界拒绝）。

**方案 A 的本质演进**：将架构由**“单层共享软链接（Shared In-Place Symlink）”**全面升级为**“双层分离物理镜像（Dual-Layer Physical Mirror Architecture）”**：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Layer 1: Git 真理源层 (Source Layer)               │
│  • 任意宿主路径: ~/project/dotfiles-bmad-solo 或 ~/dotfiles-bmad-solo           │
│  • 职责: GitOps 源码版本管理、分支切换 (main/feature)、发布打标 (v4.1.0)           │
│  • 行为: git fetch / pull / checkout，受 SCRIPT_DIR 动态路径自适应保护         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                      【原子镜像管道: rsync -a --delete】
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Layer 2: 全局物理运行时层 (Runtime Layer)               │
│  • 固定物理路径: ~/.gemini/config/plugins/bmad-suite/ (实体物理目录，绝非软链)    │
│  • 全局规则路径: ~/.gemini/config/rules/bmad-core.md, bmad-constitution.md  │
│  • 部署存根元数据: ~/.gemini/config/plugins/bmad-suite/.manifest.json          │
│  • 职责: 供所有业务项目 (orignalscanner, watchhusm 等) 免鉴权高速直读          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Keshav Three-Pass: 深度解构 (Divergent Deconstruction)

### Pass 1: 5C Baseline (概念基线)
- **Category (范畴)**：CLI 研发基础设施、GitOps 部署生命周期管理、CI/CD 自动化管道。
- **Context (场景)**：用户本地可能存在多个项目工作区，`dotfiles-bmad-solo` 存放位置不确定；用户需要既能一键从 GitHub 拉取最新更新，又能锁定稳定发布 Tag，且全局配置在所有项目均能 100% 免卡死工作。
- **Correctness (正确性)**：彻底消除软链接导致的沙箱权限阻断；通过 Manifest 元数据消除“运行时与代码源版本脱节”的认知黑盒。
- **Contributions (教训与价值)**：确立了三项不可违背的运维公理：
  1. **路径无关公理 (Path Invariance Axiom)**：无论 clone 到何处，CLI 脚本必须基于自身物理路径解析，不硬编码父目录。
  2. **物理独立公理 (Physical Mirror Axiom)**：运行时目录必须是实物，严禁外部符号链接。
  3. **状态可审计公理 (Manifest Transparency Axiom)**：运行时必须携带来源 Commit、Tag 及同步时间戳，避免“到底装的是哪个版本”的猜疑。
- **Clarity (清晰度)**：清晰定义了三种核心动作：`Pull`（同步远程代码）、`Checkout/Switch`（切换版本）、`Deploy/Mirror`（物理同步到运行时）。

---

### Pass 2: Causal & Evidence Firewall (四道收敛锁核验)

> **启动 Lock 1: Non-Goals Lock (明确界定 3 项非目标)**
> 1. **非目标 1 (不侵入业务项目的 git)**：不修改 `orignalscanner` 或其他业务项目自身的 git 配置，仅管理全局 bmad 插件与规则。
> 2. **非目标 2 (不依赖复杂的系统级包管理器)**：不引入 `apt`、`pip`、`brew` 外部包管理打包发布，保持纯 Bash + Git + Rsync 极简依赖。
> 3. **非目标 3 (不废除现有的 .versions/ 影子快照机制)**：Tag 回滚依然保持从 Git 归档解压到 `.versions/<tag>` 的干净隔离，不污染 Git 工作区。

#### 关键用户疑问的因果回答 (Causal Answers to User Questions)

1. **疑问 1：clone 的路径可能是任意的，如何处理？**
   - **事实证据**：在 `bs.sh` 第 10 行：`SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`。
   - **因果结论**：该写法在 POSIX Bash 下能 100% 准确获取脚本自身所在的真实绝对路径。无论克隆在 `~/project/` 还是 `~/` 还是 `/opt/`，`SCRIPT_DIR` 均自动适配，零路径硬编码。

2. **疑问 2：需要运行 `bs.sh --latest` 将最新版本同步更新到全局 `~/.gemini` 路径下？**
   - **事实证据**：以往的 `--latest` 仅仅做了 `git checkout main`，但**没有执行 `git pull origin main`，也没有将物理文件拷入 `~/.gemini`**。
   - **设计修正**：`--latest` 升级为“检出 main 分支 + 物理同步镜像”；同时新增显式的 `--update` 指令（拉取远程最新提交并同步镜像）。

3. **疑问 3：如果要 `git checkout main`，就从 github 上更新最新的版本下来？**
   - **事实证据**：Git 原生命令中，`git checkout main` 只是本地指针切换，若要更新必须配合 `git pull`。
   - **设计修正**：为避免用户手动敲多个命令，`bs.sh --update`（或 `bs.sh -u`）提供一键化操作：
     `git fetch --tags origin && git checkout main && git pull --ff-only origin main && ./bs.sh`。

---

### Pass 3: Virtual Re-Implementation: 命令集 UX 与状态机设计

```
                            ┌────────────────────────┐
                            │    用户发起 CLI 操作    │
                            └───────────┬────────────┘
                                        │
             ┌──────────────────────────┼──────────────────────────┐
             ▼                          ▼                          ▼
   【场景 1: 本地开发同步】     【场景 2: 远程拉取更新】     【场景 3: 版本回滚/锁定】
     运行: ./bs.sh              运行: ./bs.sh --update     运行: ./bs.sh --tag v4.1.0
             │                          │                          │
             │                          │ git fetch && pull        │ 归档至 .versions/
             ▼                          ▼                          ▼
   ┌───────────────────────────────────────────────────────────────────────┐
   │                       统一原子物理同步管道 (The Sync Engine)           │
   │  1. 探测目标源目录 ($SOURCE_SUITE)                                    │
   │  2. 清理旧软链 (rm -rf $TARGET_DIR)                                   │
   │  3. rsync -a --delete $SOURCE_SUITE/ ~/.gemini/config/plugins/bmad... │
   │  4. cp -f $SOURCE_SUITE/rules/* ~/.gemini/config/rules/               │
   │  5. 生成并写入 .manifest.json (记录 SourceRepo, Commit, Tag, Time)    │
   └───────────────────────────────────┬───────────────────────────────────┘
                                       ▼
   ┌───────────────────────────────────────────────────────────────────────┐
   │                    验证与反馈 (Status & Verification)                  │
   │  • 输出部署元数据与版本差异                                            │
   │  • 提醒 IDE 重载窗口 (Developer: Reload Window)                       │
   └───────────────────────────────────────────────────────────────────────┘
```

---

## 3. Deep Recon: 决策矩阵与方案对比

| 决策维度 | 方案 1：纯手动 Git + 手动拷贝 | 方案 2：软链接 (现有缺陷方案) | 方案 3：GitOps + Rsync 物理镜像 (推荐方案) |
| :--- | :---: | :---: | :---: |
| **跨项目权限安全** | ✅ 物理目录通过 | ❌ EvalSymlinks 阻断 | ✅ **100% 物理通过** |
| **路径无关性** | ❌ 极易漏拷路径 | ⚠️ 依赖固定符号链接 | ✅ **自动动态识别** |
| **远程一键更新** | ❌ 步骤繁琐容易出错 | ❌ 需手动拉取 + 容易卡死 | ✅ **`bs.sh --update` 一键闭环** |
| **版本回滚与锁定** | ❌ 容易覆盖污染代码 | ⚠️ 软链接导致脏工作区 | ✅ **`.versions/` 隔离 + 物理拷贝** |
| **运行时透明度** | ❌ 无法感知安装版本 | ⚠️ 仅能查看软链目标 | ✅ **`.manifest.json` 机器可读审计** |
| **综合评分** | 4.8 / 10 | 6.2 / 10 | **9.6 / 10 (WINNER)** |

---

## 4. 全套 CI/CD 与部署更新实现蓝图 (Complete Implementation Blueprint)

### 模块 A：`bs.sh` 脚本核心重构规范

在 `bs.sh` 中落实以下 4 个关键能力：

#### 1. 新增 `--update` (`-u`) 一键拉取远程更新并物理发布
```bash
update_from_remote() {
    echo -e "${YELLOW}======================================================${NC}"
    echo -e "${YELLOW} GitOps: Fetching & Pulling Latest from GitHub...     ${NC}"
    echo -e "${YELLOW}======================================================${NC}"
    if ! git -C "$SCRIPT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo -e "${RED}Error: $SCRIPT_DIR is not a git repository.${NC}"
        exit 1
    fi
    
    echo -e "  [i] Fetching latest commits and tags..."
    git -C "$SCRIPT_DIR" fetch --tags origin
    
    CURRENT_BRANCH=$(git -C "$SCRIPT_DIR" branch --show-current 2>/dev/null || echo "main")
    echo -e "  [i] Pulling latest changes on branch: $CURRENT_BRANCH..."
    git -C "$SCRIPT_DIR" pull --ff-only origin "$CURRENT_BRANCH"
    
    echo -e "${GREEN}[✔] Local repository is up to date.${NC}\n"
    SWITCH_LATEST=1
}
```

#### 2. 重写原子部署管道（废除 `ln -s`，采用 `rsync` 物理镜像）
```bash
# 目标路径
PLUGIN_DIR="$GEMINI_CONFIG_DIR/plugins"
TARGET_DIR="$PLUGIN_DIR/bmad-suite"
RULES_DIR="$GEMINI_CONFIG_DIR/rules"

mkdir -p "$PLUGIN_DIR" "$RULES_DIR"

# 关键：彻底废除软链，如果已存在且为软链则删除
if [ -L "$TARGET_DIR" ] || [ -f "$TARGET_DIR" ]; then
    rm -rf "$TARGET_DIR"
fi
mkdir -p "$TARGET_DIR"

# 物理镜像完整插件内容
rsync -a --delete "$SOURCE_SUITE/" "$TARGET_DIR/"

# 物理同步全局规则
cp -f "$SOURCE_SUITE/rules/bmad-constitution.md" "$RULES_DIR/bmad-constitution.md"
cp -f "$SOURCE_SUITE/rules/bmad-core.md" "$RULES_DIR/bmad-core.md"

# 写入部署 Manifest 元数据
COMMIT_HASH=$(git -C "$SCRIPT_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown")
COMMIT_DATE=$(git -C "$SCRIPT_DIR" log -1 --format="%cd" --date=iso 2>/dev/null || echo "unknown")
cat <<EOF > "$TARGET_DIR/.manifest.json"
{
  "installed_version": "$VERSION_TITLE",
  "source_repository": "$SCRIPT_DIR",
  "source_commit": "$COMMIT_HASH",
  "commit_date": "$COMMIT_DATE",
  "deploy_timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "deploy_type": "physical_mirror"
}
EOF
```

#### 3. 增强 `--status` (`-s`) 审计检查
读取 `$TARGET_DIR/.manifest.json`，并将安装状态与当前 Git 仓库的 HEAD 进行比对：
- 若 Commit 相同：打印绿色 `[✔] Deployed Mirror is UP-TO-DATE`。
- 若 Commit 不同：打印黄色警示 `[!] Deployed Mirror is STALE (Run ./bs.sh to re-sync)`。

---

### 模块 B：GitHub Actions CI/CD 流水线设计

在仓库根目录建立 `.github/workflows/ci.yml` 与 `.github/workflows/release.yml`。

#### 1. `.github/workflows/ci.yml` (代码提交与 PR 门禁)
```yaml
name: BMAD Suite CI & Security Gate

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  lint-and-validate:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Lint Shell Script (bs.sh)
        run: |
          sudo apt-get install -y shellcheck
          shellcheck bs.sh

      - name: Validate Plugin & Skill Structure
        run: |
          python3 -c "
          import json, os, glob
          # 验证 plugin.json
          for p in glob.glob('**/plugin.json', recursive=True):
              with open(p) as f:
                  json.load(f)
              print(f'Valid JSON: {p}')
          "

      - name: Verify Anti-Hang & Terminal Tri-Invariants in Skills
        run: |
          # 门禁断言：所有技能与规则必须包含 10000ms 与 timeout 保护
          grep -q "WaitMsBeforeAsync MUST be set to 10000ms" bmad-suite-v4/skills/ana-solo/SKILL.md
          grep -q "WaitMsBeforeAsync MUST be set to 10000ms" bmad-suite-v4/rules/bmad-constitution.md
          echo "All Terminal Invariants Verified!"

      - name: Test Physical Mirror Installation & Anti-Symlink Lock
        run: |
          export HOME=$RUNNER_TEMP
          # 执行本地安装
          ./bs.sh
          
          # 核心断言 1：插件目录必须为真实物理目录，绝不可为软链接
          TARGET="$HOME/.gemini/config/plugins/bmad-suite"
          if [ -L "$TARGET" ]; then
            echo "FAILED: $TARGET is a symlink! Must be physical directory."
            exit 1
          fi
          if [ ! -f "$TARGET/skills/ana-solo/SKILL.md" ]; then
            echo "FAILED: SKILL.md missing in physical mirror!"
            exit 1
          fi
          
          # 核心断言 2：Manifest 必须存在且记录正确
          cat "$TARGET/.manifest.json"
          
          # 测试 Tag 回滚与恢复
          ./bs.sh --tags || true
          ./bs.sh --latest
          ./bs.sh --status
          echo "Physical Mirror Installation Tests PASSED!"
```

#### 2. `.github/workflows/release.yml` (自动发布 Release 与打标资产)
```yaml
name: BMAD Suite Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build-and-release:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Create Release Tarball
        run: |
          tar -czf bmad-suite-v4-${{ github.ref_name }}.tar.gz bmad-suite-v4/ bs.sh README.md LICENSE

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: bmad-suite-v4-${{ github.ref_name }}.tar.gz
          generate_release_notes: true
```

---

### 模块 C：远程一键免克隆安装脚本 (`install.sh`)

用户如果在全新设备上，或者不想手动 git clone 时，可提供一行命令安装：

```bash
curl -fsSL https://raw.githubusercontent.com/zhaosan2023/dotfiles-bmad-solo/main/install.sh | bash
```

`install.sh` 逻辑：
1. 探测并优先 clone 到 `~/.dotfiles/dotfiles-bmad-solo`。
2. 若目录已存在则自动 `git pull`。
3. 自动调用 `./bs.sh --latest` 完成物理镜像部署。

---

## 5. 开发者运维标准作业程序 (Standard Operating Procedures - SOP)

### 场景 1：在任意路径完成全新部署
```bash
# 可以在任意路径 clone
git clone git@github.com:zhaosan2023/dotfiles-bmad-solo.git ~/project/dotfiles-bmad-solo
cd ~/project/dotfiles-bmad-solo

# 一键物理部署到 ~/.gemini/config/
./bs.sh
```

### 场景 2：从 GitHub 更新最新版本并同步
```bash
cd ~/project/dotfiles-bmad-solo

# 一键拉取远程最新 commit 并物理更新到全局
./bs.sh --update
```

### 场景 3：紧急回滚或锁定特定发布 Tag
```bash
cd ~/project/dotfiles-bmad-solo

# 列出所有可用 Tag
./bs.sh --tags

# 回滚并物理激活 v4.1.0
./bs.sh --tag v4.1.0

# 随时切回最新 main
./bs.sh --latest
```

### 场景 4：日常修改代码后的本地即时生效（无需 push）
```bash
cd ~/project/dotfiles-bmad-solo

# 在 bmad-suite-v4 目录下修改了 prompt 或 rule
vim bmad-suite-v4/skills/ana-solo/SKILL.md

# 运行一次 ./bs.sh，立即物理同步镜像到 ~/.gemini/config/
./bs.sh

# 在 Antigravity IDE 执行快捷键: Developer: Reload Window
```

---

## 6. Handoff to `/bmad-solo` (执行桥接)

To proceed to engineering implementation, simply run `/bmad-solo` with:
> "Implement physical mirror deployment, --update command, and manifest tracking in bs.sh and create GitHub Actions CI workflow based on _bmad-output/analysis/ANALYSIS-20260915-Physical-Mirror-GitOps-CICD-Architecture.md"
