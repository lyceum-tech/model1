# Lyceum security implementation plan

**Status:** Proposed delivery plan; current controls and staffing remain to be assessed.  
**Period:** 4 November 2026–30 June 2027.  
**Audience:** Leadership and the people accountable for implementation.  
**Companion:** [Lyceum security principles](lyceum-security-principles.md) explains the rationale, enduring policies, and relationship between security and compliance. This plan contains the procedures, training curriculum, exception workflow, and delivery evidence.

Implementation reference: [baseline procedures](#appendix-a--baseline-operating-procedures), [training curriculum](#appendix-b--training-curriculum-and-delivery), [exception workflow](#appendix-c--exception-workflow), and [obligations and assurance](#appendix-d--obligations-and-customer-assurance-reference).

## 1. Outcome and sequencing

By 30 June 2027, Lyceum should operate a demonstrable security practice suitable for an EU AI inference provider serving large, regulated customers. The outcome includes controlled access, managed devices, reviewed production automation, trained staff, tested incident response and recovery, and evidence customers can assess.

The plan spans three calendar quarters: the remainder of Q4 2026, then Q1 and Q2 2027. It replaces the earlier generic 90-day rollout. Dates below are proposed delivery targets, not statements that work has already been completed.

| Quarter | Focus | Quarter-end outcome |
| --- | --- | --- |
| Q4 2026: 4 November–31 December | Establish ownership, understand exposure, and close immediate gaps | An assessed baseline, critical protections, named owners, and a funded implementation and assurance scope |
| Q1 2027: 1 January–31 March | Enforce the operating model and collect evidence | Controls working across the agreed service scope, with tested access boundaries and regular evidence collection |
| Q2 2027: 1 April–30 June | Validate effectiveness and prepare independent assurance | Exercised recovery, independently reviewed security, corrected findings, and an evidenced certification/customer-assurance position |

The sequence follows dependencies: assess assets and threats before selecting controls; implement and test controls before claiming they work; accumulate operating evidence before an audit of effectiveness. Legal duties and signed customer commitments apply on their own dates and may require work earlier than this schedule.

**Immediate protection takes precedence over the quarter plan.** Act on exposed credentials, public sensitive data, uncontrolled production access, or other urgent findings as soon as identified. Do not admit sensitive customer workloads into an environment that cannot meet their required safeguards. Where an existing service falls short, contain the exposure and agree remediation with the accountable owner; the roadmap does not authorize an unsafe interim state.

## 2. Ownership and initial decisions

Assign named people and deputies to these roles by **13 November 2026**. Roles may be combined in a small team, but independent approval requires different people.

| Role | Accountability |
| --- | --- |
| Executive sponsor | Budget, priorities, business-risk decisions, and staffing for independent approvals |
| Security coordinator | Threat model, control register, evidence, training coordination, exceptions, and delivery reporting |
| IT owner | Identity, devices, approved applications, onboarding, departures, and account recovery |
| Engineering owner | Secure development, dependencies, secrets, model changes, and release safeguards |
| Production owner | Production permissions, deployment automation, monitoring, incident response, and recovery |
| Infrastructure owner | Owned machines, firmware/BMCs, VM-provider controls and contracts, NICo, network, storage and recovery capacity |
| Platform owner | Kubernetes, Run:ai, Dynamo, model-serving isolation, platform upgrades and NPI coordination |
| Operations/people owner | Building access, visitors, equipment, travel and personal-safety arrangements, and training enrollment |
| Legal/privacy owner or qualified adviser | Applicability of laws, privacy roles and agreements, contractual duties, and notification requirements |
| Commercial/customer owner | Customer assurance requirements, procurement deadlines, service commitments, and approved external claims |

By **20 November**, leadership should adopt the initial workstation and authentication policies, confirm the people available for two-person production approval and emergency coverage, and fund the immediate work. By **18 December**, approve the prioritized risk-treatment plan, service recovery objectives, and assurance scope. Record staffing or budget gaps as delivery risks with an owner and resolution date.

## 3. Q4 2026 — establish the baseline and immediate protections

### November: discover, decide, and contain

| Work and target | Accountable owner | Evidence of completion |
| --- | --- | --- |
| Inventory critical services, data, people, devices, privileged accounts, premises, and suppliers by 30 November. Map prompts, outputs, model files, caches, logs, and support access. | Security coordinator, with domain owners | Inventory and data-flow map; unknowns and owners recorded; first threat model and ranked risks reviewed by leadership |
| Protect critical identities and revoke obsolete access as they are discovered; complete the initial sweep by 30 November. Enforce phishing-resistant authentication for privileged roles, secure recovery routes, and establish controlled production approvals. | IT and production owners | Account coverage report; sampled login and recovery checks; access removals; evidence that urgent production paths are controlled |
| Assess device and physical-access coverage by 30 November. Enroll the Apple fleet in Jamf, select the supported Linux approach, and identify unsupported devices or premises gaps. | IT and operations owners | Device and access inventory; encryption/update evidence; remediation dates; visitor and lost-device procedures |
| Confirm the most important customer requirements and legal-scope questions by 30 November. | Legal/privacy and commercial owners | Initial obligations register covering GDPR, AI Act roles, NIS2 applicability, DORA-related customer commitments, payment scope, and relevant countries |
| Document owned-hardware versus VM-only responsibility boundaries and production layers P01–P09 by 30 November. Escalate the known absence of spare site-loss capacity immediately. | Infrastructure, platform and production owners | Per-site responsibility matrix; vendor/version inventory; initial provider-evidence gaps; leadership risk record |

### December: establish the operating foundations

| Work and target | Accountable owner | Evidence of completion |
| --- | --- | --- |
| Enforce the agreed device baseline and key-based privileged sign-in by 18 December; restrict sensitive access from devices that do not meet it. | IT owner | Managed-device and authentication coverage, plus explicitly approved and safeguarded exceptions |
| Deliver Security 101 (appendix B) to the existing team by 18 December and put it into onboarding. Register and assess exceptions, including any actual Finance/Windows or Legal/collaboration-tool needs. | Security coordinator and operations owner | Training results; exception decisions, owners, safeguards, and expiries |
| Publish incident contacts, establish protected backups, and restore a representative critical dataset by 18 December. Agree acceptable service interruption and data-loss limits. | Production owner and executive sponsor | Incident contact test, restoration record, and approved recovery objectives; gaps prioritized |
| Establish reviewed release rules, secret storage, an approved-tool process, and supplier ownership by 31 December. Identify remaining automation and privileged-access gaps. | Engineering, IT, and production owners | Review settings, secrets inventory, tool/supplier register, and dated production-control backlog |
| Define the ISO 27001 service scope and assess gaps by 31 December. Obtain auditor proposals and decide whether customer demand justifies SOC 2 or another assurance track. | Security coordinator and commercial owner | Scope covering the real inference service, risk-treatment plan, audit budget and provisional schedule; customer requirements mapped to evidence |
| By 18 December, approve the DRP capacity strategy, reduced-service priorities and proposed RTO/RPO; establish independently protected backup/key custody and fund isolated recovery-test capacity. | Executive sponsor, infrastructure and production owners | Site-loss capacity calculation; funded capacity or explicit service limitations; backup-protection test; recovery-test resources |
| By 18 December, establish the security on-call roster and escalation/runbook baseline, NPI gates, and the cryptographic inventory/PQC workstream. | Security coordinator, platform and IT owners | Tested primary/secondary paging and fallback communications; approved-platform register; cryptographic inventory with owners and vendor dependencies |

**Q4 acceptance review — 31 December:** Leadership reviews the assessed baseline, critical-access protections, managed-device coverage, first training results, restoration evidence, and open risks. Every unmet item has containment where needed, an owner, and a dated action. An unknown safeguard is not counted as implemented. Any gap in independent production approval remains an explicit gap against the principles.

## 4. Q1 2027 — enforce controls and demonstrate routine operation

| Work and target | Accountable owner | Evidence of completion |
| --- | --- | --- |
| By 31 January, complete role-based access design, joiner/mover/leaver procedures, account-recovery controls, and privileged-account reviews. Include cloud owners and identity administrators. | IT and production owners | Tested access grants and removals; privileged-role inventory; review records; no unrecorded standing production access |
| By 28 February, complete the Zero Touch Production implementation across the agreed scope: reviewed automation for releases, infrastructure, database changes, and maintenance; independent control of approval settings and emergency access. | Engineering and production owners | Recorded release and emergency exercises; bypass attempts rejected; short-lived scoped access; protected audit records and verified separation of environments |
| By 28 February, implement inference-specific safeguards and data-handling commitments. Cover customer isolation, prompt/output/cache/log retention, deletion, model provenance, controlled model updates, and customer-content training policy. | Engineering and production owners, with Legal/privacy | Isolation and deletion test results; data-flow map reconciled to actual behavior; approved model/release records; customer commitments reflected in configuration |
| By 28 February, operate dependency and secret checks, vulnerability triage with response targets, and routine alert escalation. | Engineering and production owners | Findings with owners and deadlines; sampled fixes; alert-to-responder exercise and escalation records |
| By 31 March, complete role-specific training and practical exercises for IT, engineering, operators, and approvers (appendix B). Review physical-access safeguards and priority supplier controls. | Security coordinator and domain owners | Observed exercise results, remediation or retraining, supplier responsibility records, and physical-access review |
| By 31 March, complete the first full access review and incident exercise, and assemble the ISO management-system records. | Security coordinator | Access-review actions; incident exercise report; risk treatment and control selection with reasons; management review and corrective-action records |
| By 31 January, agree VM-provider security/recovery schedules; by 28 February, qualify representative owned and VM platforms through NPI and measure clean rebuild, data restore and model-loading times. | Infrastructure and platform owners, with Legal/privacy | Contractual responsibilities and guarantees; boot/firmware/isolation evidence; provider recovery evidence; measured DRP inputs |
| By 28 February, pilot supported PQC connections and verify backup/key recovery; by 31 March, exercise ransomware containment and the on-call approval/escalation path. | IT, security and production owners | Negotiated-protocol evidence; compatibility/performance results; restore/key tests; incident timeline and corrective actions |

Complete an internal assessment by **31 March**, using reviewers who are independent of the work being assessed. Close urgent findings before accepting the affected customer workload. Confirm with the certification body whether readiness supports a Q2 audit.

If SOC 2 Type II is selected, agree scope and the observation period with the auditor early. Start the period only when the scoped controls are operational and evidence can be retained consistently. Do not retrospectively treat the implementation period as proof of effective operation.

**Q1 acceptance review — 31 March:** Domain owners demonstrate the controls with evidence, including an attempted unauthorized production change, a contractor departure, an incident escalation, and representative customer-data isolation and deletion. Leadership approves the remaining risk treatment and Q2 assurance schedule. Customer commitments must match the controls actually in service.

## 5. Q2 2027 — validate, remediate, and obtain assurance

| Work and target | Accountable owner | Evidence of completion |
| --- | --- | --- |
| By 30 April, commission a focused independent security assessment of the inference service and its administration and release paths. Include isolation between customers and relevant model/API abuse scenarios. | Security coordinator and engineering owner | Assessment scope and report; findings triaged with owners, containment, and deadlines |
| By 30 April, exercise recovery from a serious outage or compromise, including encrypted-data recovery, unavailable normal approval systems, independent emergency access, and customer communication. | Production owner with IT, Legal/privacy, and commercial owners | Measured recovery results against objectives; decision and communication records; gaps and corrective actions |
| By 31 May, retest remediated assessment findings and exercise customer exit/data return, deletion, and relevant supplier-failure scenarios. | Engineering and production owners | Independent retest where appropriate; export/deletion evidence; supplier and exit-exercise results |
| During April–June, complete ISO 27001 readiness and certification audits where the agreed scope is ready. The first audit stage reviews readiness; the second evaluates implementation. | Security coordinator and executive sponsor | Audit reports, corrective actions, and the certification body's decision if issued; otherwise a precise remaining-work and decision-date record |
| By 30 June, complete the second quarterly access and threat review, training catch-up, exception review, and leadership review. | Security coordinator and domain owners | Updated risk and obligations registers; current evidence; exception renewals or closures; approved next-quarter actions |
| By 30 June, publish a controlled customer-assurance pack and determine the next certification investment. | Commercial owner with security and Legal/privacy | Approved service scope, architecture/data-flow summary, supplier responsibilities, recovery evidence, assessment summary, contractual information, and accurate certification/report status |
| By 30 April, exercise a ransomware clean rebuild and a site-loss scenario under the actual capacity constraints; by 31 May, retest material recovery gaps. | Production and infrastructure owners | Minimum/full service recovery estimates and measured results; achieved RPO; trusted-rebuild evidence; capacity shortfall and mitigation decisions |
| By 30 June, complete supported PQC migrations, review the NPI status of every platform, and validate sustained on-call coverage. | IT, platform and security owners | PQC coverage and exceptions; qualified/restricted platform register; page-response and handover evidence; updated vendor support and recovery commitments |

**ISO 27001 target:** Seek certification by 30 June if controls, audit availability, and corrective-action closure support it. The certification body makes the decision; the plan must never report an intended certificate as achieved. If certification is not issued by June, the quarter-end report must state why, what remains, and the revised date.

**SOC 2 Type II target, if selected:** Complete or materially progress the agreed observation period by June. If that period ends on 30 June, report issuance ordinarily follows the period and audit work; do not promise a final report on the same date. Record the actual observation dates, exceptions, and expected issuance date with the auditor.

**Q2 acceptance review — 30 June:** Demonstrate that the security practice operates, recovery has been exercised, material findings have been addressed or escalated with defensible restrictions, and customer-facing claims are supported. Publish the achieved assurance status and the July-onward plan, including continued monitoring, reviews, and audit follow-up.

The production acceptance package includes the P01–P09 control evidence, provider contracts, NPI decisions, hardware trust tests, measured cyber-recovery results, the funded capacity position, on-call exercises, and PQC coverage. A tabletop exercise can validate decisions but cannot by itself validate disk rebuild throughput or full-site failover performance.

## 6. Certification and customer-assurance choices

The following is a proposed commercial and security roadmap, not a claim that every item is mandatory. Confirm procurement requirements with target customers before committing to an audit program.

| Priority | Certification or assessment | Why and when to pursue it |
| --- | --- | --- |
| First | **ISO/IEC 27001 certification** | Establish a common security-management foundation. Include production, development and releases, staff access, incident response, and supplier dependencies within a credible service scope. Use an appropriately accredited certification body. [ISO](https://www.iso.org/standard/27001) |
| Early, if requested by target customers | **SOC 2 Type II report** | Provides independent examination of controls over an observation period. Useful when customers require evidence of ongoing operation. This is an attestation report, not an ISO-style certification; agree the relevant coverage, particularly security, availability, and confidentiality. Start retaining evidence early. [AICPA: SOC services](https://www.aicpa-cima.com/resources/landing/system-and-organization-controls-soc-suite-of-services) |
| Build into the initial control design | **ISO/IEC 27017 and 27018** | Cloud-security and public-cloud personal-data protection guidance, respectively. Particularly relevant to customer isolation, shared responsibilities, and processing customer content. These are control-guidance standards; evaluate any additional assessment or certificate scheme explicitly rather than treating them as equivalent to standalone management-system certification. [ISO 27017](https://www.iso.org/standard/27017), [ISO 27018](https://www.iso.org/standard/27018) |
| Next, according to AI responsibilities | **ISO/IEC 42001 certification** | Establishes an AI management system. Valuable where we select, integrate, change, or operate models and must demonstrate governance of AI risks and impacts. Its scope should reflect our actual role, and it does not certify that every output is correct or every use is lawful. [ISO: ISO 42001 explained](https://www.iso.org/insights/iso-42001-explained) |
| Next, where privacy assurance matters | **ISO/IEC 27701 certification** | A privacy information management system for organizations acting as controllers or processors. Relevant where sensitive customer content and privacy responsibilities are central to the service. It supports disciplined privacy management without replacing GDPR obligations. [ISO 27701](https://www.iso.org/standard/27701) |
| Market-specific | **BSI C5 attestation** | Assess for German cloud procurement when customers request cloud-specific assurance. It is an audit attestation against BSI's criteria, not a blanket EU regulatory approval. [BSI: C5 criteria](https://www.bsi.bund.de/SharedDocs/Downloads/EN/BSI/Publications/CloudComputing/ComplianceControlsCatalogue-Cloud_Computing-C5.pdf?__blob=publicationFile&v=3) |
| Market-specific | **SecNumCloud qualification** | Assess for French customers requiring the qualified cloud offering and its particular security and jurisdictional safeguards. Qualification concerns a defined service; running on qualified infrastructure does not automatically qualify our inference application. [ANSSI: SecNumCloud FAQ](https://cyber.gouv.fr/enjeux-technologiques/cloud/faq-qualification-secnumcloud/) |
| Activity-specific | **HDS certification** | Assess before entering French health-data hosting activities covered by the HDS regime. An insurance customer alone does not determine applicability; the actual data, purpose, and hosting activity do. [French digital health agency: HDS](https://gnius.esante.gouv.fr/en/regulations/regulation-profiles/healthcare-data-hosting-hds) |

**ISO 22301**, the business-continuity management standard, is another relevant option when customers depend on continuous inference availability. Apply its continuity disciplines early; pursue certification when critical-service contracts or procurement requirements justify it. [ISO: Business continuity management](https://www.iso.org/standard/75106.html)

Select the next investment from actual customer requirements: a German bank requesting C5 may make it more urgent than ISO 42001; a customer assessing our AI governance may reverse that order. Reuse the same operational controls and evidence across frameworks. Certification of our underlying cloud provider is supplier evidence, not certification of Lyceum.

## 7. Production architecture and baseline controls by layer

The production stack comprises infrastructure (machines, virtual machines, network, and storage, with NICo where deployed), Run:ai and Dynamo, and Lyceum's web/API frontends and backend applications such as billing. We operate multiple sites, but **all available capacity is currently saturated**. Some sites contain hardware we own; other sites supply only virtual machines. These are material differences in responsibility and recoverability.

NICo is NVIDIA Infra Controller, a platform for bare-metal lifecycle management. Its documented capabilities include provisioning, firmware validation, and network isolation. Record the deployed version and integrations; do not assume it manages every hypervisor, storage system, or security boundary in our deployment. Using NVIDIA software does not mean NVIDIA operates our service or accepts our operational responsibilities. [NVIDIA: What is NICo?](https://docs.nvidia.com/infra-controller/documentation/overview/what-is-nico)

The production owner must assign an infrastructure owner and a platform owner, with deputies, by 20 November. Engineering owns application controls. Each site gets a responsibility matrix identifying Lyceum, the datacenter, VM/storage/network providers, and any managed operator. Mark each control as directly operated, supplier-operated with verified evidence, or a gap.

### Baseline controls and acceptance evidence

These controls form the minimum production operating baseline. Apply them before sensitive workloads are admitted. These controls also supply much of the evidence for certification.

| ID / layer | Required baseline | Evidence and accountable role |
| --- | --- | --- |
| P01 — Physical machines | Inventory chassis, disks, GPU/network devices and firmware; restrict rack access; isolate management interfaces; remove default credentials; enforce the approved boot chain; patch supported firmware and drivers; sanitize before reuse. | Infrastructure owner: per-model acceptance record, configuration export, firmware inventory, boot rejection tests, sanitization records, datacenter access responsibilities. |
| P02 — Hypervisors and VMs | Separate host administration from guest administration; harden and patch each; approved guest images; scoped console and snapshot access; guest Secure Boot and virtual TPM where supported; test customer isolation. A virtual TPM does not prove the physical host is trustworthy. | Owned hypervisor: Lyceum verifies host and guest. VM-only service: provider proves host controls and Lyceum verifies guest controls; record evidence scope and gaps. |
| P03 — Network | Separate management, customer traffic, storage, cluster control, and backup paths. Deny unnecessary connections; restrict outgoing traffic; encrypt sensitive traffic with authenticated peers; protect DNS and certificates. Test Ethernet and high-speed GPU fabrics separately: ordinary Kubernetes network policies may not cover RDMA or other bypass paths. | Infrastructure owner: approved flow map, firewall/fabric policies, negative connectivity tests, certificate inventory and expiry alerts. |
| P04 — Storage and backups | Per-customer authorization, encryption, controlled key custody, protected snapshots, explicit retention/deletion, and independently protected recovery copies. Separate backup administration from ordinary production administration. Replication alone is not a backup. | Infrastructure and data owners: denied cross-customer reads, key access records, retention tests, failed unauthorized backup-deletion test, successful isolated restore. |
| P05 — NICo and shared infrastructure control | Restrict APIs, service identities, provisioning artifacts, databases, and administrative interfaces; protect signing and trust configuration; review changes; export audit records and recoverable configuration. Protect the management cluster that runs the controller. | Infrastructure owner: privilege map, controlled image/configuration pipeline, access review, independent log export, tested controller rebuild. |
| P06 — Kubernetes and Run:ai | Central sign-in and least-privilege roles; separate customers/projects; restrict cluster-admin and workload service identities; enforce workload admission rules; block unnecessary host access, privilege, and secret mounts; apply resource quotas and GPU isolation appropriate to the threat model. | Platform owner: Run:ai and Kubernetes permission tests, workload-policy rejection tests, customer isolation and quota tests, patch/upgrade records. |
| P07 — Dynamo and model serving | Put inference behind an authenticating gateway; authorize each customer and model; isolate workers, discovery/event/request services, caches, and GPU data-transfer paths. Disable unnecessary debug/admin surfaces. Approve model artifacts and executable model code; limit worker privileges and outgoing connections. | Platform owner: gateway-bypass test, model-access tests, artifact integrity records, cache-isolation tests, disabled debug routes, vendor security-bulletin review. |
| P08 — Web and API frontends | Secure sessions and API credentials; server-side authorization on every operation; customer-scoped identifiers; input and upload limits; rate limits, bounded queues and request deadlines; protection against common injection and browser attacks; controlled dependencies and releases. | Engineering owner: abuse/authorization tests, secret scans, penetration-test findings, session/key revocation tests, overload tests and monitored errors. |
| P09 — Backend applications and billing | Separate service identities and databases; authorize every business operation; protect administrative workflows; verify payment-provider callbacks; deduplicate retried events; keep auditable usage and billing records; reconcile invoices against source events. Keep card data out unless explicitly scoped. | Engineering and finance owners: signed release record, denied unauthorized actions, billing replay/reconciliation tests, immutable or otherwise tamper-evident audit evidence, restore results. |

Run:ai provides authentication and role-based authorization, but Lyceum must configure and test the effective permissions, including the underlying Kubernetes paths. [NVIDIA: Run:ai authentication and authorization](https://docs.nvidia.com/run-ai/self-hosted/v3.0/documentation/platform-management/authentication/overview)

Dynamo's documented trust model assumes a protected internal environment and an authenticating gateway. Do not expose internal coordination or diagnostic interfaces directly to customers. Review the installed version's deployment guidance before upgrades; demo manifests do not establish a hardened deployment. [NVIDIA: Dynamo secure deployment guidelines](https://docs.dynamo.nvidia.com/dynamo/v1.6.0/security/secure-deployment-guidelines)

Across all layers, enforce reviewed changes, short-lived scoped credentials where supported, independent production approval, vulnerability handling, time-synchronized protected logs, and tested recovery. A namespace or scheduler project is not sufficient evidence of isolation against hostile workloads. Where the required separation cannot be demonstrated, use stronger boundaries, such as dedicated nodes or clusters, or restrict the supported workload.

### Owned hardware versus VM-provider contracts

For owned equipment, Lyceum owns the firmware, boot-policy, hypervisor, sanitization, and recovery procedures even when a datacenter supplies power and rack access. Agree physical-access, remote-hands, parts-replacement, and incident-support arrangements. For VM-only sites, Lyceum cannot inspect or repair the physical host itself; obtain enforceable provider commitments and evidence before relying on those protections.

Each VM-provider contract or security schedule must identify:

- **Boundary and access:** who manages hardware, firmware, hypervisor, guest, storage and backups; who can access consoles, memory, snapshots and disks; administrator authentication, independent approval and emergency exceptions; subprocessors and processing/support locations.
- **Isolation and maintenance:** tenant and GPU isolation, dedicated versus shared capacity, overcommit policy, supported versions, vulnerability response deadlines, maintenance notice, Secure Boot/attestation capabilities, and device sanitization between tenants.
- **Evidence and incidents:** scoped audit reports and exceptions, right to obtain additional evidence or audit as applicable, prompt incident notice, forensic preservation, access to relevant logs, named 24/7 escalation, and assistance investigating provider-side compromise.
- **Recovery and exit:** backup and key ownership, deletion protections, restoration responsibilities, measured restore throughput, availability of replacement VMs/GPUs, reserved versus best-effort recovery capacity, service recovery commitments, data export and deletion evidence, and termination assistance.

Legal and infrastructure owners must turn these topics into measurable obligations, including notice and remediation times, by 31 January. A service credit or an uptime percentage is not a guarantee of replacement GPU capacity. Missing evidence remains a supplier risk; a contractual promise alone is not a passed technical test.

## 8. Machine trust: firmware, Secure Boot, and admission to production

### What can prevent an unapproved kernel from booting?

On supported hardware, **UEFI Secure Boot** checks authorized signatures or hashes before executing boot components. Its trust configuration includes a Platform Key (PK), keys authorizing trust-store updates (KEK), an allowed database (db), and a revocation database (dbx). A Linux bootloader or shim must continue verification to the kernel. Secure Boot does not simply consult the same public certificate authorities used by a web browser. Dell documents custom trust-store management on supported PowerEdge generations. [Dell: Secure Boot configuration](https://www.dell.com/support/manuals/en-us/precision-r7960-workstation/idrac9_7.xx_ug/secure-boot-configuration-from-bios-settings-or-f2?guid=guid-be352116-0b12-4f57-badf-41a4b199fc15&lang=en-us)

Our proposed policy is to boot only explicitly approved operating-system artifacts. Decide per platform whether to trust a restricted distribution signing chain or a Lyceum-controlled signing chain. Retaining broad vendor/distribution trust may permit other validly signed software; it does not enforce “only our approved kernel.” Protect enrollment, signing, revocation, recovery, and removal of keys through independent approval. Keep private signing keys outside build workers in an approved signing service or hardware-backed store.

Verify the complete path: firmware, bootloader, kernel, initial filesystem and boot configuration, and subsequently loaded kernel modules, including GPU and network drivers. Where supported, a signed unified kernel image can bind the kernel, initial filesystem, and boot parameters together. Separately address integrity of the root filesystem and applications; a signed kernel does not validate every file it later reads. Require module-signature enforcement and suitable kernel lockdown, and test the actual distribution configuration rather than assuming Secure Boot enables every protection. [Linux kernel: Module signing](https://docs.kernel.org/admin-guide/module-signing.html), [systemd: Unified kernel image construction](https://www.freedesktop.org/software/systemd/man/254/ukify.html)

### Why BIOS and BMC need their own assurance

The BIOS/UEFI initializes the machine; the BMC is a separate management computer that can provide power control, remote console, and virtual installation media. A compromised management controller can threaten the host independently of its operating system. Secure Boot relies on firmware behaving correctly, so an enabled setting is insufficient assurance about that firmware.

Require model-specific evidence of authenticated firmware updates, hardware-rooted verification where available, rollback protection, recovery from trusted firmware, update support, and relevant security advisories. HPE documents silicon-rooted firmware validation and recovery, with capabilities depending on generation and licensing. Supermicro publishes a security-feature matrix and descriptions of secure boot/update/recovery features. These are vendor claims to verify for our exact models, not blanket guarantees for every server from that brand. [HPE: Silicon root of trust](https://support.hpe.com/hpesc/public/docDisplay?docId=a00026171en_us&docLocale=en_US&page=GUID-8D98A576-E52D-4C5B-A733-471CE9EDF90B.html), [Supermicro: Security Center](https://www.supermicro.com/en/support/security_center), [Supermicro: Security feature descriptions](https://www.supermicro.com/es-es/support/security-features-description)

Use NIST's protect, detect and recover framework to evaluate firmware resilience. Confidence comes from verified implementation on supported models, timely vulnerability handling and tested recovery; signed firmware can still contain exploitable flaws. Hardware roots of trust reduce some attack paths but do not justify assuming that a vendor or its signing infrastructure cannot be compromised. [NIST SP 800-193: Platform firmware resiliency](https://csrc.nist.gov/pubs/sp/800/193/final)

Keep BMC interfaces off customer and public networks, require managed access with individual identities, disable unused interfaces and virtual-media access, rotate device credentials, and export logs. A BMC administrator may be able to disable Secure Boot or change trust settings; protect those privileges with the same independent control as production releases. Where a vendor cannot enforce this separation, place access behind independently controlled tooling and record any remaining bypass.

**Measured boot** records boot measurements in a TPM. **Remote attestation** lets a separate verifier compare signed measurements with approved expectations. It detects a different class of problem from Secure Boot; it does not automatically block boot. Gate workload scheduling or secret release on successful attestation where supported, with fresh challenges, controlled reference measurements, and a quarantine path. Neither a TPM nor a successful measurement proves absence of vulnerabilities or runtime compromise. [Intel: Measured boot and attestation](https://docs.trustauthority.intel.com/main/articles/articles/ita/concept-trusted-boot.html), [GNU GRUB: Measured boot](https://www.gnu.org/software/grub/manual/grub/html_node/Measured-Boot.html)

### Acceptance tests for each hardware/firmware family

Before production admission, test a representative spare or isolated system: reject an unsigned boot image; reject an otherwise signed but unapproved image; reject an unauthorized module; detect revoked or downgraded components; alert on Secure Boot being disabled or its trust store changing; reject or quarantine unexpected measurements; exercise authorized recovery. Test firmware rejection/recovery only using vendor-supported, non-destructive procedures. Record unsupported controls explicitly.

Maintain an evidence pack per model, motherboard revision, firmware version, GPU/network configuration and licence. Include configuration exports, vendor advisories, test results, and change history. Update it after relevant firmware, driver, signing-key or boot-chain changes. Do not infer a fleet-wide result from one vendor demonstration. For VM-only sites, obtain corresponding host evidence from the provider and test the guest chain ourselves; guest Secure Boot alone does not protect against a malicious hypervisor. Confidential-computing claims need separate hardware, attestation, GPU-path and threat-model verification.

## 9. Production evidence for certifications and assurance

The following is Lyceum's implementation mapping, not an exhaustive reproduction of any standard or a statement that every named technical mechanism is mandated. The security coordinator must map applicable requirements from the current standards and customer contracts to P01–P09, identify exclusions, and agree evidence scope with assessors. Baseline controls remain necessary even before certification; certification adds systematic governance and independently assessable evidence.

| Framework | Machines/VMs, NICo, network and storage: P01–P05 | Run:ai and Dynamo: P06–P07 | Web/API and business applications: P08–P09 |
| --- | --- | --- | --- |
| ISO 27001 | Asset/risk ownership; physical and supplier controls; privileged-access reviews; approved configurations and patches; change, logging and recovery evidence. Explain inherited VM-provider controls and residual risks. | Risk treatment for shared compute and model serving; tested access/isolation; dependency management; controlled model/platform changes; incident responsibilities. | Secure development and access controls; privacy/security requirements; reviewed releases; vulnerability treatment; business-data protection and tested recovery. |
| SOC 2 Type II | Evidence across the agreed observation period: access reviews, change records, monitoring responses, provider oversight, backup/restore results. Availability coverage must reflect the saturated-capacity limitation. | Samples of effective workload permissions, releases, isolation checks, vulnerability fixes and incident response; identify provider controls and customer responsibilities. | Evidence that authentication, releases, alerts and data handling actually operate. Include billing accuracy controls if processing integrity is in scope; define confidentiality/privacy coverage explicitly. |
| ISO 27017 / 27018 guidance | Document cloud shared responsibilities, virtual-resource separation, administrative access, customer-data location, sanitization and return/deletion. | Customer workload separation, data-access restrictions, cache/log retention and provider/subprocessor responsibilities. | Explain permitted use of customer content, controlled support access, return/deletion and disclosures; enforce commitments consistently through APIs and billing/support systems. |
| ISO 27701 | Map personal-data locations, provider roles, agreements, access, retention and disposal, including backup copies and support access. | Inventory personal data in prompts, outputs, caches and telemetry; govern purpose and retention; verify restrictions on reuse. | Implement applicable notices, rights requests, retention, exports/deletion and controller/processor responsibilities; track requests to completion. |
| ISO 42001 | Identify AI supply-chain dependencies, platform limitations and risks from compromised artifacts or unavailable compute. | Record model provenance, approved versions, evaluations, intended uses, changes, monitoring and responses to AI incidents within our role. | Document intended customer use, relevant limitations, oversight and impact/risk assessment; ensure applications do not bypass approved model-use restrictions. |
| ISO 22301 | Business-impact assessment, dependency and capacity analysis, alternate facilities/providers, recovery resources and tested restoration. | Rebuild platform and approved models; measure minimum and full serving capacity; test degraded operation. | Recover authentication, customer service and financial records; communicate, reconcile transactions, and test return to normal operation. |
| BSI C5, when selected | Map cloud operational, infrastructure, provider and environmental evidence to the selected catalogue and audit scope. | Include platform isolation, administration, changes, incident handling and resilience in the scoped cloud service. | Include the actual delivered inference/API service and its data/operations boundaries; infrastructure attestation alone does not cover it. |
| SecNumCloud, when required | Assess the actual offering against technical, organizational, legal and jurisdictional requirements, including operators and subcontractors. | Establish how platform operation and support fit the qualified service scope. | Confirm whether Lyceum's service needs its own qualification; hosting on qualified infrastructure does not confer it. |
| HDS or PCI DSS, if applicable | Determine the regulated data/environment first; identify covered hosting/processing activities and supplier responsibilities. | Prevent unsupported health/card-data uses; if allowed, include relevant platform paths, storage and administration in the assessment. | Scope actual health-data or payment handling and associated validation; a financial/insurance customer alone does not settle applicability. |

The primary sources for these frameworks remain linked in section 6. GDPR, the AI Act, DORA and NIS2 are obligations to assess separately, not substitute certifications. Use the legal references and applicability guidance in appendix D. Our evidence pack must expose limitations such as absent site-loss capacity, unsupported attestation or a provider's administrative bypass; do not conceal them behind a certificate.

## 10. Disaster recovery plan (DRP), including ransomware

The DRP restores trusted service after site loss, destructive mistakes, ransomware, or compromise of infrastructure and administrative systems. It works alongside incident response: stopping an attacker and restoring availability are related but distinct tasks. The production owner maintains executable runbooks; security approves recovery trust decisions; Legal/privacy and the communications lead manage external obligations.

### Capacity reality and continuity policy

**Current limitation:** Other sites have no unused serving capacity. Moving the failed site's workloads would overload surviving sites unless existing work is displaced. Multiple sites, replicated data, and a successful scheduler do not create spare GPUs. Full service recovery after site loss is not currently demonstrated and has no defensible committed RTO until capacity is secured or the site returns.

By 18 December, record each site's usable capacity by model, GPU/memory type, network and storage constraints, and measure capacity remaining after each possible site loss. Compare it with committed demand; GPU count alone is insufficient. Reserve resources for identity, routing, monitoring and recovery tooling so inference saturation cannot disable control of the incident.

Leadership must choose and fund reserved headroom, guaranteed compatible provider capacity, or contractually agreed reduced service. Best-effort capacity procurement is an uncertainty, not a recovery guarantee. Define customer/workload priorities and minimum allocations before an incident, including which batch jobs can pause and whether existing workloads may be displaced. Commercial and Legal owners must reconcile this policy with current contracts.

During an outage, route only admitted traffic to surviving sites; use quotas, bounded queues, request deadlines, and explicit retry/backoff responses. Avoid unlimited retries and automatic evacuation that causes a second site to fail. Do not silently substitute a different model, jurisdiction, or customer-isolation level. [Google SRE: Handling overload](https://sre.google/sre-book/handling-overload/)

### Define and prove RTO and RPO

**Recovery time objective (RTO)** is the target elapsed time from service disruption to an explicitly defined service level being restored. Count detection, decisions, capacity acquisition, rebuilding, data restore and validation—not only the file-copy operation. Record separate times for minimum service and full contracted capacity.

**Recovery point objective (RPO)** is the maximum intended loss of committed data, expressed as time. Measure the gap between the incident and the latest usable, consistent recovery point. A backup job every 15 minutes does not prove a 15-minute RPO if copies are incomplete, inaccessible or contaminated. Ransomware discovered late may require an older clean point and therefore a larger actual data loss.

| Recovery scope | Initial planning objective / decision | What must be demonstrated |
| --- | --- | --- |
| Incident communications, trusted administration and identity recovery | Proposed RTO: 4 hours; approved configuration and independently held recovery material available. | Recovery without the normal identity provider, compromised laptops, or production secret store; independent approvals still work. |
| Minimum inference service after site loss | RTO and supported demand **uncommitted pending capacity decision** by 18 December. | Named recovery capacity or agreed demand reduction, compatible models/GPUs, data permissions, model loading and admission tests. |
| Full inference capacity after site loss or fleet-wide compromise | RTO **uncommitted** until replacement/rebuild capacity and timings are validated. | Provider/parts commitments, rebuild concurrency, storage throughput and full-load validation; publish the resulting achievable target. |
| Customer/account and billing state | Proposed data RPO: 15 minutes where feasible; proposed application RTO: 8 hours, contingent on trusted infrastructure. | Consistent recovery, event replay and reconciliation. Do not silently lose accepted billable events or invent charges; preserve durable event sources or report the actual loss. |
| Deployment configuration, images and model artifacts | Every approved release recoverable; minimum serving set prioritized. | Independently retained manifests, artifacts, hashes, licences and dependencies; usable copies without the compromised registry. |
| Prompt/output data and transient caches | Follow each product's retention promise; do not create recovery copies of data promised to be ephemeral. | Explicit policy for interrupted requests, retained customer content, cache discard, and deletion records. |

These numbers are proposals for the December business-impact review, not measured capabilities or customer guarantees. Keep ordinary-failure and cyber-compromise RTO/RPO results separate. Recovery testing should assess integrity as well as time and recovery point. [Google Cloud: Testing recovery from data loss](https://docs.cloud.google.com/architecture/framework/reliability/perform-testing-for-recovery-from-data-loss)

### Backups that survive an administrator-level compromise

Create an independently administered recovery environment with separate credentials, approval controls, and recovery keys. A production administrator or compromised controller must not be able to delete recovery copies, shorten their retention, disable all future copies without alerting, or destroy the only decryption key. Evaluate provider/root-account override paths, not just ordinary backup-user permissions.

Use encrypted, versioned recovery copies outside the production failure domain, with enforced immutable retention and an offline or independently isolated copy for critical state. Validate what “immutable” means in the actual product, including deletion of the account, retention changes, encryption keys and billing suspension. Replication and writable snapshots may faithfully replicate encryption or deletion. [UK NCSC: Mitigating malware and ransomware](https://www.ncsc.gov.uk/guidance/mitigating-malware-and-ransomware-attacks)

Back up the information needed to rebuild the service: configuration and infrastructure definitions; identity recovery material; NICo and cluster state as appropriate to the supported recovery method; network/storage policies; database backups and transaction logs; model and application artifacts; usage events; protected audit evidence; and the recovery instructions themselves. Preserve version compatibility. Store recovery keys separately with independent custodians and test access if the normal key-management service is lost. Offline material must remain controlled and current.

Retain multiple recovery points for a documented period long enough to investigate delayed compromise; agree the period with security, data owners and Legal rather than retaining all customer data indefinitely. Test denial of deletion and retention weakening by production identities, and monitor backup freshness from outside production. Restore representative data monthly in isolation, and test the full critical chain quarterly. CISA recommends protected offline backups, maintained trusted system images, and tested recovery procedures. [CISA/MS-ISAC: Ransomware guide](https://www.cisa.gov/sites/default/files/publications/CISA_MS-ISAC_Ransomware%20Guide_S508C_.pdf)

### Ransomware scenario: all production drives are encrypted

Assume production credentials, configuration, and boot images may also be compromised until investigated. Also investigate data theft: wiping and restoring disks does not undo disclosure. Do not base the DRP on an attacker supplying a working decryptor. If no clean, decryptable recovery copy survives, data may be permanently lost; neither a finite recovery time nor the planned RPO can be guaranteed. Reinstalling empty servers is not business recovery.

1. **Declare and contain.** Page a SEV1 incident, isolate affected hosts and management paths, stop destructive automation and unsafe replication, revoke exposed access, and protect recovery systems. Use the independent communications channel. Preserve representative forensic evidence and relevant logs before destructive work, under the incident commander's coordinated plan.
2. **Establish a clean control environment.** Use trusted responder devices and independently held recovery identities. Determine the entry point and extent of compromise. Obtain a known-clean recovery point and verify the offline artifacts; scan and investigate backups rather than assuming the latest copy is safe.
3. **Recover trust before workload data.** Rebuild or re-establish identity, signing, secret management, audit collection and approved provisioning infrastructure. Rotate compromised credentials and service certificates, and revoke or replace affected trust roots using a planned transition. Preserve the ability to decrypt historical backups; do not destroy old encryption keys indiscriminately during rotation.
4. **Reclaim compute safely.** On owned systems, recover firmware/BMC/DPU trust using vendor-supported procedures, sanitize or replace media as appropriate, and reinstall from verified artifacts. If firmware trust cannot be established, quarantine or replace the platform. For VM-only sites, require provider investigation of the host boundary, fresh trusted instances/volumes and evidence of remediation; reinstalling the guest cannot repair a compromised provider hypervisor.
5. **Rebuild in dependency order.** Restore the minimal independent management cluster and NICo where required, network/DNS/time services, storage and keys, then guest hosts/hypervisors as applicable, Kubernetes/Run:ai, and Dynamo with an approved minimum model set. Recover the web/API and business services with their databases and event streams. Resolve bootstrap dependencies explicitly; NICo's own management environment must not depend exclusively on resources only the failed NICo can create.
6. **Restore and reconcile state.** Restore consistent database/transaction sets; validate data integrity, access controls, customer isolation and billing totals. Replay only verified events, with deduplication. Reapply deletions, revocations and permission changes newer than the backup so recovery does not resurrect access or unlawfully deleted records. Discard transient caches unless explicitly required and validated.
7. **Release capacity in stages.** Security and production owners approve a canary, then controlled customer traffic under the capacity-priority policy. Confirm the intrusion path is closed, monitoring is operating and recovery objectives are measured. Return full traffic only when capacity and trust are demonstrated. Keep suspect systems isolated.
8. **Close and learn.** Record actual downtime, data loss, data-exposure findings, customer impact and recovery bottlenecks. Complete notifications through the assigned legal/customer process. Repair the original site and conduct a separately approved failback with reconciled data, fencing against competing writers, and rollback criteria.

### How long does wiping and rebuilding take?

There is no credible fleet-wide number yet. A secure erase, an operating-system reinstall, and restoring trusted service are different operations. Cryptographic erase can avoid rewriting an entire medium when its encryption and key-destruction conditions are satisfied; this refers to our controlled media-encryption system, not an attacker's ransomware keys. It does not remove firmware persistence or prove the platform clean. Select and verify sanitization methods for each media type using vendor support and NIST guidance. [NIST SP 800-88 Rev. 2: Media sanitization](https://csrc.nist.gov/pubs/sp/800/88/r2/final)

Measure these stages separately: incident detection and containment; forensic/trust assessment; capacity availability; firmware recovery and media sanitization; image deployment; data restore and log replay; model transfer/loading; security/business validation; and staged reopening. Include supplier response queues, physical parts, reboot cycles, object retrieval delays and shared bandwidth.

For planning, `restore-copy time >= bytes to restore / measured aggregate restore throughput`. If restoring 100 TB at a sustained aggregate 2 GB/s, copying alone takes about 13.9 hours, using decimal units. This is an illustration, not Lyceum's measured performance; decryption, decompression, replay and validation add time. For independent hosts, rebuild time depends on the number of concurrent recovery slots and time per batch; disk wipes in parallel may still saturate shared controllers and networks.

The total recovery estimate is the **critical path** through the dependency graph, not the fastest host's result or an arbitrary sum of tasks that can run in parallel. With no spare capacity, some recovery stages compete with surviving customer traffic. By 28 February, measure one representative owned-hardware rebuild and one VM-provider rebuild, plus database and model restore throughput. In April, exercise recovery with the primary site and normal credentials treated as unavailable. Record minimum/full service times, achieved RPO, capacity shortfall, and any untested assumptions. Use isolated exercises and planned load tests; do not take a saturated production site offline merely to prove the plan.

## 11. Security on-call using Google SRE practices

Adopt Google's principles of sustainable on-call coverage, actionable paging, explicit incident command, rehearsed response and blameless learning. The staffing, times and severity thresholds below are Lyceum proposals, not Google requirements. [Google SRE: On-call](https://sre.google/workbook/on-call/)

### Coverage and responsibilities

Provide a 24/7 primary responder and a distinct secondary responder before promising 24/7 security response to customers. Initially this may share the production rotation, backed by a security specialist and contracted incident-response support. Maintain reachable infrastructure/platform/application experts, provider escalation contacts, Legal/privacy and communications contacts. Monitoring without an empowered responder is not coverage.

Two people on one shift are not a sustainable two-person team. By 18 December, fund a roster with leave, sickness and time off covered; use a qualified external provider if necessary. A detection provider does not automatically have permission to change production. Define who can approve and who can execute. Preserve time for engineering improvements, track overnight workload, provide recovery time and compensation, and rotate responders during prolonged incidents.

Require training, shadowing, a completed exercise and access checks before someone joins the rotation. Use scheduled handovers covering active incidents, temporary permissions, exceptions, planned changes and capacity limits. Maintain contact and runbook access outside the normal production/identity failure domain; test the fallback channel.

### Page for urgent security action, ticket routine work

Each page identifies the affected service/site/customer boundary, triggering evidence, severity, runbook, owner and next action. Correlate duplicates, test alert delivery, and detect loss of logging or paging itself. Never include credentials or raw sensitive prompts in pager messages.

| Severity | Examples | Proposed response and escalation |
| --- | --- | --- |
| SEV1 | Active ransomware, credible ongoing data extraction, broken customer isolation, compromised signing/production administration, or destructive changes across sites | Page primary and secondary immediately, 24/7; acknowledge within 5 minutes. If no acknowledgment, escalate at 5 minutes to backup and at 10 minutes to the incident commander/executive route. Establish command within 15 minutes; aim for updates every 30 minutes. |
| SEV2 | Credible contained compromise, unauthorized access attempt with substantial evidence, or loss of a critical security control requiring urgent action | Page primary, notify secondary; acknowledge within 15 minutes; escalate if missed. Set a documented investigation/containment plan and update cadence. Promote to SEV1 when impact or uncertainty warrants it. |
| SEV3 | Routine findings, non-urgent vulnerabilities, review tasks and low-confidence events without immediate impact | Create an owned ticket with a risk-based deadline; review during business hours. Escalate if new evidence or missed deadlines change the risk. |

Acknowledgment is not containment or resolution. Track each separately. Regulatory and contractual notification clocks require independent assessment; they do not start or stop merely because our internal severity changes.

Use service-level objectives (SLOs) for customer-visible availability and latency, and alert on rapid consumption of the permitted failure budget where appropriate. Security detections such as data extraction or privilege escalation must page even if availability is perfect. An availability error budget is never permission to tolerate a confidentiality breach. [Google SRE: Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)

### Incident command and controlled action

For major incidents, appoint an incident commander to coordinate, an operations lead to direct technical recovery, and a communications lead to maintain updates, with a scribe or incident log. Separate coordination from hands-on work as soon as staffing permits. Record hypotheses, decisions, approvals, actions and timestamps in a protected incident record. [Google SRE: Incident response](https://sre.google/workbook/incident-response/)

The primary responder may inspect approved sanitized telemetry and request containment. Sensitive reads, destructive actions, emergency production access and changes still require independent approval; one person cannot approve their own action using another account. Pre-approved, bounded automatic containment may execute under its reviewed policy and must produce an alert and audit record. A human trigger that materially changes production follows the same independent approval rule. If the secondary is unavailable, escalate rather than silently bypassing Zero Touch Production.

Initial runbooks must cover ransomware; privileged/signing-key compromise; customer-data exposure; unauthorized model or release changes; NICo/BMC/hypervisor compromise; provider incident; site loss with saturated surviving capacity; and loss of identity, backup or audit services. Include safe actions, required approvals, evidence preservation, provider contacts, DRP entry criteria and communications ownership.

For every SEV1 and significant SEV2 or near miss, draft a blameless post-incident review within five business days. Record contributing conditions, detection/response gaps, measured RTO/RPO, and corrective actions with owners and dates. Review progress monthly and share a suitable customer summary where required. [Google SRE: Postmortem culture](https://sre.google/workbook/postmortem-culture/)

## 12. Post-quantum cryptography: inventory, verify, and migrate

Post-quantum cryptography (PQC) addresses attacks from future cryptographically capable quantum computers. Long-lived confidential data is exposed to a “collect now, decrypt later” risk. The migration therefore covers protocols, key establishment, signatures, trust stores, hardware and recovery—not just generating longer keys. The EU has published a coordinated transition roadmap; record applicable customer and national requirements without treating its general milestones as Lyceum-specific certification. [European Commission: PQC roadmap](https://digital-strategy.ec.europa.eu/en/news/eu-reinforces-its-cybersecurity-post-quantum-cryptography)

### Two algorithm candidates and what their recognition means

| Candidate | Purpose and proposed use | Standards/assurance status |
| --- | --- | --- |
| **ML-KEM**, initially evaluate ML-KEM-768 | Establish shared secrets for protected connections through an interoperable, reviewed hybrid protocol combining classical and post-quantum protection. | Standardized by NIST in FIPS 203. A standards-conformant algorithm is not by itself a FIPS-validated implementation or cryptographic module. [NIST FIPS 203](https://csrc.nist.gov/pubs/fips/203/final) |
| **FrodoKEM**, parameter set selected against current national guidance and product support | Evaluate as a conservative alternative for connections where European customer requirements and supported products justify it, using a reviewed hybrid construction. | Recommended in German BSI guidance; ANSSI guidance discusses its use in hybrid products. This is European national-agency support, **not a blanket “EU-certified algorithm.”** Require the actual product certificate/qualification, scope and configuration if a customer requires certified cryptography. [BSI TR-02102-1](https://www.bsi.bund.de/SharedDocs/Downloads/EN/BSI/Publications/TechGuidelines/TG02102/BSI-TR-02102-1.pdf?__blob=publicationFile), [ANSSI: PQC migration guidance](https://cyber.gouv.fr/uploads/2022/04/anssi-avis-migration-vers-la-cryptographie-post-quantique.pdf) |

Both candidates are key-encapsulation mechanisms, not disk-encryption or digital-signature algorithms. For signatures, separately assess NIST-standardized ML-DSA and SLH-DSA against product support and the threat model. For bulk encryption, retain approved symmetric constructions and review key strength (for example AES-256) and key wrapping; do not encrypt disks directly with a KEM. [NIST: Finalized PQC standards](https://www.nist.gov/news-events/news/2024/08/nist-releases-first-3-finalized-post-quantum-encryption-standards)

Do not claim the fleet is quantum-resistant because one API gateway supports PQC. Secure Boot, BMC firmware signatures, hardware security keys, certificate authorities, SSH, internal service connections, backup encryption-key wrapping and external providers may retain classical algorithms. Record unsupported paths and vendor migration plans. Do not replace a supported boot trust chain with an experimental signing format the firmware cannot verify, or invent our own hybrid cryptography.

### Dated work and evidence

- **Q4, by 18 December:** IT and infrastructure owners inventory cryptographic algorithms, keys, certificates, protocols, libraries, hardware modules and trust dependencies across P01–P09. Record data sensitivity/lifetime, issuer, owner, expiry, rotation/recovery, vendor support and customer requirements. Prioritize long-lived customer secrets and externally observable traffic. Obtain exact vendor certification evidence where required.
- **Q1, by 28 February:** Engineering and security pilot supported hybrid ML-KEM connections and evaluate whether a FrodoKEM product path is justified. Test actual negotiation at every termination point, downgrades/fallback, interoperability, latency, throughput, memory use and denial-of-service exposure. Assess signatures separately. Retain packet/protocol evidence without storing secret key material.
- **Q2, by 30 June:** Roll out approved supported paths with canaries and independent change approval. Test rotation, certificate/key recovery and restoration of old encrypted backups. Where supported, rewrap retained data keys under the new protection; otherwise plan controlled migration of historical copies. Preserve necessary old decryption material until retention ends. Record remaining classical dependencies, business impact, vendor dates and expiry-reviewed exceptions.

The June deliverable is a verified coverage matrix and completed supported migrations, plus a funded backlog for unsupported components—not an unsupported claim of universal post-quantum security. Standardization, algorithm testing, module validation and product certification must be recorded as separate facts.

## 13. New Platform Introduction (NPI)

NPI is the controlled process for admitting a new server family, motherboard/firmware generation, GPU or network fabric, hypervisor/VM provider, datacenter, storage service, or material Run:ai/Dynamo platform change. The platform owner coordinates it; security participates from selection through production approval. Do not buy capacity first and discover that its controls cannot meet customer commitments afterwards.

| Gate | Required work | Exit evidence / decision owner |
| --- | --- | --- |
| 1 — Need and scope | Define workloads, customers, data categories, performance/capacity needs, intended sites and service commitments. Identify owned hardware versus supplier-operated boundaries and affected assurance scopes. | Business sponsor and platform owner approve requirements and total support/recovery cost. |
| 2 — Security and supplier design | Threat model; P01–P09 gap analysis; boot/firmware/key architecture; provider contract and evidence; data locations; PQC support; backup and recovery design. Assess supply-chain authenticity, end-of-support dates, licensing and patch access. | Security, infrastructure and Legal approve design or record rejection/conditions before production purchase commitments. |
| 3 — Isolated qualification | Test signed boot and trust changes, firmware update/recovery, isolation and privilege boundaries, storage sanitization, customer-data handling, monitoring, load limits and performance with security enabled. | Engineering/infrastructure supply reproducible results for the exact model and versions. Security accepts results and resolved findings. |
| 4 — Operational readiness | Complete rebuild and backup-restore tests; measure recovery throughput; validate capacity impact and failure domains; establish provider escalation, runbooks, spares, trained on-call and independent approvals. | Production owner accepts demonstrated readiness; security accepts trust recovery. Unfunded site-loss capacity remains an explicit service limitation. |
| 5 — Limited production rollout | Admit a bounded workload/customer set with suitable data permissions, observability, rollback criteria and approved change. Preserve the existing recovery path. | Production and engineering approve canary results; security reviews control regressions. |
| 6 — General admission and review | Resolve blocking findings, publish approved versions/configuration, update inventories and assurance scope, and hand over operations. Review the rollout after 30 days. | Production owner and an independent security approver authorize general use; executive sponsor accepts documented business risks within policy. |

A business risk acceptance cannot waive law, customer contracts, or turn an untested control into a verified one. Permit a restricted pilot only within an explicitly approved scope. Firmware/trust-root changes, critical vulnerabilities, provider/control-boundary changes and major platform upgrades trigger targeted requalification; minor changes follow a documented impact assessment. Store all vendor references, tests, exceptions and sign-offs with the NPI record.

Introduce the NPI template and approved-platform register by **18 December**. By **28 February**, qualify representative owned-hardware and VM-provider platforms and their recovery paths. By **30 June**, ensure every production platform is either qualified for its actual use or has a time-limited, approved restriction and remediation plan. Existing systems are not automatically qualified merely because they are already running.

## 14. Checklist, evidence, and reporting

The companion spreadsheet should translate this document into observable outcomes. Each row should identify the domain, threat addressed, required protection, priority, owner, due date, implementation status, verification evidence, last review date, and any exception with its expiry.

For production, include layer/control ID P01–P09, site and ownership model, inherited supplier control and contractual evidence, platform/NPI record, applicable assurance requirements, recovery dependencies and measured RTO/RPO, on-call/runbook owner, and PQC coverage where relevant. Keep intended targets separate from observed test results.

Include training controls with the required audience, completion date, and evidence of understanding. Maintain a linked exception register recording the requester, business need, affected standard and assets, alternatives considered, safeguards, remaining risk, reviewers, approver, implementation evidence, expiry, and renewal or closure decision. Keep sensitive details accessible only to those who need them.

Link checklist controls to the obligations register and relevant certification or customer-assurance scope. Record the applicable requirement and evidence, rather than using a single “compliant” checkbox for the whole company.

Use statuses that distinguish **not assessed**, **missing**, **in progress**, **implemented but unverified**, and **verified**. A justified **not applicable** status should include a reason. Track accepted risk separately so it is never confused with a protection that works.

For example, “enable strong authentication” is too vague. A verifiable item is: “All privileged accounts require approved phishing-resistant authentication; recovery routes have been reviewed; enforcement was tested on the recorded date.” Likewise, “production is automated” is incomplete unless we also verify that an individual cannot bypass approval or obtain unilateral access.

## 15. Delivery management and dependencies

Review the implementation backlog weekly, report progress and exceptions to leadership monthly, and hold the three quarter-end acceptance reviews. Address urgent incidents or exposures immediately rather than waiting for a meeting. A postponed milestone needs a reason, interim safeguards, customer impact assessment, and a new owner-approved date.

The monthly report should include managed-device and strong-authentication coverage; outstanding privileged-access and production-approval gaps; training completion and exercise results; overdue high-risk findings; recovery performance; expiring exceptions; and assurance milestones. State both counts and denominators so percentages cannot conceal missing assets.

The main dependencies are named owners with protected time, at least two trained people and deputies for sensitive approvals, support for every approved device platform, access to supplier evidence, legal review of the actual service and customer contracts, and auditor availability. Validate these dependencies in Q4 and update the delivery forecast when they change.

Use the future spreadsheet for row-level work items with stable identifiers, quarterly milestones, dependencies, and evidence links. This plan establishes the sequence; the principles document remains the source for the enduring rules. Review both when a policy decision changes, and preserve the distinction between a target, an implemented control, and a verified result.

## Appendix A — Baseline operating procedures

These procedures implement the [security principles](lyceum-security-principles.md). Sections 3–5 set delivery dates and accountable owners; the procedures below define the work and operating safeguards. Production-specific layer controls and recovery requirements remain in sections 7–13.

### Threat assessment and baseline

The initial assessment should bring together leadership, operations, and engineering. Start with an inventory of important information, accounts, equipment, suppliers, buildings, and services. Record who owns each item, who can access it, where it is held, and what depends on it. Include personal accounts currently used for company work and outsourced services.

Then map how sensitive information moves: who supplies it, where we store it, which people and programs handle it, and where it leaves our control. This exposes boundaries where checks are needed, including boundaries between customers and between development and production.

The scenarios below are hypotheses to assess, not findings about Lyceum:

| Scenario | Potential consequence | Questions for the baseline |
| --- | --- | --- |
| A criminal impersonates a founder or supplier | Fraudulent payment or disclosure | Are payment changes verified through a separate, known channel? Who approves them? |
| An attacker steals an employee account or laptop | Access to documents, code, or customer information | Is strong sign-in enforced? Is the laptop managed and encrypted? Can access be revoked? |
| A visitor enters an unattended work area | Theft, overheard discussions, or access to equipment | How are visitors admitted, escorted, and kept away from sensitive work? |
| A competitor or other motivated actor targets our research or leaders | Loss of intellectual property, coercion, or personal harm | What makes us a plausible target? Which exposure warrants additional protection? |
| A compromised software component or build tool enters a release | Malicious software reaches customers or production | Who can change the release process? Can untrusted code obtain production credentials? |
| An employee, contractor, or automated process has excessive access | Accidental damage or deliberate misuse | Can one identity read, change, or delete more than its task requires? |
| A service fails, data is deleted, or ransomware strikes | Extended interruption and permanent loss | Are recovery copies protected from the same failure, and have we restored them? |

For each scenario, record likelihood, business impact, existing safeguards, gaps, and an accountable owner. Simple low, medium, and high ratings with a written explanation are sufficient initially. Mark unverified safeguards as **unknown**, rather than assuming they work or claiming they are absent. Record the risk that remains after protections are applied.

Prioritize plausible scenarios with severe consequences and gaps that expose many assets at once, such as weak central account security. Revisit the model quarterly and after significant changes: a new product, sensitive customer data, a new office, a major supplier, or an incident.

### Physical security and protection of people

Physical security covers our workplace, equipment, conversations, and people's safety. It also applies in shared offices, at home, at conferences, and while travelling.

Our proposed baseline is individual, revocable building access; prompt removal of departing staff access; visitor registration and escorting; locked storage for sensitive equipment and documents; and secure disposal. Shared-office access does not imply permission to enter our work area. Guest networks and shared building equipment should be separated from company systems.

Confidential discussions belong in suitable spaces. Screens, whiteboards, printed documents, and visible prototypes can disclose information without a computer being compromised. Employees should know how to report a lost device, suspicious visitor, attempted manipulation, or concern about personal safety.

Threats to leaders and other exposed colleagues deserve explicit consideration: impersonation, harassment, stalking, coercion, and industrial espionage. Additional measures should follow credible exposure, such as sensitive negotiations, public visibility, or valuable research. Options include reducing unnecessary publication of personal details and travel plans, travel briefings, and professional assistance when warranted. Immediate danger goes to local emergency services; staff should not confront a suspected threat themselves.

Any monitoring should have a defined security purpose, limited access and retention, and appropriate review of privacy obligations. Protecting people must include respecting their privacy.

### IT security: identities, devices, and everyday work

#### A deliberately small device environment

The proposed workstation policy is **company-managed macOS or approved Linux; no Windows workstations**. This is a scope decision that reduces the number of environments we must maintain. Neither macOS nor Linux is secure merely because of its name.

Use Jamf to manage the Apple fleet, including enrollment, configuration, and update policies. Jamf Pro is an Apple device-management product; Linux needs a separately selected management approach that delivers equivalent safeguards. [Jamf Pro](https://www.jamf.com/products/jamf-pro/)

Before a device receives sensitive company access, require an inventory record, supported software, disk encryption, automatic screen locking, managed security updates, and evidence of compliance. Restrict routine administrator rights and provide a controlled path for tasks that need them. Define a lost-device response, including access revocation and remote lock or erasure where supported; remote erasure cannot be relied upon when a device is offline.

Linux support should be limited to approved distributions and versions that we can maintain. Decide explicitly how phones and personal devices may access company information; until a managed approach is established, they should not store sensitive company data.

#### Strong identities and recoverable access

Each person needs an individual company account. Centralize sign-in where practical so access can be granted, reviewed, and removed consistently. Use a company password manager for remaining passwords and remove shared credentials wherever possible.

The proposed default is phishing-resistant sign-in: authentication designed to resist a fake website collecting a reusable login secret. Require hardware security keys for administrators, production approvers, finance, and leadership; use security keys or approved passkeys for other staff. NIST distinguishes cryptographic phishing-resistant authentication from passwords and manually entered one-time codes. [NIST: Authenticator and verifier requirements](https://pages.nist.gov/800-63-4/sp800-63b/authenticators/)

Issue a separately stored backup key for key-dependent access and document a verified recovery process. Recovery and enrollment of a new key must not become an easy bypass; privileged-account recovery needs independent approval. Strong sign-in does not eliminate risks from compromised devices or stolen active sessions.

Remove access promptly when someone leaves, review it when responsibilities change, and include contractors, connected applications, and automated accounts. Protect emergency administrator credentials separately, alert on their use, and test recovery without weakening the normal policy.

#### Networks, applications, and information

A VPN creates an encrypted connection to a network; it does not establish that every connected person or device is trustworthy. Prefer access to specific applications based on identity and device checks. Where a private service needs a VPN, restrict what it can reach and retain checks at the service itself. This follows Google's guidance to combine Zero Trust with least privilege and separation of duties. [Google: Implement Zero Trust](https://docs.cloud.google.com/architecture/framework/security/implement-zero-trust)

Maintain an approved application list and a lightweight way to request additions. Assess suppliers according to the information and access they receive. This includes collaboration tools, browser extensions, AI assistants, and meeting-recording services. Define what information may be entered into each tool and how it is retained or shared.

Use a simple information classification: public, internal, confidential, and restricted. Give staff examples and handling rules; customer secrets, recovery credentials, and highly sensitive research need the strongest controls. Prefer named recipients over public sharing links, and remove information when the business no longer needs it.

Protect payment and bank-detail changes with independent verification using a known contact route. A message, voice call, or video that appears to come from a leader should not override that process.

### Development security

Development security covers what we design, the code we write or import, and the tools that turn it into a release.

Before building a sensitive feature, document what data it uses, who should be allowed to do what, how it might be abused, and how failures will be detected. For example, a customer export needs checks that the requester may access those specific records, limits on misuse, and an audit record of the export.

Require independent review for changes to shared release branches. Test security properties directly, including whether one customer can access another customer's information and whether a low-privilege account can perform an administrative action. Automated checks should detect exposed credentials, vulnerable dependencies, and common coding errors, with an owner and response deadline for findings.

Keep passwords, access tokens, and encryption keys out of source code and chat. Store them in a controlled secrets-management service. Use artificial or appropriately sanitized data in development; copying production data to a laptop should not be the normal debugging method.

Treat external libraries, outsourced code, AI-generated code, and build tools as inputs that need review. Keep an inventory of dependencies, limit who can introduce them, and maintain an update process. Protect the automated build-and-release system because compromising it can compromise every subsequent release. Untrusted test runs must not receive production credentials.

Before a first sensitive launch or a major increase in exposure, arrange a focused independent security review. Establish a clear route for reporting vulnerabilities and a process to assess, fix, and communicate them.

### Zero Touch Production procedures

**Production** is the live environment serving customers or running real business operations. We adopt **Zero Touch Production** alongside Zero Trust: approved automation performs routine production changes, and no individual has unilateral human access to production.

These principles are related but distinct. Zero Trust governs whether an access request should be permitted. Zero Touch Production governs how people operate live systems. The latter is Lyceum's proposed operating policy, not a claim that Google mandates this exact model.

#### The normal path is reviewed automation

A person proposes a change, another authorized person reviews it, automated checks run, and a controlled release process applies it. This includes infrastructure, application releases, database changes, and operational maintenance. Each release should be traceable to the reviewed change and its built software, with a tested way to reverse or safely recover from failure.

People have no standing ability to log into production machines, browse live databases, download customer records, or make direct changes. Routine investigation uses sanitized operational views with role-based access; a dashboard must not become an unrestricted view of customer information. Any exceptional human access, including sensitive read-only access, requires independent approval, narrow scope, a stated purpose, an expiry time, and an audit record.

Automation receives only the access required for its task, using short-lived credentials where possible. Development, testing, and production must have separate access boundaries and credentials. Production databases and administrative interfaces should not be directly exposed to the public internet.

#### Protect the mechanisms that enforce the rule

Automation alone does not prevent unilateral control. Someone who can rewrite the release process, approve their own change, or grant themselves administrator access can bypass the policy.

Protect release rules, approval settings, account permissions, recovery routes, and audit records with the same independent controls. Include the most powerful cloud and identity accounts. Verify that one person cannot bypass the process by using a different account or changing the rules. Choose services and account arrangements that support this requirement; any remaining unilateral provider-owner capability is a documented gap, not evidence that Zero Touch Production is complete.

#### Emergency access remains controlled

Prepare an emergency procedure for incidents where normal automation is unavailable or too slow. It must preserve independent approval: one person requests narrowly scoped access and another authorizes it. Establish a separately protected way to do this if the normal sign-in or approval service is unavailable.

Access should expire automatically and produce protected records of approvals and actions. Review its use promptly, revoke temporary permissions, and turn any necessary manual repair into a reviewed, repeatable change. Logs must avoid recording secrets unnecessarily.

This policy requires at least two trained, available people and deputies. If only one is available, we accept that some recovery actions must wait; a single-person bypass would contradict the policy. Leadership must plan staffing and service commitments around that tradeoff.

#### Detect incidents and prove recovery

Monitor unusual sign-ins, permission changes, sensitive data access, releases, and attempts to weaken protections. Every actionable alert needs a responsible person and an escalation route. Protect audit records so a compromised production account cannot simply erase the evidence.

Agree how long each critical service may be unavailable and how much recent data the business can afford to lose. Keep protected recovery copies separated from routine production credentials, and test restoration against those objectives. Backups alone do not demonstrate recoverability.

Maintain an incident procedure covering containment, evidence preservation, recovery, and communication. Name an incident coordinator and deputies, keep essential contacts available outside the affected systems, and decide who assesses customer and regulatory notification obligations. Practice with a realistic scenario and use the findings to improve the system.

## Appendix B — Training curriculum and delivery

The security coordinator owns both training tracks, with operations managing enrollment and domain owners assessing practical competence. Deliver Security 101 to the existing team by **18 December 2026** and complete role-specific training and practical exercises by **31 March 2027**. Onboarding and training before sensitive access or privileged responsibilities apply throughout the rollout. Record completion, exercise results, and follow-up work in the evidence tracker described in section 14.

Everyone needs enough understanding to make safe decisions and recognize when to ask for help. IT and engineering staff need additional practical competence because their mistakes can affect many people and systems. The proposed program combines a common foundation with training tied to responsibilities, consistent with NIST's approach to cybersecurity learning. [NIST: Building a Cybersecurity and Privacy Learning Program](https://csrc.nist.gov/pubs/sp/800/50/r1/final)

### Track 1 — Security 101 for everyone

Provide Security 101 during onboarding, before sensitive access is granted, with an annual refresher and short updates when threats or company practices change. Include employees, founders, and contractors with company access. Explain the reasons behind the rules using everyday situations:

- **Devices and physical access:** Never connect an unknown USB stick or other unapproved device, including a found device or conference giveaway. Hand it to IT without trying it on a personal computer. Use only approved removable media, lock screens, and report lost equipment or access badges promptly.
- **Deception and verification:** Recognize suspicious links, unexpected sign-in prompts, impersonation, and pressure to bypass a process. Verify unusual requests through a known, independent contact route, even when they appear to come from leadership.
- **Accounts and information:** Use the company password manager and approved authentication methods. Check recipients and sharing permissions, respect information classifications, and never disclose credentials or recovery codes to someone claiming to provide support.
- **Reporting:** Know how to report a mistake, suspected compromise, or physical safety concern immediately. Practice reporting without needing to prove that an attack occurred.

Everyone should also understand the following concepts at an intuitive level; mathematical knowledge is unnecessary.

| Concept | Plain-language meaning and practical lesson |
| --- | --- |
| Symmetric key | The same secret key encrypts and decrypts information. Anyone who obtains it may be able to read the protected information, so every copy needs protection. |
| Asymmetric keys | A related public and private key form a pair. Depending on the scheme, they support encryption, digital signatures, or establishing shared secrets. A public key may be distributed; the private key must remain protected. Confirm whose public key it is before relying on it. |
| Digital signature | A private key signs data and the corresponding public key verifies the signature. This can show that data has not changed and was signed using that key; it does not prove the content is safe or keep it confidential. |
| Private-key protection | A private key can confer the ability to impersonate someone, authorize actions, or decrypt information. Keep it in approved protected storage, preferably hardware that prevents extraction where appropriate. Never paste it into chat, source code, a support ticket, or an AI tool. Report suspected exposure immediately. |
| Shared-key management | A secret used by several systems needs a named owner, controlled distribution, an inventory of authorized users or systems, and a replacement and recovery process. Use an approved vault or key-management service. Prefer individual identities for people; passing around a common password weakens accountability. |
| Certificate authority (CA) | A trusted issuer digitally signs a certificate linking a public key to an identity, such as a website domain. A valid certificate does not establish that a business is honest. Do not bypass certificate warnings or install a new trusted CA at someone's request; refer the issue to IT. |
| Root of trust | A starting point on which other security checks depend. Examples include a protected device component and a deliberately trusted root CA key. If that foundation is compromised or replaced, checks built on it may become unreliable. Zero Trust still requires carefully protected trust foundations. |
| Multi-signature (multi-sig) | A mechanism requiring signatures from several distinct keys before an action is accepted—for example, two of three authorized signers. For independent human control, different people must control those keys. This differs from one person using several authentication factors, and from an ordinary two-person approval workflow. |

These explanations draw on NIST's [cryptographic glossary](https://pages.nist.gov/800-63-4/sp800-63/glossary/), [root-of-trust definition](https://csrc.nist.gov/glossary/term/roots_of_trust), and [trust-anchor definition](https://csrc.nist.gov/glossary/term/trust_anchor). Multi-signature systems provide a concrete example of requiring several valid signatures; this does not imply that Lyceum needs blockchain technology. [Ethereum: Multi-signature contracts](https://ethereum.org/developers/docs/smart-contracts/#multisig)

### Track 2 — Practical training for engineers, IT, and privileged roles

Provide engineers with practical security training, with role-specific content for IT staff, production operators, and approvers. Complete the relevant training before granting privileged responsibilities. IT staff should be able to enforce device policies, manage account recovery, recognize certificate-chain problems, and revoke compromised access. Engineers should be able to model threats, test authorization boundaries, handle secrets safely, and protect the build and release process. Production operators and approvers should practice independent approval, emergency access, and recovery.

For example, use [GitHub Security Lab’s Secure Code Game](https://securitylab.github.com/secure-code-game/) for hands-on engineer training in finding and fixing vulnerabilities in intentionally vulnerable code. Follow selected challenges with a team discussion of the underlying weakness and how to prevent it in Lyceum’s code and reviews.

Key-management training must cover generation, storage, access, distribution, rotation, revocation, backup, recovery, and eventual destruction. Explain how loss of an encryption key can make backups unreadable, and how theft of a signing key can permit impersonation. Practice certificate renewal and trust-store changes, and distinguish multi-signature approval from splitting a secret into recovery shares: reconstructing one key can restore unilateral control. Use established cryptographic services and libraries rather than inventing mechanisms.

Exercises should use a safe training environment and test outcomes: respond to an exposed test key, replace it without disrupting a service, recover from a lost security key, reject an unauthorized production change, and restore encrypted data with the correct recovery material. Finance and Legal also need role-specific scenarios, including payment fraud and confidential document sharing.

The security coordinator owns the curriculum and records completion, demonstrated competence, and follow-up needs. Refresh role-specific training annually and when responsibilities or systems change. A completed video is insufficient evidence on its own; use short scenarios for everyone and observed exercises for privileged roles. Findings should improve both training and the systems people use, without blaming employees for reporting mistakes.

## Appendix C — Exception workflow

The security coordinator maintains the exception register described in section 14. Establish the process and assess initial exceptions by **18 December 2026**, with domain owners implementing safeguards and accountable business leaders making independent risk decisions.

A standard must support real work. Finance may need software that only runs on Windows; Legal may be unable to use Microsoft 365 for a particular workflow. These needs deserve a clear route to a decision so people do not have to improvise outside company controls. An exception authorizes a defined departure from a standard while preserving its security purpose as far as possible.

### Request, assess, approve, and review

1. **Describe the need.** The requester records the business task, the standard that cannot be followed, why it is unsuitable, who needs access, what information is involved, and the required duration. Establish the actual constraint: compatibility, customer restrictions, confidentiality, accessibility, or another reason. Do not infer it from a department's preference alone.
2. **Consider workable alternatives.** The relevant IT or service owner works with the requester to assess supported options, including changes to the workflow. Compare usability, cost, support effort, data handling, and risk. A request cannot be resolved simply by insisting on a tool that does not meet the business need.
3. **Define the safeguards and remaining risk.** The security coordinator and system or information owner identify what the departure changes and how to contain it. Specify the users, devices, applications, data, permissions, monitoring, recovery arrangements, and support owner. Record what risk remains after these safeguards.
4. **Make an independent decision.** The accountable business leader accepts or rejects the remaining risk, with security review and confirmation that the service owner can support the arrangement. The requester cannot be the sole approver. Involve Legal or a qualified adviser where contractual or legal obligations are affected; internal approval cannot waive those obligations. Record the decision, conditions, and expiry date before enabling access.
5. **Implement and verify.** The service owner applies the safeguards and records evidence that they work. Inform affected staff of the permitted scope and reporting route. Approval alone does not mean the exception is ready for use.
6. **Review, renew, or close.** Review before expiry and after relevant incidents or changes. Renewal requires fresh confirmation of the need, safeguards, and remaining risk. At expiry, access ends unless renewed; plan migration, data retention, and removal in advance so closure does not unexpectedly interrupt critical work or destroy records.

Proposed default: approve exceptions for at most 90 days initially, then reassess. A continuing business requirement may justify a longer documented review period. An urgent request uses the same independent decision process with a shorter authorization period and prompt follow-up; urgency does not permit self-approval.

### Example: Finance needs Windows-only software

Confirm the required software and whether a supported alternative meets Finance's needs. If Windows is necessary, assess a dedicated managed Windows device or an isolated hosted Windows environment, including whether the software is supported there. The exception applies only to named users and the defined task.

Require supported software, encryption, managed updates, endpoint protection, strong sign-in, restricted administration, limited network and file access, and appropriate backups. Name someone able to maintain the Windows environment; an unmanaged machine is not an acceptable implementation. Test any exchange of financial files with the rest of the company and remove the environment when no longer needed.

### Example: Legal cannot use Microsoft 365

Record why Microsoft 365 does not meet the specific need and which documents and collaborators are affected. If Microsoft 365 is the company standard, assess an alternative document or collaboration service against those requirements. This example does not assume Microsoft 365 has already been selected or that Legal's constraint has a particular cause.

The alternative needs company-controlled accounts, appropriate authentication, restricted sharing, suitable confidentiality and supplier terms, defined retention, audit visibility, and a workable export and recovery process. Review data location and contractual requirements where relevant. Assign administration and offboarding ownership, and avoid uncontrolled copies across both platforms. Personal email or consumer storage is not an approved substitute by default.

An exception to a product or operating-system standard does not automatically relax least privilege, information handling, or independent production approval. If the proposed arrangement cannot preserve a core principle, escalate it as an explicit policy decision; do not describe it as compliant with that principle.

## Appendix D — Obligations and customer-assurance reference

Legal/privacy and commercial owners establish the initial obligations register by **30 November 2026** and keep it current through delivery and service changes. Use this reference to support the scope decisions and assurance roadmap in section 6.

For Lyceum, the working assumption is an EU AI inference business serving mainly large, regulated customers, including telecommunications, finance, and insurance. Inference means running models to produce results from inputs. Customer prompts, outputs, uploaded documents, model files, operational logs, and administrative access all belong in the assessment. Even if prompts are not retained, processing them can create obligations; retention is only one part of the question.

### Understand which kind of requirement we are dealing with

| Framework | What it establishes | Relevance to Lyceum |
| --- | --- | --- |
| ISO/IEC 27001 | A certifiable management system for information security: how an organization assesses risk, assigns responsibility, operates controls, and improves them. | Our proposed first certification target. Define a scope that includes the actual inference service and its supporting operations. Certification is generally voluntary, but customers can require it contractually. [ISO](https://www.iso.org/standard/27001) |
| PCI DSS | Payment-industry security requirements for environments handling payment-card data or affecting its security. It is generally enforced through payment-industry arrangements, rather than being an EU law. | Scope follows the payment-data environment, not the fact that a customer is a bank. Avoid accepting card data into inference inputs unless explicitly supported and assessed. [PCI SSC](https://www.pcisecuritystandards.org/merchants/) |
| GDPR | EU law governing personal-data processing and individuals' rights. Security is one part of the obligations. | Determine our role for each activity: a processor acts on a customer's instructions; a controller decides the purposes and means. We may have different roles for customer content, billing, and staff records. [EU guidance](https://europa.eu/youreurope/business/governance-and-sustainability/digital-and-data-compliance/data-protection-gdpr/index_en.htm) |
| EU AI Act | EU law with obligations depending on the AI activity, the organization's role, and the risk category. | Assess each offering and use case, including whether we provide an AI system or model, deploy one, or provide infrastructure. Operating inference does not by itself answer that classification. [European Commission](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai) |

GDPR also concerns lawful purposes, transparency, minimization, retention, individuals' rights, supplier agreements, and international transfers. For example, encrypting prompts does not authorize reusing them to train a model. Map the purpose and legal basis before introducing such reuse. Neither hosting in the EU nor obtaining ISO 27001 certification automatically establishes GDPR compliance. [EU: Data protection under GDPR](https://europa.eu/youreurope/business/governance-and-sustainability/digital-and-data-compliance/data-protection-gdpr/index_en.htm)

Outsourcing card payments can substantially reduce our PCI DSS scope, but does not automatically eliminate the merchant's responsibilities. Confirm the applicable validation route with the acquiring bank or other organization managing our payment compliance. [PCI SSC: Outsourced payment processing](https://www.pcisecuritystandards.org/faqs/does-pci-dss-apply-to-merchants-who-outsource-all-payment-processing-operations-and-never-store-process-or-transmit-cardholder-data/)

The AI Act extends beyond cybersecurity into matters such as prohibited practices, transparency, human oversight, and AI literacy. A secure model can still be used in a prohibited or improperly governed way. Requirements have phased application dates and amendments; assess the current rules for the specific service and customer use case before launch or material change. ISO 42001 certification does not replace the applicable legal assessment or conformity-assessment process. Sources checked on 4 November 2026. [European Commission: AI Act](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai), [Implementation guidance and dates](https://digital-strategy.ec.europa.eu/en/faqs/navigating-ai-act)

### Regulated customers bring additional obligations

**Finance and insurance: DORA.** The Digital Operational Resilience Act places requirements on financial entities within its scope, including how they manage technology suppliers. Expect contract requirements concerning service descriptions and levels, processing locations, incident assistance, data return, and termination. Services supporting critical or important functions attract additional provisions, including audit and access rights, continuity arrangements, and exit planning. Build the ability to support these requirements into our service and contracts. [DORA, Article 30](https://eur-lex.europa.eu/eli/reg/2022/2554/oj)

Supplying a financial institution does not automatically make Lyceum a designated critical ICT third-party provider. Such designation creates a separate EU oversight relationship. There is no general-purpose “DORA certificate” that discharges the customer's or supplier's responsibilities. [European Banking Authority: DORA oversight](https://www.eba.europa.eu/activities/direct-supervision-and-oversight/digital-operational-resilience-act/dora-oversight)

**Telecommunications and cloud: NIS2.** NIS2 covers specified sectors, including electronic communications and cloud services, and includes supply-chain security. Assess whether our own service falls within national implementing law, considering its classification, size, and any special inclusion rules. Independently of direct scope, telecom customers may impose supplier controls and evidence requirements. A customer's NIS2 obligations and our own legal obligations must be recorded separately. [European Commission: NIS2 scope and requirements](https://digital-strategy.ec.europa.eu/en/faqs/directive-measures-high-common-level-cybersecurity-across-union-nis2-directive-faqs)

Certification priorities and timing are defined in section 6. Select assurance that covers the actual service and customer requirements; a supplier’s certification does not certify Lyceum.

For an inference service, prepare evidence about isolation between customers; treatment of prompts, outputs, caches, and logs; model provenance and controlled updates; privileged support access; data deletion; processing and support locations; subcontractors; and incident and recovery exercises. Explain whether customer content is used for training, and enforce the agreed policy technically and contractually. These are proposed assurance priorities arising from our service and customers, not a list of controls that a certificate automatically guarantees.

### Run one practice with a clear obligations register

Legal or a qualified adviser should establish applicability with the service owners, using the countries served, customer sectors, data flows, AI roles, and contracts. Record each obligation, its scope, effective date, owner, required evidence, and review date. Separate legal duties, contractual commitments, voluntary standards, and internal policy choices.

Map each obligation to implemented controls and retain evidence once for reuse. For example, an access review can support security risk management, a certification audit, and a customer contract, while privacy notices and AI transparency requirements need their own work. An internal exception cannot waive a law or unilaterally amend a customer contract. Alternative controls are acceptable only through the routes the relevant requirement actually permits.

Maintain the security practice continuously and demonstrate compliance within its assessed scope. Certification and customer assurance should reflect working controls and current evidence. Delivery milestones and audit targets are set out in sections 3–6.
