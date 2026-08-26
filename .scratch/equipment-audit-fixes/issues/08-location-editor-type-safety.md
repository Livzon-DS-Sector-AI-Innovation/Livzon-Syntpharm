# 08: LocationEditor Type Safety

**What to build:** Replace `initialData?: any` in LocationEditor with proper generated types from the OpenAPI schema, so that the component has type-safe props and catches type errors at compile time.

**Blocked by:** None (can start immediately)

**Status:** completed

- [x] Replace `initialData?: any` with `Location` type
- [x] Update component implementation to use typed props
- [x] Ensure TypeScript compilation passes with strict mode
- [x] All existing tests continue to pass
- [x] No `any` types remain in component props
