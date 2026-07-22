"""原料检验数据表 Schemas"""

from typing import Any

from pydantic import BaseModel


class CreateTableRequest(BaseModel):
    """创建数据表请求"""

    table_name: str
    table_description: str | None = None
    columns_config: list[Any] = []


class UpdateTableRequest(BaseModel):
    """更新数据表请求"""

    table_name: str | None = None
    table_description: str | None = None
    columns_config: list[Any] | None = None
    is_active: bool | None = None


class RowDataRequest(BaseModel):
    """行数据请求"""

    row_data: dict[str, Any]


class BatchRowsRequest(BaseModel):
    """批量行数据请求"""

    rows: list[dict[str, Any]]
