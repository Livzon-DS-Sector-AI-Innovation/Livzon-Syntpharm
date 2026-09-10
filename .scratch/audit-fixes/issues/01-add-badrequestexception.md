# 01: Add BadRequestException class

**What to build:** Consistent exception handling for 400 errors across the equipment module. When a request has invalid parameters, the API should raise BadRequestException instead of HTTPException, matching the pattern of NotFoundException, DuplicateException, etc.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] BadRequestException class added to app/core/exceptions.py
- [ ] BadRequestException inherits from AppException
- [ ] BadRequestException accepts a message parameter
- [ ] BadRequestException returns HTTP 400 status code
- [ ] Existing tests still pass
