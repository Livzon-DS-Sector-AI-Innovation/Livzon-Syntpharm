# 02: Create EquipmentImportRow Pydantic model

**What to build:** Type-safe validation for equipment import data. When users upload equipment data for preview or batch import, the system should validate the input using a Pydantic model instead of accepting untyped dictionaries.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] EquipmentImportRow Pydantic model created in app/modules/equipment/schemas/equipment.py
- [ ] Model includes fields: 资产编号, 资产说明, 实物所在部门, 资产类别说明, 当前成本, 报废状态, 数量
- [ ] Model validates field types and required fields
- [ ] Model can be used in preview_import and batch_import endpoints
- [ ] Existing tests still pass
