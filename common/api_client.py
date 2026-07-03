"""
API 调用封装
提供重试机制、超时处理、统一响应格式解析
用于 Windows 端调用 Ubuntu 端 API
"""

import time
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests
from requests.exceptions import RequestException

from common.config import get_config
from common.logger import logger

# 默认 API 配置
_DEFAULT_TIMEOUT = 30  # 秒
_DEFAULT_RETRIES = 3
_DEFAULT_RETRY_DELAY = 1.0  # 秒


class ApiClient:
    """Ubuntu 端 API 客户端"""

    def __init__(
        self,
        base_url: str = None,
        timeout: int = None,
        max_retries: int = None,
        retry_delay: float = None,
    ):
        self.base_url = base_url or get_config("app", "api_base_url", "http://127.0.0.1:5000")
        self.timeout = timeout or get_config("app", "api_timeout", _DEFAULT_TIMEOUT)
        self.max_retries = max_retries or get_config("app", "api_retries", _DEFAULT_RETRIES)
        self.retry_delay = retry_delay or get_config("app", "api_retry_delay", _DEFAULT_RETRY_DELAY)
        self.session = requests.Session()

    def _request_with_retry(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict] = None,
        files=None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        带重试的 HTTP 请求
        :param method: GET / POST / PUT / DELETE
        :param path: API 路径，如 "/api/goal"
        :param json_data: JSON 请求体
        :param files: 文件上传
        :param kwargs: 其他 requests 参数
        :return: 解析后的响应字典
        """
        url = urljoin(self.base_url.rstrip("/") + "/", path.lstrip("/"))
        last_error = None

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"{method} {url} (尝试 {attempt + 1}/{self.max_retries})")

                if files:
                    resp = self.session.request(
                        method, url,
                        data=json_data,
                        files=files,
                        timeout=self.timeout,
                        **kwargs,
                    )
                else:
                    resp = self.session.request(
                        method, url,
                        json=json_data,
                        timeout=self.timeout,
                        **kwargs,
                    )

                resp.raise_for_status()
                result = resp.json()

                # 解析统一响应格式
                if result.get("code") == 0:
                    return result
                else:
                    logger.error(f"API 返回错误: code={result.get('code')}, msg={result.get('msg')}")
                    # 仅对 2xx 外的错误码重试
                    if result.get("code", 0) in (2, 3):
                        continue

                return result

            except requests.exceptions.Timeout:
                last_error = f"请求超时: {url}"
                logger.warning(f"{last_error} (尝试 {attempt + 1}/{self.max_retries})")
            except requests.exceptions.ConnectionError as e:
                last_error = f"连接失败: {url} - {e}"
                logger.warning(f"{last_error} (尝试 {attempt + 1}/{self.max_retries})")
            except RequestException as e:
                last_error = str(e)
                logger.error(f"请求异常: {e}")
                raise  # 非可重试错误，直接抛出

            # 指数退避
            wait_time = self.retry_delay * (2 ** attempt)
            time.sleep(wait_time)

        raise RuntimeError(f"API 请求失败，已重试 {self.max_retries} 次: {last_error}")

    def get(self, path: str, params: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """GET 请求"""
        return self._request_with_retry("GET", path, json_data=params, **kwargs)

    def post(self, path: str, json_data: Optional[Dict] = None, files=None, **kwargs) -> Dict[str, Any]:
        """POST 请求"""
        return self._request_with_retry("POST", path, json_data=json_data, files=files, **kwargs)

    def put(self, path: str, json_data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """PUT 请求"""
        return self._request_with_retry("PUT", path, json_data=json_data, **kwargs)

    def delete(self, path: str, **kwargs) -> Dict[str, Any]:
        """DELETE 请求"""
        return self._request_with_retry("DELETE", path, **kwargs)


# 全局单例
_default_client: Optional[ApiClient] = None


def get_api_client() -> ApiClient:
    """获取全局 API 客户端单例"""
    global _default_client
    if _default_client is None:
        _default_client = ApiClient()
    return _default_client


def reset_client() -> None:
    """重置 API 客户端（用于测试）"""
    global _default_client
    if _default_client:
        _default_client.session.close()
    _default_client = None
