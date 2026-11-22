# Kubernetes in Practice

## 01. What survives a failure?

Imagine joining a shift with one small responsibility. Your team runs a status page. It promises to tell readers whether a service is working. At nine in the morning, the process serving that page disappears. What, exactly, brings it back?

A container image can start a new process. On its own, the image never notices that the old one died. Kubernetes adds a continuing agreement. You describe how many copies should exist. A controller observes what exists now and asks for changes. Another component starts the replacement. This cycle is called reconciliation.

Our book follows that status page through its working life. Keep two questions in mind. Who owns the object I am looking at? And what would a reader see right now? A controller can report the desired number of copies while a reader still gets an error. By the end of this recording, you will know how to investigate both sides of that sentence.

## 02. From a request to a running process

When you submit a Deployment, you talk to the API server. It checks your identity and permissions, validates the request, and records the accepted state in etcd. The Deployment controller notices the new object. It creates a ReplicaSet, which in turn asks for Pods. At this stage a Pod can exist on paper while no machine has started its process.

The scheduler looks for a suitable node and records its choice. The kubelet on that node watches for assigned work. It asks the container runtime to pull the image and start the containers. Status travels back through the API.

Now imagine the scheduler is unavailable for a minute. An existing status page might continue serving traffic. A replacement Pod could be waiting with no assigned node. That difference tells you which part of the system to examine. A failure in cluster management and a failure in the customer request path can have quite different timelines.

## 03. Your first local cluster

On Windows, start Docker Desktop and enable its Kubernetes cluster. Use Linux containers for the exercises. Open PowerShell and ask kube control for the current context. A context combines a cluster, an identity, and optionally a default namespace. Confirm that you selected Docker Desktop, then list the nodes. Wait until a node reports Ready.

The command line client can exist on your laptop even when the server is stopped. Checking the client version proves one thing. Getting a live answer from the API proves another. If PowerShell works but your Linux shell does not, inspect the configuration file used by each shell. They can have different home directories.

Our project lives in a namespace called kube book, written with a hyphen. Create that namespace from the supplied file and apply the base directory with Kustomize. Give the images time to download. Two ready replicas are your first milestone. Later, you will also send a request to check what those replicas serve.

## 04. Reading an object

Open the Deployment and read it from the outside in. The kind identifies the type of object. Metadata gives it a name and a namespace. The specification describes the state you want. The live object also carries a status written by Kubernetes components. This is why a file on your laptop and an object returned by the server can look different after a successful deployment.

Follow one label. Our Pods carry the application label for the status page. A Service uses a selector to find that label. The selector sees the labels on the Pod template. A decorative label on the Deployment itself does not put anything on the Pod.

Try predicting what will happen if you edit a Service selector and leave the Pods alone. The Pods keep running. The Service can still exist and have an address. The connection between them can disappear. This small distinction will be enough to solve our last incident.

## 05. Three containers and two ready

Containers inside a Pod share a network address. They can reach each other on localhost. They also share any volumes explicitly mounted into both containers. Their writable image filesystems remain separate. Use a multi-container Pod when processes actually need that shared lifetime or local communication. Two separate web replicas belong in two separate Pods.

In the diagnostic exercise, three containers start together. Two stay alive. The third writes a short message, then exits with code one. The Pod can show two out of three ready and a restart count that keeps increasing. A restart delay gives the failing process time between attempts. The delay is a symptom, not the explanation for the exit.

Read the events, name the failing container, then request the logs from its previous instance. A small log message, the exit code, and the container name together tell a much better story than the word Running.

## 06. Changing a running Deployment

A Deployment owns a template and a desired replica count. Its ReplicaSet keeps track of the Pods that match one revision of that template. When you change the template, the Deployment can create another ReplicaSet and move capacity from old to new in stages.

Our status page normally has two replicas. During an update we allow one extra Pod and ask Kubernetes to keep the available count at two. This improves continuity, but only if the cluster has space for the third Pod and the new version becomes ready. Watch the old and new ReplicaSets. A stalled rollout while the old page still works is entirely possible.

Scaling from two replicas to three changes a number. Changing the content volume reference changes the Pod template and creates a rollout. Rollback restores a retained template. It cannot recreate a configuration object someone already deleted. Keep that dependency in mind before calling any rollback successful.

## 07. Configuration has a lifetime

Our status page serves a small file supplied by a ConfigMap. The image contains the web server. The mounted file supplies the message. Two environments can use the same image and display different text. The application reads the file when it handles a request.

A value injected as an environment variable is captured when the container starts. An ordinary mounted ConfigMap may update later, after the node refreshes it. An application that read the file only once might still need a reload. A file mounted using subPath does not receive these projected updates.

For a release we give the new content a new object name and change the reference in the template. That makes the old content available for recovery. Put actual credentials in a Secret with appropriate access restrictions. Base sixty-four is a way to represent bytes. Anyone who can read the value can recover them. Use a harmless sample value when practicing.

## 08. Finding a Service

A reader should not have to learn a new Pod address after each replacement. A Service provides a stable name. In our namespace, a client can ask for status web, written with a hyphen. The Service accepts traffic on port eighty. Its named target port resolves to port eighty eighty on each selected Pod.

Begin a network investigation with three questions. Did the name resolve? Did the Service select the expected endpoints? Did the server answer on the target port? The answers point to different owners of the problem. Inspect the EndpointSlice and look at readiness as well as addresses.

Port forwarding is convenient when you are at your laptop. Forward local port eighteen thousand eighty to the Service, and your browser can display the page. The forwarding session picks a Pod. A successful local request leaves a separate question open. Can another Pod reach the Service through cluster networking? The supplied client gives you a way to test that path.

## 09. Bringing traffic into the cluster

Suppose the platform team gives you a shared gateway and a domain. The infrastructure team maintains the listener. Your application team owns a route that matches a host or a path and sends traffic to the status Service. Gateway API expresses that agreement with different objects.

A GatewayClass identifies an implementation. A Gateway describes listeners. An HTTPRoute describes matching and forwarding. The controller must exist, and the listener must allow the route to attach. In an older installation you may instead see an Ingress and an Ingress controller serving a similar entry point.

Read the route status for acceptance and resolved references. Then send a request with the expected host name. A healthy backend cannot make a request match the wrong host. Conversely, an accepted route can point to a Service whose Pods are all unready. Diagnose the listener, the route, and the backend as separate steps. On a basic laptop cluster, you can do the rest of the book with port forwarding.

## 10. Health is a question with a purpose

A startup probe gives a slow process time to initialize. Readiness determines whether the Pod should receive ordinary Service traffic. Liveness gives the kubelet grounds to restart a container that is no longer making progress. The same failure signal can be helpful for one decision and harmful for another.

Imagine that a shared database is offline for thirty seconds. Restarting all web servers may add load just as the database recovers. Choose a liveness test whose failure a restart can plausibly fix. Our simple server uses a local port check for liveness and an actual file request for readiness.

During shutdown a process also needs time to stop accepting work and finish active requests. Routing changes and local shutdown can overlap. Measure what callers see during a release. For a quick thought experiment, make the readiness path point to a missing file. Expect a running process, a failing readiness check, and fewer eligible backends. Restart counts need not rise.

## 11. The price of a replica

A CPU request is part of the scheduler's placement calculation. A CPU limit can throttle a busy container. Memory pressure behaves differently. Crossing a memory limit can end a process with an out of memory kill. A restart without a visible application exception can therefore have a resource explanation.

Read our page's request as a fraction of one core. Fifty millicores is one twentieth of a core. Two replicas each requesting fifty millicores ask the scheduler to account for one hundred in total. A rollout with one extra replica temporarily needs room for a third request as well.

Capacity planning has two useful views. The scheduler considers requests against allocatable capacity and existing commitments. A live usage graph describes recent consumption. A quiet node can still have too little uncommitted requested capacity for the next Pod. If a Pod stays Pending, inspect its scheduling events. If a container restarts after it ran, inspect the last termination reason and its memory history.

## 12. Choosing a node

A Pod can require particular node labels, prefer to sit near particular workloads, or avoid sharing a failure domain. A taint lets a node repel Pods that lack a matching toleration. A toleration permits a placement and leaves the scheduler free to choose another suitable node.

Consider two replicas on a single laptop node. They give you two application processes. Losing the laptop removes both. A rule that strictly requires different nodes cannot manufacture a second node. One replica can remain Pending. A preference can permit a practical local exercise while allowing a different decision in a larger cluster.

A DaemonSet addresses another requirement. You may need a log collector on each eligible node. Adding a node then creates a reason to run another collector there, even if the status page has exactly the same traffic. Start placement design by naming what must survive and which machines are actually eligible.

## 13. Where files live

Write a file into a container's writable layer and it belongs to that container instance. An empty directory volume can survive a container restart inside the same Pod. A replacement Pod gets a new empty directory. For data that must survive the replacement, the project can ask for a persistent volume claim.

A claim requests storage. A storage class describes how a provider can provision it. Binding and mounting are different stages. A class may delay binding until a Pod needs the volume so that placement and storage topology agree. Check the claim, the consumer Pod, and their events together.

In the exercise you write a small note to the mounted volume. Delete only the named consumer Pod, recreate it, then read the note. Keeping the same claim is part of the experiment. Keeping a claim is also different from having a backup. If a program overwrites the note, the volume usually preserves the new mistake just as faithfully as the original.

## 14. Stable names and stateful applications

A StatefulSet gives replicas predictable identities, such as ledger zero and ledger one. A headless Service supports direct discovery of the members. A volume claim template can give each ordinal its own claim. When the Pod for ledger zero is replaced, its successor can use the same identity and the same claim.

Here is a common design error. Two Pods with stable names and two persistent disks do not automatically form a replicated database. Replication, membership, leader election, and recovery depend on the database or its operator. Kubernetes supplies building blocks for that program to use.

Our small ledger exercise deliberately avoids a database. Write a different note on each replica. Replace just the first Pod. Look for the original first note and confirm that the second replica still has its own note. This experiment makes the identity guarantee visible without hiding it underneath database behavior.

## 15. Work with an ending

A web service should continue running. A daily report should finish and record an outcome. A Job tracks completion. A CronJob creates Jobs on a schedule. Failure may produce another attempt, so think about what happens if a process writes its result and crashes before reporting success.

Give each reporting period a stable identifier. If the report for Tuesday already exists, a retry can recognize it and avoid a second copy. The same idea applies to messages, invoices, and exports. A successful process exit and exactly one business outcome are separate engineering problems.

Our exercise creates a suspended schedule and launches one Job from its template by hand. Wait for completion and inspect the logs. Setting the concurrency policy to Forbid can prevent overlapping scheduled executions from the same CronJob. It cannot act as a universal lock for jobs started by other paths. Choose the history limits, retry policy, and time zone deliberately.

## 16. Who is allowed to read?

Your terminal identity and your application's identity can have different rights. A ServiceAccount belongs to a namespace. A Role describes allowed verbs on resources there. A RoleBinding connects the Role to a subject. In the exercise, the reader can list Pods and cannot read Secrets through this binding.

Test both sides of that promise. A positive test confirms that the application can do its work. A negative test can reveal permissions from another binding, because role-based access grants are additive. Testing as another identity requires permission to impersonate it. A refusal to impersonate tells you something about your own account.

The status page has no reason to call the Kubernetes API. Its template turns off automatic mounting of the service account token. Starting with the question, which request does this program need to make, leads to a much smaller set of permissions than granting a wide role and hoping to reduce it later.

## 17. Containing a workload

Security settings answer different questions. A non-root user reduces the authority of the process inside its container. A read-only root filesystem makes accidental writes to the image layer fail. Dropping unused capabilities removes specific privileges. Our web server listens on a high port and serves mounted files, so it can work within those restrictions.

NetworkPolicy controls which connections participating Pods may make or receive. It requires a network implementation that enforces the rules. Our optional policy selects the status page and allows incoming traffic from client Pods with the expected access label in the same namespace.

Test from two clients. The labeled client should reach the page. An otherwise similar client without the label should time out when enforcement is active. Both opening the page is evidence worth investigating. Confirm the policy selector, the clients' labels, and the network implementation. A successful request from a browser using port forwarding is a different path and is a poor test of this rule.

## 18. More replicas and fewer interruptions

A horizontal autoscaler observes a metric and adjusts the desired replica count. When its target is average CPU utilization, the percentage is relative to CPU requests. If two replicas average eighty percent and the target is fifty, a simplified calculation suggests four replicas. Tolerance, missing samples, and stabilization can change the actual decision.

An autoscaler cannot supply missing nodes, missing metrics, or a faster database. Check that the metrics API returns fresh values before interpreting an unknown target. When you hand control of the count to the autoscaler, continually applying a conflicting fixed count creates needless oscillation.

A disruption budget addresses another question. During voluntary eviction, how much availability should be maintained? With two healthy replicas and a minimum available count of one, one eviction may be allowed. A sudden node failure does not ask the budget for permission. On a single laptop node, inspect this budget and its allowed disruptions without draining your only node.

## 19. What did the reader experience?

A green Pod is a statement about a Pod. A successful page request is a statement about a reader's journey. Collect both. Logs explain individual events, metrics count and measure them over time, and a distributed trace follows one request through participating services.

Consider a ten-minute window with one thousand eligible page requests and five server errors. If that is your definition of failure, observed availability is ninety-nine point five percent. Now ask where you counted. A counter inside the application may miss failures that happened at the gateway before the request got there. Select the measurement point to match the promise made to users.

Our small server writes a request log to standard error. Compare a request for the home page with one for a missing path. Look at the client result as well as the container logs. In a larger system, group by route or status class, and keep unique request identifiers in logs where they can help investigate one case.

## 20. Diagnosing a failed page

A report arrives. The status page is down. Start by recording the failing route, the time, and an example response. Confirm which cluster and namespace you are inspecting. Then follow the request toward the application. At each boundary choose a test that can distinguish between two possible causes.

If the client can resolve the Service name but there are no ready endpoints, inspect the Service selector and the Pod labels. If there are endpoints, test the named port and the process. If a container keeps restarting, record its last exit and previous logs before replacing it. If no node was assigned, application logs may not yet exist.

Keep your incident notes small and precise. Write down an observation, what it suggests, and the next test. A good note might say that two Pods are Ready, that the Service has no addresses, and that you are checking the selector. That gives the next engineer a reason to follow the same evidence or to challenge it.

## 21. One application, several environments

Copying a full manifest for every environment is initially convenient. It becomes difficult to tell whether a difference is intentional. Kustomize provides a base and overlays. Start with the same status page, add a second configuration object, and patch just the reference in the Deployment. Render the result before sending it to the cluster.

The rendered manifest makes a useful review artifact. Look for the namespace, versioned content name, replica count, and image. A small patch can have a large effect if it hits the wrong field. Our release deliberately keeps the first configuration object, which makes a rollback meaningful.

Helm tackles packaging with charts, templates, and values. Rendering a chart locally lets you review the Kubernetes objects it will produce. A successful rendering still leaves questions for the cluster, such as whether the storage class exists. In both tools, the output is a concrete contract that you can inspect before a release.

## 22. Following a release through Git

Picture a change that turns the status page from version one into version two. A reviewer should be able to see what changed, which environment will receive it, and how the team will recognize success. A pipeline can validate the rendered manifests, apply them, wait for readiness, and issue a request through the Service.

In a pull-based GitOps setup a controller observes the approved repository revision and reconciles the cluster toward it. A manual rollback may be temporary if Git still calls for the broken revision. Record the corrective change in the same source of truth as the release.

Use the content of the response as your last check. A successful rollout and an HTTP success code can both occur while the old page is still being served. Ask for the expected version marker. Now you have evidence that users see the intended release, and a concrete observation to include in the deployment record.

## 23. Recovering the right thing

Suppose a cluster disappears overnight. Git can supply the manifests. The container registry can supply the images. Neither normally contains the business records written into a database after deployment. Inventory the configuration, credentials, application data, and external dependencies that rebuilding actually requires.

A backup of etcd concerns Kubernetes API state in a self-managed cluster. It does not copy the contents of application volumes. Volume snapshots depend on storage support and may need coordination with the database for a consistent restore. In a managed service, establish which recovery actions belong to the provider and which belong to your team.

Test recovery in an isolated namespace or cluster. Read a known record and perform a functional check. Time the procedure. The recovery time objective tells you how long the service may be down. The recovery point objective tells you how much recent data loss the business can tolerate. The strongest evidence is a completed restore with measured results.

## 24. Your first incident handoff

Finish by running the whole story. Deploy version one. Read its marker through the internal Service. Apply the version two overlay, wait for the rollout, and confirm the new marker. Now use the supplied practice file to change only the Service selector.

Look at what stays healthy. The Deployment still has its replicas. The processes are still running. The Service name still resolves. Then inspect the EndpointSlice. The link between the Service and the Pods has been lost. Restore the correct selector from the base Service file. Give discovery a moment to catch up. Repeat the same client request. The page should still say version two.

Finally, roll back the application template and verify version one through the same path. You have completed two different repairs and measured their effects separately. For your handoff, record the symptom, the evidence, the change, and the result. Those four pieces will serve you on a real shift long after you forget a particular command.
