# Lyceum layers, ownership and scale

Eight-slide companion to [the main plan](astra0.md).

**Deliverables:** [PowerPoint](layers-and-ownership.pptx), [PDF](layers-and-ownership.pdf), [browser slides](layers-and-ownership.html).

The deck shows proposed ownership, current implementation gaps and sizing assumptions; it is not a deployed-state claim.

## 1. Three layers. One accountable owner each.

Organize teams around decisions and contracts; vendors are implementation choices.

Capacity owns Atlas host allocation and Hydra/Kubernetes assembly. Hardware owns physical lifecycle only where Lyceum has authority; otherwise it owns the provider interface and evidence. Workload owns its own software releases and SLO, even when software runs on Kubernetes. Storage backend and web implementation are not established by this review. Source: astra0.md §4 software and team matrix.

## 2. Two hardware authority profiles

The same capacity interface must describe different powers and recovery guarantees.

The authority profile is per host/pool, not inferred from legal asset ownership. Host access may be insufficient for kubelet, runtime or driver installation: require provider bootstrap or exclude the host. Do not invoke unavailable power/reimage/wipe operations. External maintenance/withdrawal is a failure assumption covered by provider terms, replicas and reserve. Customer-root rentals require a distinct credential handoff from managed inference. Source: astra0.md §4 Two hardware authority profiles.

## 3. Dedicated inference and machine rental differ

All products keep their customer contract above the shared capacity interfaces.

A dedicated inference replica remains managed by Iris on the qualified Kubernetes/Dynamo path. Whole-machine rentals are exclusive and must not be simultaneously offered to Iris or Streamer/Execlet. Existing Execlet product remains on disjoint hosts until explicitly migrated. Raw events are deduplicated by source/id; Croesus aggregates meter readings into independently idempotent ledger transactions. Source: lyceum/README.md; docs/wiki/docs/core/explanations/{hydra,croesus,gateway}.md; astra0.md §4.

## 4. Remove duplicate authority, retain useful signals

The rule is one writer for each decision—not one program for every layer.

Source confirms legacy gateway business logic and multiple Iris backends; confirm deployed consumers before retirement. Do not introduce Run:ai Knative frontend/scaling alongside this Dynamo route. PDBs cover supported voluntary disruptions; provider withdrawal and physical faults are separate. Driver image policy and GPU Operator are complementary only when their writes are disjoint. Source: astra0.md §4 duplicate-authority table and §6 Phase 3.

## 5. Make the handoffs the team contracts

Each team operates its layer and publishes evidence the next layer can trust.

Hardware supplies only capabilities it controls or has a provider contract for. Capacity owns host eligibility/booking, one placement authority and the drain journal. Workload owns service admission and traffic. A quota is not physical reserved capacity. Raw usage receipt and ledger transaction idempotency are separate. API/software ownership is distinct from the Capacity team operating a database or installing an approved CRD. Source: astra0.md §4 Team handoff contracts.

## 6. One fleet across N main sites + P small sites

N ≥ 3 main sites. Each small site has tens of machines; distribution is still to be defined.

Revised fleet assumption: 1,250 GPU hosts (10,000 GPUs at eight per host), fewer than 10,000 CPU hosts, and 1,000 storage hosts across N main sites, N >= 3, plus P small sites with tens of machines each. The totals include the small sites; their machines are not added a second time. N, P, per-site composition and the exact small-site counts are unspecified. A site is a physical/operational location; one site may have multiple clusters and resource pools. Earlier five-GPU-cell / ten-CPU-cell arithmetic is only an illustrative packing case, not the fleet topology. Qualify a smaller control footprint for small sites while retaining the declared authority, locality and recovery contracts. Hardware authority is a separate dimension: both lifecycle-controlled and host-access-only sites are possible. Source: user topology clarification and astra0.md §5.

## 7. Budget control compute; measure the rest

Preliminary load-test allocations. VM resources below are not physical-server counts.

The six-VM / 144-vCPU / 576-GiB allocation is a preliminary large-compute-cell test budget. Fifteen such cells would total 90 VMs, 2,160 vCPU and 8,640 GiB (8.44 TiB), but the N-main-plus-P-small-site topology does not establish that count. Sum large-cell budgets, separately qualified small-site budgets and main-site/shared services; do not charge every small site the full large-cell package. Database, telemetry and application capacity are additional. Reserve physical management capacity inside the fewer-than-10,000 CPU-host total; 90 VMs do not imply 90 physical hosts. The 1,000 storage hosts still need usable-capacity, performance and durability inputs. NICo covers only lifecycle-controlled inventory and is separately budgeted. Source: astra0.md §5.

## 8. Split ownership now; qualify scale in stages

Three accountable teams, with workload sub-owners as the organization grows.

The fleet program does not expand the existing four-to-six-week AWS MVP estimate. Each layer owns code, release, metrics, on-call and recovery; interfaces name escalation owners. Capacity hosts application infrastructure but does not own every application schema or customer semantic. Future batch, discounted inference, fine-tuning and RL remain outside this inference MVP. CPU cell qualification is 100→500→1,000 workers as demand arrives. Source: astra0.md §§4–8.

## Primary scale references

- [Kubernetes large clusters](https://kubernetes.io/docs/setup/best-practices/cluster-large/): published node/Pod/container envelope; qualify the pinned version.
- [Run:ai scale](https://docs.nvidia.com/run-ai/self-hosted/v3.0/documentation/installation-and-configuration/operate/nvidia-run-ai-at-scale): service tuning and measured scale examples.
- [Run:ai HA](https://docs.nvidia.com/run-ai/self-hosted/v3.0/documentation/installation-and-configuration/operate/high-availability): system nodes, replication and database restrictions.
- [NICo large-site measurements](https://docs.nvidia.com/infra-controller/documentation/reference/development/large-site-sizing-and-settings): simulated ingestion only, with stated exclusions.
