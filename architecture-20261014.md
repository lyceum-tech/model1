# Cluster execution architecture

Original date: 2026-10-14. Revised: 2026-10-15.

Status: proposed architecture, not implemented or performance-qualified. Numerical scale targets and candidate technologies are not production guarantees.

Related specification: [Scheduling, queueing, and cluster execution](scheduling-queue.md). This revision is authoritative where the documents differ: PostgreSQL replaces the initial embedded consensus design; workload identity no longer requires a stable task IP; scheduling and availability objectives are class-specific and admission-backed; advanced sharing, migration, and nested sandbox combinations require separate qualification. Earlier requirements are not implicitly carried forward when they conflict with these boundaries.

## 1. Purpose, boundaries, and requirement levels

Build a cluster-local platform that coordinates expensive capacity, useful work, and recovery across Sonium HPC, CI/batch, GPU inference, and agent fleets. Sonium is a client, not a platform dependency. The differentiation is workload-aware capacity and lifecycle coordination, not reproducing every Compute Engine or Kubernetes facility.

Three layers separate responsibilities:

| Layer | Owns | Does not own |
| --- | --- | --- |
| Execution foundation | Transactional ownership, allocations, operations, machine execution contracts, identities, capability registry. | Workload-specific optimization and business reporting. |
| Workload and policy controllers | Batch, gang, serving and agent lifecycles; admission, scheduling, entitlements, maintenance planning. | Unchecked commands to machines or independent allocation ledgers. |
| Providers and integrations | Runtime, network, storage, Kubernetes, artifacts, BMC and facility interfaces. | Permission to grant new workload ownership or weaken the declared contract. |

Requirements have three levels:

- **Core:** correctness and operational contracts required by every production deployment.
- **Qualified profile:** a supported combination of backend, hardware, runtime and behavior, enabled only after its acceptance tests pass.
- **Candidate:** an experiment or later extension, unavailable as a promised capability until qualified.

Core includes the local control plane, durable queue and operations, transactional allocation and quota enforcement, a replaceable scheduler, explicit recovery rules, audit, and operational controls. Native containers, KVM VMs, Kubernetes execution, GPU/RDMA access and storage providers are qualified profiles, not an arbitrary Cartesian product of supported features.

Candidates include transparent process/VM migration, fractional GPU sharing, custom Kubernetes scheduling, elastic gang recovery, and nested gVisor profiles. Their absence must not prevent ordinary qualified execution.

The scheduler, authority, machine agent, SDK and platform integration code should be Rust. PostgreSQL, OCI runtimes, QEMU/KVM and optional CRIU are dependencies, not rewrite targets. Provider and RDMA native-library requirements are explicit integration decisions.

## 2. Workload contracts and common queue

Use one durable backlog and common resource/accounting model, with distinct workload controllers. The queue is an indexed view of durable intent and dependencies, not a second execution authority. Expose the full relevant backlog through snapshots and incremental views without rescanning it on every scheduling decision.

| Class | Durable identity and controller | Success and recovery contract |
| --- | --- | --- |
| HPC gang | Job, ranks, gang generation and coherent checkpoint lineage. | Full-group readiness, topology-compatible execution, retained progress; initially coordinated restart after rank loss. |
| CI/batch | Job, dependency graph, task and attempt history. | Correct output, completion time, fair access and bounded retry/lost-work policy. |
| Inference service | Service, desired replicas, release and readiness policy. | Request success/latency, ready capacity and safe rollouts; continuously running is not batch completion. |
| Agent fleet | Durable session/workflow, workspace, mailbox and external-operation journal. | Activation latency, durable progress and safe resumption; session identity outlives its current process. |

All workload envelopes declare accounting owner, resource requests, capability profile, topology, priority, capacity contract, recovery policy and required observations. Controllers translate intent into proposals and operations. They do not bypass ownership or fencing rules.

A task persists across attempts. Replacement creates a new attempt and ownership epoch. A terminal attempt never becomes running again. Running, ready and making useful progress are distinct observations.

An agent activation need not create a new VM or Pod. A qualified warm worker pool can host successive activations under explicit isolation, cleanup and ownership rules. Durable agent state stays outside the worker. Suspend compute while waiting when the workload supports it; mailbox delivery, workspace durability and external-effect reconciliation remain active responsibilities.

The SDK reports readiness, application progress, checkpoint commits, quiescence and completion. Reports are evidence, not permission to claim resources. External operations need recorded intent, idempotency keys where available, and outcome reconciliation. The platform cannot promise exactly-once effects against arbitrary third-party APIs.

## 3. Cluster autonomy and failure domain

Essential services run on dedicated management machines or VMs under the host service manager. They do not depend on ordinary scheduled jobs for startup, discovery, credentials, upgrades or recovery. Loss of WAN, global dashboards or submission routing must not stop admitted local work or local control.

One to five management machines is an initial deployment envelope, not a proven sizing limit. One is a development profile. Three is a starting production topology to qualify, not automatic database consensus or fault tolerance. Storage, physical hosts, power and network placement determine actual independence. Larger management capacity may be required by measured load.

Separate three failure scopes:

1. **Component loss:** scheduler, controller, database process, worker or management host loss within surviving local infrastructure.
2. **Cluster disruption:** management-pool loss, power outage, network partition or shared storage failure requiring independent recovery automation.
3. **Disaster:** loss or corruption of local state, trust material or the entire facility, requiring retained recovery material outside the affected failure domain.

Normal operation is local. Disaster recovery may depend on externally retained backups, keys and approved releases. Local autonomy does not justify storing every recovery copy in the same failure domain. WAN artifact delivery and implementation of offsite transport are outside scope; recovery/export interfaces and restore procedures are in scope.

Cross-cluster routers may choose a cluster before admission. An admitted workload has one owning cluster. Moving durable stateful work across clusters requires a separate transfer/fencing protocol; independent resubmission after a timeout is unsafe. Cross-cluster transactions and automatic active-active execution are not initial capabilities.

## 4. Components and authority boundaries

| Component | Responsibility | Constraint |
| --- | --- | --- |
| API and queue views | Submission, desired-state requests, backlog and diagnostics. | Cannot directly launch work. |
| Workload controllers | Batch, gang, serving and agent lifecycle decisions. | Submit bounded transition requests. |
| Admission/policy controller | Capacity contracts, effective limits, entitlement feasibility and maintenance plans. | Policy decisions become versioned durable state. |
| Scheduler | Placement, backfill, preemption and optimization proposals. | No direct worker/provider commands or authoritative allocation state. |
| Reliability authority | Validate ownership, reservations, fencing, transition preconditions, disruption permissions and cluster mode. | Small, conservative semantic contract. |
| State engine | Execute domain transactions and preserve state, effects and recoverable changes. | Defines concurrency and durability semantics. |
| Operation controllers/effect runners | Advance durable workflows, reconcile providers and deliver effects. | Cannot invent ownership or bypass committed permissions. |
| Machine lifecycle controller | Derive eligibility from inventory, health, intent and qualification. | Cannot clear fencing obligations by editing status. |
| Machine agent | Privileged local enforcement and runtime reconciliation. | Executes scoped committed authority; no global scheduling decisions. |
| Providers/adapters | Network, storage, Kubernetes, devices, artifacts and facilities. | Declare capabilities, limits and evidence. |
| Accounting/SLO pipelines | Usage ledger, reports, useful-progress and objective evaluation. | Heavy calculations stay outside allocation transactions. |

These are logical boundaries. Initially a control-server can host the API, authority and controller modules, with a separately deployable scheduler, PostgreSQL, machine agents and restricted helpers. A module does not require its own service or database.

The stable authority implements finite primitives: acquire/release allocation, transfer ownership after fencing, reserve disruption scope, authorize operation step and enforce cluster mode. It validates compiled policy constraints. It does not contain billing formulas, GPU packing heuristics, calendar planning, facility protocols or application checkpoint logic.

Version controller requests, operation schemas and worker protocols independently. A new scheduler can change optimization without expanding its privileges. Changes to authority semantics require invariant and failure testing.

## 5. Replaceable scheduler

The interface is conceptually `SchedulingView -> Proposal`. Views contain workload demand, resource/topology summaries, effective policy, allocations and explicitly fresh-enough observations. Proposals identify affected objects and revisions.

Stateless means no authoritative durable state. Caches, indexes, learned estimates and optimization state may be disposable. Waiting history, entitlements, reservations and operation progress are durable. A replacement reconstructs a snapshot and follows changes without interrupting workloads.

Begin with one active proposer and standby/shadow schedulers. The authority must remain correct under duplicated, conflicting or stale proposals. Shadow evaluation compares decisions and rejection rates before rollout.

Use a responsive placement path and a separately bounded optimization path. Consider useful progress, staging/warm-up, checkpoint cost, migration overlap, service headroom and topology fragmentation. Packing alone is not the objective. Explicitly report infeasible admission promises and repeated policy vetoes rather than silently weakening protection.

## 6. Transactional state contract

PostgreSQL is the first backend. Do not add another authoritative consensus log for the same control state. A later distributed transactional engine is possible only if it implements and qualifies the same semantics; a generic CRUD interface is insufficient.

Conceptual domain operations:

```text
ReadSchedulingView(scope, cursor)
TryCommitProposal(proposal, expected_revisions, policy_version)
AdvanceOperation(operation_id, expected_revision, event)
RecordConsequentialObservations(batch)
ClaimEffects(partition, executor, lease)
ReadChanges(cursor, scope)
```

The contract specifies:

- Atomic allocation, ownership, ancestor-limit and disruption reservations over the affected entities.
- Concurrency behavior equivalent to serial execution for these invariants, whether implemented with locks, conditional updates or serializable transactions.
- Durable acknowledged commits, unique operation/event identities and monotonic ownership epochs.
- Atomic state and outbox writes; at-least-once effect delivery and idempotent consumption.
- Revisioned changes with a documented ordering scope, consistent snapshot/cursor handoff, retention and resynchronization procedure. No unnecessary global ordering of unrelated events.
- Explicit bounds on transaction size, including maximum gang reservations and shared quota contention.

Scheduling reads may lag. Commit-time validation checks current authoritative records and required evidence freshness. Telemetry is not automatically promoted to authoritative state.

**Production automatic failover must not lose acknowledged ownership/allocation commits and must fence competing database writers.** Select replication, failover and storage settings to satisfy that contract. If it cannot be established, stop new mutations and recover explicitly. Replica count alone proves nothing.

Disaster restore from an older backup is a different protocol: isolate old authority, reconcile or fence surviving execution, establish a new recovery generation, and validate resource ownership before admission resumes. Replaying an old epoch counter is unsafe. Define backup RPO and restore RTO separately from ordinary failover durability; numerical targets remain launch gates.

## 7. Bounded transitions and durable asynchronous operations

```text
transition(relevant_state, command_or_event)
    -> mutations + durable_effects + result
```

Each evaluation is deterministic, bounded and side-effect-free. Time and identifiers are explicit inputs. Read only the relevant entities; there is no single transaction or function over the whole cluster. Independent transitions can execute concurrently, with shared invariants checked transactionally.

```text
Command / proposal / observation / persisted timer
    -> validated transaction
    -> state + outbox commit
    -> effect delivery / provider inspection
    -> observation
    -> next bounded transition
```

Hours or days of waiting are durable operation phases, never open transactions, sleeping RPCs or retained controller threads. Persist deadlines, retries, provider references and the next inspection time. Reconstruct timers after restart.

Every operation phase specifies entry preconditions, mutations, effects, accepted events, cancellation, timeout and crash recovery. A timeout is evidence of uncertainty, not proof that an external action failed or stopped. Cancellation may need safe completion rather than rollback.

If a provider accepted a command before the controller crashed, reconcile by operation identity or inspect actual state. Do not repeat non-idempotent actions blindly. Delivery leases do not fence an already issued external action. Workers/providers require the appropriate epoch, idempotency or physical/resource fencing mechanism.

## 8. Ownership, failure behavior and local continuation

Every assignment specifies its authority epoch, execution profile, lease/continuation behavior, local retry limits and protected resources. Root privilege on a host cannot fence a remote database or third-party API; those resources need their own enforcement or application protocol.

| Event | Required behavior |
| --- | --- |
| Scheduler crash/update | Existing work continues; rebuild disposable views. |
| Controller crash | Resume from operation state and inspect ambiguous effects. |
| Database unavailable | No new authoritative allocations; existing work follows its continuation contract. |
| Worker partition | No unsafe replacement merely because heartbeats stopped. Fence the old owner or wait for a qualified lease/resource-enforcement mechanism. |
| Worker-agent restart | Reconcile its journal with actual runtimes; do not kill healthy work by default. |
| Host reboot | New boot identity; stale assignments do not authorize resurrection. |
| Provider timeout | Preserve ambiguous operation and reservations until reconciled or safely fenced. |
| Management-pool loss | Independent automation restores control; admission remains blocked until authority is established. |
| WAN outage | Local control and cached approved dependencies remain usable. |

Continuation profiles distinguish independently safe computation from exclusive mutable work. A compute attempt may continue while disconnected if no conflicting replacement is authorized. A workspace writer or effectful agent must stop or lose protected access when its qualified authority expires. Document clock, watchdog and enforcement assumptions for lease-based fencing; expiry in the database alone does not stop a process.

The architecture deliberately chooses safety over replacement availability when ownership cannot be established. It does not promise unrestricted disconnected execution and immediate exclusive replacement simultaneously.

## 9. Capacity contracts, hierarchy and admission

Every workload belongs to one `organization -> team -> service` path. Service is an accounting owner for any workload class. Use stable IDs and preserve historical ownership.

| Concept | Meaning | Enforcement |
| --- | --- | --- |
| Limit | Maximum concurrent resource reservation allowed at a hierarchy level. | Atomic checks at every ancestor. |
| Entitlement | Explicit capacity or service commitment under stated conditions. | Admission feasibility, reserved headroom and declared failure assumptions. |
| Borrowing | Extra capacity available subject to reclaim. | Explicit victim eligibility, notice, checkpoint/lost-work and reclaim policy. |

Initial deployments can provide limits plus best-effort execution. Guaranteed-start profiles must not be exposed until entitlement admission and capacity backing are implemented and qualified. Borrowing must not weaken an existing commitment silently.

Limits are vectors: CPU, memory, storage, and GPU class/allocation mode. Each allocation fits the current machine/device capacity and every ancestor limit. Child limits may sum above a parent limit; they are ceilings, not guarantees. A quota does not establish physical availability. Compute Engine makes the same quota/reservation distinction. [GCE quotas](https://docs.cloud.google.com/compute/resource-usage), [GCE reservations](https://docs.cloud.google.com/compute/docs/instances/reservations-overview).

Entitlements specify resource class, topology, concurrency, time interval, failure assumptions and start/progress commitment. Admission accounts for fragmentation, existing promises, maintenance, recovery headroom, staging and reclaim latency. A guaranteed request that cannot be backed is rejected or explicitly offered best effort, not admitted under an impossible promise.

Quota policy updates and reports may be asynchronous. Allocation enforcement is not. A decrease below usage blocks growth without implicitly killing work. Reparenting requires drained reservations or a validated atomic transfer; history is unchanged. Warm pools, recovery reserve and source/destination overlap have explicit owners.

Begin with transactional ancestor counters; benchmark hot organizations. Bounded delegated budgets may reduce contention later, provided their sum never exceeds the parent and transfer is transactional. Delayed reporting cannot enforce a hard cap.

## 10. Workload-specific objectives and measurement

No universal five-minute scheduling SLO, 95% replica-availability default, or 90% gang-goodput promise is adopted. Targets require measured workloads, capacity backing and a versioned admission profile.

| Class | Objective to qualify | Necessary contract |
| --- | --- | --- |
| Capacity-backed batch/gang | Eligible-to-full-allocation and eligible-to-ready deadlines. | Bounded request size/topology and backed capacity. A 99% within five minutes target is a candidate for a specified cohort only. |
| Best-effort batch | Queue-age distributions, starvation indicators, completion and retained-progress measurements. | Explicit fairness and reclaim rules; no invented start guarantee. |
| Serving | Request success/latency, time below minimum ready capacity, recovery and rollout duration. | Reserved headroom, failure-domain spread and bounded disruption. |
| Agents | Activation latency by warm/cold path, durable mailbox age and workflow recovery. | Session/workspace persistence, worker capacity and external-effect recovery. |
| HPC execution | Productive gang availability, retained goodput and lost resource-hours. | Application progress/checkpoint instrumentation. |
| Infrastructure | Qualified capacity-time and restoration time by device class and failure domain. | Fresh observations and declared maintenance accounting. |

Record submission, admission, eligibility, full allocation, process start, application readiness and completion separately. Capacity waiting after eligibility counts against an admitted start deadline. Report pre-admission delay too, so withholding admission cannot hide poor experience. Pending work crossing its deadline is a miss; completed-only samples are invalid. Partial gang placement is not successful allocation.

For continuously required replicas, ready replica-time divided by desired replica-time is a useful diagnostic, not a complete availability contract. Also measure minimum/quorum violations, longest outage and request behavior. Dormant agent sessions do not count as failed replicas. Desired-count changes cannot retrospectively erase outages.

Goodput credits useful work retained in a committed checkpoint or final output relative to reserved resource-time. Startup, blocked ranks, checkpoint pauses and replay remain in the denominator under a declared weighting model. Uncheckpointed progress is provisional. Without qualified instrumentation, report proxies and coverage, not claimed goodput compliance.

Publish gross and any prospectively agreed maintenance-adjusted availability. Separate CPU/GPU classes and correlated rack/power/cooling failures. SLO evaluators run asynchronously; safety constraints remain synchronous. An error budget is not permission to violate fencing or disruption limits. Targets and missing evidence are visible and versioned.

## 11. Machine inventory and lifecycle

Maintain a machine database within the state engine. A management-tier lifecycle controller combines host-agent, BMC/Redfish/IPMI, hypervisor and maintenance evidence. Its schema separates:

- Identity: asset ID, enrollment generation, host/VM type and boot incarnation.
- Inventory: CPU/NUMA, memory, disks, NICs, GPUs, firmware and software digests.
- Dependencies: physical parent, rack, power, cooling, network and storage relationships.
- Observations: reachability, power, faults, source, timestamp and freshness.
- Administrative intent: eligible, drain, upgrade, repair, quarantine or retire.
- Operation phase and provider references.
- Qualification, effective resource capacity, ownership and fencing evidence.

Operator labels are derived summaries, not the sole state machine:

| Label | Meaning |
| --- | --- |
| DISCOVERED / INSTALL / VALIDATING | Enrollment, installation or qualification incomplete. |
| READY | Required checks pass and no blocking intent; occupied capacity can still be healthy. |
| DRAINING / UPGRADE / REPAIR | A lifecycle operation restricts placement. |
| DOWN | Host execution unavailable, management path reachable. |
| HARDDOWN | Host and management paths unavailable with sufficient evidence for intervention. |
| UNKNOWN | Evidence stale, contradictory or insufficient. |
| QUARANTINED / RETIRED | Explicit integrity/administrative restriction. |

A machine in REPAIR may also have unreachable host and BMC observations. Preserve both facts. HARDDOWN does not prove power-off, fencing or safe intervention. Correlated network failures and authentication errors must not become false physical diagnoses. Device-only faults may reduce capacity without disabling the whole host.

Typical repair operation:

```text
Requested -> PlacementDisabled -> Draining -> AwaitingFencing
    -> ReadyForIntervention -> RequestingRepair -> AwaitingRepair
    -> Validating -> Completed
```

Repair may wait days. `safe_for_intervention` requires workload, guest, device, storage and power preconditions, independently of the summary label. Provider completion never directly sets READY. Placement and drain race through the same revision/eligibility checks. Management hosts use a separate availability-preserving maintenance procedure.

## 12. Privileged machine agent and qualified execution

Run one root/privileged machine agent under the host service manager on each natively managed host; a managed guest agent has authority only inside its VM. Management machines use an infrastructure-only profile. The agent is essential infrastructure, not a scheduled workload.

Keep the privileged supervisor small. Artifact transfer, telemetry and complex parsers run as restricted helpers where practical. Reserve CPU, memory, journal disk and control-network capacity. A separately bootstrapped updater/recovery path must repair a failed agent release.

The agent validates cluster/machine identity, enrollment, operation ID, control generation and workload epoch. It journals accepted assignments, effects, runtime IDs, attachments and unacknowledged outcomes outside workload storage. Durable acceptance and successful execution are different acknowledgments. Journal loss blocks new ownership-sensitive actions pending reconciliation.

Local autonomy is bounded by assignment: probing, resource enforcement, allowed retries and continuation. A local process restart is not permission to create a replacement attempt. Gang and effectful-agent recovery follow their controller contracts. On reconnect use jitter, bounded buffering and explicit reconciliation.

Initial runtime profiles to qualify independently:

| Profile | Required mechanism | Initially excluded unless separately qualified |
| --- | --- | --- |
| Native OCI container | Namespaces, cgroup v2, OCI runtime, private writable layer, scoped network/volumes and security policy. | Transparent checkpoint/migration and arbitrary device sharing. |
| KVM VM | QEMU/KVM, per-VM writable storage, host cgroups, restricted VMM identity and management socket. | Live migration, GPU passthrough and nested application sandbox combinations. |
| Exclusive GPU container | Qualified OCI profile plus device ownership, driver/runtime and topology validation. | Fractional sharing and transparent GPU checkpoint. |
| HPC transport | Declared TCP or separately qualified RDMA NIC/fabric profile. | Assuming veth/private addressing implies RDMA isolation. |

Native binary bundles execute inside a qualified sandbox; they are not an unrestricted host-process API. CRIU complements namespaces/cgroups for supported process checkpointing; it is not the container runtime or VM snapshot engine.

Preparation and cleanup have durable receipts. Verify process trees, mounts, devices and contexts are released before making capacity available; parent-process exit is insufficient. VMM-running, guest-booted and application-ready are distinct.

Support a hardened container-confined VMM profile: the userspace VMM is confined; KVM remains in the host kernel. Launch the VMM unprivileged where supported, grant only necessary descriptors/devices, and exclude blanket privileged containers or host-control sockets. Container confinement and a VM boundary are not independent guarantees against all host-kernel/device failures.

VMM-inside-gVisor remains experimental: gVisor's KVM platform does not establish arbitrary QEMU `/dev/kvm` support inside its application sandbox. gVisor within a guest, using a supported platform such as systrap, is a separate candidate. Qualify the complete stack, including overhead, devices and recovery. [gVisor platforms](https://gvisor.dev/docs/user_guide/platforms/), [compatibility](https://gvisor.dev/docs/user_guide/compatibility/).

## 13. Storage, checkpoints and workspace ownership

Storage is an explicit provider contract, not a consequence of P2P artifact distribution. Reuse qualified storage systems; building a distributed filesystem is outside the initial platform scope.

| Data | Durability and lifecycle |
| --- | --- |
| Immutable software/model artifacts | Verified manifests, retained seeds, cache eviction and approved release policy. |
| Ephemeral scratch | May be lost with an attempt; never the only acknowledged durable result. |
| Persistent workspace/volume | Declared writer model, attach fencing, durability, quota, backup and deletion policy. |
| Checkpoint | Committed payload plus manifest, application generation and compatibility metadata. |
| VM writable disk | Explicit persistent or ephemeral contract, separate from immutable base image. |
| Control/accounting state | Database durability, recovery and retention contract. |

A provider declares consistency, failure domains, attach/detach semantics, snapshot consistency, encryption/key access, restore latency and fencing capability. Single-writer handoff requires enforcement at the actual storage boundary or qualified old-owner fencing. Unmount requests and network disconnection alone are not proof.

Publish checkpoints only after payload and manifest are committed. Gang checkpoints identify coherent membership/generation. Restore checks runtime, CPU/device, volume and application compatibility before ownership/endpoint exposure. Application checkpoint/restart is the baseline recovery option where transparent snapshots are unsupported.

Snapshots can contain credentials and private memory. They are access-controlled tenant data, not automatically eligible for the shared artifact swarm. Retention/garbage collection respects live operations, workspace references, audit policy and recovery pins. Test restore, not merely backup creation. Offsite retention and total-cluster restoration requirements must be selected before production launch.

## 14. Networking and discovery

Separate stable workload identity, logical service endpoint and current execution address. Private workload networks and explicit ingress/egress policy are required. A stable IPv6 address per logical task is optional provider functionality, not a portable core requirement. Stable addressing does not preserve TCP/RDMA connections or establish ownership after restart.

The network provider declares address allocation, routing/overlay behavior, network isolation, source validation, tenant visibility, attach/detach and any stable-address handoff. Native containers use qualified namespace attachments; VMs use qualified virtual NIC paths. Reuse network providers rather than building a general SDN as part of the scheduler.

Keep workload traffic away from management, BMC and facility networks except for narrow permissions. Private addresses alone are not isolation. Device/RDMA paths require fabric and DMA qualification beyond ordinary namespace networking.

Provide cluster-local logical service discovery with authenticated watch/resolve and a DNS projection. Initially store durable service definitions and authorized endpoint assignments in the existing state engine, serving cached indexed views. Health is bounded soft state; DNS queries do not trigger database reads. Define TTL/staleness policy, snapshot/cursor recovery and reconnect behavior.

Publish endpoints only for authorized ready attempts. Withdraw/drain through lifecycle operations, recognizing that cached DNS and existing connections outlive withdrawal. Discovery is not fencing. A dormant agent may use a qualified activation gateway rather than an obsolete worker address.

Bootstrap uses pinned identities and addresses for trust, database, API and artifact seeds. It works before DNS or the runtime registry. Runtime discovery failure must not prevent restoring discovery itself. No service mesh or additional consensus database is mandatory.

## 15. GPU capacity and useful economics

Optimize useful output per installed GPU-hour under latency, fairness, isolation and recovery constraints. Allocation occupancy is a diagnostic, not the objective.

Inventory device identity/class, memory, health, driver/runtime compatibility, partition state and CPU/NUMA/PCIe/NVLink/NIC/fabric relationships. Requests distinguish device count, memory requirement, compute entitlement, topology and isolation. Whole-device, hardware-partition and software-sharing units are not interchangeable fractions.

Begin with exclusive-device allocation, topology-aware gangs, inference headroom and qualified release/reset behavior. Evaluate hardware partitioning and software sharing separately against this baseline. Ordinary GPU time slicing does not provide MIG-equivalent memory/fault isolation. [NVIDIA sharing documentation](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/25.3.4/gpu-sharing.html).

GPU operations are durable workflows:

```text
ReclaimRequested -> DisruptionAuthorized -> QuiesceOrCheckpoint
    -> StopOrQualifiedResize -> VerifyRelease -> CapacityAvailable
```

Device reset, driver maintenance and partition reconfiguration reserve the entire actual impact domain. Check IOMMU groups, DMA/peer access, reset scope and guest/sibling effects. A timeout cannot free a device in accounting while old contexts may remain active.

Stage data/models before reserving scarce devices where feasible. Protect inference warm capacity according to measured latency. Separate intentional reserve from fragmentation, unhealthy capacity, insufficient demand, loading, data starvation and lost work. Measure completed HPC/CI work, retained progress, inference throughput under latency constraints, activation delay, reclaim time, power and GPU-hours lost.

Evaluate [Run:ai](https://github.com/dsx-ai-factory/run-ai) and [KAI Scheduler](https://github.com/kai-scheduler/KAI-Scheduler) component by component: topology/gang scheduling, resource hierarchy, fraction enforcement, workload modeling and reproducible tests. Public availability is not qualification. Pin versions and compare identical workloads. A Kubernetes deployment may delegate scheduling to a qualified KAI integration; two schedulers must never allocate the same GPU capacity independently.

## 16. Kubernetes compatibility and ownership

Compatibility means a shared workload/admission/accounting contract with declared backend capabilities, not identical execution guarantees or a replacement implementation of every Kubernetes API.

| Backend | Platform owns | Backend owns |
| --- | --- | --- |
| Initial Kubernetes integration | Durable platform intent, workload controllers, business limits, operation history and accounting. | Kubernetes owns node placement, Pod execution and its network/storage resources. |
| Native execution | Placement, native assignments and machine lifecycle for enrolled resources. | Qualified runtime/network/storage providers implement effects. |
| Later custom Kubernetes scheduler | Placement for explicitly assigned pools plus platform lifecycle. | Kubernetes retains Pod execution and its resource state. |

A local platform reservation in integration mode is a business accounting reservation, not a firm reservation of Kubernetes node capacity. Guaranteed-start admission requires a qualified dedicated-capacity arrangement or a coordinated admission integration. Declare guarantees unavailable otherwise.

Select one authority per decision and field. If Kueue/KAI or customer policy performs admission, define its relationship to our business limits and entitlement promises. Do not combine independent fairness, reclaim and admission loops without an explicit hierarchy. Native agents do not restart kubelet-owned Pods or manipulate their cgroups.

The database/Kubernetes boundary is asynchronous: record desired effects, create or inspect objects using stable identities, and reconcile actual status. API acceptance is not placement, readiness or gang success. There is no cross-database atomic transaction. CRDs may expose intent/status but are not an independent allocation ledger.

Custom scheduling starts only on dedicated pools with enforced admission isolation; `schedulerName` alone does not reserve resources. Customers without host privilege get a restricted profile using their automation interfaces, with host repair, power, device reset and fencing capabilities declared accordingly.

Kubernetes native quotas are namespace-scoped; our hierarchy adds business semantics, not automatic physical capacity. [Resource quotas](https://kubernetes.io/docs/concepts/policy/resource-quotas/). Standard upstream scale guidance describes up to 5,000 nodes; larger GKE profiles have their own constraints. Qualify our actual workload mix rather than asserting Kubernetes cannot operate at 25,000 nodes. [Upstream guidance](https://kubernetes.io/docs/setup/best-practices/cluster-large/), [GKE planning](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/planning-large-clusters).

## 17. Artifacts, installation and datacenter-local P2P

Use immutable identified bundles, OCI images, VM bases, model weights and host/runtime packages. A local publication boundary receives artifacts from an external delivery system; WAN distribution is out of scope. Publication verifies approved metadata and required local seed retention before deployment can rely on it.

Use [iroh](https://docs.iroh.computer/) and [iroh-blobs](https://github.com/n0-computer/iroh-blobs) as candidates for local transport and verified blob transfer. Peer selection, authorization, replication, retention and rollout remain platform responsibilities. Pin compatible releases and qualify them. Public discovery/relay dependencies are excluded; use explicit local peers and local relay infrastructure only if needed.

Artifact helpers fetch from authorized peers with bounded concurrency and seed fallback. Hash possession does not grant access. Authenticated manifests bind format digests and transfer hashes; an OCI SHA digest and BLAKE3 transfer hash are not interchangeable. Verify the original format digest before activation. Signed release metadata governs publisher trust, compatibility, rollback and revocation. Keep credentials out of shared artifacts.

Separate installation adapters: OCI runtime import, sandboxed bundle extraction, VM base plus writable disk, and privileged host upgrade. Do not unpack untrusted packages as root or expose arbitrary installer scripts as the automation API.

```text
Requested -> Authorized -> Staging -> Verified -> Prepared
    -> Activating -> HealthChecking -> Completed
```

Persist exact desired/observed digests and recovery receipts. Pin active, rollback and recovery artifacts. Rollback of software does not imply rollback of schemas or application data. Bound disk/CPU/network use so P2P does not starve control, checkpoint or HPC traffic. Cross-tenant caching must respect confidentiality and authorization.

## 18. Turnup, zero-touch production and independent recovery

ZTP means zero-touch production: humans submit governed intent, while automation executes changes. Production denies interactive host/container/VM/database/BMC access, including SSH, exec/attach and consoles. Scoped diagnostics and recovery APIs must be sufficient to operate this policy.

Provide a resumable entry point, initially a script around versioned tooling:

```sh
./turnup --seed /path/to/cluster-seed.yaml
./turnup --seed /path/to/cluster-seed.yaml --resume
./turnup --seed /path/to/cluster-seed.yaml --check
```

The signed seed specifies cluster/security identity, management inventory, trust anchors and credential references, pinned bootstrap endpoints, release digests, network/storage configuration, database durability profile, enabled capabilities and readiness thresholds. It contains no reusable private keys. Powered machines with a trusted bootstrap image and reachable provisioning path are prerequisites; bare-metal imaging is a separate provider phase.

Turnup validates prerequisites, claims bootstrap ownership, installs foundational host services, initializes or discovers storage, starts identity/API/authority/discovery/artifact services, enables controllers/adapters, qualifies workers, runs an end-to-end canary and emits a capability-specific readiness report.

Before database availability, a bootstrap journal and per-machine receipts preserve idempotency. Import them with an explicit handoff using the same operation identities. Conflicting seeds or ambiguous initialization never authorize destructive reformatting. Repeated invocation reconciles; `--check` is read-only. Turnup cannot clear incident latches or revive stale ownership.

Automation must recover the automation. Maintain independently bootstrapped management access, trust material, approved recovery images and database restore tooling. Restrict recovery operations; it is not a hidden arbitrary remote shell. The recovery path must remain usable after a bad agent/control-server deployment and loss of normal discovery. Define who can authorize recovery and how its authority is revoked/reconciled.

Development-only breakglass is disabled under production profiles. Sessions are scoped, expiring and audited, exclude conflicting automation and require reconciliation or reimaging afterward. Production enrollment removes development credentials/endpoints; a normal API toggle cannot enable them.

Production launch requires demonstrated automated recovery from management-pool loss and a failed automation rollout, plus a disaster-restore exercise. Recovery procedure completion is part of the ZTP requirement, not deferred operational documentation.

## 19. Panic, planned shutdown and emergency action

Use explicit durable cluster modes with separate recovery latches. Mode precedence for disruptive action is emergency safety handling, panic restrictions, planned shutdown restrictions, then ordinary operation. A less restrictive mode never clears a stronger latch implicitly.

**Panic:** one authorized SRE action commits a freeze and advances the control epoch. No new ordinary orchestration permission may be committed afterward. Hold undispatched effects; executors check current authority. Continue observations, audit and non-disruptive reconciliation. Hardware protection and existing ownership/lease enforcement continue.

Panic is not instantaneous physical quiescence. Already accepted provider operations and bounded delegated actions may finish; unreachable workers cannot acknowledge immediately. Expose commit time, propagation/acknowledgment status, in-flight effects and disconnected authority-expiry bounds. Fail closed for fresh mutations when authority cannot be established. An independent recovery channel may further disable executors when the database is down, but cannot grant placements or silently resume.

Resume is explicit and audited: reconcile real state, revalidate held work and release at bounded rate. Never blindly replay a backlog. Panic has no automatic expiry.

**Planned shutdown:** stop admission/growth, reserve required shutdown resources, drain services, checkpoint or terminate under workload contracts, verify release and persistence, stop workers, then stop management/database components in the qualified order. A separate out-of-band runner completes actions after the database is intentionally down. Customer windows and explicit disruption permissions still apply.

**Emergency shutdown:** a preauthorized, scoped one-action interface invokes facility-approved hazard runbooks over an independently operable path. It can override panic and maintenance windows, does not wait for checkpoints, and does not depend on the scheduler/database. Power/cooling order comes from facility engineering. This is integration with safety infrastructure, not a replacement for fire protection, hardware interlocks or emergency power-off systems.

Record outcomes locally when central audit is unavailable and reconcile afterward. Power restoration does not authorize workload restart. Inspect facility state, restore management authority, reconcile storage/device ownership and explicitly clear applicable latches before admitting work. Test hazardous paths through approved simulation or controlled environments.

## 20. Facility telemetry and customer maintenance

Maintain facility inventory and dependency edges for feeds/UPS/PDUs, fans/air handling, liquid-cooling CDUs/pumps/loops/leak sensors, racks and emergency zones. Preserve redundancy relationships and physical VM ancestry. A facility adapter ingests readings; it does not become the physical safety controller.

Observations include source/ingestion timestamps, units, sequence/quality and freshness. Define sampling and alarm-latency targets per qualified provider; “real time” is not a universal subsecond guarantee. Raw high-rate telemetry stays outside allocation transactions. Persist consequential alarms and conservative eligibility/power summaries. Unknown sensors and observer network failure remain explicit uncertainty.

Translate qualified conditions into placement limits, drain or shutdown proposals with their real impact scope. Independent hardware protection remains active during panic/control-plane outages. Autonomous facility actuation beyond approved emergency interfaces is a separately qualified capability.

Maintenance windows support dedicated machines, VM sets and authorized inventory scopes. Record timezone/DST policy, UTC occurrences, allowed operations, preparation permissions, target snapshot, duration estimate, latest start, overrun handling and impact permissions.

Distinguish two contracts:

- **Start window:** disruptive work may begin in the interval; completion may extend under the declared policy.
- **Bounded disruption window:** the plan must budget execution, validation and safe completion within the interval; admission needs sufficient slack/capacity. Unexpected overruns still require safe completion and escalation, not an impossible hard-stop promise.

The UI/API must state which applies. A window is permission, not an obligation to disrupt. GCE's conventional sole-tenant maintenance windows illustrate why start time and completion bounds must be distinguished. [Sole-tenant maintenance](https://docs.cloud.google.com/compute/docs/nodes/sole-tenant-nodes).

Host maintenance expands to affected guests and shared device/reset domains. Guest-only updates expand to host/siblings only when their actual mechanism requires it. One VM owner's permission is not permission to reboot a shared host. Calendar conflicts or insufficient capacity produce a visible infeasible plan, never silent authorization.

Stage beforehand if allowed; revalidate scope, windows, health and disruption budgets at execution. Do not start a non-interruptible action without its required allowance. Preserve safe completion on overrun, record exceptions and validate before returning capacity. Report maintenance capacity cost and gross/adjusted availability separately.

## 21. Accounting and billing exports

Emit accounting events atomically with allocation changes. Idempotent ledger ingestion preserves allocation ID, resource class/quantity, owner hierarchy, policy revision and effective interval. Reservation, measured activity and billable usage are separate quantities.

Initially report core-hours, memory GiB-hours, GPU-hours by class/mode and storage GiB-hours. Define charging start/end, failed-start treatment, platform faults, shared pools and migration overlap before invoicing. Rate cards are effective-dated and applied asynchronously; they do not change raw usage history.

Missing heartbeats do not invent release timestamps. Mark unresolved intervals provisional; late events produce auditable adjustments or recomputation. Report completeness watermarks, provenance and drill-down to allocations. Owner moves and rate changes do not rewrite closed history silently.

Reporting may lag without blocking scheduling while durable events remain retained. Bound retention/backpressure and alert before exhaustion. External billing aggregation is not a local execution dependency.

## 22. Scale qualification and operational budgets

25,000 machines and 2.5 million cores are design inputs, not an achieved envelope. Before claiming support, specify concurrent tasks/sessions, backlog, launches/activations per second, report sizes/rates, gang widths, discovery watches, artifact fanout and correlated failure bursts.

For illustration, 25,000 machines reporting every five seconds generate 5,000 machine reports/second before task events. This does not require a transaction per report. Coalesce telemetry, index durable changes, shard observations and use disposable scheduling/discovery views. Bound transaction width and prevent reporting storms from starving ownership/recovery.

Measure submission/admission, scheduling, commit, ready, reclaim and recovery latency separately. Benchmark organization-level quota contention, large gang reservations, device release, warm-pool activation, outbox backlog and database failover under load. Single healthy steady-state throughput is insufficient.

Management sizing follows these measurements and the selected fault model. No promise that five VMs suffice regardless of task churn. Record saturation behavior, backpressure, retry bounds and capacity headroom. Database replacement is justified by demonstrated bottlenecks and semantic conformance, not by core count alone.

## 23. Lessons and comparison with public systems

Public papers and interfaces inform decisions; they do not disclose complete internal implementations or qualify our design.

| Reference | Lesson to retain | Boundary for this platform |
| --- | --- | --- |
| Borg/Omega | Cell autonomy, separation of placement policy from authoritative validation, cached scheduling state and concurrency control. | Preserve local failure domains and small authority; do not assume a paper supplies a reusable production implementation. |
| Compute Engine | Explicit infrastructure lifecycle, quota versus capacity reservation, maintenance/recovery limits. | Integrate infrastructure providers instead of silently promising all private-cloud services. Application recovery remains explicit. |
| Kubernetes | Declarative intent, reconciliation, replaceable controllers and runtime/network/storage interfaces. | Reuse execution where present; add workload progress and capacity contracts without turning every agent activation into infrastructure churn. |
| Twine/Tupperware | Application-aware maintenance and large-scale resource management. | Evaluate ideas against our cluster-local dependency/failure boundary. |
| Slurm | HPC topology, queue policy, accounting and backfill informed by runtime assumptions. | Preserve gang/progress requirements while adding serving and durable-agent controllers. Terminology such as gang scheduling differs across systems. |
| Kueue/KAI/Volcano/YuniKorn/Armada | Queue admission, sharing, placement and orchestration can be distinct layers. | Select one owner per decision; avoid stacking competing admission/preemption authorities. |
| Run:ai | GPU economics, topology, hierarchy and runtime enforcement deserve separate evaluation. | Adopt qualified components or ideas without assuming portable GPU isolation or performance. |
| AX/Agent Substrate | Agent identity, workspaces and activation can be modeled above ephemeral execution. | Treat agent state as a first-class workload concern; do not inherit a specific Kubernetes/Redis/PostgreSQL implementation unquestioned. |
| AWS public engineering guidance | Static stability and idempotent operations reduce dependency and retry failures. | Inform continuation and durable operations; do not infer Amazon's undisclosed scheduler internals. |

The evolution from Borg to Kubernetes and agent-oriented substrates does not invalidate reconciliation. It changes the useful abstraction and update frequency: infrastructure allocation can be relatively coarse while durable agent sessions activate frequently. Separate those lifetimes and measure whether the substrate meets actual activation requirements.

Useful references:

- [Borg paper](https://research.google.com/pubs/archive/43438.pdf), [Omega](https://research.google/pubs/omega-flexible-scalable-schedulers-for-large-compute-clusters/), [Borg, Omega, and Kubernetes](https://research.google.com/pubs/archive/44843.pdf).
- [Twine paper](https://www.usenix.org/system/files/osdi20-tang.pdf), [Meta Rebalancer](https://github.com/facebook/rebalancer).
- [Slurm scheduling](https://slurm.schedmd.com/sched_config.html), [Kueue overview](https://kueue.sigs.k8s.io/docs/overview/).
- [AX](https://github.com/google/ax), [Agent Substrate architecture](https://github.com/agent-substrate/substrate/blob/main/docs/architecture.md).
- [AWS static stability](https://aws.amazon.com/builders-library/static-stability-using-availability-zones/), [idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/).
- [GCE live migration](https://docs.cloud.google.com/compute/docs/instances/live-migration-process): GPU-attached VMs are a concrete example of why maintenance must support restart/application recovery instead of promising universal live migration.
- [Kubernetes disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/): disruption budgets constrain supported voluntary actions; they are not application availability guarantees.

## 24. Delivery sequence and acceptance gates

### Stage 1: establish correctness and operational foundations

Specify the failure model, state contract, ownership/lease semantics and database failover/restore protocol. Implement PostgreSQL transactions, deterministic transitions, outbox reconciliation, basic queue/limits, machine inventory and a small native OCI profile. Build turnup, local artifact staging, discovery, audit, panic and independent recovery with this first production boundary.

Gate: concurrent proposals cannot overallocate; stale owners cannot reacquire resources; interrupted effects reconcile; no acknowledged ownership is lost during qualified failover; restore cannot resurrect stale assignments; WAN-disconnected bootstrap/recovery works; panic reports its actual propagation limits.

### Stage 2: useful mixed workloads and expensive devices

Qualify exclusive GPU execution, gang readiness and application checkpoint/restart, batch fairness, serving readiness/disruption, and the basic KVM profile independently. Implement capacity entitlements before exposing bounded-start commitments. Add workspace storage, durable agent sessions and warm activation as their own lifecycle contract. Establish usage exports and workload-specific measurements.

Gate: compare useful output and recovery against representative Sonium HPC/CI and inference baselines. Test partial gang startup, repeated preemption, noisy capacity demand, GPU release uncertainty, workspace fencing, model cold-start storms and agent external-effect recovery. Do not use aggregate GPU utilization as the acceptance result.

### Stage 3: customer integration and qualified scale

Qualify Kubernetes integration, customer windows and provider-specific infrastructure workflows. Increase load through representative task churn and correlated failures. Validate facility telemetry and emergency interfaces with the responsible operators. Publish the supported deployment envelope and capability matrix.

Gate: no conflicting kubelet/native ownership; Kubernetes outage leaves intent/history available; calendar impact expansion is correct; management loss, restore, stale observations and mass reconnect preserve invariants. Production emergency recovery and ZTP exercises pass. Report measured management capacity and limitations.

### Later capabilities

Custom Kubernetes placement, shared GPU profiles, transparent migration, nested sandboxes, elastic gangs and alternative databases require independent design/qualification. A new capability must state its authority boundary, resource/accounting semantics, failure recovery and interaction with panic/maintenance before admission can expose it.

## 25. Decisions required before production promises

| Decision | Required evidence |
| --- | --- |
| Database HA, writer fencing and recovery generation | Failure tests establishing acknowledged-commit durability; backup RPO/restore RTO and completed restore drill. |
| Runtime continuation and resource fencing | Per-profile enforcement mechanism and partition/clock/reboot tests. |
| Capacity commitments and workload SLO values | Representative traces, admission feasibility and measured failure/headroom assumptions. |
| Storage and network providers | Ownership, isolation, snapshot/restore, attachment and recovery contracts. |
| Runtime/GPU/RDMA support matrix | Pinned versions, security assumptions, performance and failure qualification. |
| Kubernetes admission hierarchy | One authority per decision and evidence supporting any capacity guarantee. |
| Management and maximum cluster envelope | Task/activation rates, transaction contention, storm recovery and latency results. |
| Facility actions and maintenance contracts | Approved scope, start/completion semantics, independent execution and safe recovery procedures. |
| Billing terms and retention | Auditable interval definitions, rate/adjustment policy and ledger reconciliation. |

These decisions gate the corresponding promises. Best-effort development can proceed before every production profile exists, but unsupported guarantees must remain explicit rather than implied by the architecture.
