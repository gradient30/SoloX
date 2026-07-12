#!/usr/bin/env python3
"""
SoloX 依赖版本验证脚本
验证 pyproject.toml 中的依赖版本是否与测试过的兼容版本一致
"""

import re
import sys
from pathlib import Path


def configure_utf8_stdout() -> None:
    """将可重配置的标准输出切换为 UTF-8，避免旧 Windows 代码页编码失败。

    GitHub Actions 的 Windows Python 3.10 runner 可能使用 CP1252 标准输出；
    本脚本包含中文和状态图标，直接 ``print`` 会抛出
    :class:`UnicodeEncodeError`。UTF-8 是 GitHub Actions 日志与本仓库脚本
    输出的统一编码。无法重配置的自定义输出流保持原状。
    """
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (OSError, ValueError):
            pass


def parse_pyproject_dependencies():
    """解析 pyproject.toml 中 [project].dependencies。"""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"

    if not pyproject_path.exists():
        print("❌ pyproject.toml 文件不存在")
        return None

    with open(pyproject_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"\[project\][\s\S]*?dependencies\s*=\s*\[(.*?)\]"
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        print("❌ 无法找到 [project].dependencies 部分")
        return None

    deps_text = match.group(1)
    deps = []

    for line in deps_text.split("\n"):
        line = line.strip()
        if line.startswith('"') and line.endswith('",'):
            dep = line[1:-2]
            if dep and not dep.startswith("#"):
                deps.append(dep)

    return deps

def check_critical_versions(dependencies):
    """检查关键依赖的版本"""
    critical_deps = {
        'Flask': '2.0.3',
        'Werkzeug': '2.0.3',
        'Jinja2': '3.0.1',
        'Flask-SocketIO': '4.3.1',
        'python-socketio': '4.6.0',
        'python-engineio': '3.13.2',
        'tidevice': '0.9.7'
    }
    
    found_deps = {}
    issues = []
    
    for dep in dependencies:
        if '==' in dep:
            name, version = dep.split('==')
            found_deps[name] = version
        elif '>=' in dep:
            name, version = dep.split('>=')
            found_deps[name] = f">={version}"
        else:
            found_deps[dep] = "latest"
    
    print("🔍 检查关键依赖版本...")
    print("=" * 50)
    
    for name, expected_version in critical_deps.items():
        if name in found_deps:
            actual_version = found_deps[name]
            if actual_version == expected_version:
                print(f"✅ {name:<20} {actual_version}")
            else:
                print(f"❌ {name:<20} {actual_version} (期望: {expected_version})")
                issues.append(f"{name}: 期望 {expected_version}, 实际 {actual_version}")
        else:
            print(f"⚠️ {name:<20} 未找到")
            issues.append(f"{name}: 依赖缺失")
    
    print("=" * 50)
    
    # 显示其他依赖
    other_deps = {k: v for k, v in found_deps.items() if k not in critical_deps}
    if other_deps:
        print("\n📦 其他依赖:")
        for name, version in other_deps.items():
            print(f"   {name:<20} {version}")
    
    return issues

def main():
    configure_utf8_stdout()
    print("🔧 SoloX 依赖版本验证工具")
    print("=" * 40)
    print()

    dependencies = parse_pyproject_dependencies()
    if dependencies is None:
        sys.exit(1)

    print(f"📋 在 pyproject.toml 中找到 {len(dependencies)} 个依赖")
    print()
    
    # 检查关键版本
    issues = check_critical_versions(dependencies)
    
    print()
    if issues:
        print("❌ 发现问题:")
        for issue in issues:
            print(f"   • {issue}")
        print()
        print("建议修复 pyproject.toml 中的依赖版本")
        sys.exit(1)
    else:
        print("🎉 所有关键依赖版本正确！")
        print()
        print("✅ pyproject.toml 依赖验证通过")
        print("✅ 依赖版本与测试兼容版本一致")
        print()
        print("现在可以安全使用:")
        print("  pip install -e .")
        print("  或")
        print("  pip install -r requirements.txt")

if __name__ == "__main__":
    main()
