"""Administration module public API — cross-module access points.

Other modules should import from this file instead of directly accessing
internal service/repository/models.

注意：车辆管理（VehicleRequest / Vehicle / ITServiceTicket 等）已下线，
`models.py`、`repository.py`、`schemas.py` 当前均为空占位，此处不再导出任何实体。
恢复该功能前，先补回模型与迁移，再在此恢复导出；在那之前本模块没有跨模块契约。
"""

__all__: list[str] = []
