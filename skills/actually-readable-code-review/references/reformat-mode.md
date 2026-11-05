# Reformat mode

Use this when the developer hands you another reviewer's output (CodeRabbit, Copilot,
`/code-review`, a bot's PR comments, a pasted review) and wants it readable. The result uses
the same contract as a review (`output-contract.md`) and the same method
(`review-method.md`).

## Steps

1. Collect every finding in the source review.
2. For each one, open the code it cites and confirm the defect exists in the current code.
   Drop it when it does not, when the cited code is gone, or when the claim cannot be checked
   against the code.
3. Merge duplicates into one finding.
4. Score each confirmed finding on ARCR's scale. Ignore the source's severity labels.
5. Write your own diff and blast radius, from your own caller search. Never copy the source's
   fix without verifying it.
6. A defect that your verification or caller search proves counts like any other finding.

## Stats line

The stats line ends with the source:

`<N> findings · top impact <X>/5 · <F> files · from <source>: <K> confirmed, <D> dropped`

- `<source>` is the tool's name when known ("CodeRabbit"), otherwise `pasted review`.
- `<K>` counts the source's findings you confirmed, with duplicates counted once. `<D>` counts
  the ones you dropped as unconfirmed. `<K>` never exceeds `<N>`.
- `<F>` counts the files in the reviewed diff. Without a diff, count the distinct files among
  the confirmed findings.

## Example

<!-- example:start review -->
## Fix before merge
1 finding · top impact 4/5 · 6 files · from CodeRabbit: 1 confirmed, 3 dropped

---

### 1. 🔴 [4/5] Password reset links never expire
`src/auth/resetToken.ts:22`
**PROPOSED FIX:**
```diff
@@ migrations/0042_reset_token_expiry.sql:1 @@
+   | -- 🟩 Fix: give every reset token an expiry time.
+ 1 | ALTER TABLE reset_tokens ADD COLUMN expires_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
@@ src/auth/resetToken.ts:22 @@
 22 |   return db.resetTokens.insert({
 23 |     userId,
 24 |     token: hash(token),
+   |     // 🟩 Fix: a new token stops working after one hour.
+25 |     expiresAt: new Date(Date.now() + 60 * 60 * 1000),
 26 |   });
@@ src/auth/resetPassword.ts:14 @@
 14 |   const record = await db.resetTokens.findByToken(hash(token));
-   |   // 🟥 Problem: any stored token works forever, so a leaked reset email can still change the password.
-15 |   if (!record) throw new InvalidTokenError();
+   |   // 🟩 Fix: reject a token once its expiry has passed.
+15 |   if (!record || record.expiresAt < new Date()) throw new InvalidTokenError();
```
**Blast radius:**
- Unused tokens issued before the migration expire at once, because the new column defaults to the migration time (`migrations/0042_reset_token_expiry.sql:1`).
- `tests/auth/resetPassword.test.ts:30` covers a valid token only; an expired token needs its own case.
<!-- example:end -->
