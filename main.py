import logging
import os
import time

import pyautogui
import pygetwindow as gw

# 添加日志基础配置（建议在文件顶部添加）
logging.basicConfig(
    level=logging.DEBUG,  # 设置日志级别
    format="%(asctime)s [%(levelname)s] %(message)s",  # 添加时间戳格式
    handlers=[logging.StreamHandler()],  # 控制台输出
)


def find_image_and_click(
    image_path,
    timeout=10,
    x_offset=0,
    y_offset=0,
    fail_silently=False,
    window_title=None,
    verify_image=None,
    verify_timeout=3,
):
    """
    查找屏幕上的图像并在指定偏移量处点击
    :param image_path: 图像文件路径（相对于pics目录的路径）
    :param timeout: 最大等待时间（秒）
    :param x_offset: X轴偏移量
    :param y_offset: Y轴偏移量
    :param fail_silently: 是否静默失败（False时抛出异常）
    :param window_title: 窗口标题（支持部分匹配）
    :param verify_image: 验证图片路径（点击后的预期结果）
    :param verify_timeout: 验证超时时间（秒）
    :return: 坐标元组或None
    """
    try:
        # 窗口处理
        window = _get_target_window(window_title) if window_title else None
        region = _get_search_region(window)

        # 路径处理
        full_image_path = _get_full_image_path(image_path)

        # 查找主图
        location = _locate_image(full_image_path, region, timeout)
        if not location:
            return _handle_failure(full_image_path, fail_silently, window_title)

        center = pyautogui.center(location)
        x, y = center
        logging.info(f"成功找到图片: {full_image_path} 位置: ({x}, {y})")

        # 执行点击
        pyautogui.click(x + x_offset, y + y_offset)

        # 验证流程
        if verify_image:
            return _handle_verification(
                full_image_path,
                verify_image,
                verify_timeout,
                x,
                y,
                x_offset,
                y_offset,
                fail_silently,
            )

        return x, y

    except Exception as e:
        logging.error(f"发生未知错误: {str(e)}")
        if not fail_silently:
            raise
        return None


def _get_target_window(window_title):
    """获取目标窗口"""
    windows = gw.getWindowsWithTitle(window_title)
    if not windows:
        error_msg = f"未找到匹配的窗口: {window_title}"
        logging.error(error_msg)
        raise ValueError(error_msg)
    window = windows[0]
    window.activate()
    return window


def _get_search_region(window):
    """获取搜索区域"""
    if window:
        return (window.left, window.top, window.width, window.height)
    screen_size = pyautogui.size()
    return (0, 0, screen_size.width, screen_size.height)


def _get_full_image_path(image_path):
    """获取完整图片路径"""
    base_dir = os.path.join(os.path.dirname(__file__), "pics")
    return os.path.join(base_dir, image_path.strip("\u202a"))


def _locate_image(full_image_path, region, timeout):
    """定位图像"""
    if not os.path.exists(full_image_path):
        raise FileNotFoundError(f"文件 {full_image_path} 不存在，请检查路径")

    logging.debug(f"开始查找图片: {full_image_path}, 超时时间: {timeout}s")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            return pyautogui.locateOnScreen(
                full_image_path, grayscale=True, confidence=0.8, region=region
            )
        except pyautogui.ImageNotFoundException:
            time.sleep(1)
    return None


def _handle_failure(full_image_path, fail_silently, window_title):
    """处理失败情况"""
    error_msg = f"在窗口 '{window_title}' 中查找图片 {full_image_path} 超时"
    logging.error(error_msg)
    if not fail_silently:
        raise RuntimeError(error_msg)
    return None


def _handle_verification(
    full_image_path,
    verify_image,
    verify_timeout,
    x,
    y,
    x_offset,
    y_offset,
    fail_silently,
):
    """处理验证流程"""
    verify_result = verify_image_displayed(verify_image, verify_timeout)

    if not verify_result:
        logging.warning("首次验证失败，开始重试流程")
        retry_location = pyautogui.locateOnScreen(
            full_image_path, grayscale=True, confidence=0.8
        )

        if retry_location:
            retry_center = pyautogui.center(retry_location)
            retry_x, retry_y = retry_center
            logging.info(
                f"重新找到原图片: {full_image_path} 位置: ({retry_x}, {retry_y})"
            )

            pyautogui.click(retry_x + x_offset, retry_y + y_offset)
            verify_result = verify_image_displayed(verify_image, verify_timeout * 2)

            if not verify_result:
                error_msg = f"二次验证失败: {verify_image} 未找到，操作终止"
                logging.error(error_msg)
                if not fail_silently:
                    raise RuntimeError(error_msg)
                return None
        else:
            error_msg = f"无法重新定位原图片 {full_image_path}，操作终止"
            logging.error(error_msg)
            if not fail_silently:
                raise RuntimeError(error_msg)
            return None

    logging.info(f"验证通过: {verify_image}")
    return x, y


def verify_image_displayed(image_path, timeout=5):
    """
    验证指定图片是否在屏幕上显示
    :param image_path: 验证图片路径
    :param timeout: 超时时间
    :return: 成功找到返回True，否则返回False
    """
    full_image_path = _get_full_image_path(image_path)

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            if pyautogui.locateOnScreen(
                full_image_path, grayscale=True, confidence=0.8
            ):
                logging.info(f"验证成功: 找到预期图片 {full_image_path}")
                return True
        except pyautogui.ImageNotFoundException:
            pass
        time.sleep(0.5)

    logging.warning(f"验证超时: 未找到预期图片 {full_image_path}")
    return False


if __name__ == "__main__":
    # 在点击image.png后验证disk_e.png是否出现
    # 验证失败时会自动重试一次点击流程
    find_image_and_click("image.png", window_title="此电脑", verify_image="disk_e.png")
    # 如果验证成功才会继续执行后续操作
    find_image_and_click("disk_e.png")
