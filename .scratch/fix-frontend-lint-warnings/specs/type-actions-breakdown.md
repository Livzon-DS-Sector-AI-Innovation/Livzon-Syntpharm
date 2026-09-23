# Type Actions Breakdown Spec

## Problem Statement

As a developer working on the Livzon-Syntpharm frontend, I'm facing 843 TypeScript lint warnings in the action files. These warnings indicate that our server actions are using `any` types, which defeats the purpose of TypeScript's type safety. The warnings are concentrated in 38 files, with the safety domain alone accounting for 305 warnings. This makes the codebase harder to maintain, increases the risk of runtime errors, and prevents IDEs from providing proper autocomplete and type checking when consuming these actions in components.

## Solution

Break down the work into 39 smaller, domain-focused tickets (plus one parent ticket) that each type a specific subset of action functions. Each ticket will add explicit return types to action functions, remove `as any` type assertions, and ensure components receive properly typed data. This incremental approach allows us to make steady progress without breaking the build, with each ticket independently testable and mergeable.

## User Stories

1. As a developer, I want action functions to have explicit return types, so that I can understand what data structure each action returns without guessing.

2. As a developer, I want to remove `as any` type assertions from safety check actions, so that safety check components receive properly typed data and get IDE autocomplete support.

3. As a developer, I want to remove `as any` type assertions from safety hazard actions, so that hazard inspection workflows have type-safe data flow.

4. As a developer, I want to remove `as any` type assertions from safety accident actions, so that accident reporting forms have proper type checking.

5. As a developer, I want to remove `as any` type assertions from safety contractor actions, so that contractor management features are type-safe.

6. As a developer, I want to remove `as any` type assertions from safety training actions, so that training record management has proper types.

7. As a developer, I want to remove `as any` type assertions from safety regulation actions, so that regulation tracking is type-safe.

8. As a developer, I want to remove `as any` type assertions from safety knowledge base actions, so that knowledge article management has proper types.

9. As a developer, I want to remove `as any` type assertions from safety special operations actions, so that special operation permits and personnel tracking are type-safe.

10. As a developer, I want to remove `as any` type assertions from safety EHS change actions, so that EHS change management has proper type checking.

11. As a developer, I want to remove `as any` type assertions from safety occupational health actions, so that occupational health monitoring is type-safe.

12. As a developer, I want to remove `as any` type assertions from safety daily risk report actions, so that daily risk reporting has proper types.

13. As a developer, I want to remove `as any` type assertions from safety helper functions, so that utility functions used across safety features are type-safe.

14. As a developer, I want to remove `as any` type assertions from HR employee actions, so that employee management features have proper type checking.

15. As a developer, I want to remove `as any` type assertions from HR training actions, so that HR training record management is type-safe.

16. As a developer, I want to remove `as any` type assertions from HR annual training plan actions, so that annual training planning has proper types.

17. As a developer, I want to remove `as any` type assertions from equipment main actions, so that equipment management features are type-safe.

18. As a developer, I want to remove `as any` type assertions from equipment inspection actions, so that equipment inspection workflows have proper type checking.

19. As a developer, I want to remove `as any` type assertions from equipment personnel actions, so that equipment personnel assignment is type-safe.

20. As a developer, I want to remove `as any` type assertions from energy device actions, so that energy device management has proper types.

21. As a developer, I want to remove `as any` type assertions from energy alert actions, so that energy alert configuration is type-safe.

22. As a developer, I want to remove `as any` type assertions from research project actions, so that research project management has proper type checking.

23. As a developer, I want to remove `as any` type assertions from research module actions, so that research module configuration is type-safe.

24. As a developer, I want to remove `as any` type assertions from research deliverable actions, so that research deliverable tracking has proper types.

25. As a developer, I want to remove `as any` type assertions from quality main actions, so that quality management features are type-safe.

26. As a developer, I want to remove `as any` type assertions from quality CPV actions, so that CPV (Critical Process Variable) management has proper type checking.

27. As a developer, I want to remove `as any` type assertions from quality inspection table actions, so that inspection table recognition is type-safe.

28. As a developer, I want to remove `as any` type assertions from quality doc-check actions, so that document checking workflows have proper types.

29. As a developer, I want to remove `as any` type assertions from registration main actions, so that registration management features are type-safe.

30. As a developer, I want to remove `as any` type assertions from registration ledger actions, so that registration ledger tracking has proper type checking.

31. As a developer, I want to remove `as any` type assertions from regulatory tracker actions, so that regulatory document tracking is type-safe.

32. As a developer, I want to remove `as any` type assertions from deviation actions, so that deviation management has proper types.

33. As a developer, I want to remove `as any` type assertions from material-report actions, so that material report generation is type-safe.

34. As a developer, I want to remove `as any` type assertions from static-data actions, so that static data management has proper type checking.

35. As a developer, I want to remove `as any` type assertions from validation-audit actions, so that validation audit tracking is type-safe.

36. As a developer, I want to remove `as any` type assertions from product actions, so that product management features have proper types.

37. As a developer, I want to remove `as any` type assertions from administration actions, so that system administration features are type-safe.

38. As a developer, I want to remove `as any` type assertions from dossier-writer actions, so that dossier writing workflows have proper type checking.

39. As a developer, I want to remove `as any` type assertions from equipment-personnel actions, so that equipment-personnel assignment is type-safe.

40. As a developer, I want to remove `as any` type assertions from small utility actions, so that utility functions across the system are type-safe.

41. As a developer, I want each ticket to be independently mergeable, so that I can make incremental progress without breaking the build.

42. As a developer, I want to reuse existing type definitions, so that I don't duplicate type definitions across the codebase.

43. As a developer, I want components to automatically receive proper types from actions, so that I get IDE autocomplete and type checking when consuming actions.

44. As a developer, I want the type boundary to be at the action level, so that server API functions can remain untyped for now while still providing type safety to components.

## Implementation Decisions

### Ticket Breakdown Strategy

The work is broken down by domain and file size:

- **Large files (>20 warnings)**: Split by function category within the domain. The safety domain (306 warnings) is split into 12 tickets by entity type. HR (83 warnings), equipment (121 warnings), energy (40 warnings), research (85 warnings), quality (51 warnings), and registration (31 warnings) are split into 2-4 tickets each by sub-module or function area.

- **Medium files (8-20 warnings)**: One ticket per file for deviation, material-report, static-data, validation-audit, administration, dossier-writer, and equipment-personnel.

- **Small files (1-7 warnings)**: Grouped into a single ticket for small utility actions across 8 files.

### Type Boundary Pattern

Each action function will be updated to:
1. Add an explicit return type annotation using existing types from the type definitions directory
2. Replace `as any` type assertions with `as <SpecificType>` assertions where needed
3. Use the API response envelope type to wrap the domain-specific data type

The action layer serves as the type boundary: server API functions continue to return untyped data, but action functions provide explicit types to consuming components. This allows components to receive properly typed data without requiring changes to the server API layer.

### Type Reuse Strategy

All type definitions will be reused from the existing type definitions directory. No new type definitions will be created. Each action function's return type will reference existing domain types (e.g., SafetyCheck, Equipment, Employee, etc.) wrapped in the standard API response envelope.

### Incremental Merge Strategy

Each ticket is designed to be independently mergeable:
- No cross-ticket dependencies
- Each ticket passes type checking after completion
- Each ticket removes warnings from its targeted scope
- Components consuming the typed actions automatically benefit from the improved types

## Testing Decisions

### What Makes a Good Test

Since this is a type-only refactoring with no logic changes, testing focuses on:
1. **Type checking**: `tsc --noEmit` must pass after each ticket
2. **Lint verification**: `pnpm eslint` on modified files must show zero `@typescript-eslint/no-explicit-any` warnings in the targeted scope
3. **Manual smoke test**: Verify that affected pages still load and function correctly (no runtime behavior changes expected)

### Which Modules Will Be Tested

Each ticket tests its own scope:
- The modified action functions
- Components that consume those actions (implicitly, through type checking)
- The overall build (through `tsc --noEmit`)

### Prior Art

This approach follows the pattern established in tickets 17-26, where API client files were typed incrementally by domain. Each ticket in that series:
- Added explicit return types to API functions
- Removed `as any` assertions
- Passed type checking
- Was independently mergeable

The action typing work extends this pattern one layer up the stack, from API clients to server actions.

## Out of Scope

- **Typing server API base functions**: This is covered by ticket 59, which will type the foundational `apiFetch` and `apiFetchFormData` functions. That work is separate because it affects 770+ call sites across the entire codebase.

- **Adding runtime validation or type guards**: This spec focuses on compile-time type safety only. Runtime validation would be a separate enhancement.

- **Refactoring action function signatures**: We're only adding return types and removing `as any` assertions. Function parameters and internal logic remain unchanged.

- **Creating new type definitions**: All types already exist in the type definitions directory. We're reusing them, not creating new ones.

- **Typing components**: Components will automatically benefit from the improved action types. Explicit component typing is not part of this spec.

## Further Notes

### Ticket Structure

- **Parent ticket**: Ticket 34 (Type all action files)
- **Child tickets**: 34.1 through 34.39 (39 tickets total)
- **Total work units**: 40 tickets (1 parent + 39 children)

### Estimated Effort

Each child ticket is estimated at 15-30 minutes of work, depending on:
- Number of functions in the scope
- Complexity of the return types
- Number of components consuming the actions

### Progress Tracking

The parent ticket (34) tracks overall completion. Each child ticket is marked complete when:
- All targeted functions have explicit return types
- All `as any` assertions are removed from the scope
- Type checking passes
- Lint passes on modified files

### Relationship to Ticket 59

Ticket 59 (typing server API base functions) is a prerequisite for full type safety across the codebase. However, this spec's work can proceed independently because:
- Action functions provide the type boundary
- Components receive types from actions, not directly from server APIs
- Server API functions can remain untyped while actions provide types to components

Once ticket 59 is complete, the type assertions in actions can be simplified, but that's an optional cleanup, not a requirement.
