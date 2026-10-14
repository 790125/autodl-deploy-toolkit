# AutoDL 部署与训练工具链

在 AutoDL（或同类 GPU 云主机）上部署 **ComfyUI 推理环境** 与 **kohya/sd-scripts LoRA 训练环境** 的一组脚本，以及配套的远程运维工具。

起因很实际：本地显卡只有 12GB 显存、内存 16GB，跑不动 LoRA 训练，于是把训练和批量推理搬到云端。云端环境每次重装都要重复一堆事——装依赖、下几十 GB 权重、调进程、盯日志——这些脚本就是把这些重复动作固定下来。

> ⚠️ **本仓库不含任何凭据**。主机、端口、密码全部通过环境变量读取，见 [.env.example](.env.example)。

---

## 这些脚本解决什么问题

| 问题 | 对应脚本 |
|---|---|
| 系统盘只有 30GB，装不下模型和缓存 | `scripts/setup/kohya_setup.sh`、`scripts/setup/remote_h3.sh` |
| 几十 GB 权重下载断流、下完损坏 | `scripts/download/*` |
| `pip install -r requirements.txt` 把 CUDA 版 torch 覆盖掉 | `scripts/setup/kohya_setup.sh` |
| ComfyUI 与训练争抢显存 | `scripts/setup/kohya_setup.sh`、`scripts/service/*` |
| SSH 一断，长任务就死 | 全部脚本统一用 `nohup` / `setsid` + PID 文件 |
| 云端 WebUI 本地打不开 | `scripts/tunnel/*` |
| 重复登录敲同样的诊断命令 | `scripts/remote/*` |

---

## 部署流程

### 1. 环境准备

```bash
export AUTODL_HOST=<你的实例主机>
export AUTODL_PORT=<你的实例 SSH 端口>
export AUTODL_SSH_PASSWORD=<你的密码>
```

仓库里的 Python 脚本都从这三个环境变量读取连接信息。**不要把值写进任何文件。**

### 2. 部署 ComfyUI 推理环境

上传源码包与脚本，然后在实例上执行：

```bash
bash scripts/setup/remote_h3.sh
```

这个脚本按顺序做：

1. 后台**并行**启动全部权重下载（不等第一个下完再下第二个）
2. 建 venv，装**指定版本**的 torch + CUDA
3. 装 ComfyUI 依赖，但**先剔除 torch 系**（见下方「踩坑」第 2 条）
4. 轮询等待所有权重，并**逐字节校验大小**
5. 生成 `start_comfy.sh`
6. 清理 pip 缓存

### 3. 部署 kohya 训练环境

```bash
bash scripts/setup/kohya_setup.sh
```

关键点：**复用已有的 venv 里的 torch，不重装**，只补 kohya 需要的增量依赖。

### 4. 启动训练

```bash
python scripts/train/kohya_start_train.py
```

会同时拉起训练进程和 TensorBoard（独立端口），并把 PID 写入文件，便于后续停止。

### 5. 远程运维

```bash
python scripts/remote/h3_status.py       # 一条命令拿全：磁盘/显存/进程/端口/HTTP 探活/日志尾部
python scripts/remote/h3_cleanup_remote.py   # 清理临时文件 + 权重完整性校验
python scripts/tunnel/h3_tunnel.py       # 把云端 6006 映射到本地，直接开云端 WebUI
```

`h3_tunnel.py` 是手写的 TCP-over-SSH 端口转发（paramiko `direct-tcpip`），不依赖 `ssh -L`，方便在 Windows 下做进程管理和断线重连。

---

## 踩坑记录

这些都是实际遇到过、并在脚本里固化成处理的：

### 1. 系统盘只有 30GB

AutoDL 实例的 `/` 通常只有 30GB，`/root/autodl-tmp` 才是大盘。所以：

- `PIP_CACHE_DIR` 和 `TMPDIR` 全部指向 `autodl-tmp`
- 权重只落 `autodl-tmp`，不落系统盘
- 装完依赖主动 `pip cache purge`
- 训练前清掉数据集里的 `*.npz` 缓存（会重复生成，但很占地方）

### 2. 装依赖会把 CUDA 版 torch 冲掉

`pip install -r requirements.txt` 会按 requirements 里的版本重装 torch，可能把你已经配好的 CUDA 版本覆盖成 CPU 版或别的 CUDA 版本。

处理方式是从 requirements 里把 torch 系整行剔除，再单独装：

```bash
grep -viE '^(torch|torchvision|torchaudio|xformers)([>=< ]|$)' requirements.txt > /tmp/req.txt
pip install -r /tmp/req.txt
```

装完立刻验证，不通过就直接失败退出：

```python
assert torch.cuda.is_available()
```

### 3. 大文件下载必须校验

40GB 级别的权重，下载中断或被镜像截断很常见。脚本里做三件事：

- **`aria2c -c` 断点续传**，`--max-tries=0` 无限重试
- 用 **`.aria2` 临时文件** 判断「是在下载中」还是「已完成」
- 下载完成后**逐字节比对大小**（期望值写死在脚本里）

```bash
if [ -f "$dest" ] && [ ! -f "$dest.aria2" ]; then
  # 文件在，且没有 .aria2 残留 → 认为完整
fi
```

### 4. 国内网络走镜像

- HuggingFace 走 `HF_ENDPOINT=https://hf-mirror.com`
- GitHub 源码准备多个下载源，依次降级：镜像 → 直连 → codeload
- 下载后校验「文件大小 > 1MB」且「解压后关键文件存在」，**不认「命令没报错」**

### 5. 不要用 `pkill -f` 停服务

`pkill -f main.py` 之类的写法有概率把执行这条命令的 shell 一起杀掉。

处理方式是**优先读 PID 文件**，PID 文件不存在时再遍历 `/proc/*/cmdline` 精确匹配：

```python
for pid in os.listdir("/proc"):
    cmd = open(f"/proc/{pid}/cmdline", "rb").read()
    if <精确匹配条件>:
        os.kill(int(pid), signal.SIGTERM)
```

### 6. 显存碎片

训练和推理切换时容易 OOM，统一加：

```bash
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
```

另外训练启动前会主动停掉 ComfyUI（按 PID 文件），把显存让给训练。

### 7. 长任务必须脱离终端

SSH 断线会杀掉前台进程。所有长任务统一：

```bash
setsid nohup <cmd> >> <log> 2>&1 </dev/null &
```

`setsid` + `nohup` + `</dev/null` 三者齐全，才能真正不受 SSH 中断影响。

### 8. 日志要实时

Python 默认缓冲 stdout，重定向到文件后看不到实时进度。统一加：

```bash
export PYTHONUNBUFFERED=1
```

---

## 目录结构

```
.
├── scripts/
│   ├── setup/      环境搭建（在云端实例上执行）
│   ├── download/   模型权重下载与校验
│   ├── train/      训练启动、状态检查、日志查看
│   ├── service/    ComfyUI 服务启动与修复
│   ├── remote/     远程诊断、上传、清理
│   └── tunnel/     SSH 端口转发
├── configs/        训练配置模板（TOML）
├── docs/           文件来源说明
└── .env.example    环境变量模板
```

## 技术栈

`Ubuntu 22.04` · `bash` · `Python` · `paramiko` · `aria2c` · `ComfyUI` · `kohya sd-scripts` · `TensorBoard` · `SSH 隧道`

## 使用注意

- 脚本里的路径（`/root/autodl-tmp/...`）按 AutoDL 的目录约定写死，换平台需要改
- `scripts/setup/*.sh` 在**云端实例**上执行；`scripts/remote/*.py` 和 `scripts/tunnel/*.py` 在**本机**执行
- 本仓库不包含数据集与模型文件

## License

MIT
