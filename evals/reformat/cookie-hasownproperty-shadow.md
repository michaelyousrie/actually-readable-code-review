## Automated Review Summary

Thanks for the contribution! I have reviewed the changes to `index.js`. Overall the code is clean and well organized, but I found a few issues that are worth addressing before this is merged.

**Files reviewed:** 1
**Issues found:** 4 (1 Critical, 1 Major, 2 Suggestions)

---

### Critical

- **`index.js:305`: Unhandled `URIError` can crash the parser.**
  `decodeURIComponent` throws a `URIError` when it receives malformed percent-encoding such as `%E0%A4%A`. A client that sends a header like `Cookie: session=%E0%A4%A` will make `parse` throw, which can take down request handling for any server that parses cookies on every request. Consider wrapping the call in a `try`/`catch` and falling back to the raw value.

### Major

- **`index.js:133`: `obj.hasOwnProperty` can be shadowed by a cookie name.**
  `obj` is a plain object literal, so a cookie named `hasOwnProperty` is stored as an own property and replaces the inherited method. The next pair then calls a string and throws `TypeError: obj.hasOwnProperty is not a function`. For example, `parse('hasOwnProperty=1; a=2')` throws instead of returning both cookies. Use `Object.prototype.hasOwnProperty.call(obj, key)` instead.

### Suggestions

- **`index.js:146`: Missing semicolon.**
  `index = endIdx + 1` has no trailing semicolon, while most of the surrounding statements do. Consider adding one for consistency.

- **`index.js:104`: Prefer `const` or `let` over `var`.**
  The function declares its locals with `var`. Modern JavaScript favors block-scoped `const` and `let`, which make the intent of each binding clearer and avoid hoisting surprises.

---

### Additional Notes

- The changes are well structured and easy to follow.
- Consider adding unit tests that cover the edge cases above.
- Great job keeping the diff small and focused!

Let me know if you have any questions or would like me to take another look after the updates. Happy coding!
