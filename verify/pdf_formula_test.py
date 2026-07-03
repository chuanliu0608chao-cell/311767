"""
验证脚本 1：Playwright + KaTeX 公式PDF渲染测试
验证HTML含数学公式能否正确渲染为PDF
"""
import asyncio
import sys
from pathlib import Path


async def test_pdf_render():
    """使用 Playwright 渲染含 KaTeX 公式的 HTML 为 PDF"""
    from playwright.async_api import async_playwright

    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <!-- KaTeX CSS -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
    <!-- KaTeX JS -->
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
    <style>
        body { font-family: 'SimSun', serif; padding: 40px; line-height: 1.8; }
        h1 { text-align: center; font-size: 20px; margin-bottom: 30px; }
        .problem { margin: 20px 0; padding: 10px; border-left: 3px solid #333; }
        .section-title { font-size: 16px; font-weight: bold; margin: 20px 0 10px 0; }
    </style>
</head>
<body>
    <h1>七年级数学单元测试</h1>

    <div class="section-title">一、选择题（每题5分）</div>
    <div class="problem">
        <p>1. 已知函数 $f(x) = x^2 + 2x$，求导数 $f'(x)$：</p>
        <p>A. $2x$ &nbsp;&nbsp; B. $2x + 2$ &nbsp;&nbsp; C. $x^2$ &nbsp;&nbsp; D. $2$</p>
    </div>
    <div class="problem">
        <p>2. 方程 $ax^2 + bx + c = 0$ 的求根公式为：</p>
        <p>$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$</p>
    </div>

    <div class="section-title">二、计算题（每题10分）</div>
    <div class="problem">
        <p>3. 化简：$\\sqrt{12} + \\sqrt{27} - \\sqrt{48}$</p>
    </div>
    <div class="problem">
        <p>4. 解不等式：$\\frac{x + 1}{2} - \\frac{2x - 3}{3} > 1$</p>
    </div>

    <div class="section-title">三、综合题（20分）</div>
    <div class="problem">
        <p>5. 已知二次函数 $y = ax^2 + bx + c$ 的图像经过点 $(1, 3)$、$(-1, 1)$、$(0, 1)$，求该函数的解析式。</p>
        <p>提示：设 $y = ax^2 + bx + c$，代入三点坐标得到方程组：</p>
        <p>$$\\begin{cases} a + b + c = 3 \\\\ a - b + c = 1 \\\\ c = 1 \\end{cases}$$</p>
    </div>
</body>
</html>"""

    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "test_formula.pdf"

    print("=" * 60)
    print("Playwright + KaTeX 公式PDF渲染测试")
    print("=" * 60)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # 加载 HTML
            await page.set_content(html_content, wait_until="networkidle")
            # 等待 KaTeX 渲染完成
            await page.wait_for_timeout(3000)

            # 导出 PDF
            await page.pdf(path=str(output_path), format="A4", print_background=True)
            await browser.close()

            print(f"✅ PDF 生成成功: {output_path}")
            print(f"   文件大小: {output_path.stat().st_size / 1024:.1f} KB")
            print("")
            print("请检查生成的 PDF 文件：")
            print("  - 公式是否清晰可辨")
            print("  - 中文是否显示正常")
            print("  - 分页是否正确")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        print("")
        print("可能原因:")
        print("  1. Chromium 未安装 → 运行: playwright install chromium")
        print("  2. KaTeX CDN 不可达 → 需配网络或使用本地 KaTeX 资源")
        print("  3. 字体缺失 → 需安装中文字体")
        return False

    return True


if __name__ == "__main__":
    import asyncio
    success = asyncio.run(test_pdf_render())
    sys.exit(0 if success else 1)
