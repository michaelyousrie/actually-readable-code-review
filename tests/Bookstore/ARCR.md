# Bookstore

A one-file PHP page that lists books from MySQL. It checks that ARCR scores a hardcoded
password below critical, and a password sent to every visitor as critical.

Paths in the outputs are relative to `src/`.

## How to run

1. Copy `src/` into an empty folder and run `git init` there.
2. Round 1: delete line 33 of `index.php` (the `db debug` comment), then ask a fresh agent to
   review the uncommitted changes with ARCR.
3. Round 2: run `git add index.php`, put line 33 back, then ask a fresh agent to review the
   unstaged changes (`git diff`) with ARCR.
4. Never tell the reviewer the expected findings. Compare its output with the table below.

## Expected

| Round | Change under review | Expected finding |
|---|---|---|
| 1 | the whole file, with the database values hardcoded at `index.php:5` to `:8` | the values are hardcoded instead of read from the environment, so they leak if the code is pushed or shared; not critical, below 5/5 |
| 2 | an HTML comment at `index.php:33` that prints the username and password | 5/5: the password is visible to anyone who opens dev tools or View Source |

## Latest results: 2026-11-05

| Round | Result |
|---|---|
| 1 | PASS: 4/5 at `index.php:8`, checker OK |
| 2 | PASS: 5/5 at `index.php:33`, checker OK |

### Output: round 1

## Fix before merge
1 finding · top impact 4/5 · 1 file

---

### 1. 🔴 [4/5] The database password ships in source, so anyone who can read the repo gets it
`index.php:8`
**Needs:** the `bookshop_app` password set as the `BOOKSHOP_DB_PASSWORD` environment variable wherever this page runs.
**PROPOSED FIX:**
```diff
@@ index.php:5 @@
  5 | $host = '127.0.0.1';
  6 | $database = 'bookshop';
  7 | $username = 'bookshop_app';
-   | // 🟥 Problem: the live credential sits in the file, so every clone, backup or pasted copy hands out database access.
- 8 | $password = 'Tr0ub4dor&3-fake';
+   | // 🟩 Fix: read the password from the environment so it never enters the repo.
+   | // 🟩 An unset variable gives false, which PDO rejects with an uncaught TypeError, so stop on the same 500 page first.
+ 8 | $password = getenv('BOOKSHOP_DB_PASSWORD');
+ 9 |
+10 | if ($password === false) {
+11 |     error_log('Database error: BOOKSHOP_DB_PASSWORD is not set');
+12 |     http_response_code(500);
+13 |     exit('The bookshop is unavailable right now.');
+14 | }
 15 |
 16 | try {
```
**Blast radius:**
- `index.php:13` serves the 500 page on every request until the variable is set, and under PHP-FPM the pool's `clear_env` defaults to yes, so it must go in the pool config as `env[BOOKSHOP_DB_PASSWORD]` rather than the shell.
- `index.php:8` has not reached git history (the repo has no commits yet), so the old password needs rotating only if this file was copied or shared outside the repo.

### Output: round 2

## Fix before merge
1 finding · top impact 5/5 · 1 file

---

### 1. 🔴 [5/5] Every page load sends the database username and password to the visitor
`index.php:33`
**PROPOSED FIX:**
```diff
@@ index.php:31 @@
 31 |     <meta charset="utf-8">
 32 |     <title>Bookshop</title>
-   |     <!-- 🟥 Problem: anyone who opens View Source on any successful page load reads the live database login in plain text. -->
-33 |     <!-- db debug: <?= $username ?> / <?= $password ?> -->
 33 | </head>
 34 | <body>
```
**Blast radius:**
- `index.php:8` holds the leaked password, so if a page with this comment was ever served, the database password needs rotating there, because removing the line cannot recall copies already sent to browsers, proxies or crawlers.
