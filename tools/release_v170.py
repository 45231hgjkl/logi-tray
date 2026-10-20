#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发布 v1.7.0：安装方式从「解压 + 批处理」改为标准的 Setup 安装程序。

本版的核心变化只有一个：**分发包从 .zip 换成 Inno Setup 编译的 -setup.exe**。
三个版本的功能本身没有改动，但安装与卸载体验完全不同：

- 双击安装包按向导安装，全程不弹 UAC（装到 %LOCALAPPDATA%\\Programs\\<app>）；
- 在「设置 → 应用」里有正规的卸载登记，开始菜单里也有「卸载 …」入口；
- 安装器会先检测 .NET 8 桌面运行时，缺失时引导下载，而不是等程序启动后莫名退出；
- 安装完成自动启动，并把新增的托盘图标从 Windows 11 的折叠区提出来；
- 卸载会退出进程、清自启项、快捷方式、程序文件与托盘注册记录，保留用户配置。

为什么必须升版本号：
    三个包原来的版本号是 1.2.3 / 1.2.2 / 1.2.2，和 v1.6.0 完全相同。若不升，
    已装用户点「检查更新」比出来的结果是「已是最新」，永远收不到这版安装包。
    因此三个版本各前进一位：1.2.4 / 1.2.3 / 1.2.3。

为什么资产名也换了：
    应用内的「检查更新」按 `{前缀}-v{版本}-setup.exe` 解析资产名。旧的 .zip 资产
    不参与比较，因此老发布页上残留的 zip 不会把用户引回「解压再跑批处理」的旧包。
    tools/readme_vs_latest.py 也已同步为只认 -setup.exe。

为什么默认先建草稿、要显式 --publish 才公开：
    上传资产是多步操作，中途失败会留下一个「公开但缺包」的发布页，而
    /releases/latest 会立刻指向它、README 承诺的文件却下载不到。

用法：
    python tools/release_v170.py              # 建/更新为草稿并上传资产
    python tools/release_v170.py --publish    # 同上，并转成公开
"""
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

REPO = "yixing233/logi-tray"
TAG = "v1.7.0"
TITLE = "v1.7.0 · 改用标准安装程序（Setup.exe），不再需要解压与批处理"
PROXY = "http://127.0.0.1:7890"

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RELEASE_DIR = os.path.join(REPO_DIR, "release")
README = os.path.join(REPO_DIR, "README.md")
ASSETS = [
    "logi-tray-v1.2.4-setup.exe",
    "logi-tray-lite-v1.2.3-setup.exe",
    "multi-tray-v1.2.3-setup.exe",
]


def token() -> str:
    p = subprocess.run(["git", "credential", "fill"],
                       input="protocol=https\nhost=github.com\n\n",
                       capture_output=True, text=True, cwd=REPO_DIR)
    for line in p.stdout.splitlines():
        if line.startswith("password="):
            return line[len("password="):]
    raise SystemExit("no token: " + p.stdout + p.stderr)


TOKEN = token()


def _open(req):
    """先直连再走代理：这台机器上 7890 有时是唯一出口，但代理本身也可能不通，
    两条路都试并把各自的错误都报出来，否则只会看到「连不上」，分不出是墙、
    是代理挂了、还是 token 失效。"""
    last = None
    for proxies in ({}, {"https": PROXY, "http": PROXY}):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler(proxies))
        try:
            return opener.open(req, timeout=600)
        except urllib.error.HTTPError:
            raise
        except Exception as e:  # noqa: BLE001
            last = e
    raise last


def api(method, path, body=None, raw=None, ctype="application/json"):
    url = path if path.startswith("http") else "https://api.github.com" + path
    data = raw if raw is not None else (json.dumps(body).encode() if body else None)
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("User-Agent", "multi-tray-release")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Authorization", "token " + TOKEN)
    if data:
        req.add_header("Content-Type", ctype)
    try:
        with _open(req) as resp:
            b = resp.read()
            return resp.status, (json.loads(b.decode()) if b else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


NOTES = """## v1.7.0 · 改用标准安装程序

**三个版本的功能没有改动**，变的是安装方式。以前是下载 zip、解压、双击
`一键安装.bat`；现在双击一个 `*-setup.exe` 走标准安装向导。

### 🎁 安装体验

| | 旧（v1.6.0 及以前） | 新（v1.7.0） |
| --- | --- | --- |
| 安装 | 解压后双击 `一键安装.bat` | 双击 `*-setup.exe`，向导点下一步 |
| 卸载 | 运行包内 `卸载.bat` | 开始菜单「卸载 …」或「设置 → 应用」 |
| 卸载登记 | 无 | ✅ 正规登记，可被系统识别 |
| .NET 检测 | 批处理里做 | 安装器里做，缺失时引导下载 |
| 静默部署 | 不支持 | `/VERYSILENT /NORESTART` |
| 安装日志 | 无 | `/LOG=路径` |

共同点：**都不需要管理员权限**，都装到 `%LOCALAPPDATA%\\Programs\\<app>`，
三个版本仍然可以同时安装、同时运行、分别卸载。

安装器还会在结束时把新增的托盘图标从 Windows 11 的折叠区里提出来 ——
以前图标默认蜷在 `^` 里，很多人会以为「装完没反应」。

### 🔢 版本号

功能没变但必须升版本号：原来的 1.2.3 / 1.2.2 / 1.2.2 与 v1.6.0 相同，
不升的话已装用户点「检查更新」只会看到「已是最新」，永远收不到这版新包。

| 版本 | 上一版 | 本版 |
| --- | --- | --- |
| 完整版 `logi-tray` | 1.2.3 | **1.2.4** |
| 轻量版 `logi-tray-lite` | 1.2.2 | **1.2.3** |
| 多品牌版 `multi-tray` | 1.2.2 | **1.2.3** |

### 📦 下载

| 文件 | 大小 | 内存占用（空闲） | 适合 |
| --- | --- | --- | --- |
| `logi-tray-v1.2.4-setup.exe` | 约 2.9 MB | 工作集 63 MB / 提交 15 MB | 完整版：亚克力毛玻璃 + 三种图标样式 |
| `logi-tray-lite-v1.2.3-setup.exe` | 约 2.6 MB | 工作集 51 MB / 提交 12 MB | 轻量版：只要电量数字，占用尽可能低 |
| `multi-tray-v1.2.3-setup.exe` | 约 2.6 MB | 工作集 61 MB / 提交 15 MB | 多品牌版：键鼠耳机多台不同品牌 |

安装包比原来的 zip 大，是因为安装器本身带了中文向导、卸载程序与图标资源，
**程序文件体积没有变化**。需要 **.NET 8 桌面运行时**（安装器会自动检测并引导下载）。

> **三个版本各自独立编号**，同一次发布里三个包的版本号互不相同
> （本次是 `1.2.4` / `1.2.3` / `1.2.3`）。应用内的「检查更新」比的是
> **你自己那一版**的最新包，不是这个 tag。
>
> 内存为**实测空闲值**（启动后不打开任何窗口，等待 9 秒稳定）。

### 🔄 从旧版本升级

直接运行新的安装包即可：安装位置会被记住，配置与历史记录都在
`%LOCALAPPDATA%\\<app>` 下，不受影响。

如果旧版是用 `一键安装.bat` 装的，安装器会自动关掉正在运行的旧进程，
并清理旧的开始菜单快捷方式，不会出现两个同名入口。

### ⚠️ 协议来源与验证范围

| 品牌 | 实现依据 | 实机验证 |
| --- | --- | --- |
| 罗技 | 本项目 native HID++ 读取器（5 条特性回退） | ✅ 实机稳定读到 |
| 迈从 MCHOSE | [同型号开源实现](https://github.com/rafagfran/mchose-v9-pro-battery-tray) | ✅ 电量实机读到；充电状态经**双向采样校准** |
| ATK Z87 键盘 | 官方网页驱动 `hub.atk.pro` v3.2.27 的 WebHID 抓包 | ✅ 实机读到电量与充电位，**20/20** |

协议解析层共 **251 项合成帧单测**（无需硬件）。本版新增了针对分发形式变更的
回归用例：旧的 `.zip` 资产**不参与**「有没有新版本」的判断，确保不会把用户
引回需要解压再跑批处理的旧包。

### 命令行

```bat
multi-tray.exe --list             :: 列出检测到的设备与当前电量（休眠的会带上次电量）
multi-tray.exe --check-update     :: 检查更新，打印本版资产版本号与比较结果
multi-tray.exe --diag-atk         :: 排查 ATK 设备（打印原始收发字节）
multi-tray.exe --diag-mchose      :: 排查迈从耳机的状态字节（watch 模式每秒采样一次）
multi-tray.exe --test-protocols   :: 运行协议解析层自检（无需硬件）
```

### 已知限制

- 同一型号的多台设备会合并为一条显示（去重按 VID/PID/产品名）
- ATK 各型号 Report ID 不统一，本版只对 Z87 完成验证
- 多品牌版刻意不提供续航预测与历史图表，只有电量显示与低电量预警
- 迈从的「已充满」档（`0x01`/`0x03`）尚未观测到，未做映射
- ATK 协议 1 与协议 2 的应答里没有充电位，这两路的充放电状态显示为「充电状态未知」

---

[README](https://github.com/yixing233/logi-tray#readme) · GPL-3.0
"""


def readme_names() -> list:
    with open(README, encoding="utf-8") as f:
        text = f.read()
    names = re.findall(r"`((?:logi-tray|multi-tray)[A-Za-z0-9._-]*-setup\.exe)`", text)
    return sorted({n for n in names if re.search(r"-v\d+\.\d+", n)})


def main(argv) -> int:
    publish = "--publish" in argv

    # 资产先在本地说清楚：README 承诺的三个包与接下来要上传的三个包必须同名，
    # 否则「发布成功」只是把不一致固化到线上。
    promised = readme_names()
    print("=== README 承诺的下载文件 ===")
    for n in promised:
        print(f"   {'[本地有]' if os.path.exists(os.path.join(RELEASE_DIR, n)) else '[本地缺]'} {n}")
    if promised != sorted(ASSETS):
        print(f"\nREADME 承诺 {promised}")
        print(f"本次上传   {sorted(ASSETS)}")
        print("两者不一致 —— 先统一再发布。")
        return 1

    print(f"\n=== 本地包 === ({RELEASE_DIR})")
    for name in ASSETS:
        path = os.path.join(RELEASE_DIR, name)
        if not os.path.exists(path):
            print(f"   [缺失] {name} —— 先跑 python tools/package_release.py")
            return 1
        print(f"   {name:<28} {os.path.getsize(path)/1024:>7.0f} KB")

    # 草稿没有真 tag（GitHub 先给 `untagged-<hash>`，转公开时才打上 TAG），
    # 所以先按 tag 查、查不到再列全部 release 按 tag_name 找。否则重跑本脚本
    # 会把已存在的草稿当成不存在 → POST 同名 tag → 422 already_exists。
    status, rel = api("GET", f"/repos/{REPO}/releases/tags/{TAG}")
    if status != 200:
        _, all_rel = api("GET", f"/repos/{REPO}/releases?per_page=100")
        hit = next((r for r in (all_rel or []) if r.get("tag_name") == TAG), None)
        if hit is None:
            # 草稿的 tag_name 是 `untagged-<hash>` 占位串，按真 tag 永远匹配不到。
            # 只按 tag_name 找的话，重跑本脚本会把第一次留下的草稿当成「不存在」，
            # 于是再 POST 一个，线上就出现两个 v1.7.0（本次发布实际踩到了）。
            # 因此退回「按标题找同名草稿」：标题里带 TAG 前缀即可认定是同一版。
            hit = next(
                (r for r in (all_rel or [])
                 if r.get("draft") and str(r.get("name", "")).startswith(TAG)),
                None,
            )
            if hit is not None:
                print(f"找到同名草稿（tag_name={hit['tag_name']!r}），复用而不是新建")
        status, rel = (200, hit) if hit else (status, rel)
    if status == 200:
        print(f"\nrelease 已存在: {rel['html_url']}")
        print(f"  当前状态: draft={rel['draft']} prerelease={rel['prerelease']}")
        rid = rel["id"]
        st, _ = api("PATCH", f"/repos/{REPO}/releases/{rid}", {"name": TITLE, "body": NOTES})
        print(f"  说明已刷新 ({st})")
    else:
        print(f"\n创建 release {TAG}（草稿）…")
        status, rel = api("POST", f"/repos/{REPO}/releases",
                          {"tag_name": TAG, "name": TITLE, "body": NOTES,
                           "draft": True, "prerelease": False})
        if status not in (200, 201):
            print(f"创建失败 {status}: {rel}")
            return 1
        rid = rel["id"]
        print(f"  已创建: {rel['html_url']}")

    _, fresh = api("GET", f"/repos/{REPO}/releases/{rid}/assets")
    existing = {a["name"]: a["id"] for a in (fresh or [])}
    print(f"\n现有资产: {list(existing)}")

    for name in ASSETS:
        path = os.path.join(RELEASE_DIR, name)
        if name in existing:
            st, _ = api("DELETE", f"/repos/{REPO}/releases/assets/{existing[name]}")
            print(f"  删除旧资产 {name} ({st})")
        with open(path, "rb") as f:
            payload = f.read()
        upload = (f"https://uploads.github.com/repos/{REPO}/releases/{rid}/assets"
                  f"?name={urllib.parse.quote(name)}")
        st, res = api("POST", upload, raw=payload, ctype="application/octet-stream")
        print(f"  {'上传成功' if st in (200, 201) else f'上传失败 {st}'} {name}"
              f"  {len(payload)/1024:.0f} KB")
        if st not in (200, 201):
            print(f"    {str(res)[:250]}")

    _, final = api("GET", f"/repos/{REPO}/releases/{rid}/assets")
    got = sorted(a["name"] for a in (final or []))
    print(f"\n=== {TAG} 资产核对 ===")
    for a in (final or []):
        print(f"  {a['name']:<30} {a['size']/1024/1024:.2f} MB")
    if got != sorted(ASSETS):
        print(f"\n资产与预期不符：实际 {got} 期望 {sorted(ASSETS)} —— 不自动公开。")
        return 1
    print("三个资产一致 [OK]")

    if publish:
        # 必须带上 tag_name：草稿的 tag_name 是 `untagged-<hash>` 占位串，
        # 只改 draft 会把占位串原样留在发布页上（v1.5.0 就是这么挂掉的）。
        st, upd = api("PATCH", f"/repos/{REPO}/releases/{rid}",
                      {"draft": False, "prerelease": False, "tag_name": TAG})
        if st != 200:
            print(f"\n转公开失败 {st}: {upd}")
            return 1
        print(f"\n已公开: {upd['html_url']}")
        print(f"  tag_name = {upd['tag_name']!r}")
        if upd["tag_name"] != TAG:
            print(f"  !! tag_name 不是 {TAG!r} —— 跑 python tools/attach_release_tag.py --fix")
            return 1
    else:
        print(f"\n当前仍是草稿。核对后执行：")
        print(f"  python tools/release_v170.py --publish")
        print(f"  python tools/readme_vs_latest.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
