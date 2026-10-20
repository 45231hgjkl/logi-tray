"""Build all editions of logi-tray and package each one as a Windows setup program.

Usage:
    python tools/package_release.py

Produces three independent Setup executables, so users pick the edition they want:
    release/logi-tray-vX.Y.Z-setup.exe        full edition (WPF + acrylic, 3 icon styles)
    release/logi-tray-lite-vX.Y.Z-setup.exe   lightweight edition (WinForms, number icon)
    release/multi-tray-vX.Y.Z-setup.exe       multi-brand edition (Logitech / MCHOSE / ATK)

安装方式改用 Inno Setup 编译 setup/*.iss 得到的单文件安装程序：双击即装、
全程不弹 UAC（装到 %LOCALAPPDATA%\\Programs\\<app>），在「应用和功能」里有
正规的卸载登记，支持 /SILENT 与 /LOG=... 便于排查。
不再生成「一键安装.bat / 卸载.bat」：批处理无法登记卸载项、无法静默部署，
也无法在程序运行中安全替换文件。

编译机需要 Inno Setup 6（winget install JRSoftware.InnoSetup）。
ISCC 路径见 ISCC_CANDIDATES，也可用环境变量 INNO_SETUP_DIR 指定。

版本号取自各自的 csproj（三者独立编号，互不相同），发布脚本再按这些名字
去 release/ 取包上传 —— 所以改了 csproj 的 <Version> 就必须重跑本脚本。
"""
import os
import re
import shutil
import subprocess

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RELEASE = os.path.join(REPO, "release")
SETUP = os.path.join(REPO, "setup")

# Inno Setup 的命令行编译器。找不到就明确报错，不要去猜用户机器上的路径。
ISCC_CANDIDATES = [
    os.environ.get("INNO_SETUP_DIR", ""),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6"),
    r"C:\Program Files (x86)\Inno Setup 6",
    r"C:\Program Files\Inno Setup 6",
]


def csproj_version(path):
    with open(path, encoding="utf-8") as f:
        m = re.search(r"<Version>([^<]+)</Version>", f.read())
    return m.group(1) if m else "0.0.0"


FULL_VER = csproj_version(os.path.join(REPO, "wpf", "MouseBatteryTray.csproj"))
LITE_VER = csproj_version(os.path.join(REPO, "lite", "LogiTrayLite.csproj"))
MULTI_VER = csproj_version(os.path.join(REPO, "multi", "MultiTray.csproj"))
print(f"full version = {FULL_VER}")
print(f"lite version = {LITE_VER}")
print(f"multi version = {MULTI_VER}")

USAGE_FULL = r"""{title} v{version} · 使用说明
==================================================

【两个版本怎么选】
  完整版   logi-tray        带亚克力毛玻璃效果，支持三种托盘图标样式与主题切换。
  轻量版   logi-tray-lite   纯 WinForms 实现，内存占用显著更低，托盘图标固定为数字样式。
  两者数据目录相互独立，可同时安装、同时运行。

【快速开始】
  1. 双击安装包（如 logi-tray-vX.Y.Z-setup.exe），按向导点「下一步」（无需管理员权限）
  2. 托盘图标即刻出现在任务栏右下角
  3. 若图标被折叠，点击任务栏的 ^ 箭头即可看到

【日常操作】
  · 左键点击托盘图标    展开电量详情卡片
  · 右键点击托盘图标    打开菜单（详情 / 设置 / 图标样式 / 外观主题 / 退出）

【设置中心】
  · 电量阈值与提醒      自定义低电量与严重低电量阈值，可开关桌面通知
  · 托盘图标样式        电池胶囊 / 环形进度 / 纯数字
  · 外观主题            跟随系统 / 浅色模式 / 深色模式
  · 亚克力效果          可关闭改用纯色底板，兼顾性能
  · 开机自动启动        仅写入当前用户注册表
  · 后台刷新间隔        10 秒 ~ 2 分钟

【安装位置】
  程序装在 %LOCALAPPDATA%\Programs\{app}；
  配置与历史记录在 %LOCALAPPDATA%\{data}（卸载时保留）。

【常见问题】
  Q: 显示「设备离线或休眠」？
  A: 鼠标长时间未操作会进入休眠，动一下鼠标即可恢复读数。

  Q: 提示缺少 .NET 8？
  A: 安装程序会先检测运行时；缺失时会引导你打开微软官方的
     .NET Desktop Runtime 8.0（Windows x64，免费）下载页，
     装好后重新运行安装包即可。

  Q: 怎么卸载？
  A: 开始菜单 → {title} → 「卸载 {title}」，
     或「设置 → 应用 → 已安装的应用」里找到它。
"""

USAGE_LITE = r"""{title} v{version} · 使用说明
==================================================
【这个版本是什么】
  轻量版：纯 WinForms 实现，不加载 WPF 渲染栈，
  因此内存占用显著低于完整版。代价是界面为朴素风格，没有亚克力效果，
  托盘图标固定为纯数字样式。

  需要亚克力毛玻璃与三种图标样式，请改用完整版 logi-tray。

【快速开始】
  1. 双击安装包（如 logi-tray-vX.Y.Z-setup.exe），按向导点「下一步」（无需管理员权限）
  2. 托盘图标即刻出现在任务栏右下角
  3. 若图标被折叠，点击任务栏的 ^ 箭头即可看到

【日常操作】
  · 左键点击托盘图标    展开电量详情卡片
  · 右键点击托盘图标    打开菜单（显示详情 / 设置 / 退出）

【设置】
  · 电量阈值与提醒      自定义低电量与严重低电量阈值，可开关桌面通知
  · 开机自动启动        仅写入当前用户注册表
  · 后台刷新间隔        10 秒 ~ 2 分钟
  · 关于                查看版本、作者、开源协议，并检查更新

【外观】
  自动跟随 Windows 的浅色 / 深色应用主题，无需手动切换。

【安装位置】
  程序装在 %LOCALAPPDATA%\Programs\{app}；
  配置与历史记录在 %LOCALAPPDATA%\{data}（卸载时保留）。

【常见问题】
  Q: 显示「设备离线或休眠」？
  A: 鼠标长时间未操作会进入休眠，动一下鼠标即可恢复读数。

  Q: 托盘图标可以换成电池或环形吗？
  A: 轻量版只提供数字样式；如需切换请使用完整版。

  Q: 提示缺少 .NET 8？
  A: 安装程序会先检测运行时；缺失时会引导你打开微软官方的
     .NET Desktop Runtime 8.0（Windows x64，免费）下载页，
     装好后重新运行安装包即可。

  Q: 怎么卸载？
  A: 开始菜单 → {title} → 「卸载 {title}」，
     或「设置 → 应用 → 已安装的应用」里找到它。
"""

USAGE_MULTI = r"""{title} v{version} · 使用说明
==================================================

【这个版本是什么】
  多品牌版：在同一个托盘图标里显示键盘、鼠标、耳机等多台设备的电量。
  支持罗技、迈从 MCHOSE，以及 ATK / VXE / VGN。

  与另外两个版本的区别：
    完整版 / 轻量版  logi-tray、logi-tray-lite   仅支持罗技设备
    多品牌版         multi-tray                  支持上述多家品牌，多设备同屏

  本版本只做两件事：显示电量、低电量预警。
  不含续航预测与历史曲线。

【多设备时托盘显示哪一台】
  显示**电量最低**的那台在线设备，一眼就能看到最需要充电的设备。
  右上角的小圆点表示「还有其它设备」，鼠标移到图标上可看到全部设备。

【快速开始】
  1. 双击安装包（如 logi-tray-vX.Y.Z-setup.exe），按向导点「下一步」（无需管理员权限）
  2. 托盘图标即刻出现在任务栏右下角
  3. 若图标被折叠，点击任务栏的 ^ 箭头即可看到

【日常操作】
  · 左键点击托盘图标    查看各设备电量列表
  · 右键点击托盘图标    打开菜单（查看设备 / 立即刷新 / 设置 / 退出）

【设置】
  · 电量阈值与提醒      自定义低电量与严重低电量阈值，可开关桌面通知
  · 后台刷新间隔        10 秒 ~ 2 分钟
  · 启用的设备来源      可单独关闭某个品牌，避免对其反复探测
  · 开机自动启动        仅写入当前用户注册表

【已经实测读到的设备】
  罗技 PRO X Wireless 鼠标   稳定读出
  迈从 MCHOSE V9 PRO 耳机    协议已校准（充电 / 放电状态可区分）
  ATK Z87 键盘               协议已破解，实测 100% / 充电中，20 次连测全部成功

【休眠后会显示什么】
  设备休眠时，主数字位显示 --（表示「此刻读不到」，绝不显示推算值），
  下方小字显示休眠前的最后一次电量，例如「上次 77% · 2 小时前」。
  这些历史只用于显示，不参与排序，也不触发低电量提醒 ——
  拿旧电量报警会误导你去找一根并不需要的线。

【命令行】
  multi-tray.exe --list             列出检测到的设备与当前电量
  multi-tray.exe --test-protocols   运行协议解析层自检（无需硬件）
  multi-tray.exe --check-update     检查更新，并打印本版资产版本号与比较结果
                                    （退出码 0=已是最新、1=有新版本、2=网络不可达）
  multi-tray.exe --diag-atk         打印 ATK 键盘协议的探测过程
  multi-tray.exe --diag-mchose      打印迈从耳机的探测过程

【安装位置】
  程序装在 %LOCALAPPDATA%\Programs\{app}；
  配置与历史记录在 %LOCALAPPDATA%\{data}（卸载时保留）。

【常见问题】
  Q: 某台设备一直显示「已休眠 / 离线」？
  A: 无线设备长时间不用会休眠。动一下鼠标、按一下键盘，
     或重新连接耳机后点「立即刷新」即可。

  Q: 换了个 USB 口之后就读不到了？
  A: 迈从与 ATK 的设备标识是 HID 接口路径，换口会变，
     原先记下的「上次电量」就对不上了（主电量显示不受影响）。
     罗技设备按型号识别，不受换口影响。

  Q: 读不到我的设备怎么办？
  A: 这两家使用厂商私有协议，不同型号的指令可能不同。本版本已内置
     实测验证过的协议，但仍可能有个别型号不兼容。
     请运行 multi-tray.exe --list 并把输出反馈给作者。

  Q: 会不会显示一个猜测的电量？
  A: 不会。读不到就显示 --，绝不显示推算值。
     罗技设备若由只报档位或电压的特性读出，会明确标注「推算」。

  Q: 为什么应用里显示的版本号和下载页的 tag 不一样？
  A: 三个版本各自独立编号，一次发布的 tag（如 v1.4.0）统一，
     但每个包的版本号各自演进。应用内的「检查更新」比的是
     你自己那一版的最新包，所以不会出现「已经是新的还一直提示更新」。

  Q: 提示缺少 .NET 8？
  A: 安装程序会先检测运行时；缺失时会引导你打开微软官方的
     .NET Desktop Runtime 8.0（Windows x64，免费）下载页，
     装好后重新运行安装包即可。

  Q: 怎么卸载？
  A: 开始菜单 → {title} → 「卸载 {title}」，
     或「设置 → 应用 → 已安装的应用」里找到它。
"""


EDITIONS_USAGE = {
    "logi-tray": USAGE_FULL,
    "logi-tray-lite": USAGE_LITE,
    "multi-tray": USAGE_MULTI,
}


def find_iscc():
    """Locate Inno Setup's command line compiler."""
    for base in ISCC_CANDIDATES:
        if not base:
            continue
        exe = os.path.join(base, "ISCC.exe")
        if os.path.isfile(exe):
            return exe
    raise SystemExit(
        "找不到 Inno Setup 6 的 ISCC.exe。\n"
        "装一下：winget install JRSoftware.InnoSetup\n"
        "或用环境变量 INNO_SETUP_DIR 指向安装目录。"
    )


def build(project_rel):
    r = subprocess.run(["dotnet", "build", project_rel, "-c", "Release", "-v", "minimal"],
                       cwd=REPO, capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        print(f"  BUILD FAILED for {project_rel}")
        print(r.stdout[-1500:])
        return False
    print(f"  built {project_rel}")
    return True


def write_readme(app, version):
    """Materialise the per-edition 使用说明.txt that the installer ships.

    生成物放在 setup/readme/ 下而不是直接塞进 bin，安装工程按需引用：
    这样同一份说明既能被 Inno 装进程序目录，也能被本脚本重跑时覆盖更新。
    """
    os.makedirs(os.path.join(SETUP, "readme"), exist_ok=True)
    path = os.path.join(SETUP, "readme", app + ".txt")
    text = EDITIONS_USAGE[app].format(title=app, app=app, data=app, version=version)
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(text)
    return path


def compile_setup(iscc, iss_name, version):
    """Compile one Inno Setup project. Returns the produced setup path."""
    iss = os.path.join(SETUP, iss_name)
    # 版本号从 csproj 读出来再传进去：入口 .iss 里的默认值只是给手工编译用的，
    # 打包脚本不能依赖它，否则改了 csproj 却忘了改 .iss 就会静默发出旧版本号。
    r = subprocess.run([iscc, "/Qp", f"/DAppVersion={version}", iss], cwd=REPO,
                       capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        print(f"  ISCC FAILED for {iss_name}")
        print((r.stdout or "")[-2000:])
        raise SystemExit(1)
    return True


os.makedirs(RELEASE, exist_ok=True)
ISCC = find_iscc()
print(f"ISCC = {ISCC}")

EDITIONS = [
    # (显示名, app 名, csproj, 安装工程, 使用说明)
    ("full edition",  "logi-tray",      os.path.join("wpf", "MouseBatteryTray.csproj"),
     "logi-tray.iss"),
    ("lite edition",  "logi-tray-lite", os.path.join("lite", "LogiTrayLite.csproj"),
     "logi-tray-lite.iss"),
    ("multi-brand edition", "multi-tray", os.path.join("multi", "MultiTray.csproj"),
     "multi-tray.iss"),
]

produced = []
for label, app, project, iss_name in EDITIONS:
    print(f"\n=== {label} ===")
    if not build(project):
        raise SystemExit(1)

    version = csproj_version(os.path.join(REPO, project))
    write_readme(app, version)
    compile_setup(ISCC, iss_name, version)

    setup_exe = os.path.join(RELEASE, f"{app}-v{version}-setup.exe")
    if not os.path.isfile(setup_exe):
        print(f"  MISSING: {setup_exe}")
        raise SystemExit(1)
    produced.append(setup_exe)
    print(f"  setup: {os.path.basename(setup_exe)}  {os.path.getsize(setup_exe)/1024:.0f} KB")

print("\n=== summary ===")
for exe in produced:
    print(f"  {os.path.basename(exe)}  {os.path.getsize(exe)/1024:.0f} KB")
