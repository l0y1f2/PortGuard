# PortGuard · 端口 / 进程 / 服务管家

一个为 Windows 开发者做的端口管理工具。灵感来自 macOS 系统设置：界面清爽、信息密度高、操作直接。

## 核心用途

开发时间长了，经常忘了「3306 给的是哪个项目」「8080 被谁占了」。PortGuard 把这件事管起来：

- 自动扫描本机监听的 TCP/UDP 端口、运行中的进程、Windows 服务。
- 端口台账：记录每个端口属于哪个项目、期望被什么进程占用。
- 冲突检测：如果登记的端口被非预期进程占用，首页直接报警。
- 一键操作：结束进程、封禁 / 解封端口。
- 端口分配助手：自动推荐可用端口，避免新项目和旧端口撞车。

## 目录说明

```
PortGuard/
├─ server.py                  # 本地服务入口（Python 标准库 http.server，无第三方 Web 框架）
├─ core/
│  ├─ collector.py            # 端口 / 进程 / 服务采集（psutil 主路径 + PowerShell 兜底）
│  ├─ actions.py              # 结束进程、防火墙封禁 / 解封
│  ├─ registry.py             # 端口台账 JSON 持久化、冲突检测、可用端口推荐
│  └─ portlore.py             # 常见端口 / 进程常识库
├─ web/
│  ├─ index.html              # 主页面
│  ├─ style.css               # Apple 风格样式
│  └─ app.js                  # 前端逻辑
├─ data/
│  └─ registry.json           # 端口台账数据（自动创建）
├─ dist/
│  └─ PortGuard.exe           # 单文件打包程序（双击即用，可拷贝到其他机器）
├─ 启动 PortGuard.bat         # 普通权限启动
├─ 以管理员身份启动.bat       # 管理员启动（可结束任意进程 / 操作防火墙）
└─ README.md
```

## 如何启动

### 方式零（推荐，免安装，可直接拷贝到别的机器）：单文件 EXE

已打包好的单文件程序在 `dist/PortGuard.exe`：

- **双击即可运行**，自动打开浏览器访问 `http://127.0.0.1:8770/`，无需安装 Python 或任何依赖。
- 端口台账数据保存在 EXE **同目录**下的 `data/registry.json`（若放在只读目录如 `C:\Program Files`，会自动改存到 `%APPDATA%/PortGuard`）。
- 退出：点左下角「关于 PortGuard」→「退出 PortGuard」；或直接关闭进程。
- 需要结束系统进程 / 封禁端口：在「关于」弹窗里点「以管理员身份重启」，会弹出 UAC 提权后重新运行。

### 方式一：bat 脚本启动（源码运行）

1. 普通查看 → 双击 `启动 PortGuard.bat`
2. 需要结束系统进程或封禁端口 → 右键 `以管理员身份启动.bat` → 以管理员身份运行

启动后会自动打开浏览器访问 `http://127.0.0.1:8770/`。

### 方式二：命令行

```powershell
C:\Users\zzyy\.workbuddy\binaries\python\envs\default\Scripts\python.exe server.py
```

管理员：

```powershell
# 在管理员 PowerShell 中运行
python server.py
```

## 使用建议

1. **第一次用**：先看「总览」，确认有没有「冲突与提醒」。
2. **把端口记下来**：在「端口」页点击「登记」，填写项目名、用途、期望进程。
3. **日常维护**：新起服务前，到「总览」底部的「要用新端口？让我帮你挑」拿个空闲端口。
4. **权限**：普通权限能查看全部信息。杀系统进程、防火墙操作必须用管理员启动。

## 注意事项

- 服务只监听 `127.0.0.1`，不会暴露到局域网 / 互联网。
- 系统关键进程（System、lsass、csrss 等）禁止结束，防止系统崩溃。
- 防火墙规则统一以 `PortGuard_Block_` 命名，方便在 Windows 防火墙里查找或手动清理。
- 台账数据保存在 `data/registry.json`，可以备份或迁移。

## 技术栈

- 后端：Python 3.13 + `http.server` + `psutil`
- 前端：原生 HTML/CSS/JavaScript，无构建步骤
- 部署：直接运行脚本，无需安装 Node

## 从源码构建 EXE（可选，给自己或其他机器打包）

需要 Python 3.10+ 与 `psutil`、`pyinstaller`：

```powershell
pip install psutil pyinstaller
pyinstaller --noconsole --onefile --name PortGuard --add-data "web;web" server.py
```

构建产物在 `dist/PortGuard.exe`，双击即用。

## 开源信息

- 开发者：李云飞
- 仓库：<http://github.com/l0y1f2>
- 协议：MIT

欢迎提 Issue / PR。
