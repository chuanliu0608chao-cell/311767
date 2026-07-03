"""
验证脚本 3：OpenCV 摄像头检测与拍照测试
枚举所有摄像头设备，选择分辨率最高的设备进行测试
"""
import cv2
import numpy as np
from pathlib import Path
import sys


def enumerate_cameras(max_tests=10):
    """枚举可用的摄像头设备"""
    cameras = []
    print("=" * 60)
    print("摄像头检测设备")
    print("=" * 60)

    for i in range(max_tests):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)

            # 尝试读取一帧验证摄像头真正可用
            ret, frame = cap.read()
            if ret and frame is not None:
                cameras.append({
                    "index": i,
                    "width": width,
                    "height": height,
                    "fps": fps if fps > 0 else 30,
                    "available": True,
                })
                print(f"  ✅ 摄像头 {i}: {width}x{height} @ {fps:.0f}fps")
            else:
                print(f"  ⚠️  摄像头 {i}: 无法读取画面")
                cameras.append({
                    "index": i,
                    "width": width,
                    "height": height,
                    "fps": fps if fps > 0 else 30,
                    "available": False,
                })
            cap.release()
        else:
            break  # 连续不可用，停止枚举

    return cameras


def capture_test(camera_index, output_dir):
    """指定摄像头拍照测试"""
    print(f"\n  正在从摄像头 {camera_index} 拍照...")

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"  ❌ 无法打开摄像头 {camera_index}")
        return False

    # 设置最佳分辨率
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    ret, frame = cap.read()
    if not ret or frame is None:
        print(f"  ❌ 拍照失败")
        cap.release()
        return False

    # 图像预处理：去噪 + 对比度增强
    # 高斯模糊去噪
    denoised = cv2.GaussianBlur(frame, (5, 5), 0)
    # CLAHE 对比度增强
    lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    enhanced = cv2.merge((cl, a, b))
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

    # 保存原始和增强后的图片
    output_dir.mkdir(parents=True, exist_ok=True)
    orig_path = output_dir / "camera_test_original.jpg"
    enh_path = output_dir / "camera_test_enhanced.jpg"

    cv2.imwrite(str(orig_path), frame)
    cv2.imwrite(str(enh_path), enhanced)

    cap.release()

    print(f"  ✅ 拍照成功!")
    print(f"     原始图片: {orig_path} ({orig_path.stat().st_size / 1024:.0f} KB)")
    print(f"     增强图片: {enh_path} ({enh_path.stat().st_size / 1024:.0f} KB)")
    print(f"     分辨率: {frame.shape[1]}x{frame.shape[0]}")

    # 检查文字可辨识性（简单的边缘密度检测）
    gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.count_nonzero(edges) / edges.size * 100
    print(f"     边缘密度: {edge_density:.1f}%")

    if edge_density > 5:
        print(f"     ✅ 图像质量良好，文字可辨识")
    else:
        print(f"     ⚠️  图像质量偏低，建议调整光线或焦距")

    return True


def main():
    cameras = enumerate_cameras()

    print(f"\n{'=' * 60}")
    if not cameras:
        print("❌ 未检测到任何摄像头设备")
        print("")
        print("  排查建议:")
        print("  1. 确认高拍仪已连接 USB")
        print("  2. 检查权限: ls -la /dev/video*")
        print("  3. 尝试安装 v4l-utils: sudo apt install v4l-utils")
        print("  4. 运行 v4l2-ctl --list-devices 查看设备")
        print(f"{'=' * 60}")
        return False

    # 选择分辨率最高的可用摄像头
    available = [c for c in cameras if c["available"]]
    if not available:
        print("❌ 没有可用的摄像头")
        print(f"{'=' * 60}")
        return False

    best = max(available, key=lambda c: c["width"] * c["height"])
    print(f"\n  最佳摄像头: 索引={best['index']}, 分辨率={best['width']}x{best['height']}")

    # 拍照测试
    output_dir = Path(__file__).parent.parent / "data" / "camera_test"
    success = capture_test(best["index"], output_dir)

    print(f"\n{'=' * 60}")
    if success:
        print("✅ 摄像头验证通过!")
        print(f"  后续代码中使用: cv2.VideoCapture({best['index']})")
    else:
        print("⚠️  摄像头验证未完成")
    print(f"{'=' * 60}")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
