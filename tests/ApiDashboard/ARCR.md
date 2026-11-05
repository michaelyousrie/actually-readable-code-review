# ApiDashboard

A six-file PHP dashboard that reads service status from a monitoring API and lets the operator
import a feed and open a report. Deliberately vulnerable, like the other fixtures. It checks
that ARCR finds a server-side request forgery and a file inclusion, scores both critical, and
fixes each with validation rather than a filter that is easy to slip past.

Paths in the outputs are relative to `src/`.

## How to run

1. Copy `src/` into an empty folder and run `git init` there. Every file stays untracked.
2. Ask a fresh agent to review the uncommitted changes with ARCR.
3. Never tell the reviewer the expected findings. Compare its output with the table below.

## Expected

| Change under review | Expected finding |
|---|---|
| `ApiClient::fetch()`, called from `fetch.php`, requests any operator-supplied URL server-side, follows redirects, and checks neither scheme nor host | 4/5 or 5/5: one POST reaches internal hosts, the cloud metadata API (169.254.169.254) or a local file via `file://`; one or two findings (the sink and the entry point) both count |
| `view.php` passes `$_GET['view']` straight to `include` | 5/5: `view=/etc/passwd` or `php://filter` reads any file, and `http://` or `data://` is remote or dynamic code execution when the PHP config allows it |
| the SSRF fix | scheme allowlist plus a resolved-IP check that rejects private, loopback and link-local ranges, redirects off or re-checked, and a timeout |
| the inclusion fix | an allowlist of real report files, or basename plus a realpath confined to the templates directory; never the raw parameter |
| token from the environment, status output escaped with `htmlspecialchars` | no hardcoded-secret and no XSS finding |

Anything else the reviewer reports is unplanted and is judged on its own.

## Latest results: 2026-11-05

| Check | Result |
|---|---|
| SSRF | PASS: 5/5 at `ApiClient.php:31`, covering the sink and `fetch.php`, checker OK |
| File inclusion | PASS: 5/5 at `view.php:6`, fixed with an allowlist |
| Fixes | PASS: verified in PHP that the IP filter rejects 169.254/127/private and allows a public IP |
| False alarms | PASS: no hardcoded-secret and no XSS finding |
| Unplanted | an unset `STATUS_API_TOKEN` crashes every page under `strict_types` (4/5); verified it throws a TypeError |

### Output

## Fix before merge
3 findings · top impact 5/5 · 6 files

---

### 1. 🔴 [5/5] Pasted feed URL makes the server fetch internal hosts, the cloud metadata API and any local file
`ApiClient.php:31`
**PROPOSED FIX:**
```diff
@@ ApiClient.php:28 @@
 28 |     /** Import a feed the operator pastes into the dashboard. */
 29 |     public function fetch(string $url): string
 30 |     {
+   |         // 🟩 Fix: allow only http(s) URLs so file://, gopher:// and dict:// cannot read local files or reach internal protocols.
+31 |         $parts = parse_url($url);
+32 |         $scheme = strtolower($parts['scheme'] ?? '');
+33 |         if (!in_array($scheme, ['http', 'https'], true) || empty($parts['host'])) {
+34 |             throw new InvalidArgumentException('Only http and https feed URLs are allowed.');
+35 |         }
+   |         // 🟩 Fix: resolve the host once and reject private, loopback and link-local IPs, including the metadata address 169.254.169.254.
+36 |         $ip = gethostbyname($parts['host']);
+37 |         if (!filter_var($ip, FILTER_VALIDATE_IP, FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE)) {
+38 |             throw new InvalidArgumentException('Feed URL resolves to a non-public address.');
+39 |         }
+40 |         $port = $parts['port'] ?? ($scheme === 'https' ? 443 : 80);
+41 |
 42 |         $ch = curl_init($url);
 43 |         curl_setopt_array($ch, [
 44 |             CURLOPT_RETURNTRANSFER => true,
-   |             // 🟥 Problem: the URL comes straight from the import form, redirects are followed and no scheme or host check runs, so one POST reaches internal services, the metadata API or any local file via file://.
-34 |             CURLOPT_FOLLOWLOCATION => true,
+   |             // 🟩 Fix: stop following redirects, pin the already validated IP, and restrict curl to http(s) so a redirect cannot bounce to an internal host.
+45 |             CURLOPT_FOLLOWLOCATION => false,
+46 |             CURLOPT_PROTOCOLS => CURLPROTO_HTTP | CURLPROTO_HTTPS,
+47 |             CURLOPT_RESOLVE => ["{$parts['host']}:{$port}:{$ip}"],
+48 |             CURLOPT_TIMEOUT => 5,
 49 |         ]);
 50 |         $body = curl_exec($ch);
 51 |         curl_close($ch);
 52 |
 53 |         return (string) $body;
 54 |     }
@@ fetch.php:10 @@
 10 | $url = $_POST['url'] ?? '';
-   | // 🟥 Problem: fetch() now rejects a blocked URL by throwing, and an uncaught throw here is a 500 that can leak a stack trace.
-11 | $body = $client->fetch($url);
+   | // 🟩 Fix: catch the rejection and answer with a 400 and the short reason.
+11 | try {
+12 |     $body = $client->fetch($url);
+13 | } catch (InvalidArgumentException $e) {
+14 |     http_response_code(400);
+15 |     header('Content-Type: text/plain');
+16 |     echo $e->getMessage();
+17 |     return;
+18 | }
 19 |
 20 | header('Content-Type: text/plain');
 21 | echo $body;
```
**Blast radius:**
- `fetch.php:11` now answers a blocked URL with a 400 and a message, so the import form at `index.php:29` shows that text in place of feed contents.
- With redirects off at `ApiClient.php:45`, a feed that returns a 301 to its real location now yields the redirect response body, not the final page.
- IPv6-only feed hosts are rejected, because `gethostbyname` at `ApiClient.php:36` resolves IPv4 only and hands back the hostname itself, which fails the public-IP check.
- No test exercises `fetch()` at `ApiClient.php:29`; add cases for a metadata-IP URL, a file:// URL, and a valid public URL.

---

### 2. 🔴 [5/5] The report chooser runs any file on disk through include
`view.php:6`
**PROPOSED FIX:**
```diff
@@ view.php:3 @@
  3 | declare(strict_types=1);
  4 |
-   | // 🟥 Problem: $_GET['view'] flows straight into include, so ?view=/etc/passwd or php://filter reads any file on disk and can run code.
- 5 | $view = $_GET['view'] ?? 'templates/home.php';
- 6 | include $view;
+   | // 🟩 Fix: resolve the request against a fixed allowlist of real report files and 404 anything else.
+ 5 | $allowed = [
+ 6 |     'templates/home.php' => __DIR__ . '/templates/home.php',
+ 7 | ];
+ 8 | $requested = $_GET['view'] ?? 'templates/home.php';
+ 9 | $path = $allowed[$requested] ?? null;
+10 | if ($path === null) {
+11 |     http_response_code(404);
+12 |     exit('Unknown report.');
+13 | }
+14 | include $path;
```
**Blast radius:**
- `index.php:35` posts `view=templates/home.php`, the one allowed key, so the form keeps working; every new report file must be added to the `$allowed` map at `view.php:5`.
- The free-text placeholder at `index.php:36` now misleads, since any path other than an allowlisted key returns a 404.

---

### 3. 🔴 [4/5] Every page 500s when STATUS_API_TOKEN is not set
`config.php:7`
**PROPOSED FIX:**
```diff
@@ config.php:6 @@
 6 |     'api_base' => getenv('STATUS_API_BASE') ?: 'https://status.example.com/api',
-  | // 🟥 Problem: getenv returns false when STATUS_API_TOKEN is unset, and under strict_types false passed to the ?string token fatals in ApiClient's constructor, so every page 500s.
-7 |     'api_token' => getenv('STATUS_API_TOKEN'),
+  | // 🟩 Fix: turn a missing or empty token into null, which the ?string parameter accepts.
+7 |     'api_token' => getenv('STATUS_API_TOKEN') ?: null,
 8 | ];
```
**Blast radius:**
- `index.php:8` and `fetch.php:8` both construct `ApiClient` with this token and both stop fatally erroring once it can be null.
- With a null token, `status()` at `ApiClient.php:19` sends `Authorization: Bearer ` with no value, so the monitoring API may reject it and every service reads `unknown` at `index.php:24`.
