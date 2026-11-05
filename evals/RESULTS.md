# Eval results

## 2026-11-04

These outputs predate the format changes of 2026-11-05: colored score dots, line-numbered
**PROPOSED FIX** diffs, and `Problem:` and `Fix:` comments inside the diff in place of
**Impact:** on findings that have a fix. The cases have not been rerun in the current format.

Each run used a fresh agent that saw only `SKILL.md` and its folder, the prepared checkout and,
for reformat, the source review. Each checkout was a fresh repo with one commit, "baseline", no
remote, and none of the tests the fix added, so nothing in it named the fix. `score.py` also
runs the format checker.

| Case | Mode | Result |
|---|---|---|
| `chi-routeheaders-double-serve` | review | PASS: found the bug at `middleware/route_headers.go:81`, scored 4/5 |
| `cookie-hasownproperty-shadow` | reformat | PASS: kept the bug at `index.js:133` (4/5), dropped the false finding and both style nitpicks (1 confirmed, 3 dropped) |
| `multipart-header-carryover` | review | prepared and verified, not run |

Rendering is verified only in the Claude Code terminal. It is unverified in other clients.

An earlier run the same day also passed, but its checkouts kept the fix commit's history and
the tests the fix added, and the chi reviewer cited both. Those results were discarded.

### Output: chi-routeheaders-double-serve (review)

## Fix before merge
1 finding · top impact 4/5 · 1 file

---

### 1. [4/5] Routers with no header routes run every request's handler twice
`middleware/route_headers.go:81`
**Impact:** a `HeaderRouter` with no routes now falls through to the `"*"` fallback at `:100` and calls `next` a second time, so every request runs the handler twice and writes its body twice (a scratch run of one POST returned `okok`). Any non-idempotent handler behind it, such as one that inserts a row, does its work twice per request.
```diff
@@ middleware/route_headers.go:79 @@
 		if len(hr) == 0 {
 			// skip if no routes set
 			next.ServeHTTP(w, r)
+			return
 		}
 
 		// find first matching header route, and continue
```
**Blast radius:**
- `middleware/route_headers.go:100` is the fallback that made the second call; with the return restored an empty router stops after the first call, and routers with at least one route never enter the `:79` branch, so they behave as before.
- Nothing in this repo calls `RouteHeaders` beyond its doc comment (`middleware/route_headers.go:16`) and the README table (`README.md:356`), so only downstream apps see the change.
- No test covers `middleware/route_headers.go:79` because `middleware/` has no `route_headers_test.go`; it needs an empty-router case asserting `next` runs once and the body is written once.

### Output: cookie-hasownproperty-shadow (reformat)

## Fix before merge
1 finding · top impact 4/5 · 1 file · from pasted review: 1 confirmed, 3 dropped

---

### 1. [4/5] Any client can make cookie parsing throw, and crash some servers, with one cookie name
`index.js:133`
**Impact:** a cookie named `hasOwnProperty` overwrites the method on the result object, so the next cookie in the same header throws a `TypeError` (`parse('hasOwnProperty=1; a=2')` throws, where the code before this diff returned both cookies). Any client can send that header, and a server that does not catch the error, like the README's plain `http` example, exits on the first such request.
```diff
@@ index.js:23 @@
 var __toString = Object.prototype.toString
+var __hasOwnProperty = Object.prototype.hasOwnProperty
@@ index.js:132 @@
     // only assign once
-    if (!obj.hasOwnProperty(key)) {
+    if (!__hasOwnProperty.call(obj, key)) {
       var valStartIdx = startIndex(str, eqIdx + 1, endIdx);
```
**Blast radius:**
- `README.md:194` passes the raw request header to parse inside a plain http server (`:212`), the documented setup that stays up again once the fix lands.
- `test/parse.js:72` covers the toString and valueOf names only, and no test uses hasOwnProperty, so a case with that name followed by a second cookie is needed to stop this coming back.
