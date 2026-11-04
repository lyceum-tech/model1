# Architecture and production design patterns

[Pierre Aubert](mailto:pierre@lyceum.technology)\- v0 \- 20261021 – add your name

**TL;DR:** Soon Lyceum will manage 1000s of GPUs and the number will grow quickly. We need to transition from pets to cattle management. I proposed a few design patterns that we want to implement in the stack and iteratively converge to it. Each exception needs to be vetted. Production principles are also critical and follow the same patterns and processes.

* It follows the KISS principle (simple is better than complicated).  
* If you don’t have the time to do it well, when will you have the time to do it again?

Notes: 

* the principles will be skills for agents and will be checked automatically by a to be built non-regression. It is still essential that you understand them and agree with them. Questions and comments are welcome.  
* See also [docs/wiki/docs/development/explanations/first-principles.md](https://devdocs.lyceum.technology/development/explanations/first-principles/)  
* I am trying not to mix the principles with how you implement them.   
* We should partition the principles  
  * Architecture (this doc)  
  * Production (another doc)  
  * Development (we have that in [first-principle.md](https://devdocs.lyceum.technology/development/explanations/first-principles/))  
  * Using AI (another doc)

# Architecture 

## Trees are better than Graphs

*The architecture is built with layers. A service from a layer can only call down the stack and never up. Within a layer, you need a circuit breaker and a retry policy.*

### Examples

K8S needs a service discovery system. Where should it run? You can put etcd on a bare metal machine but then you do not benefit from elasticity which is bad because you want to be able to scale reads at least. You can run etcd on top of K8S but then you have a loop (both depends on each others and that make things more complicated for debugging, rolling out, etc)

### Counter Examples

Let's suppose I need a distributed file system. Ideally it would run on top of K8S. But K8S also would like to store some data somewhere safe. Ideally k8s would have its own dedicated instance of the distributed file system. In this case that's too complicated to run and too expensive a complex distributed file system. OK but know you need to know.

### Why

* Hysteresis cycles and dependency loops lead to disaster.  
* Graphs are harder to reason about than trees.

## Locality is your best friend

*The control plan is collocated with the computer and network plane at the cluster level. Global control planes talk to local ones. They are replicated. Local control planes are low dependencies. Local planes never call the global one.*

### Examples

Kubernetes control plane is in the same cluster as the machines / VM it manages. Doing cross datacenter or cross-region is yolo-yolo.

### Counter Examples

Alerting and black box monitoring are the 2 classical examples.

### Why

- Again less complexity, less correlated failures.  
- Also the cost of building locally (a few cpu) is marginal wrt to the cost of an incident.

## Low dependency is survival.

A critical part of the infrastructure needs to have as little dependencies as possible both in code and in calls to services.

### Examples

If K8S goes down, then the whole infra is locally crashed. You don't want your K8S to do authentication outside the local cluster and you clearly want  a way for K8S to work even if authentication does not.

Low dependency is also true for the code. You don't want to rely on too many packages/libraries of dubious quality which are also a security risk.

### Counter Examples

Not many. Usually exceptions are made for conveniences.

### Why

* Low dependency improves reliability.

## Pets vs Cattles

In general, machines are many and we are few. Automation is the only way to implement and control so many machines, rules, policies etc GPUs are partly a counter example explained below.

### Examples

At scale machine management or container management is automated, think K8S. It is always cheaper and faster to automate than to do something manual. Manual actions are risky and reserved for on-call.

### Counter Examples

GPU are so expensive that the time a machine is down is costly enough that paying something to repair it makes sense.

## Why

- At a small scale 1000 machines, 20 services, 50 policies it is already unmanageable.  
- At a larger scale or a more complex setup, like VeraRubin then automation is not an option: everything is automated. You will spend less time designing and coding a system than doing it manually.

# Production Principles

I will add more to them soonish but would like to concentrate on the design part first.

## Reliability

Reliability is critical but like most things it has a cost. The balance between cost and quality is defined by the SLO. 

## Security

Security is not an option. We need to design for it. Secure by default, least access policy and enforced automatically. Security required defense in depth, for ex nested containers to prevent escaping from KVM.

## Policies are hierarchical

Policies are better in a tree where a policy inherits the properties of the node above in the tree and of course as an owner of the node you cannot change the policies from above.

## Zero Touch Prod

You shall not do manual action on a production machine. Root access is severely restricted and ideally removed. Immutable images are a good idea.

## Mutations

* We should split the intent from the execution.   
  * What's the problem? You want to update a bunch of machines or vms and you want them to be on this new kernel that does not have a security bug. You run your ansible playbook. Most machines upgrade but some don’t (in repair, bugs, down, …). How do you keep the fleet up to date?   
  * The intent is that all machines need to have kernel-7.5.6 and the actuation is the loop that makes it happen. When size increases you can never be 100% compliant but you can converge to it.  
* Mutations are rate limited and all controllers need to respect them. \[something which is not in K8S but that we will add)  
* Rolling over is better than rolling back.  
* “Big Red button” \-\> stop mutation globally, cool down and things.

## Incident management

Let's follow the SRE playbook.

