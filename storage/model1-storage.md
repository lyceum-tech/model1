# Model1 storage plan

Status: proposed architecture; implementation and failure testing pending.

Date: 2026-10-29.

## Objectives

- Keep primary storage available with any one or two physical servers unavailable, starting from a healthy system.
- Store authoritative model weights, datasets, and artifacts in RustFS.
- Provide persistent Kubernetes volumes through Longhorn for Run:ai workloads and platform services.
- Prefer InfiniBand for model downloads, with explicit Ethernet fallback.
- Use Ethernet for storage coordination, Longhorn traffic, management, and backups.
- Encrypt valuable data and preserve access to keys during failures and recovery.

Availability means continued service or bounded, tested recovery. It does not mean that a pod, mounted volume, training job, or established network connection survives its host disappearing without interruption. Define acceptable recovery time and recovery point objectives before deployment.

## Confirmed inventory

| Equipment | Quantity and configuration | Raw storage |
| --- | --- | ---: |
| GPU servers | 16 servers; each has 8 GPUs, 8 DPUs, and 8 × 2 TB NVMe drives | 256 TB |
| SSD server | 1 server with 6 × 15.36 TB SSDs | 92.16 TB |
| NFS server | 1 server with 12 × 24 TB drives | 288 TB |
| InfiniBand fabric | 1 NVIDIA Q3400-RA switch | — |
| Ethernet fabric | 2 NVIDIA SN4700-A switches | — |
| Server connectivity | At least 2 × 200 Gb/s Ethernet links; IB is physically separate | — |

Capacities in this document use decimal TB. Filesystem overhead, reserved space, snapshots, object versions, and backups reduce available capacity further.

Assumption to confirm: the eight NVMe drives on each GPU server are available for data and exclude operating-system and boot storage. Confirm that the Ethernet connections have independent NIC/DPU and switch failure paths.

## Proposed disk allocation

Assign whole drives rather than dividing each drive between both systems.

| Per GPU server | Cluster allocation | Purpose |
| --- | --- | --- |
| 4 × 2 TB NVMe | 64 drives; 128 TB raw | RustFS object storage |
| 4 × 2 TB NVMe | 64 drives; 128 TB raw | Longhorn volume storage |

Give each system exclusive ownership of its assigned data paths. Use stable device identification and persistent mounts. Do not place distributed RustFS data volumes on replicated Longhorn volumes in this architecture.

Boot storage, container images, logs, and disposable model caches need a separate capacity budget. If boot/scratch disks are not separate, revise the split before provisioning.

## RustFS design

Use distributed RustFS on local disks, exposed to Kubernetes through local PVs with node affinity or an equivalent deployment with explicit disk ownership.

Proposed logical topology:

- Four pools, each spanning all 16 GPU servers.
- One dedicated SSD from each server in each pool.
- One 16-drive erasure set per pool.
- STANDARD objects encoded with 12 data shards and 4 parity shards, `EC:4`.
- Apply an equivalent protection policy to every storage class clients may use; do not allow reduced-redundancy writes to undermine the availability objective.

This topology makes two host failures remove two shards from each set, rather than concentrating multiple lost shards from the same host in one set. A 16-drive `EC:4` object requires 12 valid shards for reads and writes.

This is a logical design, not a ready-to-apply Helm configuration. Validate support in the pinned RustFS release and chart/operator, including endpoint ordering, pool placement, internal metadata and lock quorum, and startup with failed peers. Inspect the initialized topology and perform failure tests before claiming two-host availability.

Do not substitute a four-host/four-disk-per-host default deployment: losing two such hosts removes eight of sixteen drives. Pool and set layout are persisted and cannot be casually changed after initialization.

Capacity:

- Raw: 128 TB.
- After 12+4 coding: approximately 96 TB.
- Initial operating budget with 30% headroom: approximately 67.2 TB, including object-version growth within that budget.

Use buckets for authoritative models, datasets, and artifacts, with explicit retention and backup policies. Local weight caches remain disposable and must be refillable from RustFS.

## Longhorn design

Longhorn consumes its assigned local disks and exposes volumes through Kubernetes CSI. Do not first export these disks through an independently managed iSCSI service. Longhorn's V1 engine manages its own iSCSI frontend.

For valuable persistent volumes:

- Use three replicas on three different physical servers.
- Set replica node-level soft anti-affinity to false so replicas cannot share a host.
- Avoid creating volumes with degraded replica placement.
- Reserve capacity, CPU, RAM, and network bandwidth for replicas and rebuilds.
- Pin the Longhorn release and data engine after checking OS, Kubernetes, encryption, backup, and performance compatibility.

With three healthy replicas on distinct hosts, two host losses leave at least one data replica. Longhorn does not require a majority of those replicas to remain operational. An application whose host fails still needs rescheduling, safe attachment, and volume recovery. Measure that interruption.

| Proposed StorageClass | Replicas | Use |
| --- | ---: | --- |
| `longhorn-ha-encrypted` | 3 | Valuable workspace data, checkpoints, and appropriate application volumes |
| `longhorn-cache` | 1 | Disposable data that can be fetched again; no two-host availability guarantee |

Keep high-rate read-only model distribution in RustFS plus local caches where practical. Avoid triplicating every cached copy of a model. Do not use a single RWX mount as a replacement for a tested highly available shared filesystem design; validate its share-manager recovery separately.

Capacity assuming all assigned space is used for three-replica volumes:

- Raw: 128 TB.
- Logical capacity before overhead and snapshots: approximately 42.7 TB.
- Initial logical operating budget with 30% headroom: approximately 29.9 TB.

Single-replica caches and snapshot history consume this same physical pool and reduce the capacity available for three-replica data. Avoid aggressive thin-provisioning overcommit.

## Network architecture

| Traffic | Preferred fabric | Failure behavior |
| --- | --- | --- |
| RustFS model downloads | TCP/IP over IPoIB | Client retries through Ethernet |
| RustFS internal coordination and erasure traffic | Redundant Ethernet | Surviving Ethernet path |
| Longhorn replication and volume access | Redundant Ethernet | Surviving Ethernet path |
| Backups to NFS | Ethernet only | Surviving Ethernet path |
| Kubernetes, DNS, management, key services | Redundant Ethernet | Surviving Ethernet path |
| GPU collectives and supported Dynamo KV transfers | Native IB where supported | Separate application-specific design |

Cable one Ethernet link from every server to each SN4700. Begin with a tested active-backup design, or use LACP only with a correctly configured and supported MLAG design. Separate management, storage, workload, and backup traffic through appropriate subnets/VLANs and policies.

Budget recovery performance for one surviving 200 Gb/s Ethernet link per server. Do not assume 400 Gb/s is continuously available or that VLAN separation reserves bandwidth. Rate-limit backup and rebuild traffic and validate switch uplinks, peer links, MTU, routing, and NIC/DPU resource limits.

Configure Longhorn's storage network before creating production volumes. Its Multus storage-network setting is not a built-in IB-to-Ethernet failover policy. Keep Longhorn on Ethernet initially; cross-fabric failover for persistent volumes would require a separately engineered stable-address routing design.

### Model-download fallback

Expose the same RustFS cluster through separate reachable endpoints, for example:

```text
models-ib.site.example   -> IPoIB endpoint addresses
models-eth.site.example  -> Ethernet endpoint addresses
```

Both endpoints must provide the same objects and authentication, with valid TLS certificates. Validate that the chosen RustFS listener, Kubernetes networking, and endpoint/load-balancer implementation actually carry model data over the intended fabric.

Implement fallback in the model-download layer:

1. Attempt the IB endpoint with bounded connection and read timeouts.
2. On failure, retry the Ethernet endpoint with bounded backoff.
3. Resume range downloads when supported, or restart downloads safely.
4. Validate object version/checksum before publishing a completed cache entry.
5. Prevent simultaneous retries from overwhelming Ethernet when IB fails.

IPoIB transports ordinary TCP/IP; it is not a claim of native RDMA or GPUDirect Storage support. Changing DNS alone does not migrate established connections. Native IB-dependent GPU jobs require their own recovery policy.

The single Q3400 is a failure point for the IB fabric. Its loss should leave primary storage and control services functioning on Ethernet, but may interrupt distributed training or IB-dependent inference. Add a second independent IB fabric if uninterrupted IB service is required.

## Standalone SSD server

Use the 92.16 TB raw SSD server for services that can disappear without stopping primary storage:

- Fast model-download or registry cache with upstream fallback.
- Temporary staging, artifact ingestion, and backup acceleration.
- Monitoring or management components whose critical state is independently protected.

A possible layout is three mirrored pairs, approximately 46.08 TB before overhead. Final RAID/filesystem selection depends on its operating system, controller, workload, and drive characteristics. Disk redundancy does not protect against this server failing.

Do not put the only model copy, registry required for recovery, Kubernetes control plane, database, or encryption-key service on this server. It may host one member of an independently distributed service.

## NFS backup server

Use the 288 TB raw NFS server as a backup/archive destination independent of the primary GPU-server storage:

- Longhorn volume backups.
- RustFS object backups using a verified tool and restore procedure.
- Database and etcd snapshots.
- Configuration exports and separately protected key-recovery material.

If supported by its platform, an illustrative layout is two six-drive RAIDZ2 groups: approximately 192 TB before overhead. This tolerates up to two disk failures within each group, not the loss of the server. Choose the actual layout after reviewing controller, filesystem, replacement, and rebuild constraints.

Plan retention from measured change rates; raw capacity does not establish how many backup generations fit. Keep backup credentials isolated from ordinary workloads, encrypt sensitive backup material, and maintain an additional off-site or offline copy of critical data.

Failure of this server should suspend backups, not primary inference or storage. Do not make its NFS exports mandatory runtime mounts for all workloads.

## Encryption and key availability

- Longhorn: use encrypted StorageClasses with LUKS/dm-crypt and Kubernetes Secret references. Install the required host tools/modules. Prefer keys separated by volume or tenant. Backups of encrypted volumes remain encrypted, but metadata and other backup material need their own review.
- RustFS: evaluate SSE-KMS with Vault KV2 or Transit against the exact pinned release. Enforce the intended encryption policy and use HTTPS for S3 access.
- Kubernetes: enable Secrets encryption at rest, least-privilege access, and protected recovery backups.
- Networking: configure transport encryption separately from storage encryption; review client, replication, and management paths individually.
- Recovery: preserve keys independently of encrypted storage. Test new mounts, fresh processes, new object writes, and restoration while key-service members and storage hosts are unavailable.

The key service must meet the two-host failure objective. Avoid circular dependencies where the only key service needs encrypted storage that it must first unlock. A single Vault instance on either standalone server is insufficient.

## Whole-platform availability

The storage design alone does not provide whole-site availability.

- For an etcd quorum that survives any two member-host failures, use five voting members on five physical hosts. Use independent, suitably fast local storage for their state.
- Prefer dedicated management hosts. If unavailable, place management VMs/services on distinct GPU hosts with protected CPU, memory, storage, and lifecycle policies.
- Review the independent quorum and failover requirements of NICo/Run:ai databases, messaging, key management, DNS, ingress, and API load balancers.
- Distribute inference replicas across physical hosts. Define recovery for stateful and gang-scheduled workloads.
- Reserve enough GPU capacity: two failed GPU hosts remove 16 of 128 GPUs, leaving 112. Critical workloads must fit within the surviving capacity.
- Map actual rack, power, switch, NIC, and DPU failure domains. Two-server tolerance is not automatically rack or power-feed tolerance.
- Integrate storage draining with NICo lifecycle operations. Do not reprovision or sanitize a storage member until its data has been safely evacuated and its membership updated.

## Implementation sequence

1. Inventory device IDs, boot/scratch disks, firmware, NIC/DPU connections, power/rack placement, and storage software versions.
2. Agree recovery objectives, critical workload capacity, retention, and encryption requirements.
3. Build and test redundant Ethernet networking and the independent management/control plane.
4. Reserve host resources; configure stable disk mounts, monitoring, key management, and recovery access.
5. Deploy Longhorn with dedicated disks, explicit network settings, and encrypted three-replica classes. Validate with disposable PVCs.
6. Validate the proposed RustFS topology against the pinned release and deployment tooling. Deploy on dedicated local disks and inspect every pool/set mapping.
7. Configure bucket policies, credentials, TLS, encryption, and the two model-download endpoints.
8. Integrate PVC and S3 access with Run:ai projects; implement model-cache download fallback for Dynamo workloads.
9. Configure Ethernet-only backups and demonstrate restoration into clean storage.
10. Execute failure tests, record results, and approve production use only after meeting the agreed objectives.

## Acceptance tests

| Test | Required outcome |
| --- | --- |
| One GPU/storage host powered off | Primary storage continues or recovers within the agreed objective; affected workloads reschedule |
| Two GPU/storage hosts powered off simultaneously | RustFS reads/writes and Longhorn data remain recoverable/available within objectives; surviving capacity is sufficient |
| Two hosts unavailable during a cold restart | Documented startup, quorum, key-service, and recovery behavior meets the objective |
| One Ethernet switch or server link unavailable | Storage/control services remain reachable through the surviving path |
| IB switch unavailable during model downloads | Downloads recover through Ethernet; RustFS peers and Longhorn remain healthy |
| SSD cache server unavailable | Clients can use authoritative storage directly |
| NFS backup server unavailable | Primary services continue; backup failures alert and resume after recovery |
| Key-service members unavailable | Remaining service can authorize fresh mounts/writes; recovery is demonstrated |
| Host replacement and storage rebuild | Data integrity holds; recovery traffic does not starve critical workloads |
| Backup restored to clean storage | Data and keys can be recovered without relying on the original storage installation |

Test reads, writes, deletes, listings, multipart objects, encrypted data, and application behavior rather than relying only on pod readiness. Verify checksums, record latency/error rates, and confirm healing completes after failures are repaired. Use disposable data for destructive tests.

## Open decisions

- Are boot, OS, container-image, and model-cache disks separate from the eight NVMe drives?
- Exact NIC/DPU topology, independent failure paths, switch OS, Ethernet bonding/routing design, and IB interface speeds.
- Rack and power-domain mapping.
- GPU-host CPU/RAM budgets available for storage and control services.
- Required logical capacity, object sizes, model sizes, write rates, and retention.
- Recovery time and recovery point objectives, including whether two failures must be tolerated during maintenance.
- Pinned RustFS/Longhorn releases and the tooling that expresses the required RustFS pool layout.
- SSD/NFS server OS, controller/filesystem, usable capacity, and backup throughput.
- KMS/Vault placement, recovery keys, and protection of offline/off-site backups.

## References

- [RustFS pool layout, erasure coding, and quorum](https://docs.rustfs.com/en/operations/cluster-lifecycle)
- [RustFS Kubernetes installation](https://docs.rustfs.com/en/installation/cloud-native)
- [RustFS network and health endpoints](https://docs.rustfs.com/en/operations/status-check)
- [RustFS encryption options](https://docs.rustfs.com/en/security-compliance/encryption)
- [Longhorn architecture and replica behavior](https://longhorn.io/docs/1.13.0/concepts/)
- [Longhorn production recommendations](https://longhorn.io/docs/1.13.0/best-practices/)
- [Longhorn storage networking](https://longhorn.io/docs/1.13.0/advanced-resources/deploy/storage-network/)
- [Longhorn volume encryption](https://longhorn.io/docs/1.13.0/advanced-resources/security/volume-encryption/)
- [etcd quorum and failure tolerance](https://etcd.io/docs/v3.6/faq/)
- [NVIDIA IPoIB documentation](https://docs.nvidia.com/networking/display/mlnxofedv23070512/ip%2Bover%2Binfiniband%2B%28ipoib%29)

Documentation links identify the references reviewed during planning; they do not pin deployment versions. Recheck compatibility and support before implementation.
