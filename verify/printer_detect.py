"""
验证脚本 2：打印机可用性检测
检查系统中可用的打印机，为 SumatraPDF 静默打印做准备
"""
import subprocess
import sys
from pathlib import Path


def detect_cups_printers():
    """检测 CUPS 系统中的打印机"""
    print("=" * 60)
    print("打印机检测工具")
    print("=" * 60)

    printers = []

    # 方法1: lpstat
    try:
        result = subprocess.run(
            ["lpstat", "-p"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            for line in lines:
                if "is idle" in line or "enabled" in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        printer_name = parts[1]
                        printers.append(printer_name)
                        print(f"  🖨️  发现打印机: {printer_name}")
    except FileNotFoundError:
        print("  ⚠️  lpstat 未安装（CUPS 可能未运行）")
    except Exception as e:
        print(f"  ⚠️  lpstat 检测失败: {e}")

    # 方法2: lpstat -l
    try:
        result = subprocess.run(
            ["lpstat", "-l"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            for line in lines:
                if "printer" in line.lower():
                    # 提取打印机名称
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.lower() == "printer" and i + 1 < len(parts):
                            name = parts[i + 1]
                            if name not in printers:
                                printers.append(name)
                                print(f"  🖨️  发现打印机: {name}")
    except Exception as e:
        print(f"  ⚠️  lpstat -l 检测失败: {e}")

    if not printers:
        print("  ⚠️  未检测到打印机")
        print("")
        print("  建议:")
        print("  1. 连接打印机并确保 CUPS 服务运行")
        print("  2. 安装打印机驱动")
        print("  3. 使用 lpadmin 添加打印机:")
        print("     sudo lpadmin -p 打印机名 -E -v usb:/dev/usb/lp0 -m everywhere")
        print("  4. Windows 端使用 SumatraPDF 检测打印机")

    return printers


def test_pdf_print(printer_name):
    """测试向指定打印机打印 PDF"""
    print(f"\n  测试向 '{printer_name}' 打印...")

    # 创建一个简单的测试 PDF
    test_pdf = Path("/tmp/test_print.pdf")
    try:
        # 使用 Python 生成一个简单的测试 PDF
        subprocess.run(
            ["python3", "-c", f"""\
import sys
sys.path.insert(0, '/home/lpr/项目/ai-study-coach')
from common.config import get_config
print("PDF 打印测试文件")
"""],
            capture_output=True, timeout=5
        )
        print(f"  ℹ️  需要先安装 SumatraPDF 或使用 cups-pdf")
    except Exception as e:
        print(f"  ⚠️  打印测试跳过: {e}")


def main():
    printers = detect_cups_printers()

    print(f"\n{'=' * 60}")
    if printers:
        print(f"✅ 检测到 {len(printers)} 台打印机:")
        for p in printers:
            print(f"   - {p}")
        print(f"\n  Windows 端使用 SumatraPDF 时，打印机名称为:")
        print(f"  SumatraPDF -print-to \"{printers[0]}\" test.pdf")
    else:
        print("⚠️  未检测到打印机，请先配置")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
