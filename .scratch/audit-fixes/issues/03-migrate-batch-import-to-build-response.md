# 03: Migrate batch_import.py to build_response and BadRequestException

**What to build:** batch_import endpoints return proper ApiResponse with validation and correct error handling. The preview_import and batch_import endpoints should use build_response() instead of success_response(), and raise BadRequestException for validation errors instead of HTTPException.

**Blocked by:** 01, 02

**Status:** ready-for-agent

- [ ] preview_import endpoint uses build_response() instead of success_response()
- [ ] batch_import endpoint uses build_response() instead of success_response()
- [ ] Validation errors raise BadRequestException instead of HTTPException
- [ ] preview_import accepts EquipmentImportRow list instead of list[dict[str, Any]]
- [ ] batch_import accepts EquipmentImportRow list instead of list[dict[str, Any]]
- [ ] Response models are set correctly on endpoints
- [ ] Existing tests still pass
- [ ] New tests verify BadRequestException behavior
