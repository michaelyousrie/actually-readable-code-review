# Eval results

## 2026-11-05

Each run used a fresh agent that saw only `SKILL.md` and its folder, the prepared checkout and,
for reformat, the source review. No agent was told the expected finding. Each checkout was a
fresh repo with one commit, "baseline", no remote, and none of the tests the fix added, so
nothing in it named the fix. `score.py` checks the format, then checks for a finding at the
case's expected file and line range with at least the expected score; the reformat case also
requires the false finding gone and at least one drop reported.

These runs use the current output format: colored score dots, line-numbered **PROPOSED FIX**
diffs, and `Problem:` and `Fix:` comment lines with colored squares inside the diff.

| Case | Mode | Result |
|---|---|---|
| `chi-routeheaders-double-serve` | review | PASS: found the bug at `middleware/route_headers.go:81`, scored 4/5 |
| `cookie-hasownproperty-shadow` | reformat | PASS: kept the bug at `index.js:133` (4/5), dropped the false finding and both style nitpicks (1 confirmed, 3 dropped) |
| `multipart-header-carryover` | review | PASS: found the bug at `multipart/multipart.py:1615`, scored 4/5 |

All line numbers in the diffs were checked against the files by hand, and the format checker
ran clean on all three. Rendering is verified only in the Claude Code terminal; it is
unverified in other clients.

### Output: chi-routeheaders-double-serve (review)

## Fix before merge
1 finding · top impact 4/5 · 1 file

---

### 1. 🔴 [4/5] An empty RouteHeaders serves every request twice, re-running the downstream handler
`middleware/route_headers.go:81`
**PROPOSED FIX:**
```diff
@@ middleware/route_headers.go:79 @@
 79 | 		if len(hr) == 0 {
 80 | 			// skip if no routes set
 81 | 			next.ServeHTTP(w, r)
+   | 			// 🟩 Fix: without this return an empty router falls through and the default-route branch below serves the request a second time.
+82 | 			return
 83 | 		}
```
**Blast radius:**
- `middleware/route_headers.go:77` is the exported `Handler`; any chi user who mounts `RouteHeaders()` with zero routes added currently runs `next` twice, so the handler's writes and side effects happen twice and the HTTP response is written twice.
- `middleware/route_headers.go:79` has no test (`middleware/` ships no `route_headers_test.go`), so the regression is uncovered; add a case asserting an empty router calls `next` exactly once.

### Output: cookie-hasownproperty-shadow (reformat)

## Fix before merge
1 finding · top impact 4/5 · 1 file · from pasted review: 1 confirmed, 3 dropped

---

### 1. 🔴 [4/5] A cookie named `hasOwnProperty` makes parsing throw on the next cookie
`index.js:133`
**PROPOSED FIX:**
```diff
@@ index.js:132 @@
 132 |     // only assign once
-    |     // 🟥 Problem: obj is a plain {} (index.js:104), so a cookie named hasOwnProperty becomes an own key that shadows the method, and the next pair throws TypeError. Introduced by this diff.
-133 |     if (!obj.hasOwnProperty(key)) {
+    |     // 🟩 Fix: call hasOwnProperty off Object.prototype so no cookie name can shadow it.
+133 |     if (!Object.prototype.hasOwnProperty.call(obj, key)) {
 134 |       var valStartIdx = startIndex(str, eqIdx + 1, endIdx);
```
**Blast radius:**
- Users sending a Cookie header with a cookie named `hasOwnProperty` followed by another pair previously got a thrown `TypeError`; after the fix `parse` returns every cookie (`index.js:133`).
- `test/parse.js:72` ("should parse native properties") checks `toString` and `valueOf` but never `hasOwnProperty`, so the regression ships green; add a case like `parse('hasOwnProperty=1; a=2')` to lock the fix in.

### Output: multipart-header-carryover (review)

## Fix before merge
1 finding · top impact 4/5 · 1 file

---

### 1. 🔴 [4/5] Later multipart parts inherit earlier parts' headers, corrupting field and file data
`multipart/multipart.py:1615`
**PROPOSED FIX:**
```diff
@@ multipart/multipart.py:1615 @@
 1615 |             def on_part_begin():
-     |                 # 🟥 Problem: without the per-part reset the previous part's headers stay in the dict; a later part that omits Content-Transfer-Encoding inherits an earlier base64 or quoted-printable and its data is decoded wrong, silently corrupting the field or file.
-1616 |                 pass
+     |                 # 🟩 Fix: clear the headers dict at the start of every part so each part is parsed with only its own headers.
+1616 |                 # Reset headers in case this isn't the first part.
+1617 |                 nonlocal headers
+1618 |                 headers = {}
 1619 |
 1620 |             def on_part_data(data: bytes, start: int, end: int) -> None:
```
**Blast radius:**
- `multipart/multipart.py:1668` reads `Content-Transfer-Encoding` with a `7bit` default, so a stale `base64` or `quoted-printable` from an earlier part wraps a later part's writer in a decoder and mangles its bytes; the fix restores correct decoding.
- `multipart/multipart.py:1650` reads `Content-Disposition`, so a part that omits it would otherwise inherit the previous part's name and filename and be misfiled as the wrong field or file; the fix closes that too.
- `tests/test_multipart.py:773` runs the `.http` fixtures, but `multiple_fields`, `multiple_files` and `single_field_single_file` all give every part its own Content-Disposition and no Content-Transfer-Encoding, so none exercises header carryover and none would catch this regression; a new fixture with an encoded part before a plain part, asserting the plain part is stored verbatim, is needed.
