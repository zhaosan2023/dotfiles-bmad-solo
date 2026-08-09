---
name: bmad-dotfiles-sync
description: Automates the backup (Push) and deployment (Restore) of the BMAD-Solo configuration dotfiles. Use when the user wants to "应用/部署 bmad-solo" or "备份 bmad-solo".
---

# bmad-dotfiles-sync 

本技能用于自动处理 BMAD-Solo 全局配置（宪法与技能库）在云端 Git 仓库的备份与跨服务器还原。

## 1. 意图拦截与模式判断
根据用户的指令，判断是进入 **Backup (备份模式)** 还是 **Deploy (还原部署模式)**。
- 触发词如：“备份 bmad-solo”、“同步配置”、“提交更改” -> 进入 **Backup 模式**。
- 触发词如：“应用 bmad-solo”、“部署 bmad-solo”、“新机器还原配置” -> 进入 **Deploy 模式**。

## 2. Deploy (还原部署模式) 工作流

如果在全新的 VPS 上触发还原，请按照以下步骤执行：

1. **信息收集 (自动提问)**
   - 检查用户当前指令是否包含了目标 GitHub 的 **SSH Host (例如 github-dxa)** 和 **用户名**。
   - **如果没有提供，必须停止并向用户提问**：“请提供您的 GitHub SSH Host 和用户名（例如：`github-dxa:zhaosan2023`）”。
2. **克隆配置仓库**
   - 使用用户提供的信息拼接 URL。目标路径必须是：`~/dotfiles-bmad-solo`。
   - 运行：`git clone git@<Host>:<Username>/dotfiles-bmad-solo.git ~/dotfiles-bmad-solo`
3. **建立符号链接映射 (Symlinks)**
   依次执行以下命令完成还原（切勿手动篡改路径）：
   ```bash
   mkdir -p ~/.gemini/config
   ln -sf ~/dotfiles-bmad-solo/GEMINI.md ~/.gemini/GEMINI.md
   ln -sf ~/dotfiles-bmad-solo/config/AGENTS.md ~/.gemini/config/AGENTS.md
   rm -rf ~/.gemini/config/skills
   ln -sf ~/dotfiles-bmad-solo/config/skills ~/.gemini/config/skills
   ```
4. **汇报成功**
   通知用户：“BMAD-Solo 全局配置已成功还原！您可以随时体验极客模式。”

## 3. Backup (备份漫游模式) 工作流

如果用户要求将当前更改同步到云端（漫游），请按照以下步骤执行：

1. **检查目录**
   - 确认 `~/dotfiles-bmad-solo` 或 `~/dotfiles/gemini-bmad-solo` 目录存在。
2. **执行一键推送**
   运行命令实现自动提交与漫游：
   ```bash
   # 优先使用 ~/dotfiles/gemini-bmad-solo (如果存在)
   cd ~/dotfiles/gemini-bmad-solo || cd ~/dotfiles-bmad-solo
   git add .
   git commit -m "chore: auto-sync bmad-solo rules"
   git push
   ```
3. **汇报成功**
   向用户反馈同步结果及推送了多少变更。
