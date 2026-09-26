# T-04.8 — Connect the second machine through authenticated encryption

**Planned.** [STEPS](../../STEPS.md) owns delivery status. This task pulls the necessary remote-transport portion of R-089 forward for M-04 and informs R-051/R-052. It does not establish public hosting, game admission or identity-provider entitlement checks.

## Outcome

The selected second-client topology can reach the intended community service without exposing lab credentials or gameplay traffic on an unencrypted network connection. The client verifies the intended server's identity before sending credentials, and a failed verification stops the connection.

If two legitimate concurrent game clients are actually demonstrated on one machine and use the existing loopback service, document that evidence and defer remote transport explicitly. A proposed same-machine arrangement is insufficient to waive this prerequisite.

## Needs

- The actual machine/service arrangement selected in [T-04.6](../T-04.6/README.md).
- The [current transport policy](../../ARCHITECTURE.md#4-protocol-and-persistence) and current host/configuration validation on both sides.
- Original diagnostic clients can verify the transport before the second game installation is ready. Shared-state implementation in [T-04.7](../T-04.7/README.md) is an independent workstream.

## Current restriction

The server validates `bindAddress` as `127.0.0.1`, listens on loopback and requires that exact loopback Host header. The Python adapter validates a loopback-only configuration and opens `HTTPConnection("127.0.0.1", ...)`. Changing a config address or opening a firewall port does not provide a supported second-machine connection.

The selected route needs either an explicitly implemented encrypted transport or a documented, authenticated encrypted tunnel that preserves the local endpoints. Neither route has been verified by existing task evidence.

## Work

1. Select one narrow lab route and document each hop, process, trust boundary, endpoint and credential owner. For direct TLS, implement explicit endpoint/server-identity configuration. For a tunnel, verify its authenticated peer and all network hops, with only local plaintext segments inside the declared endpoints.
2. Establish the expected server identity through a trusted setup step, using the selected certificate/trust anchor or pinned host identity. Do not disable verification or accept an unexpected identity automatically to make a test connect.
3. Preserve authentication, request/body bounds, timeout/cancellation, community scoping and compatibility checks. Define hostname/Host-header behavior deliberately; proxy headers must not silently become trusted identity.
4. Provision separate principal-only client configurations. Never copy the administrative key, another participant's key or the whole server configuration to a game client. Keep private keys, certificates where sensitive and credentials in ignored local storage.
5. Fail closed on wrong/untrusted identity, expired credentials and encryption failure. Test the selected route's applicable certificate/host-key failures, timeout, server outage, interrupted connection and recovery. There must be no automatic plaintext fallback.
6. Verify successful authentication and bounded request/response traffic from the second machine, then confirm wrong-community/wrong-principal attempts are rejected. Ensure logs and diagnostics omit secrets. Record endpoint and process restoration after the run.
7. Add exact setup/run/check/remove commands for the chosen route once implemented, including any dependency/license selection and private trust setup. Keep existing local mode's restriction explicit; a development tunnel is not a supported public deployment product.

## Acceptance

- The intended server identity is verified before credentials cross the remote connection; a wrong identity blocks authentication. Every cross-machine hop carrying traffic is encrypted.
- A second-machine diagnostic client reaches the same service under its own principal, while disconnect and rejection remain bounded and recoverable.
- The selected route's setup, failure cases and cleanup are reproducible without committed secrets. Any required game adapter endpoint/configuration changes are implemented and tested.
- Transport evidence is reported separately from game integration. Two synthetic clients or a working tunnel cannot complete M-04.

## Entry points

[Current server configuration validation](../../../src/Community.Server/Configuration.cs) · [Listener and Host checks](../../../src/Community.Server/Program.cs) · [Adapter configuration and HTTP client](../../../src/Community.AdapterLab/service_client.py).

[Current protocol boundary](../T-04.1/protocol.md) · [Transport and persistence design](../../ARCHITECTURE.md#4-protocol-and-persistence) · [Longer-range roadmap](../../ROADMAP.md).
