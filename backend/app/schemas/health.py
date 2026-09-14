"""健康检查接口的响应模型。"""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """表示 API 进程已启动并可响应请求。"""

    status: Literal["ok"]
