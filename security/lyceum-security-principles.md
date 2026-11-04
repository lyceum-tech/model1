# Lyceum security principles

**Status:** Proposed foundation for discussion, not a statement of controls already implemented.  
**Audience:** Founders, leaders, and team members; no IT background assumed.  
**Purpose:** Explain why security matters, the principles behind our choices, and the policies that guide our security practice. The [implementation plan](lyceum-security-plan.md) contains implementation procedures, training content, and delivery sequencing through June 2027; a future companion spreadsheet will track implementation and evidence.

## 1. Start with principles

### Understand the threats and establish where we stand

Security starts with understanding what matters to the business, what could harm it, and which protections already work. A **threat model** is a structured account of these questions. It helps us choose safeguards that address realistic risks instead of purchasing tools first and inventing a justification afterwards.

For Lyceum, the starting questions are: What must we protect? Who could threaten it, deliberately or accidentally? How could they succeed? What would the consequences be? What evidence do we have that our current safeguards would stop, detect, or contain the event?

We must distinguish a documented intention from a verified protection. “We have backups” is an intention until we can demonstrate that we can restore the information we need within an acceptable time.

### Apply least privilege everywhere

**Least privilege** means giving a person or system only the access needed for a defined task, for only as long as necessary. Access should follow responsibilities and expire when those responsibilities end.

This applies to building keys, financial approvals, shared documents, laptops, software tools, and production systems. Being a founder should not automatically confer unrestricted technical access. A program that sends notifications should not also be able to export the customer database.

For especially sensitive actions, we also require **separation of duties**: one person cannot request, approve, and carry out the entire action alone. This limits both mistakes and the damage an attacker can cause through one compromised account.

### Reduce the attack surface

The **attack surface** is the collection of places through which someone could reach our people, information, or systems. Every extra account, application, exposed service, device type, and retained copy of sensitive data adds something we must protect.

We should collect less information, retain it only as long as needed, remove unused access, and operate a small set of supported tools. Simplicity is a security advantage because a small team can understand and maintain a simpler environment.

### Apply Zero Trust principles

**Zero Trust** means that access is not automatically safe because it comes from our office, our network, or someone with a company email address. Each access decision should consider the identity involved, the requested action, and relevant conditions such as whether the device meets our security requirements. Access should be reassessed when those conditions change.

This is a design principle, not a product or a statement of distrust in employees. Google's BeyondCorp approach illustrates moving access decisions from the network perimeter toward users and devices. [Google: What is Zero Trust?](https://cloud.google.com/learn/what-is-zero-trust)

### Build security into decisions from the beginning

A **security-first approach** makes security part of choosing a supplier, designing a feature, opening an office, and launching a service. We define the necessary protections before committing to a design and make safe settings the default. Google's security-by-design guidance supports integrating security throughout development and operations. [Google: Implement security by design](https://docs.cloud.google.com/architecture/framework/security/implement-security-by-design)

The level of effort should follow the risk. A public brochure and a customer-data export feature need different scrutiny. Where we accept a risk, a named leader should understand the consequences and set a date to revisit it.

### Assume a protection can fail

We need several independent safeguards, visibility into significant events, and a practiced recovery process. A stolen password should encounter another barrier; a compromised account should have limited reach; a destructive action should leave evidence and recoverable data.

Security therefore includes prevention, detection, response, and recovery. A practice that only tries to prevent incidents is incomplete.

## 2. Why this matters for a new startup

Lyceum depends on its people, ideas, cash, customer relationships, and ability to deliver. A security failure can expose intellectual property, endanger a colleague, divert a payment, interrupt service, or destroy trust. A young company has limited capacity to absorb these losses.

Early habits also become the company's operating model. Informal account sharing and unrestricted founder access may feel convenient with three people, but become difficult to unwind as employees, contractors, customers, and suppliers accumulate.

Our objective is a proportionate, repeatable practice: clear ownership, a few enforceable rules, and evidence that those rules work. Buying security software or achieving a certification would not, by itself, establish that practice.

## 3. Understand exposure before choosing controls

Base security decisions on a shared understanding of our assets, data flows, dependencies, and realistic threats. Include people, physical premises, suppliers, and the boundaries between customers and between development and production.

Assess likelihood and business impact, assign an owner to each risk, and prioritize the most consequential gaps. Treat unverified safeguards as unknown. Revisit the assessment regularly and whenever the business or its exposure changes materially.

The assessment procedure and starting scenarios are in the [implementation plan](lyceum-security-plan.md#appendix-a--baseline-operating-procedures).

## 4. Protect people and physical assets

Security covers people's safety as well as equipment and information, wherever work takes place. Access to workplaces and sensitive material should be individual, limited to a legitimate need, and revocable.

Consider threats to leaders and other exposed colleagues, including impersonation, coercion, harassment, and industrial espionage. Additional protection should follow credible exposure. Staff should have a clear route to report concerns and obtain help.

Physical safeguards and monitoring must respect privacy. The [implementation plan](lyceum-security-plan.md#appendix-a--baseline-operating-procedures) sets out workplace, visitor, travel, and equipment procedures.

## 5. Keep everyday IT controlled and manageable

Operate a small, supported device and application environment that the team can maintain. The proposed workstation standard is **company-managed macOS or approved Linux; no Windows workstations**, with business needs handled through the exception process. Sensitive access requires a managed device that meets the security baseline.

Use individual company identities and phishing-resistant sign-in: authentication designed to resist fake login sites. Require hardware security keys for administrators, production approvers, Finance, and leadership; other staff may use security keys or approved passkeys. Account recovery must preserve the same level of protection, including independent approval for privileged accounts.

Grant access according to responsibilities, review it when those responsibilities change, and remove it promptly when it ends. Apply access checks to each service, including services reached through a private network.

Choose applications and suppliers according to the information and access they receive. Handle information according to its sensitivity, limit sharing and retention, and independently verify sensitive financial instructions. Device settings, approved-tool procedures, and identity controls are detailed in the [implementation plan](lyceum-security-plan.md#appendix-a--baseline-operating-procedures).

## 6. Build security into development

Define security requirements before building sensitive features. Review changes independently, test access boundaries, and protect the tools and dependencies used to produce releases. External and AI-generated code need the same scrutiny as other contributions.

Protect secrets and customer data throughout development. Give findings an owner and a response deadline, and obtain independent security review before a sensitive launch or a major increase in exposure.

The [implementation plan](lyceum-security-plan.md#appendix-a--baseline-operating-procedures) defines development checks and release safeguards.

## 7. Operate production through independent control

**Production** is the live environment serving customers or running real business operations. We adopt **Zero Touch Production**: approved automation performs routine changes, and no individual has unilateral human access to production. Zero Trust governs access decisions; Zero Touch Production governs how people operate live systems.

Changes require independent review. People have no standing access to production machines or customer data; exceptional access, including sensitive read-only access, must be independently approved, narrowly scoped, time-limited, and recorded. Routine investigation uses sanitized operational views.

The same independent controls must protect the mechanisms that enforce this policy, including release rules, administrator permissions, account recovery, and audit records. Any remaining ability for one person to bypass approval is an explicit gap.

Emergencies preserve independent approval. Leadership must provide at least two trained, available people and deputies, with an approval path that survives failure of normal systems. If only one person is available, some recovery actions must wait; staffing and service commitments must reflect that tradeoff.

Detect significant security events, assign responders, and practice recovery against business-approved objectives. Protected backups and measured restoration are essential. The [implementation plan](lyceum-security-plan.md) covers production controls, emergency procedures, incident response, and recovery.

## 8. Train everyone, and train engineers for their responsibilities

Security training has two levels. **Everyone**, including founders and contractors with company access, needs a common foundation for safe everyday decisions, recognizing threats, and reporting concerns. **Engineers** need additional practical training to design, build, and operate secure systems; IT staff, production operators, and approvers need the relevant parts for their responsibilities.

Training must prepare people before they receive sensitive access or responsibilities, be refreshed as risks and systems change, and demonstrate understanding through practice. Reporting mistakes should lead to learning and improvement without blame.

The [implementation plan](lyceum-security-plan.md#appendix-b--training-curriculum-and-delivery) contains the Security 101 curriculum, technical concepts, exercises, delivery dates, and completion evidence.

## 9. Assign ownership and remain accountable

Leadership owns the business risk and funds the security practice. Appoint a security coordinator and deputy, with named owners for physical security, IT, development, and production. People may hold several roles in a small team, while sensitive approvals still require independent people.

Make reporting easy and safe, and give important suppliers explicit responsibilities and contacts. Review risks, access, exceptions, and control effectiveness regularly. Use evidence of protection and recovery to judge progress.

The [implementation plan](lyceum-security-plan.md) assigns delivery roles, review schedules, and measures. NIST's six functions—Govern, Identify, Protect, Detect, Respond, and Recover—provide a useful completeness check. [NIST: Cybersecurity Framework 2.0 for Small Business](https://www.nist.gov/itl/smallbusinesscyber/nist-cybersecurity-framework-0)

## 10. Handle exceptions explicitly

Standards must support real work. When a standard cannot meet a legitimate business need, assess workable alternatives and document the safeguards and remaining risk. An accountable leader must approve the exception independently, with security review and a service owner able to support it.

Exceptions need a defined scope, an expiry, and review before renewal. Verify safeguards before enabling access. Urgency does not permit self-approval, and internal approval cannot waive legal or contractual obligations.

An exception to a tool or operating-system standard does not automatically relax least privilege, information handling, or independent production approval. A departure from a core principle requires an explicit policy decision and must be described honestly.

The [implementation plan](lyceum-security-plan.md#appendix-c--exception-workflow) contains the workflow, review periods, and Finance/Windows and Legal/collaboration examples.

## 11. Distinguish security, compliance, and assurance

**Security** is our ability to protect people, information, and services against realistic threats. **Compliance** means meeting applicable laws, contracts, and standards. **Assurance** is the evidence that lets customers, auditors, or regulators assess our arrangements.

These reinforce one another, but each needs attention. A secure system may still process data for an unlawful purpose; a documented process may fail against an overlooked threat. A certificate covers a defined scope and cannot establish that every activity is secure or compliant.

As an EU AI inference business serving regulated customers, Lyceum must assess obligations against its actual services, data flows, countries, customer commitments, and AI roles. Legal or a qualified adviser should establish applicability with service owners. Hosting in the EU or using a certified supplier does not establish Lyceum's own compliance.

Maintain one security practice with evidence that can support multiple obligations. Keep legal duties, contractual commitments, voluntary standards, and internal policies distinct. Customer claims must reflect controls that actually work and assurance that has actually been obtained.

The [implementation plan](lyceum-security-plan.md#appendix-d--obligations-and-customer-assurance-reference) holds the framework comparison, legal references, obligations-register procedure, and customer evidence requirements; its certification roadmap sets priorities and timing.
