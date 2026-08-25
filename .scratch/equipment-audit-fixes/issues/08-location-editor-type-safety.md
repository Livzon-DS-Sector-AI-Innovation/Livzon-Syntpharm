# 08: LocationEditor Type Safety

**What to build:** Replace `initialData?: any` in LocationEditor with proper generated types from the OpenAPI schema, so that the component has type-safe props and catches type errors at compile time.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Replace `initialData?: any` with `components['schemas']['LocationUpdate']`
- [ ] Update component implementation to use typed props
- [ ] Ensure TypeScript compilation passes with strict mode
- [ ] All existing tests continue to pass
- [ ] No `any` types remain in component props
