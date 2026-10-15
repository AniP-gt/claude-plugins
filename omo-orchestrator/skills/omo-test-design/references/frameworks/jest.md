# Jest and Vitest Style Detection

Read `jest.config.*` or `vitest.config.*` (or the `jest` key in `package.json`), setup files (`setupFilesAfterEnv`, `setupFiles`, `setupTests.*`), and 2 to 3 tests near the target. Record each item below as the project does it, with one file reference.

## What to record

- **Runner**: Jest or Vitest (`vi` versus `jest` globals, whether globals are enabled or imported from `vitest`).
- **Location and naming**: colocated `*.test.ts` / `*.spec.ts` versus `__tests__/`, and the file extension.
- **Grouping**: `describe` nesting, `it` versus `test`, description language and wording ("should ..." or plain).
- **Table-driven cases**: `it.each` / `describe.each` / `test.each`, and the table form (array or template literal). Prefer it for partition and boundary cases when the project uses it.
- **Setup**: `beforeEach` / `afterEach`, factory or builder helpers, test data files.
- **Doubles**: `jest.fn` / `vi.fn`, `jest.mock` / `vi.mock` module mocks and where they are declared, `jest.spyOn`, `msw` or `nock` for HTTP, fake timers (`useFakeTimers`, `setSystemTime`), and whether mocks are reset in config (`clearMocks`, `restoreMocks`).
- **Components**: React Testing Library (`render`, `screen`, query priority `getByRole` first), `@testing-library/user-event` versus `fireEvent`, snapshot use, custom `render` wrappers with providers.
- **Assertions**: `toEqual` versus `toStrictEqual`, `toMatchObject`, `toHaveBeenCalledWith`, `expect.assertions` for async, custom matchers (`jest-dom`).
- **Async**: `async/await`, `resolves` / `rejects`, `waitFor`, `findBy*`.

## Run command

Use the project's script (`npm test`, `pnpm test`, `yarn test`) with the file path, for example `pnpm vitest run src/order.test.ts` or `npx jest src/order.test.ts -t "case name"`. Turn off watch mode.

## Common pitfalls

- Module mocks hoisted above imports, making a mock apply to the whole file.
- Mocks not reset between tests when the config does not do it.
- Floating promises: a test that ends before its assertion runs.
- Fake timers left on and breaking later tests.
- Snapshot tests used where an explicit assertion would state the behavior.
- Querying by class name or test ID when an accessible role or label exists.
