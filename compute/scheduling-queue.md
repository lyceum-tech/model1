# Scheduling, queueing, and cluster execution specification

Status: working design, capturing the discussion as of 2026-10-14. This is a proposed architecture, not a description of implemented functionality. Project evaluations below identify candidates and references, not adopted dependencies or verified production guarantees.

## 1. Purpose and scope

Build a general-purpose cluster platform for physical machines and VMs. It must support distributed computation, services, stateful agents, and background queue work. Sonium compute, solvers, and QA are clients; the platform must not depend on Sonium-specific concepts.

The platform schedules useful work, protects workload reliability, and coordinates placement with infrastructure maintenance. Keeping CPUs occupied is insufficient: scheduling decisions must consider measured application progress and service objectives.

The scheduler, actuator, SDK, and platform integration code should be Rust. CRIU and KVM/QEMU are accepted infrastructure exceptions and must not be rewritten. Whether additional native dependencies, particularly userspace RDMA providers, are acceptable remains an explicit implementation decision.

TCP and RoCE/RDMA are required execution transport capabilities. The control plane and high-volume distributed-compute data plane are separate systems.

## 2. Workload model

A job is a collection of tasks, potentially with dependencies, shared policy, and multiple containers per task. A sandbox is the execution and isolation unit for cooperating processes that share namespaces or local resources. Task identities persist across execution attempts; attempt identities and ownership epochs do not.

Supported workload classes include:

| Class | Required behavior |
| --- | --- |
| Gang computation | Reserve and coordinate a set of tasks; start according to a group readiness barrier; checkpoint and recover coherently. |
| Background batch and QA | Queue tasks and run them on available capacity; permit eviction according to declared policy. |
| Services and real-time tasks | Protect availability, latency, and declared disruption limits. Hard real-time execution guarantees require separate admission and runtime qualification. |
| Stateful agents | Preserve workspace, durable execution history, messages, and external-operation recovery across suspension and relocation. |

A job specification should include resource requests and limits, task/dependency structure, priority, scheduling constraints, service or completion objectives, recovery capabilities, network requirements, and checkpoint locations. Device and transport requirements must be explicit rather than inferred from CPU and memory requests.

A gang is not assumed to tolerate individual rank loss. A valid initial recovery strategy is coordinated restart of the gang from a committed checkpoint. Elastic membership and partial recovery are optional capabilities.

## 3. Queue and scheduler relationship

The queue is a client of the scheduler. It stores submission and workflow state and exposes the full relevant backlog, dependencies, resource needs, priorities, and objectives. It must not hide pending work behind a small dispatch window that prevents informed placement decisions.

The scheduler decides what should run and where. A queue adapter must not introduce a competing authority for placement or execution attempts.

Backlog visibility may use indexed snapshots and incremental updates; it does not require repeatedly scanning every queued task on each decision.

## 4. Two core services

### Scheduler: propose decisions

The scheduler uses the backlog, current allocations, topology, health, application metrics, and reliability policy to propose placements and transitions. It may propose starts, evictions, migrations, checkpoint/restarts, replica replacement, and maintenance evacuations.

Use a bounded, responsive scheduling path for new work and immediate changes, with optional background optimization for better placements. Score useful progress and movement costs as well as resource utilization.

### Actuator: authorize and execute transitions

The actuator independently validates proposals against current state and reliability constraints. It can accept, defer, or reject a proposal, including refusing a move or eviction that would violate a job SLO.

The actuator owns committed allocation transitions and authoritative worker instructions. It must provide:

- Durable, idempotent transition records and reconciliation after interruption.
- Exclusive attempt ownership, epochs, and worker/resource fencing.
- Atomic reservation of capacity and disruption budgets across concurrent operations.
- Validation against current topology, health, policy, and allocation revisions.
- Structured rejection or deferral reasons, with the relevant revision and retry conditions.
- Explicit recovery procedures for partially executed transitions.

Reliability protections are granted by policy and admission decisions. They are not unlimited, arbitrary job vetoes. A repeated veto must be explainable and visible to the progress and maintenance policies.

Progress protection, infrastructure management, and reliability evaluation may initially be logical controllers within these two services. The design does not require a separate deployed service for every controller.

## 5. Priority, preemption, and eventual progress

Use priority scheduling with opportunistic backfilling. Higher-priority jobs may evict lower-priority jobs to acquire a complete gang allocation. Backfill decisions must account for checkpoint time, reclaim latency, and resources that cannot safely be reclaimed.

A future start-time reservation is not the sole anti-starvation mechanism: priority-based preemption can make room for a gang. However, preemption alone cannot guarantee eventual completion under unlimited higher-priority arrivals.

A progress controller must track waiting time, productive execution, lost work, checkpoint overhead, and repeated eviction. Admission and policy must establish entitlements, protected execution intervals, aging, or another enforceable mechanism that allows admitted finite jobs to complete under stated capacity and workload assumptions.

Distinguish:

- Service availability and latency objectives.
- Batch completion deadlines or progress entitlements.
- Agent responsiveness and durable state recovery.
- Infrastructure maintenance deadlines.

When these objectives cannot all be met, report the conflict and apply an explicit escalation policy. Do not silently promise impossible completion guarantees or bypass reliability constraints.

## 6. Application SDK and observations

Provide a small Rust library linked into workload binaries. It exposes lifecycle and scheduling-relevant metrics through a simple protocol such as REST, gRPC, or a local socket. gRPC must not be required of the application itself.

Combine automatic process/runtime observations with application-defined useful-progress signals. Infrastructure counters cannot infer arbitrary application progress.

Example signals include completed work units, remaining-work estimates, solver residuals and iterations, throughput, request latency, queue depth, blocked/waiting state, checkpoint duration, and restart cost. Estimates must carry freshness and uncertainty where relevant.

The worker independently measures resource consumption and health. Application reports inform optimization but do not authorize ownership or override resource enforcement.

Lifecycle capabilities include readiness, progress reporting, quiesce, checkpoint, restore, completion/outcome reporting, and termination. Reporting must be bounded and non-blocking. Reports identify the job, task, attempt, ownership epoch, and observation time.

Checkpoints are committed asynchronously to durable storage. A checkpoint is usable only after its data and manifest are committed; control-plane metadata stores references rather than bulk checkpoint data.

## 7. Stateful agents

An agent is not a stateless request handler. Its recoverable state can include a durable workspace, journal, mailbox, child-task relationships, budgets, and external tool operations.

Suspension may release compute while retaining durable identity and state. Restoration can start a fresh process from application state; it need not imply transparent process restoration.

Require exclusive workspace ownership and durable records of external-operation intent and outcome. Retrying an attempt must not blindly repeat non-idempotent external effects. Use idempotency keys and reconciliation where supported; generic exactly-once external execution is not assumed.

Google AX is a reference for separating tasks, workspaces, and agent execution. Its implementation and roadmap should not be treated as a complete implementation of this platform's lifecycle or reliability requirements.

## 8. Job networking and stable task addresses

Each job owns a private IPv6 network. Each logical task owns a stable private IPv6 address across relocation, suspension, and execution attempts. Multiple containers in one task can share its sandbox network namespace.

| Resource | Lifetime |
| --- | --- |
| Job network | Job lifetime, including suspension. |
| Task IPv6 address | Logical task lifetime. |
| Endpoint location | Current authorized placement. |
| Endpoint ownership epoch | Current authorized handoff or execution ownership. |

The host networking layer delivers traffic to the current endpoint location. Migration changes location, not the task address. Implementations may use routed task `/128` addresses or an overlay; the workload API must not depend on that choice.

The network provider supports allocation, attachment, relocation preparation, exclusive ownership transfer, and detachment. Decide explicitly whether job prefixes can overlap. If they can, forwarding and endpoint identity must include the job network identifier.

Job-private addressing does not by itself define security policy. Inter-job access, ingress, egress, and service exposure require explicit policy.

Stable IP addresses do not preserve socket state by themselves. Transparent TCP continuation requires compatible socket restoration and a controlled traffic handoff. Application restart generally requires reconnection even when the IP is unchanged.

Stable IPv6 also does not preserve RDMA queue pairs, registered memory, or device execution state. Those require supported device migration or coordinated transport teardown and reconnection.

## 9. Containers, VMs, and migration

Create container workloads in an execution environment designed for relocation: appropriate PID, mount, network, IPC, UTS, and user namespaces, plus cgroups. Namespace isolation is not a checkpoint engine. External files, mounts, devices, sockets, and shared resources require explicit restore handling.

CRIU is the candidate mechanism for transparent Linux process/container checkpoint and restore. Application-level checkpoint/restart remains a first-class recovery mechanism.

QEMU/KVM live migration is an available mechanism for qualified VM configurations. Validate CPU compatibility, machine/device configuration, storage, networking, memory requirements, and all attached devices for the actual source/destination pair. Host kernel maintenance and guest kernel maintenance are separate operations.

Ordinary whole-GPU NVIDIA passthrough through `vfio-pci` should be classified as non-live-migratable unless a specific supported device/driver stack proves otherwise. NVIDIA vGPU migration is a distinct, conditional capability with hardware, software, topology, and workload restrictions. An independently non-migratable RDMA device can prevent migration even when the GPU is migratable.

Live migration is planned relocation, not recovery from an already lost source host. Prefer pre-copy for reliability-sensitive evacuation where feasible; post-copy introduces source/destination dependencies that require separate policy and failure handling.

A typical migration transaction is:

1. Validate compatibility and reserve destination capacity, temporary resources, and disruption budget.
2. Prepare storage and network attachments and transfer preliminary state where supported.
3. Quiesce/freeze the source, isolate its endpoint, and capture final state.
4. Restore the destination in an isolated state.
5. Transfer exclusive ownership and network reachability, then resume.
6. Verify health/readiness and release source resources.

Exact ordering depends on the migration provider. Each phase needs a durable state and recovery rule. Once the destination has resumed external effects, restarting the old source is not a safe generic rollback.

## 10. Physical machines, VMs, and topology

Begin with static, versioned infrastructure inventory. Keep dependency topology separate from live health observations. A validated configuration file is sufficient initially.

Represent related structures rather than a single failure-domain label:

| Structure | Contents |
| --- | --- |
| Physical containment | DC, room, row, rack, host, and hosted VMs. |
| Power dependencies | Feeds, UPSs, PDUs, supplies, and shared upstream dependencies. |
| Network topology | NICs, switches, links, fabrics, capacities, and shared failure points. |
| Storage dependencies | Volumes, checkpoint stores, accessibility, and shared failure domains. |

Power and network dependencies may form graphs with redundant alternatives. Two racks can share upstream power; two network paths can share a switch. Physical separation does not establish independence.

VMs inherit physical-host failure dependencies. Account for host and guest allocations without double-counting physical capacity. Unknown topology means independence is unverified.

Express reliability policies as scenarios the placement must survive, such as one host, rack, power feed, or network fabric failure. Evaluate remaining connectivity and access to storage/clients, not only the number of healthy replicas. Quorum replicas that cannot communicate do not provide quorum availability.

Topology also informs performance: tightly coupled gangs can prefer low-latency RDMA locality while checkpoint replicas reside outside the gang's shared failure domains.

## 11. Infrastructure observations, maintenance, and repair

Physical-host management uses out-of-band Redfish capabilities where available, including inventory, power/health observations, events, and logs. Host agents supply OS-level state and logs. Hypervisor providers supply VM lifecycle and placement state. Provider capability differences must be explicit.

Do not conflate health, power state, schedulability, maintenance intent, and repair status into one boolean.

An update intent specifies targets, desired version, deadline, prerequisites, validation, rollback capability, and permitted disruption. OS/kernel updates normally use the host-management path; Redfish firmware/update capabilities are provider-specific.

The scheduler proposes evacuation and update plans. The actuator protects workload objectives and coordinates canaries, concurrency limits, execution, and verification of the resulting running version. Maintenance competes for capacity and disruption budget with workload movement.

Marking a host for repair prevents new placements and initiates evacuation. A host becomes ready for repair only when workloads and relevant guests are gone or safely stopped, ownership is fenced, and required storage/device/power conditions are satisfied. An empty queue or missing heartbeat is not proof that the host is safe for intervention.

Evaluate planned maintenance together with existing failures and other approved operations. Reserve disruption budgets atomically so separately safe actions cannot jointly remove quorum. A maintenance deadline that conflicts with protected availability produces explicit escalation, not an implicit override.

## 12. Durable state and control-plane failure handling

Use replicated control state for admitted job/task identities, policies, committed allocations, ownership epochs, transition records, network allocations, topology revisions, maintenance intents, and checkpoint references. High-rate telemetry and checkpoint payloads belong outside the consensus log.

OpenRaft is a candidate consensus library, not a scheduler or complete HA service. The platform must implement and validate storage, networking, snapshots, state-machine application, and recovery. Raft agreement does not itself fence a disconnected worker or external side effects.

Distinguish node failure from partition or stale observation. Starting a replacement must respect the workload's ownership/fencing requirements, especially for agents, writable storage, and stable network endpoints.

## 13. Distributed computation and Sonium integration

The generic execution platform launches tasks, provides rank/membership and transport information, enforces lifecycle policy, and stores recovery metadata. A separate Rust communication layer supplies point-to-point operations and collectives over TCP and qualified RoCE/RDMA backends.

Sonium requires explicit distributed ownership and globally correct algorithms, not just launching the existing local solver on several machines. Distributed Krylov methods need global reductions, distributed operator application, and compatible preconditioners. Checkpoints must capture a coherent distributed algorithm state or define a safe restart boundary.

Transport failure, gang recovery, and checkpoint semantics must agree. A new attempt must not accidentally exchange messages with an old rank epoch.

## 14. Candidate projects and concepts to evaluate

| Project | Proposed role and evaluation boundary |
| --- | --- |
| OpenRaft | Replicated control metadata. Evaluate persistence, snapshot installation, failover, fencing integration, and state-machine correctness. |
| HyperQueue | Potential queue/execution component or reference. Evaluate full-backlog visibility, gang semantics, recovery, preemption, and the ability to avoid a second scheduling authority. Do not assume its journal is replicated HA. |
| Meta Rebalancer | Reference for placement models, incremental optimization, hard constraints, lexicographic goals, movement costs, and transitional capacity. Its C++ implementation is not the intended platform dependency. |
| Google AX | Reference for durable agent workspaces and task execution lifecycle; not a Rust runtime dependency. |
| COOL JAPAN projects | Candidates for Rust numerical/distributed primitives. Existing TCP collectives do not establish production RoCE/RDMA support. |
| CRIU | Accepted external checkpoint/restore engine, subject to workload and kernel capability validation. |
| QEMU/KVM | Accepted VM execution and migration infrastructure, with per-configuration qualification. |

For Rebalancer-inspired optimization, model both the desired final placement and resources consumed during transitions. A feasible destination assignment does not prove there is a safe execution path. Include checkpoint/migration cost, temporary source-plus-destination capacity, move concurrency, and disruption budgets.

If existing state already violates a constraint, define explicit repair policy. Never silently relax ownership, fencing, or isolation to improve an optimization score.

## 15. Evaluation and acceptance scenarios

Evaluate candidate implementations against shared traces and failure scenarios before committing to adoption:

- A large gang acquires capacity despite a continuous stream of small background tasks.
- Admitted background jobs make protected useful progress despite repeated high-priority arrivals, within declared admission assumptions.
- Multiple simultaneous proposals cannot overspend a service's disruption budget.
- Controller crash or leader change during each transition phase converges without duplicate ownership.
- A partitioned worker cannot retain an authorized endpoint or workspace after ownership is safely transferred.
- Container or VM relocation preserves task identity; qualified TCP migration preserves connections within measured pause limits.
- Non-migratable GPU/RDMA jobs use coordinated application checkpoint/restart.
- Rack, power, and network failure scenarios preserve the declared quorum and connectivity requirements.
- Host update and repair drains respect VM ancestry, workload objectives, and deadlines or report infeasibility.
- Telemetry identifies stalled work even when CPU utilization is high.
- Agent recovery reconciles external effects without blindly replaying them.

Measure scheduler decision latency separately from end-to-end start/reclaim latency, useful throughput, lost computation, checkpoint overhead, migration pause, service SLO impact, and recovery time. Targets and benchmark scales remain to be specified.

For OpenRaft, start with its storage conformance tests and add platform-level crash/partition testing. For HyperQueue, classify each required capability as native, adapter-provided, core modification, or unsupported. Verify the selected build's native dependencies rather than assuming all transitive code is Rust.

## 16. Open implementation decisions

- Exact priority, admission, progress-entitlement, and escalation policies.
- Queue API, backlog indexing, and HyperQueue adoption versus independent implementation.
- Durable storage backend and OpenRaft integration.
- Routed versus overlay job networking, prefix allocation, overlapping networks, and cross-job policy.
- RDMA provider implementation and whether native vendor libraries are accepted exceptions.
- Supported checkpoint/migration capability matrix for containers, VMs, GPUs, and RDMA devices.
- Metrics schema, trust/freshness rules, and progress-estimation algorithms.
- Hardware inventory format, provider APIs, and initial failure scenarios.
- Concrete latency, availability, completion, scale, and maintenance acceptance targets.

## References

- [OpenRaft](https://github.com/databendlabs/openraft)
- [HyperQueue documentation](https://it4innovations.github.io/hyperqueue/stable/)
- [Meta Rebalancer](https://github.com/facebook/rebalancer)
- [Google AX](https://github.com/google/ax)
- [COOL JAPAN](https://github.com/cool-japan)
- [Linux userspace verbs](https://docs.kernel.org/infiniband/user_verbs.html)
- [DMTF Redfish](https://www.dmtf.org/standards/redfish)
- [Libvirt migration](https://libvirt.org/migration.html)
- [QEMU VFIO migration](https://www.qemu.org/docs/master/devel/migration/vfio.html)
- [QEMU post-copy migration](https://www.qemu.org/docs/master/devel/migration/postcopy.html)
- [NVIDIA vGPU migration requirements](https://docs.nvidia.com/vgpu/latest/grid-vgpu-user-guide/modifying-vgpu-configuration.html)
- [CRIU live migration](https://www.criu.org/Live_migration)
- [CRIU TCP restoration](https://www.criu.org/TCP_connection)
- [CRIU external resources](https://criu.org/External_resources)

Version-dependent capabilities must be checked against the selected deployment releases. QEMU `master` documentation and NVIDIA `latest` documentation are moving references, not release qualification evidence.
