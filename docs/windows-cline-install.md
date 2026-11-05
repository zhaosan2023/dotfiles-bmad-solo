# Windows 10：Cline 轻量自举与交互菜单

此入口把方法论文件部署到当前用户的 `.cline`，优先使用本地套件，缺失时远程下载。不安装 Cline 扩展、不配置 MCP、不修改 IDE 设置，也不复制项目 `AGENTS.md` 或事实、任务文档。Antigravity IDE 中 Cline 的实际加载仍需在目标机器核对。

## 使用

在 Windows PowerShell 5.1 中，可免克隆运行以下入口。远程执行前应确认信任仓库及脚本内容；`main` 是可变分支，不是经过摘要绑定的冻结发行包。本地未发布的改动不会出现在远程入口。

```powershell
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
irm 'https://raw.githubusercontent.com/zhaosan2023/dotfiles-bmad-solo/main/install-win10.ps1' | iex
```

无参数运行直接展示菜单；使用 `Read-Host` 读取一次数字，回车默认选择 1，操作完成即返回，不循环、不关闭当前 PowerShell 会话。非法选择报错，不执行安装。

- `[1] 一键安装 (Install)`
- `[2] 完美卸载 (Uninstall)`
- `[3] 健康检查 (Status/Check)`
- `[0] 退出 (Exit)`

也可以下载脚本到本地后运行。以下假设仓库位于当前用户目录下；若不是，修改 `$repo` 为实际绝对路径。

```powershell
$repo = Join-Path $env:USERPROFILE 'dotfiles-bmad-solo'
$installer = Join-Path $repo 'install-win10.ps1'
& $installer
& $installer -Action Install -WhatIf
& $installer -Action Install
& $installer -Action Status
& $installer -Action Uninstall -WhatIf
& $installer -Action Uninstall
```

`-Action Check` 等同于 `Status`；`-Action Exit` 直接返回。显式 `-SourcePath` 指定本地套件目录时，缺失或无效即报错，不静默改用远程来源。不需要管理员权限、Python、Git、WSL 或旧 ZIP 构建器；不修改系统执行策略。若系统策略阻止脚本，按本机策略处理，不自动降低安全设置。

## 远程自举

安装优先读取脚本所在目录的 `bmad-suite-v4`；通过 `irm | iex` 执行而无脚本目录时，读取当前目录的同名套件。默认套件不存在时，使用原生 `Invoke-RestMethod` 下载 GitHub `main.zip` 到 `$env:TEMP` 下新建的唯一目录，再用 `Expand-Archive` 解压，验证套件及目标路径后安装。

下载、解压或安装成功和普通失败均进入 `finally`，删除本次拥有的临时 ZIP 和解压目录，并恢复脚本调整的 TLS 设置；不删除整个 TEMP。进程强制终止不能保证执行清理，清理异常会报错，不伪称成功。离线部署需提供完整本地套件。

## 文件范围

目标根为 `$env:USERPROFILE\.cline`，不存在时创建：

- `rules\bmad-router.md`：路由副本，套件链接改为部署后的相对路径。
- `bmad-solo\resources\bmad-constitution.md`：公共宪法副本，终端章节适配 Windows。
- `skills\ana-solo\`：完整技能文件，包括引用文档。
- `skills\bmad-solo\`：从套件 `skills\bmad\` 复制完整技能文件，包括文档和脚本；跨技能链接随目录改名调整。

原套件不改写。已有目标文件先全部备份到 `.cline\bmad-solo\backups\<时间与唯一标识>\`，再逐文件覆盖；非同名文件不删除。备份失败即停止，安装失败保留备份并提示可能存在部分复制，不承诺事务回滚或并发写入保护。安装时不要并行运行另一个安装器或编辑同名文件。

检测到已有受管部署记录时停止，须单独迁移；链接路径、目录占用目标文件路径、只读同名文件也停止，不自动修复。

## 卸载与健康检查

卸载删除文件范围中的路由、宪法以及两个完整技能目录，不恢复旧备份。技能目录内的额外文件也会删除；其他规则、技能与 IDE 设置保留。检测到受管部署记录时仍停止，不接管旧部署；删除前检查目标树，拒绝链接路径。

若 `.cline\bmad-solo\backups` 存在，删除规则与技能后主动询问：

> BMAD 规则与技能已全部卸载！是否连同历史备份目录一并彻底删除？[Y/N] (默认 N):

- 输入 `Y` 或 `y`：物理删除历史备份；随后仅当 `bmad-solo` 为空时删除该目录。
- 输入 `N`、回车或其他内容：保留历史备份，打印完整留存路径。
- 空的 `resources` 子目录可删除；仍包含无关文件的目录保留。历史备份删除不可撤销。

健康检查逐项输出 `[OK]` / `[MISSING]`，检查路由、宪法、两个技能目录及其 `SKILL.md` 的存在和路径类型；不下载、不写文件。文件存在不证明内容正确或 Cline 已加载。

## 验证边界

- `-WhatIf` 在安装批准点前返回，不下载、不解压、不创建目录、备份或安装文件；卸载预览不删除文件，也不询问删除备份。
- 当前 Linux 工作区没有 PowerShell，源码回归不等于 PowerShell 5.1 语法或安装运行通过。
- 在目标 Cline 中核对规则启用及两个技能的发现情况，再开启新任务核对 Plan/Act 路由。磁盘复制不证明自动技能调用、权限隔离或硬门禁生效。
- `AGENTS.md` 属于实际目标项目，不把本套件仓库的项目入口复制成全局规则。`solo-distill-mcp` 不在本次安装范围。
- 旧 `scripts/build-win10-cline-package.py` 的冻结 ZIP 安装协议与新入口不同；保留其旧载荷检查，但遇到轻量脚本时明确拒绝构建，不生成不兼容安装包。直接使用脚本的本地或远程菜单入口。
