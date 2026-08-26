# 06: Fix getApiBaseUrl() to require API_BASE_URL

**What to build:** Configuration errors fail fast instead of silently using hardcoded localhost. The getApiBaseUrl() function should throw an error if API_BASE_URL environment variable is not set, instead of falling back to hardcoded values.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] getApiBaseUrl() throws error if API_BASE_URL is not set
- [ ] Hardcoded fallback to http://localhost:8000 removed
- [ ] Hardcoded fallback to http://backend:8000 removed
- [ ] Error message clearly explains that API_BASE_URL must be set
- [ ] Existing code that sets API_BASE_URL continues to work
- [ ] Tests verify error is thrown when API_BASE_URL is missing
