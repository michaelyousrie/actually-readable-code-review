# TodoApp

An HTML form that posts to a PHP page, which runs its SQL without prepared statements. It
checks that ARCR finds SQL injection, scores it 5/5, and fixes it with bound parameters.

Paths in the outputs are relative to `src/`.

## How to run

1. Copy `src/` into an empty folder and run `git init` there. Both files stay untracked.
2. Ask a fresh agent to review the uncommitted changes with ARCR.
3. Never tell the reviewer the expected findings. Compare its output with the table below.

## Expected

| Change under review | Expected finding |
|---|---|
| user input pasted into SQL at `todos.php:18` (INSERT, title) and `todos.php:20` (DELETE, id) | 5/5: anyone can run their own SQL, such as an id of `1 OR 1=1` deleting every todo; one finding for both lines, or two at 5/5 |
| the fix | bound parameters for both queries, and a title with an apostrophe (O'Reilly) saves afterwards |
| credentials from the environment, output escaped with `htmlspecialchars` | no hardcoded-secret or XSS finding |

Anything else the reviewer reports is unplanted and is judged on its own.

## Latest results: 2026-11-05

| Check | Result |
|---|---|
| SQL injection | PASS: 5/5 at `todos.php:18`, covering lines 18 and 20, checker OK |
| Fix | PASS: bound parameters for both queries; the apostrophe case is in the blast radius |
| False alarms | PASS: no hardcoded-secret or XSS finding |
| Unplanted | a title of only spaces (3/5, on top of fix 1) and a refresh re-sending the add (3/5); both are real and appeared in earlier runs too |

### Output

## Fix before merge
3 findings · top impact 5/5 · 2 files

---

### 1. 🔴 [5/5] Any visitor can run their own SQL through either form, such as deleting every todo
`todos.php:18`
**PROPOSED FIX:**
```diff
@@ todos.php:16 @@
 16 |     if ($action === 'add') {
 17 |         $title = trim($_POST['title'] ?? '');
-   |         // 🟥 Problem: the title is pasted into the SQL, so a crafted title runs the visitor's own SQL and a plain apostrophe fails the add with a 500.
-18 |         $pdo->exec("INSERT INTO todos (title) VALUES ('$title')");
+   |         // 🟩 Fix: a bound parameter reaches the database as data, never as SQL.
+18 |         $pdo->prepare('INSERT INTO todos (title) VALUES (?)')->execute([$title]);
 19 |     } elseif ($action === 'delete') {
-   |         // 🟥 Problem: the id is pasted into the SQL, so `1 OR 1=1` deletes every todo, and a missing or non-numeric id fails with a 500.
-20 |         $pdo->exec('DELETE FROM todos WHERE id = ' . $_POST['id']);
+   |         // 🟩 Fix: only a whole number reaches the query, and it is bound as data.
+20 |         $id = filter_var($_POST['id'] ?? '', FILTER_VALIDATE_INT);
+21 |         if ($id !== false) {
+22 |             $pdo->prepare('DELETE FROM todos WHERE id = ?')->execute([$id]);
+23 |         }
 24 |     }
```
**Blast radius:**
- `index.html:11` titles with an apostrophe, such as "Mom's birthday", now save instead of showing the 500 page.
- `index.html:18` is a free text field, so a missing, non-numeric or zero-padded number such as `05` now deletes nothing and returns the list with no message saying why.
- No test covers `todos.php:18` or `:22`; add cases for an apostrophe in a title and for `1 OR 1=1` as the id, which must delete nothing.

---

### 2. 🟡 [3/5] A title of only spaces saves a blank todo
`todos.php:17`
**PROPOSED FIX (on top of fix 1):**
```diff
@@ todos.php:16 @@
 16 |     if ($action === 'add') {
 17 |         $title = trim($_POST['title'] ?? '');
-   |         // 🟥 Problem: spaces pass the form's `required` check, and trim turns them into an empty title that shows as a blank row.
-18 |         $pdo->prepare('INSERT INTO todos (title) VALUES (?)')->execute([$title]);
+   |         // 🟩 Fix: a title that is empty after trimming saves nothing.
+18 |         if ($title !== '') {
+19 |             $pdo->prepare('INSERT INTO todos (title) VALUES (?)')->execute([$title]);
+20 |         }
 21 |     } elseif ($action === 'delete') {
```
**Blast radius:**
- `index.html:11` submitting only spaces now saves nothing and returns the list with no message saying why.
- No test covers `todos.php:18`; add a case where a title of spaces leaves the table as it was.

---

### 3. 🟡 [3/5] Refreshing the list right after adding a todo saves it a second time
`todos.php:23`
**PROPOSED FIX:**
```diff
@@ todos.php:21 @@
 21 |     }
 22 |
+   |     // 🟩 Fix: the list rendered straight from the POST, so a refresh resent the form; redirecting after a write makes a refresh a plain page load.
+23 |     if ($_SERVER['REQUEST_METHOD'] === 'POST') {
+24 |         header('Location: todos.php', true, 303);
+25 |         exit;
+26 |     }
+27 |
 28 |     $todos = $pdo->query('SELECT id, title FROM todos ORDER BY id')->fetchAll();
```
**Blast radius:**
- `index.html:9` and `:16` both forms now end on a 303 redirect to `todos.php`, so the browser no longer offers to resend the form on refresh or back.
- No test covers `todos.php:23`; add a case that a POST answers 303 with `Location: todos.php` and writes once.
