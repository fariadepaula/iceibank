# Agência-to-Agência calls use a separate service credential, not the caller's JWT

`creditar-remoto` modifies a Conta, so per our own rule every such route needs a valid token — but forwarding the human caller's JWT would couple an internal system call to that session's lifetime (expiry, revocation) for no reason, and conflates "this request came from an authenticated person" with "this request came from a trusted peer Agência," which are different claims.

We use a static shared secret (env var, checked via a request header) known to all three Agência processes instead. It's a separate trust mechanism from user JWTs, not a weaker version of it — a peer Agência is never "logged in" as a Conta.

Consequence: if inter-Agência communication moves off synchronous HTTP (Sprint 2, Pub-Sub), this credential's *transport* changes but the underlying decision — peer trust is a distinct concept from user auth — should carry forward unchanged.
