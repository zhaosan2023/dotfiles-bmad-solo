

# Object-Oriented Harness: Evolving Agent Harnesses through Object-Oriented Design

Gaotang Li<sup>1,\*</sup>, Bhavana Dalvi Mishra<sup>2</sup>, Yifei Ming<sup>2</sup>, Yanfei Chen<sup>2</sup>, Zhongying CuiZhu<sup>2</sup>, Lesly Miculicich<sup>2</sup>, Long T. Le<sup>2</sup>, Rui Meng<sup>2</sup>, Chun-Liang Li<sup>2</sup>, Hanghang Tong<sup>1</sup>, Chen-Yu Lee<sup>2</sup> and Tomas Pfister<sup>2</sup>

<sup>1</sup>University of Illinois Urbana-Champaign, <sup>2</sup>Google Cloud AI Research

Agent harnesses are executable code that specifies the prompts, tools, and control flow around a language model. A single global harness can struggle with heterogeneous tasks that require different execution strategies. In this work, we introduce Object-Oriented Harness (OO-HARNESS), a harness optimization framework that evolves a hierarchy of executable harness classes using object-oriented design. During training, an evolution agent uses execution records to create a family of specialized harnesses, each implemented as a subclass of the base or an existing specialized harness via inheritance. At test time, a harness router uses routing lessons accumulated during training to select a specific harness for each task. Across three long-horizon benchmarks spanning business workflows, workspace tasks, and tool use, OO-HARNESS achieves the best performance among the compared methods, with an absolute improvement of up to 15.79% over the base harness. Extensive ablation studies examine the contributions of its core components.

## 1. Introduction

Generalizing to tasks beyond the training distribution is a central goal of language-agent research (Xi et al., 2024; Zeng et al., 2023). Recent benchmarks illustrate the breadth of tasks agents must handle: FutureX evaluates agents on forecasting real-world events using external information (Zeng et al., 2025), while APEX-Agents evaluates cross-application workflows in investment banking, management consulting, and corporate law (Vidgen et al., 2026). These workloads differ in the tool use, context management, and completion checks they require. An agent’s *harness* implements these choices as executable code around a language model (Yang et al., 2024).

Recent approaches automate agent design and harness optimization by refining executable code and other harness components using execution feedback (Hu et al., 2024; Jiang et al., 2026; Karten et al., 2026; Lee et al., 2026; Lin et al., 2026a; Lou et al., 2026; Nie et al., 2026; Zhang et al., 2025). Meta-Harness, for example, evolves candidate programs using discovery-set feedback and selects a global harness based on performance on that set (Lee et al., 2026). Such se-

lection does not guarantee that the same changes remain beneficial under distribution shift. Even within a benchmark, Agentic Harness Engineering’s component ablations show that adding evolved memory improves performance on hard tasks but reduces it on easy ones (Lin et al., 2026a). EvoHarnessBench further shows that adding tools, skills, and specialist agents can degrade previously effective behavior (Ke et al., 2026). These findings motivate specialized harnesses that share common code while preserving different execution strategies, with a router selecting a harness for each task.

Because harnesses are executable code (Ning et al., 2026), object-oriented design offers a natural way to express shared and specialized behavior. We introduce Object-Oriented Harness (OO-HARNESS), a harness optimization framework that evolves a hierarchy of executable classes (Figure 1). Each specialized harness inherits from the base or an existing specialized harness, overriding inherited methods or adding new ones.

During training, we first cluster discovery tasks by shared execution needs identified in base-harness execution records. An *evolution agent* iteratively selects a cluster and parent harness, creates a subclass, and evaluates it across the

\*This work was done during Gaotang Li’s internship at Google Cloud AI Research.

**(a) Global harness**  
One shared implementation

Heterogeneous tasks → Global harness → Executor

**(b) Flat harness family**  
Independent implementations

Task evidence → Harness router → Harness A, Harness B, Harness C, Harness D (Selected) → Executor

**(c) OO-Harness**  
Inherited implementations

Base → Quantitative computation, Legal reasoning → Goal seeking (Selected) → Executor

Task evidence → Harness router → Goal seeking (Selected) → Executor

Legend: Inheritance (green arrow), Selection (orange dashed arrow), Execution (black arrow)

The diagram illustrates three approaches to harnessing a robot: (a) Global harness with one shared implementation, (b) Flat harness family with independent implementations selected by a router, and (c) OO-Harness with inherited implementations.

Flowchart: Comparison of three harness frameworks: Global harness, Flat harness family, and OO-Harness.

**Figure 1 | Three ways to organize harness adaptation.** (a) A single global harness serves all tasks. (b) A router selects among independent harness implementations. (c) OO-HARNESS selects among specialized harnesses that share code through inheritance.

cluster’s tasks. This feedback guides subsequent revisions and accumulates as design and routing lessons. This offers two advantages. *Efficiency*: evaluating candidates on their target clusters avoids rerunning the entire discovery set. *Generalization*: specialized changes leave the base and other learned harnesses intact, so new tasks can use an appropriate harness without inheriting unrelated changes. At test time, *polymorphism* allows the executor to run a selected harness through a common execution interface. A *harness router* uses the task, an observable base trajectory, and routing lessons to select a specialized harness or retain the base result. The hierarchy and lessons are frozen before deployment; executor weights remain fixed in both phases.

Concurrent work also explores task-specific har-

ness selection. Adaptive Auto-Harness routes tasks among specialized Git branches (Liu et al., 2026b). In OO-HARNESS, inheritance shares code across harnesses, and routing lessons learned during training guide selection alongside class descriptions and observable base trajectories.

We evaluate OO-HARNESS on Automation-Bench, Workspace-Bench, and Toolathlon-GYM, where it achieves the highest primary score among the compared methods.

Our **contributions** are:

- A harness representation combining shared code and specialized behavior through inheritance, method overrides, and new methods.
- An evolution framework that learns specialized harnesses and routing lessons from execution records to support task-specific selection.
- Strong empirical results across three long-horizon benchmarks, with extensive ablations validating individual components.

## 2. Related Work

**Self-evolving agents.** Self-evolving agents use execution experience to improve prompts, memories, skills, and other persistent components. GEPA reflects on trajectories to optimize prompts (Agrawal et al., 2025), while ReasoningBank distills successful and failed experiences into reusable memories (Ouyang et al., 2026). A-Evolve considers deliberate updates to persistent agent state (Lin et al., 2026b), and HASP represents skills as executable functions that modify actions or supply corrective context (Liu et al., 2026a). These forms of adaptation provide building blocks for harness evolution. OO-HARNESS evolves specialized harnesses through inheritance and uses a harness router to select one for each task.

**Automatic harness evolution.** Recent work automates harness construction and revision through code search and execution feedback, including Meta-Harness (Lee et al., 2026), Agentic Harness Engineering (Lin et al., 2026a), and HarnessEvolve (Jiang et al., 2026). These approaches

primarily optimize a global harness across tasks, although changes that benefit one task group may not benefit another. HarnessDev benchmarks harness creation and evolution (Wu et al., 2026), while EvoHarnessBench shows that expanding tools, skills, and specialist agents can degrade previously effective behavior (Ke et al., 2026). Concurrent work explores adaptation across tasks and deployments: Adaptive Auto-Harness shares and specializes workspace contents through Git branching and rebasing (Liu et al., 2026b), while EvolveNet integrates adaptations from distributed deployments into a global harness (Nie et al., 2026). At the representation level, NOOA provides a programming model that expresses agents as native Python objects (Furgale et al., 2026). OO-HARNESS evolves a hierarchy of executable harness classes through inheritance, method overrides, and new methods. Its harness router selects a harness using routing lessons accumulated during training, class descriptions, the task, and an observable base trajectory.

## 3. Method

### 3.1. Problem setting and overview

A harness implements the prompts, tools, and execution rules around an *executor*, the language model  $M$  that carries out tasks (Ning et al., 2026). OO-HARNESS evolves this code on discovery tasks while keeping  $M$  fixed, then evaluates the frozen harnesses on disjoint held-out tasks (Figure 2). This differs from Meta-Harness’s TerminalBench-2 discovery experiment, which uses the same tasks for search and final evaluation (Lee et al., 2026). Separating discovery from evaluation is essential for assessing generalization beyond the search set (Wang et al., 2026).

A ***harness hierarchy***  $\mathcal{T}_H$  stores complete harness classes, starting from the base  $H_0$ . Each child inherits its parent’s methods and can override existing methods or add new ones. *Task clusters*  $C$  group discovery tasks with related execution needs. For cluster  $c$ , let  $\mathcal{D}_c$  denote its discovery tasks and  $H_c$  the harness currently chosen for that cluster. Clusters organize task evidence; the hierarchy organizes reusable harness code. The ***evolution agent***  $\pi$  constructs candidate subclasses from discovery-task evidence, while the

**TRAIN: discovery tasks**

Training tasks → **Execute + evolve** (Model M, Training grader) → **Hierarchy + lessons** → **Freeze hierarchy + lessons**

**TEST: held-out tasks**

New task → **Frozen deployment** (Task + observable execution traces) → **Final output**

**Evaluation only**

**Held-out grader** → **Reported score**

**No test-driven harness or lesson updates**

```
graph TD; subgraph TRAIN [TRAIN: discovery tasks]; T[Training tasks] --> E[Execute + evolve]; E --> H[Hierarchy + lessons]; E --> TG[Training grader]; H --> FH[Freeze hierarchy + lessons]; TG --> E; end; subgraph TEST [TEST: held-out tasks]; NT[New task] --> FD[Frozen deployment]; FD --> FO[Final output]; end; subgraph Eval [Evaluation only]; HG[Held-out grader] --> RS[Reported score]; end; FH --> TEST; FH --> Eval;
```

The diagram illustrates a three-phase workflow: **TRAIN: discovery tasks**, **TEST: held-out tasks**, and **Evaluation only**. In the training phase, training tasks are executed and evolved using a model (M) and a training grader to produce a hierarchy and lessons, which are then frozen. In the testing phase, a new task is processed using the frozen deployment to produce a final output. In the evaluation phase, the held-out grader reports a score. The process is designed to avoid test-driven harness or lesson updates.

Flowchart: Workflow diagram for training, testing, and evaluation of a model on discovery tasks.

Figure 2 | **Problem setting.** We use a train/test split: harnesses evolve on discovery tasks and are evaluated on disjoint held-out tasks.

*harness router*  $\rho$  selects the base or a specialized harness (Figure 3). A.1,A.4 describe model-prompts/implementation details; Table 2 compares routing inputs.

Execution records  $\mathcal{E}$  store candidate code, discovery-task trajectories, outcomes, and reflections from successful and unsuccessful proposals. Where lesson stores are enabled, we summarize these records into *design lessons*  $\mathcal{L}_\pi$  for code revision and *routing lessons*  $\mathcal{L}_\rho$  for harness selection. Design lessons describe useful changes and failed approaches; routing lessons describe when a harness applies. Both accumulate during discovery and remain frozen at deployment. The router’s model weights stay fixed; training changes the evidence that guides its decisions.

### 3.2. Representing the harness hierarchy

**Interfaces and inheritance.** Harness evolution operates on executable class definitions and supporting source files. The agent can change prompts, tools, context management, and execution control, and introduce additional methods. Where supported by the scaffold, it can also configure middleware, file backends, and subagents. The resulting class must remain compatible with the scaffold’s execution interface.

A subclass reuses inherited methods and over-

**TRAIN: discovery tasks (build and evolve harnesses)**

**1 Initialize (build initial task clusters)**

Discovery tasks and Base harness  $H_0$  are processed by a Fixed executor  $M$  to produce Base execution ( $H_0 + M$ ) and trajectories + training feedback. These are used to build Task clusters  $C_1, C_2, C_3$ .

**2 Evolve (improve harness hierarchy using training evidence)**

Task clusters (from 1) and Prior harness code (e.g.,  $H_0$ ) are processed by an Evolution agent to propose candidate subclasses using training evidence. These are used to build a subclass (class Child(Parent): # inherited methods # overrides). The subclass is executed on discovery tasks, evaluated, and if accepted, a child is added to the hierarchy. Execution records (all outcomes) are used to design lessons to inform the next evolution iteration.

**Freeze training outputs (used for deployment)**

**3 Harness hierarchy (frozen)**

The harness hierarchy (frozen) shows a base harness  $H_0$  (base) with child harnesses  $H_1, H_2, H_3$ .

**Harness router (frozen context)**

The harness router (frozen context) shows selection guided by training evidence. It includes Harness descriptions (for router context), Routing lessons\* (for router context), and a Fixed router model. Training records (from 2) inform frozen descriptions and lessons.

**TEST: held-out tasks (route and execute, no updates)**

**4**

A New task is processed by a Base execution ( $H_0 + M$ ) to produce a Task + observable trajectory. This is processed by the Harness router (frozen) to select a harness using trained descriptions and routing lessons. The selected harness (Base  $H_0$ ) is used to reuse the base result. A Specialized class (e.g.,  $H_2$ ) is used to run one instance, resulting in Inherited + overridden methods. The final result is the combination of the base result and the instance result.

\* Lesson stores vary by implementation. Test grader outputs are not used for routing or updates.

Flowchart: Workflow of training, freezing, and testing harnesses for task execution.

Figure 3 | **OO-Harness training and test-time execution.** (1) Base execution records initialize task clusters. (2) The evolution agent builds and evaluates subclasses, updating lessons from execution feedback. (3) The resulting harness hierarchy, harness descriptions, and routing lessons are frozen for testing. (4) The harness router uses the task, observable base trajectory, and frozen routing lessons to select a specialized harness or reuse the base result.

rides or adds methods for a targeted change. Overrides can call parent methods through `super()`. Figure 1 illustrates the hierarchy; Listing 1 shows inheritance in a saved harness lineage.

**Execution within one instance.** The harness router selects a complete class whose methods execute within one instance; ancestors are not separate agent runs. Methods can condition their behavior on runtime evidence, such as repeated tool errors or unfinished output artifacts.

### 3.3. Training initialization

We first run  $H_0$  on discovery tasks  $\mathcal{D}_{tr}$  and retain trajectories and evaluation feedback. We group tasks whose base executions suggest that they may benefit from a shared harness change, yielding clusters  $C$  and task sets  $\mathcal{D}_c$ . Each cluster records its shared execution needs and starts with  $H_c = H_0$ ; the initial hierarchy is  $\mathcal{T}_H = \{H_0\}$ .

### 3.4. Training iteration

At each iteration, the evolution agent works in a code workspace with filesystem access to harness source, task clusters, and execution records. It can inspect files, delegate analysis to subagents, and write or edit candidate code. It selects a target cluster and parent class, states the intended change, and implements an executable subclass. Successful and unsuccessful proposals remain available for later inspection.

We execute the candidate  $H'$  on  $\mathcal{D}_c$  with the fixed model  $M$ . Let  $S_c(H')$  denote its cluster score and  $S_c^{\text{current}}$  the stored score under current harness assignments. The candidate’s source parent need not be  $H_c$ . Evaluation runs directly on the target cluster without routing, **avoiding rerunning the full discovery set for every candidate**.

We accept  $H'$  when  $S_c(H') > S_c^{\text{current}}$  and benchmark-specific acceptance checks pass; otherwise, we reject it. These checks consider task-level outcomes and execution feedback, with a

#### **Algorithm 1** Harness evolution on discovery tasks

---

```
1: Input:  $H_0$ , fixed  $M$ , tasks  $\mathcal{D}_{\text{tr}}$ , budget  $T$ 
2: Run  $H_0$  on  $\mathcal{D}_{\text{tr}}$ ; store execution records
3: Cluster tasks from these records into  $\{\mathcal{D}_c\}$ 
4: Initialize  $\mathcal{T}_H$  and  $H_c \leftarrow H_0$ 
5: for  $i = 1, \dots, T$  do
6:   Review clusters; adjust task assignments if
     needed
7:    $\pi$  chooses a cluster  $c$  and parent in  $\mathcal{T}_H$ 
8:   Build subclass  $H'$ ; override or add methods
9:   Run  $H'$  on  $\mathcal{D}_c$ ; collect scores and feedback
10:  Compare task outcomes; apply acceptance
     checks
11:  Retain accepted  $H'$ ; update  $H_c$  if preferred
12:  Update cluster priority from acceptance his-
     tory
13:  Store outcomes; distill enabled lessons
14: end for
15: Output: freeze  $\mathcal{T}_H$ ,  $\{H_c\}$ , records, lessons
```

---

judging agent for ambiguous cases where configured. Accepted classes enter  $\mathcal{T}_H$  and can become the cluster’s selected harness  $H_c$ . All outcomes guide later revisions and lesson updates. Improvement is required on the target cluster, not all tasks. A parent remains reusable through inheritance and, if active, can still be selected separately from its specialized children.

Repeated rejections lower a cluster’s search priority, allowing evolution to explore other task groups. Cluster assignments are also re-examined at each iteration: execution feedback can motivate reassigning tasks or splitting or merging clusters, including when repeated harness revisions fail to improve a group. Algorithm 1 summarizes evolution; Appendix A.4 gives implementation details.

### 3.5. Test-time selection and execution

For a new task  $t$ , the harness router observes the base trajectory  $\omega(t)$  and selects

$$H^* = \rho(t, \omega(t), \{H_0\} \cup \{H_c\}_{c \in C}, \mathcal{L}_\rho).$$

It uses class descriptions, applicability conditions, and frozen routing lessons. If  $H^* = H_0$ , we reuse the base result. Otherwise, we execute one instance of  $H^*$  with its inherited and specialized behavior. The hierarchy and stored evidence remain fixed across all held-out tasks. Grader feedback supports evolution on training tasks only.

At test time, grader scores, verdicts, and hidden reference answers are unavailable to the router or executor.

## 4. Experiments

### 4.1. Evaluation setup

**Benchmarks and metrics.** We evaluate on AutomationBench (Shepard and Salimans, 2026) for business workflows (300 discovery and 300 held-out tasks), Workspace-Bench (Tang et al., 2026) for work across files and applications (288 discovery and 100 held-out tasks, Lite-100), and Toolathlon-GYM (Zhang et al., 2026) for multi-tool task completion (251 discovery and 252 held-out tasks). AutomationBench and Toolathlon-GYM use deterministic graders to assess task completion; Workspace-Bench evaluates outputs against task-specific rubrics.

We report Mean and strict task success (PASS) for all three benchmarks. Mean denotes mean partial credit on AutomationBench, micro-averaged rubric pass rate on Workspace-Bench, and mean reward on Toolathlon-GYM. PASS requires reward at least 0.999 on AutomationBench and Toolathlon-GYM, or all rubrics satisfied on Workspace-Bench. The primary metric is Mean for AutomationBench and Workspace-Bench, and PASS for Toolathlon-GYM. All scores are reported as percentages.

**Comparators.** We compare with the unevolved BASE harness; global harness optimization using META-HARNESS (Lee et al., 2026) and Agentic Harness Engineering (AHE; Lin et al., 2026a); and specialized harnesses using Adaptive Auto-Harness (AAH; Liu et al., 2026b). Our AHE adaptation iteratively edits a global harness from a framework-only bundle. Since OO-HARNESS uses a base trajectory for routing, we also compare with test-time scaling of the base harness to assess gains from additional inference. Inspired by Wang et al. (2026), we evaluate parallel best-of- $K$  selection ( $K \in \{2, 5\}$ ) and sequential self-refinement ( $K = 2$ ; Madaan et al., 2023). Both methods use observable trajectories without grader feedback.

**Evaluation and reporting.** All methods use the same `gemini-3.5-flash` executor and follow each benchmark’s native execution protocol. We fix the evolution agent to Claude Opus 4.8 across harness optimization methods for up to 40 iterations and use the same model for test-time trajectory selection or guidance where required. The OO-HARNESS harness router uses Claude Sonnet 5 (Appendix A.4.2). Harnesses and lessons remain frozen during held-out evaluation, and grader outputs are used only for final scoring (§3.5). For the main comparison, we perform three independent executor runs per method and benchmark and report mean  $\pm$  standard deviation. *Steps* is the mean number of steps in the finally selected trajectory, excluding other roll-outs and auxiliary selection calls.

### 4.2. Main results

**Strong empirical results.** OO-HARNESS achieves the highest primary score on all three benchmarks (Table 1), outperforming prior global harness optimization approaches and AAH’s specialized harnesses. These results support the expressiveness of object-oriented programming as a natural fit for code-based harness evolution: inheritance shares useful behavior, while method overrides and additions specialize it for different tasks. On AutomationBench, OO-HARNESS also has the lowest mean trajectory step count among all compared methods. Table 1 also shows that test-time scaling with parallel best-of- $K$  selection ( $K \in \{2, 5\}$ ) and sequential self-refinement ( $K = 2$ ) does not consistently improve performance. Additional inference alone therefore does not guarantee gains, highlighting the value of learning task-appropriate harnesses through our training pipeline.

**Global versus hierarchical approaches.** We compare more closely with META-HARNESS, a prominent prior approach to global harness optimization. During training, META-HARNESS evolves one global harness, whereas OO-HARNESS builds a hierarchy of specialized harnesses through cluster-specific evolution. Both freeze code before testing; META-HARNESS applies one harness to every task, while

OO-HARNESS selects from its learned hierarchy. Figure 4 highlights three advantages of OO-HARNESS: **training progress**, with larger early gains in the averaged discovery curve (a); **training efficiency**, with shorter recorded search duration (b); and **generalization performance**, with higher held-out scores (c). Evaluating revisions on target clusters instead of rerunning the full discovery set can reduce API calls and associated cost per candidate. These results motivate hierarchical, adaptive harness optimization for heterogeneous tasks.

**(a) Training progress**

Mean score (%) vs Recorded search progress (%)

| Recorded search progress (%) | Meta-Harness Global | OO-Harness Hierarchical |
|------------------------------|---------------------|-------------------------|
| 0                            | ~36                 | ~36                     |
| 25                           | ~42                 | ~49                     |
| 50                           | ~44                 | ~51                     |
| 75                           | ~47                 | ~52                     |
| 100                          | ~48                 | ~53                     |

**(b) Search time**

| Method | Mean duration (h) |
|--------|-------------------|
| Meta   | 109.1             |
| OO     | 29.0              |

**(c) Held-out score**

| Method | Mean score (%) |
|--------|----------------|
| Base   | 39.4           |
| Meta   | 42.3           |
| OO     | 51.4           |

The figure contains three panels. Panel (a) is a line graph showing mean score (%) vs recorded search progress (%) for Meta-Harness (dashed brown line) and OO-Harness (solid teal line). Both show an upward trend, with OO-Harness consistently higher. Panel (b) is a bar chart comparing search time in hours for Meta and OO methods. Panel (c) is a bar chart comparing held-out mean scores for Base, Meta, and OO methods.

Multi-panel chart: Training progress, search time, and held-out score comparison between Meta-Harness and OO-Harness.

**Figure 4 | Global versus hierarchical harness optimization.** Compared with META-HARNESS, OO-HARNESS shows (a) larger early training gains, (b) shorter recorded search time, and (c) higher held-out scores. Curves align runs by their fraction of recorded updates.

## 5. Analysis

In this section, we aim to understand the effectiveness of OO-HARNESS through ablations of (1) task- and execution-informed harness routing (§5.1.1) and (2) hierarchical harness optimization through inheritance (§5.1.2). These comparisons assess the roles of execution evidence and hierarchical code reuse. We then conduct detailed case studies of base-harness reuse, learned task clusters, and concrete harness changes to relate execution needs to code and routing decisions (§5.2). Finally, we construct an out-of-

Table 1 | Held-out results with a frozen executor. *Mean*: mean partial credit on AutomationBench, micro-averaged rubric pass rate on Workspace-Bench, and mean reward on Toolathlon-GYM. *PASS*: strict task success (reward  $\geq 0.999$  on AutomationBench and Toolathlon-GYM; all rubrics satisfied on Workspace-Bench). The primary metric is Mean for AutomationBench and Workspace-Bench, and PASS for Toolathlon-GYM. *Steps* counts only the finally selected trajectory, excluding other rollouts and auxiliary selection calls. Values are mean  $\pm$  standard deviation over three runs; scores are percentages. Bold marks each column’s maximum score ( $\uparrow$ ) or minimum steps ( $\downarrow$ ).  $^{\dagger}$ : supervised harness evolution with discovery-task feedback.  $^{\ddagger}$ : unsupervised test-time scaling of the base harness. Held-out grader feedback is unavailable to all methods.

| Method                                             | AutomationBench       |                       |                       | Workspace-Bench       |                      |                       | Toolathlon-GYM        |                       |                       |
|----------------------------------------------------|-----------------------|-----------------------|-----------------------|-----------------------|----------------------|-----------------------|-----------------------|-----------------------|-----------------------|
|                                                    | Mean $\uparrow$       | PASS $\uparrow$       | Steps $\downarrow$    | Mean $\uparrow$       | PASS $\uparrow$      | Steps $\downarrow$    | Mean $\uparrow$       | PASS $\uparrow$       | Steps $\downarrow$    |
| BASE                                               | 61.62$\pm$0.15        | 25.44$\pm$0.51        | 31.27$\pm$0.13        | 25.45$\pm$2.98        | 3.67$\pm$0.58        | 34.41$\pm$1.34        | 71.87$\pm$0.65        | 31.15$\pm$0.28        | 40.50$\pm$0.99        |
| <i>Test-time scaling</i>                           |                       |                       |                       |                       |                      |                       |                       |                       |                       |
| Parallel ($K=2$)<sup><math>\ddagger</math></sup>   | 61.46$\pm$2.38        | 24.67$\pm$2.83        | 31.64$\pm$0.23        | 32.54$\pm$4.30        | 5.67$\pm$1.15        | 41.62$\pm$2.56        | 74.85$\pm$1.45        | 31.55$\pm$1.96        | 39.94$\pm$0.32        |
| Parallel ($K=5$)<sup><math>\ddagger</math></sup>   | 60.24$\pm$1.07        | 24.00$\pm$0.47        | 31.29$\pm$0.05        | 37.71$\pm$0.45        | 7.67$\pm$0.58        | 48.63$\pm$1.92        | 75.69$\pm$0.79        | 32.14$\pm$0.56        | 38.90$\pm$0.00        |
| Sequential ($K=2$)<sup><math>\ddagger</math></sup> | 59.29$\pm$0.25        | 25.00$\pm$1.41        | 31.86$\pm$0.12        | 27.93$\pm$2.13        | 3.33$\pm$2.52        | 32.91$\pm$2.07        | 73.53$\pm$1.67        | 33.33$\pm$2.81        | 40.97$\pm$1.32        |
| <i>Global harness optimization</i>                 |                       |                       |                       |                       |                      |                       |                       |                       |                       |
| META-HARNESS<sup><math>\dagger</math></sup>        | 63.92$\pm$0.89        | 26.33$\pm$1.33        | 30.05$\pm$0.03        | 29.56$\pm$1.23        | 5.54$\pm$1.23        | 35.23$\pm$1.44        | 75.84$\pm$0.76        | 33.45$\pm$1.23        | 39.85$\pm$1.03        |
| AHE<sup><math>\dagger</math></sup>                 | 64.18$\pm$0.91        | 28.11$\pm$1.84        | 30.61$\pm$0.18        | 38.43$\pm$4.32        | 7.78$\pm$0.87        | 34.59$\pm$1.21        | 74.48$\pm$1.23        | 36.23$\pm$1.19        | 41.02$\pm$0.89        |
| <i>Specialized harness families</i>                |                       |                       |                       |                       |                      |                       |                       |                       |                       |
| AAH<sup><math>\dagger</math></sup>                 | 75.40$\pm$1.26        | 34.31$\pm$1.19        | 28.89$\pm$0.03        | 38.62$\pm$2.98        | 8.00$\pm$0.82        | 33.58$\pm$2.48        | 74.99$\pm$1.63        | 34.32$\pm$1.47        | 41.23$\pm$0.88        |
| OO-HARNESS<sup><math>\dagger</math></sup>          | <b>77.41</b>$\pm$1.37 | <b>37.22</b>$\pm$2.14 | <b>27.99</b>$\pm$0.02 | <b>39.48</b>$\pm$3.21 | <b>8.33</b>$\pm$2.52 | <b>32.78</b>$\pm$1.97 | <b>77.18</b>$\pm$1.15 | <b>37.45</b>$\pm$0.98 | <b>37.25</b>$\pm$0.38 |

distribution (OOD) setting with disjoint training and test application families, and examine Base reuse on the selected test tasks (§5.3).

### 5.1. Ablation studies

#### 5.1.1. Harness routing

We compare two routers with the same frozen harness catalogue, executor, grader, and held-out split. The *task-only* router uses task descriptions and metadata, requiring self-reported applicability confidence of at least 0.7 to select a specialist. The trajectory-based router also observes the base execution. Neither receives held-out grader feedback. Appendix A.6.1 details the task-only prompt setup.

Table 2 shows that the value of execution evidence depends on the workload. Compared with task-only routing, trajectory-based routing improves AutomationBench mean partial credit by 12.64 points and Toolathlon-GYM PASS by 4.37 points. The gap on Workspace-Bench is only 0.53 points. To understand why these gains differ, we further inspect the learned task clusters and the harness changes developed for them. This inspection suggests that the information needed for routing depends on how the evolution agent groups tasks and specializes harnesses to address their

| Benchmark / metric | OO-HARNESS routing evidence |           |                   |
|--------------------|-----------------------------|-----------|-------------------|
|                    | Base                        | Task only | Task + trajectory |
| Automation / Mean  | 61.30                       | 64.88     | <b>77.52</b>      |
| Workspace / Mean   | 24.57                       | 40.03     | <b>40.56</b>      |
| Toolathlon / PASS  | 31.35                       | 33.33     | <b>37.70</b>      |

Table 2 | **Routing ablation on a frozen OO-HARNESS catalogue.** *Task only* uses the task description and available task metadata; *Task + trajectory* also observes the base execution. *Base* executes without routing. Entries report primary scores (%) from single ablation runs, distinct from the repeated runs in Table 1.

shared execution needs. On Workspace-Bench, the learned cluster labels align with task types such as document writing and spreadsheet editing (Figure 6b), making the requested output a useful cue for harness selection. On AutomationBench and Toolathlon-GYM, some harnesses address execution issues shared across domains or apps, such as leaving required writes incomplete or failing to finalize within the tool-call budget. The base trajectory helps reveal whether these issues occurred, allowing the router to select a harness designed to address them. Appendix

A bar chart showing the percentage of micro rubrics for three methods: Base-reset, Flat, and OO. The y-axis is labeled 'Micro rubric (%)' and ranges from 25 to 45 with a break between 25 and 30. The x-axis labels are Base-reset, Flat, and OO.

| Method     | Micro rubric (%) |
|------------|------------------|
| Base-reset | 29.39            |
| Flat       | 35.60            |
| OO         | 40.56            |

The chart shows an increasing trend from Base-reset to Flat to OO.

Bar chart: Comparison of micro rubric percentages across three methods.

Figure 5 | **Inheritance ablation on Workspace-Bench.** We find that learning through inheritance outperforms Flat and Base-reset.

Figures 8 and 9 illustrate document-writing and completion-check changes.

#### 5.1.2. Hierarchical evolution structure

One central design choice of OO-HARNESS is evolution via inheritance. We examine its contribution on Workspace-Bench with three ways of learning harnesses. The routing procedure, executor, task splits, and nominal search budget are the same across variants; only how harness code is learned changes. **OO** extends earlier harnesses through subclasses. **Flat** copies previously evolved code into a class derived directly from the base, without inheriting from a specialized harness. **Base-reset** starts from the base and adds new changes without carrying forward previously evolved code. Each variant conducts a separate search and is evaluated once on Lite-100.

OO achieves the highest micro rubric pass of 40.56%, exceeding Flat by 4.96 points (Figure 5). Flat also improves over Base-reset, supporting the value of reusing useful code across revisions. Since Flat also carries forward evolved code, its gap to OO suggests a benefit from organizing revisions through inheritance. Each variant evolves separately, so these results compare the harnesses learned by each search strategy.

### 5.2. Case studies

**Reusing the base harness.** In OO-HARNESS, a task is rerun with an evolved specialized harness only when the router selects one; otherwise, the Base result is reused. In this case study, we examine one AutomationBench run with 300 tasks, of which 134 (44.7%) reuse Base and 166 select specialized harnesses. Table 3 compares the original Base performance of these two groups, before any specialized execution. Tasks sent to special-

|                     | Original Base performance |             |             |
|---------------------|---------------------------|-------------|-------------|
| Routing destination | Tasks                     | Mean reward | Strict PASS |
| Reuse Base          | 134                       | 77.15       | 36.57       |
| Specialized harness | 166                       | 44.40       | 14.25       |

Table 3 | **Base performance by routing destination on AutomationBench.** We find that tasks routed to specialized harnesses have substantially weaker Base performance on average, while OO-HARNESS preserves stronger Base executions through reuse.

ists have lower Base mean reward (44.40%) than those selected for Base reuse (77.15%); strict PASS follows the same pattern. These results suggest that routing directs specialization toward tasks with weaker Base executions, while preserving stronger Base results through reuse. Routing lessons guide this choice by linking observed execution problems to suitable harnesses (Figure 6c).

#### How task clusters reflect execution needs.

The evolution agent can create and revise task clusters from discovery executions, without a fixed domain or task-type taxonomy. Figure 6 contrasts two learned organizations. On AutomationBench, clusters capture failures and corrective needs visible in trajectories: `commit-gate` targets missing writes, while `compute-verify` groups tasks requiring arithmetic or time-based derivations across five business domains. On Workspace-Bench, all six learned cluster labels align with the evaluated AAH task-type groups, including document writing and spreadsheet editing. Tasks requesting the same output format often share backend requirements, so task-type clusters can emerge naturally from execution evidence. The evolution agent can thus group tasks by a shared failure or by a shared capability, depending on the workload.

Routing lessons connect execution problems to harness capabilities. In Figure 6c, the router matches repeated query-parsing errors to a saved lesson and selects an API error-normalizer that provides query-repair instructions. Appendix Table 4 shows lessons that select a resource-manifest harness or preserve a clean Base execution.

**a AutomationBench**

| OO clusters             | Domains |    |    |    |    |    |
|-------------------------|---------|----|----|----|----|----|
| commit-gate             | 3       | 5  | 4  | 1  |    | 3  |
| compute-verify          | 7       |    | 2  | 3  | 3  | 3  |
| discovery-setup         | 12      | 43 | 3  | 5  | 4  | 1  |
| exploration-budget      | 2       |    | 4  | 2  | 8  | 2  |
| injection-defense       |         |    | 2  | 1  | 4  |    |
| self-verify-gate        | 26      | 2  | 35 | 36 | 28 | 39 |
| verbatim-fidelity       |         |    |    | 2  | 1  |    |
| working-memory-multihop |         |    |    |    | 2  |    |

Fin. HR Mkt. Ops. Sales Sup.

**b Workspace-Bench**

|   | OO clusters              | Task types |    |    |    |    |    |
|---|--------------------------|------------|----|----|----|----|----|
| 1 | code-artifact            | 9          |    |    |    |    |    |
| 2 | coverage-large-workspace |            | 20 |    |    |    |    |
| 3 | office-doc-write         |            |    | 81 |    | 7  |    |
| 4 | slides-write             |            |    |    | 17 |    |    |
| 5 | spreadsheet-write        |            |    |    |    | 39 |    |
| 6 | text-nonconvergence      |            |    |    |    |    | 78 |

1 2 3 4 5 6

**c Routing from execution evidence**

**Base trajectory (schematic)**  
Call: SOQL query  
Result: query-parsing error  
Retry: revised query  
Result: query-parsing error

**Parse error**

match →

**Routing lesson**  
Repeated query-parsing errors  
Use an API error normalizer

select →

**Selected harness**  
**API error-normalizer**  
Rewrites errors as query-repair hints

Multi-panel chart: Benchmarks and routing pipeline from execution evidence to harness selection.

**Figure 6 | Learned clusters and an example router lesson.** Panels (a,b) compare learned clusters (rows) with domains or task types (columns); cells count shared discovery tasks. AutomationBench clusters largely reflect execution needs, while Workspace-Bench clusters largely follow task types. Panel (c) schematically shows how repeated query-parsing errors in a Base trajectory match a saved routing lesson, leading to selection of an API error-normalizer harness. Blank cells are zero; Workspace-Bench column IDs match the numbered rows.

**Concrete harness changes.** Inheritance supports both shared behavior and targeted specialization. On AutomationBench, the `discovery-setup` lineage extends a missing-write completion check with a near-budget reminder and tool-error guidance (Appendix Figure 9). Each node is a complete executable harness. A parent supplies shared behavior and, if active, can serve tasks that do not need a descendant’s additional changes. A document-backend specialization on Workspace-Bench appears in Appendix Figure 8.

### 5.3. Base harness reuse in OOD settings

To examine behavior in extreme OOD scenarios, we construct a setting with 254 Toolathlon-GYM training tasks and 49 Toolathlon test tasks (Li et al., 2025). Their named application families are disjoint, making the test set largely out of distribution relative to the training set (Appendix A.7). We evolve harnesses on this training split and compare OO-HARNESS against META-HARNESS. At test time, META-HARNESS applies its learned global harness, whereas the OO-HARNESS router selects the general Base harness for every test task. As Figure 7 shows, reusing Base preserves its performance, while applying the META-HARNESS harness yields a lower PASS rate. Keeping Base as a routing option allows

A bar chart comparing the Task PASS (%) for three methods: Base, Meta-Harness, and OO-Harness. The y-axis is labeled 'Task PASS (%)' and ranges from 0 to 60 in increments of 20. The x-axis labels are 'Base', 'Meta-Harness', and 'OO-Harness'. The bars are colored grey, brown, and dark green respectively. The values are 59.18, 44.90, and 59.18.

| Method       | Task PASS (%) |
|--------------|---------------|
| Base         | 59.18         |
| Meta-Harness | 44.90         |
| OO-Harness   | 59.18         |

Bar chart: Task PASS percentage for Base, Meta-Harness, and OO-Harness.

**Figure 7 | Base reuse on the selected OOD test tasks.** After evolution on the disjoint training split, OO-HARNESS reuses Base on every test task, preserving its performance, while applying the learned META-HARNESS harness reduces PASS.

OO-HARNESS to handle unfamiliar tasks without requiring them to use a specialization learned on different application families.

## 6. Conclusion

OO-HARNESS evolves specialized harnesses through inheritance and routes tasks using execution evidence. Task clusters capture shared execution needs, and inheritance allows specialized harnesses to share useful code. OO-HARNESS achieves the best performance among baselines. Ablations support inheritance and trajectory-informed routing, while case studies illustrate the effectiveness of specialization and Base reuse.

## **Limitations**

OO-HARNESS relies on the APIs and execution environment provided by its host. Service outages and rate limits can affect reliability, while interface changes may require updates to evolved harnesses. Integrating private or authenticated services also requires secure credential handling and permission configuration. These dependencies motivate further work on robust API integration and deployment across environments.

## References

Lakshya A. Agrawal, Shangyin Tan, Dilara Soylu, Noah Ziems, Rishi Khare, Krista Opsahl-Ong, Arnav Singhvi, Herumb Shandilya, Michael J. Ryan, Meng Jiang, Christopher Potts, Koushik Sen, Alexandros G. Dimakis, Ion Stoica, Dan Klein, Matei Zaharia, and Omar Khattab. GEPA: Reflective prompt evolution can outperform reinforcement learning. *arXiv preprint arXiv:2507.19457*, 2025. Accepted to ICLR 2026.

Anthropic. Claude models overview, 2026. URL <https://platform.claude.com/docs/en/models/overview>. Provider documentation; accessed October 10, 2026.

Paul Furgale, Severin Klingler, James Nolan, Matt Staats, Gaia Di Lorenzo, Elisa Martinez Abad, Christian Schüller, Razvan Dinu, Alessio Devoto, Pascal Berard, Gal Kaplun, Elad Sarafian, Ricardo Roveri, Leon Derczynski, and Ricardo Silveira Cabral. NVIDIA-labs OO Agents: Native Python object-oriented agents. *arXiv preprint arXiv:2607.20709*, 2026. URL <https://arxiv.org/abs/2607.20709>.

Google. Gemini API models, 2026. URL <https://ai.google.dev/gemini-api/docs/models>. Provider documentation; accessed October 10, 2026.

Shengran Hu, Cong Lu, and Jeff Clune. Automated design of agentic systems. *arXiv preprint arXiv:2408.08435*, 2024.

Wen Jiang, Mingmin Chu, Yimeng Tian, Qianxin Zhang, Haofei Yang, Rui Yang, Yang Liu, Tao Lv, and Fangming Li. HarnessEvolve: Learning from reference trajectories for reliable agent self-evolution. *arXiv preprint arXiv:2609.00829*, 2026.

Seth Karten, Joel Zhang, Tersoo Upaa Jr, Ruirong Feng, Wenzhe Li, Chengshuai Shi, Chi Jin, and Kiran Vodrahalli. Continual Harness: Online adaptation for self-improving foundation agents. *arXiv preprint arXiv:2605.09998*, 2026. URL <https://arxiv.org/abs/2605.09998>.

Zixuan Ke, Vaidehi Patil, Haizhou Shi, Yang Li, Ye Liu, Sarath Shekkizhar, Anurag Koul, Jiayu Wang, Xuan Phi Nguyen, Semih Yavuz, Mohit Bansal, and Shafiq Joty. EvoHarnessBench: Can your agents keep pace with an evolving harness? *arXiv preprint arXiv:2609.04280*, 2026. URL <https://arxiv.org/abs/2609.04280>.

Yoonho Lee, Roshen Nair, Qizheng Zhang, Kangwook Lee, Omar Khattab, and Chelsea Finn. Meta-Harness: End-to-end optimization of model harnesses. *arXiv preprint arXiv:2603.28052*, 2026.

Junlong Li, Wenshuo Zhao, Jian Zhao, Weihao Zeng, Haoze Wu, Xiaochen Wang, Rui Ge, Yuxuan Cao, Yuzhen Huang, Wei Liu, Junteng Liu, Zhaochen Su, Yiyang Guo, Fan Zhou, Lueyang Zhang, Juan Micheli, Xingyao Wang, Xiang Yue, Shuyan Zhou, Graham Neubig, and Junxian He. The tool decathlon: Benchmarking language agents for diverse, realistic, and long-horizon task execution. 2025. URL <https://arxiv.org/abs/2510.25726>.

Jiahang Lin, Shichun Liu, Chengjun Pan, Lizhi Lin, Shihan Dou, Zhiheng Xi, Xuanjing Huang, Hang Yan, Zhenhua Han, Tao Gui, and Yu-Gang Jiang. Agentic harness engineering: Observability-driven automatic evolution of coding-agent harnesses. *arXiv preprint arXiv:2604.25850*, 2026a.

Minhua Lin, Hanqing Lu, Zhan Shi, Bing He, Rui Mao, Zhiwei Zhang, Zongyu Wu, Xianfeng Tang, Hui Liu, Zhenwei Dai, Xiang Zhang, Suhang Wang, Benoit Dumoulin, and Jian Pei. Position: Agentic evolution is the path to evolving LLMs. *arXiv preprint arXiv:2602.00359*, 2026b.

Hongjun Liu, Yifei Ming, Shafiq Joty, and Chen Zhao. Harnessing LLM agents with skill programs. *arXiv preprint arXiv:2605.17734*, 2026a. URL <https://arxiv.org/abs/2605.17734>.

Zewen Liu, Zhan Shi, Yisi Sang, Bing He, Minhua Lin, Tianxin Wei, Dakuo Wang, Benoit Dumoulin, Wei Jin, and Hanqing Lu. Adaptive auto-harness: Sustained self-improvement for agentic system deployment on open-ended task streams. *arXiv preprint arXiv:2606.01770*, 2026b.

Xinghua Lou, Miguel Lázaro-Gredilla, Antoine Dedieu, Carter Wendelken, Wolfgang Lehrach, and Kevin P. Murphy. AutoHarness: Improving LLM agents by automatically synthesizing a code harness. *arXiv preprint arXiv:2603.03329*, 2026. URL <https://arxiv.org/abs/2603.03329>.

Aman Madaan, Niket Tandon, Prakhar Gupta, Skyler Hallinan, Luyu Gao, Sarah Wiegreffe, Uri Alon, Nouha Dziri, Shrimai Prabhumoye, Yiming Yang, Shashank Gupta, Bodhisattwa Prasad Majumder, Katherine Hermann, Sean Welleck, Amir Yazdanbakhsh, and Peter Clark. Self-refine: Iterative refinement with self-feedback. *Advances in Neural Information Processing Systems (NeurIPS)*, 2023.

Jun Nie, Yonggang Zhang, Qianshu Cai, Yiu-ming Cheung, Xinmei Tian, and Bo Han. EvolveNet: Collaborative harness evolution for agent self-improvement. *arXiv preprint arXiv:2608.04968*, 2026.

Xuying Ning, Katherine Tieu, Dongqi Fu, Tianxin Wei, Zihao Li, Yuanchen Bei, Jiaru Zou, Mengting Ai, Zhining Liu, Ting-Wei Li, Lingjie Chen, Yanjun Zhao, Ke Yang, Bingxuan Li, Cheng Qian, Gaotang Li, Xiao Lin, Zhichen Zeng, Ruizhong Qiu, Sirui Chen, Yifan Sun, Xiyuan Yang, Ruida Wang, Rui Pan, Chenyuan Yang, Dylan Zhang, Liri Fang, Zikun Cui, Yang Cao, Pan Chen, Dorothy Sun, Ren Chen, Mahesh Srinivasan, Nipun Mathur, Yinglong Xia, Hong Li, Hong Yan, Pan Lu, Lingming Zhang, Tong Zhang, Hanghang Tong, and Jingrui He. Code as agent harness. *arXiv preprint arXiv:2605.18747*, 2026.

Siru Ouyang, Jun Yan, I-Hung Hsu, Yanfei Chen, Ke Jiang, Zifeng Wang, Rujun Han, Long T. Le, Samira Daruki, Xiangru Tang, Vishy Tirumalashetty, George Lee, Mahsan Rofouei, Hangfei Lin, Jiawei Han, Chen-Yu Lee, and Tomas Pfister. Reasoning-Bank: Scaling agent self-evolving with reasoning memory. In *The Fourteenth International Conference on Learning Representations*, 2026. URL <https://openreview.net/forum?id=jL7fwchScm>.

Daniel Shepard and Robin Salimans. Automation-Bench, 2026. URL <https://arxiv.org/abs/2604.18934>.

Zirui Tang, Xuanhe Zhou, Yumou Liu, Linchun Li, Yukai Wu, Weizheng Wang, Hongzhang Huang, Wei Zhou, Jun Zhou, Jiachen Song, Shaoli Yu, Jinqi Wang, Zihang Zhou, Hongyi Zhou, Yuting Lv, Jinyang Li, Jiashuo Liu, Ruoyu Chen, Chunwei Liu, GuoLiang Li, Jihua Kang, and Fan Wu. Workspace-Bench 1.0: Benchmarking AI agents on workspace tasks with large-scale file dependencies, 2026. URL <https://arxiv.org/abs/2605.03596>.

Bertie Vidgen, Austin Mann, Abby Fennelly, John Wright Stanly, Lucas Rothman, Marco Burstein, Julien Benchek, David Ostrofsky, Anirudh Ravichandran, Debnil Sur, Neel Venugopal, Alanah Hsia, Isaac Robinson, Calix Huang, Olivia Varones, Daniyal Khan, Michael Haines, Austin Bridges, Jesse Boyle, Koby Twist, Zach Richards, Chirag Mahapatra, Brendan Foody, and Osvald Nit-ski. APEX-Agents. *arXiv preprint arXiv:2601.14242*, 2026.

Yike Wang, Huaisheng Zhu, Zhengyu Hu, Yige Yuan, Zhengyu Chen, Shakti Senthil, Hannaneh Hajishirzi, Yulia Tsvetkov, Noah A. Smith, Pradeep Dasigi, and Teng Xiao. Rethinking the evaluation

of harness evolution for agents. *arXiv preprint arXiv:2607.12227*, 2026.

Yuhao Wu, Jingyuan Zhang, Jiajun Shi, Xinping Lei, Qingshui Gu, Yuxuan Zhang, Zexuan Wang, Chen He, Chen Huang, Maojia Song, Zhiyuan Zeng, Shaowen Wang, Jinkai Liu, Yunfeng Shi, Jiaheng Liu, Shen Yan, Wenhao Huang, Ge Zhang, and Wenxuan Zhang. HarnessDev: Can LLMs create and evolve their own agent harness? *arXiv preprint arXiv:2609.01437*, 2026.

Zhiheng Xi, Yiwen Ding, Wenxiang Chen, Boyang Hong, Honglin Guo, Junzhe Wang, Dingwen Yang, Chenyang Liao, Xin Guo, Wei He, Songyang Gao, Lu Chen, Rui Zheng, Yicheng Zou, Tao Gui, Qi Zhang, Xipeng Qiu, Xuanjing Huang, Zuxuan Wu, and Yu-Gang Jiang. AgentGym: Evolving large language model-based agents across diverse environments. *arXiv preprint arXiv:2406.04151*, 2024.

John Yang, Carlos E. Jimenez, Alexander Wettig, Kilian Lieret, Shunyu Yao, Karthik Narasimhan, and Ofir Press. SWE-agent: Agent-computer interfaces enable automated software engineering. *Advances in Neural Information Processing Systems (NeurIPS)*, 2024.

Aohan Zeng, Mingdao Liu, Rui Lu, Bowen Wang, Xiao Liu, Yuxiao Dong, and Jie Tang. AgentTuning: Enabling generalized agent abilities for LLMs. *arXiv preprint arXiv:2310.12823*, 2023.

Zhiyuan Zeng, Jiashuo Liu, Siyuan Chen, Tianci He, Yali Liao, Yixiao Tian, Jinpeng Wang, Zaiyuan Wang, Yang Yang, Lingyue Yin, Mingren Yin, Zhenwei Zhu, Tianle Cai, Zehui Chen, Jiecao Chen, Yantao Du, Xiang Gao, Jiacheng Guo, Liang Hu, Jianpeng Jiao, Xiangsheng Li, Jingkai Liu, Shuang Ni, Zhoufutu Wen, Ge Zhang, Kaiyuan Zhang, Xin Zhou, Jose Blanchet, Xipeng Qiu, Mengdi Wang, and Wenhao Huang. FutureX: An Advanced Live Benchmark for LLM Agents in Future Prediction. *arXiv preprint arXiv:2508.11987*, 2025.

Jenny Zhang, Shengran Hu, Cong Lu, Robert Lange, and Jeff Clune. Darwin gödel machine: Open-ended evolution of self-improving agents. *arXiv preprint arXiv:2505.22954*, 2025.

Puzhen Zhang, Weijie Bai, Wendong Fan, and Guohao Li. Toolathlon-GYM: Large-Scale Long-Horizon Environments for Tool-Use Agents, 2026. URL [https://github.com/eigent-ai/toolathlon\\_gym](https://github.com/eigent-ai/toolathlon_gym).

## A. Implementation and evaluation details

The implementations share the problem setting described in §3, with benchmark-specific settings described below.

### A.1. Model configuration

For the main comparison across all three benchmarks, we use Anthropic’s Claude Opus 4.8 for evolution across harness-optimization methods (Anthropic, 2026). We use Google’s gemini-3.5-flash as the fixed executor (Google, 2026) for all methods. Execution follows each benchmark’s native protocol, including its agent scaffold, tool environment, execution limits, and evaluation procedure. Harness evolution changes the code around the executor while keeping its model weights fixed.

### A.2. Common training configuration

We configure a budget of up to 40 evolution iterations for each harness-optimization method on each benchmark, which we found sufficient for harness search across the evaluated methods. Candidate evaluation and selection use only discovery tasks. The resulting harnesses are frozen before held-out evaluation.

### A.3. Benchmark implementations

We retain each benchmark’s native task environment and evaluation procedure. Task counts, discovery/held-out splits, and primary metrics are given in §4.1.

**AutomationBench.** Tasks execute business workflows in a simulated application environment. The agent uses API search and request tools to inspect and modify an initialized world state. We retain the native execution loop and tools. Deterministic assertions evaluate the final state, yielding partial-credit scores and strict task-completion verdicts.

**Workspace-Bench.** Tasks operate on files in a task workspace and require outputs such as documents, spreadsheets, presentations, and code

artifacts. We use the DeepAgents scaffold with a local shell and filesystem backend. The benchmark’s agent-as-a-judge pipeline evaluates task-specific rubrics over the resulting outputs. We report micro-averaged rubric pass and full-task pass, which requires satisfying every rubric for a task.

**Toolathlon-GYM.** Tasks combine tools and application services exposed through configured MCP servers. The native runner initializes each task’s workspace and service connections, then executes the agent through the benchmark’s containerized evaluation pipeline. Task-specific graders assess completion and produce the evaluation records used to compute mean reward and strict PASS.

### A.4. OO-HARNESS implementation

This section describes the code workspace, prompts, and harness interface used to implement OO-HARNESS (§3).

#### *A.4.1. Evolution workspace and code authoring*

We run the evolution agent as a coding agent with filesystem access to harness interfaces, existing source code, task clusters, discovery trajectories, evaluation feedback, and prior reflections. It can search and read these files, delegate evidence inspection to subagents, and write executable candidate subclasses at designated paths. AutomationBench and Workspace-Bench also support shared helper modules. The resulting code is loaded, validated, and evaluated by the evolution procedure.

The Workspace-Bench authoring interface exposes file-reading, search, writing, editing, and subagent tools. Its harness interface separately supports tools, middleware, file backends, and subagent configurations. For example, the `subagents()` method supplies subagents used during benchmark task execution, while the evolution agent’s subagents inspect training evidence. The available modifications are determined by each benchmark’s harness interface.

#### A.4.2. Evolution and routing prompts

**Evolution prompt.** The evolution agent receives the harness interface, current hierarchy, target cluster or available clusters, and paths to discovery-task trajectories, evaluation feedback, and prior reflections. A condensed prompt is:

```
Read the training trajectories and prior changes.
Use subagents to inspect the execution evidence.
Identify one shared, harness-fixable mechanism.
Write one subclass of the selected parent; call super() to preserve the inherited behavior.
Do not hardcode task IDs, answers, or filenames.
Return a JSON manifest describing the change.
```

AutomationBench and Workspace-Bench bind the parent as `_Parent`; Toolathlon uses `_Base`. AutomationBench allows add, merge, and split proposals and lets the teacher choose a cluster; Workspace-Bench supplies a target cluster and parent. Toolathlon also provides its design principles and requires an observable applicability gate. Supplied lesson text is capped at 6,000 characters in all three implementations. The default proposal timeout is 2,400 seconds, separate from the executor rollout budget. A representative manifest is:

```
{"op": "add", "cluster": "<training cluster >",
 "parent": "<existing node or base>",
 "name": "<candidate name>",
 "seam": "<modified interface>",
 "hypothesis": "<shared failure and mechanism>"}
```

Toolathlon adds gate; Workspace-Bench adds changes and names the seam as `system_prompt`, `tools`, `middleware`, `subagents`, or `backend`. Merge and split proposals identify the affected clusters or an observable split criterion. The template files give the exact benchmark-specific schemas; the evolution procedure validates candidates and determines acceptance from training evaluations.

**Routing prompt.** The router receives the task, an observable Base-execution summary, and a

frozen harness catalogue, together with routing lessons where supplied. We use Claude Sonnet 5 for routing in the main comparison. The condensed AutomationBench prompt below illustrates the selection instruction:

```
Choose one available harness or base using only the Base query, observable trajectory, and retrieved training context.
Choose base when no mechanism clearly fits or a learned anti-pattern applies.
AVAILABLE HARNESSES: <frozen catalogue>
RETRIEVED CONTEXT: <retrieval response>
BASE QUERY + DIGEST: <observable evidence>
Return only JSON with choice, rule, and why.
```

Held-out grades and reference answers are excluded from the routing input.

**Inputs supplied to the router.** We summarize each benchmark’s task metadata and observable Base execution as a compact prompt record. These records provide cues for matching a task to a learned cluster, such as the tools involved, encountered errors, and required output format.

AutomationBench supplies the task query and a bounded digest of Base tool calls and results, including write counts and execution-error patterns. A first prompt retrieves relevant frozen routing rules; a second prompt selects one available harness. The final response has the following schema:

```
{"choice": "<harness-id|base>",
 "rule": "<rule-id or empty>",
 "why": "<one sentence>"}
```

For Toolathlon, each record contains the task identifier, tool families, number of recorded history events, frequent tool or event types, and execution-error categories. These fields summarize the tool environment, interaction history, and errors observed during Base execution.

For Workspace-Bench, each record contains benchmark-provided task metadata: persona and difficulty labels, requested output-file extensions, and the number of links in the file-dependency graph. It also includes Base assistant-turn and tool-call counts. Output types and file dependencies describe the requested artifact and workspace, while the execution counts summa-

rize Base’s activity. The router can therefore match both task requirements and execution patterns to the learned cluster descriptions.

Both routers receive the frozen cluster menu alongside these records; Toolathlon also receives frozen routing lessons. They return one assignment per task:

```
{"task_to_cluster": {
  "<task-id>": "<cluster-id|leave-on-base>"
}}
```

**Router invocation.** The router is called with agent tools disabled and receives only the prepared task records and frozen routing context.

**Router settings.** The following code defaults specify limits on prompt length, batch sizes, model choices, and call timeouts. In the AutomationBench reference router, the query is limited to 600 characters and the digest processes at most 60 observable message entries; the final digest is capped at 5,000 characters. Each compact routing lesson contributes at most 180 characters of lesson text and each available-harness description at most 120 characters. Retrieval requests a synthesis of at most ten lines. Defaults are Sonnet 5 for retrieval and Opus 4.8 for selection, with 400- and 1,200-second timeouts respectively. Toolathlon defaults to batches of 25 tasks, up to twelve frozen routing rules capped at 4,000 characters in total, and a 1,800-second call timeout. Workspace-Bench supplies the requested cohort’s feature table in one call, with a 1,200-second timeout. Its metadata fallback uses dependency counts and output extensions; Toolathlon’s invalid-menu fallback selects `leave-on-base`. Both allow router-model overrides, otherwise using the proposer model (default Opus 4.8). The case study in Table 3 uses Opus 4.8 for both retrieval and selection.

#### A.4.3. Inheritance example

Listing 1 illustrates how a specialized harness retains an earlier capability while adding a new one. In this saved Toolathlon lineage, parent `s7` detects formula-like writes to `.xlsx` workbooks and adds a reminder to save computed values

rather than unevaluated formula strings. Child `s30` inherits this guidance and adds a check of percentage-labelled cells in saved workbooks before finishing. The check can request one correction pass on the identified cells; Appendix B.3 details its trigger and unit convention.

The child does not redefine `manage_context`, so the parent’s context rule remains active. Its `verify_before_finish` method calls `super()` to preserve inherited completion checks before applying its own. The selected child combines these capabilities in one execution. This illustrates incremental specialization: evolution can add a targeted behavior while reusing an earlier mechanism without copying its code.

### A.5. Baseline method implementations

All baselines use the task splits and fixed executor in §4.1. Harness optimization uses discovery-task feedback; test-time trajectory selection and refinement use observable execution records without grader feedback.

**Base.** Base uses the unevolved benchmark-specific harness, including its prompts, tools, and execution loop. It performs no harness optimization or selection among specialized harnesses.

**Meta-Harness.** META-HARNESS (Lee et al., 2026)<sup>1</sup> searches for one global harness using discovery-task evaluations. The evolution agent inspects earlier candidates and execution feedback, proposes revised harness code, and evaluates the resulting program. We freeze the selected global harness and apply it to every held-out task.

**AHE.** AHE (Lin et al., 2026a)<sup>2</sup> begins with framework-source exploration and maintains an editable workspace of framework components. A debugger analyzes discovery trajectories; the evolution agent uses these reports and the change history to revise components, retain useful changes, or roll back unsuccessful edits. The selected global snapshot is frozen for held-out evaluation.

<sup>1</sup><https://github.com/stanford-iris-lab/meta-harness>

<sup>2</sup><https://github.com/china-qijizhifeng/agentic-harness-engineering>

Listing 1 | Inherited context guidance with an added completion check (Toolathlon s7 → s30). Display names and helper calls are shortened; the method names match the implementation.

```
class FormulaLiteralHarness(BaseHarness):
    def manage_context(self, messages, state):
        messages = super().manage_context(messages, state)
        return pin_literals_if_needed(messages, state)

class PercentCheckHarness(FormulaLiteralHarness):
    # Inherits manage_context from its parent.
    def verify_before_finish(self, messages, state):
        parent = super().verify_before_finish(messages, state)
        if parent:
            return parent
        return check_saved_percent_values(messages, state)
```

**AAH.** AAH (Liu et al., 2026b)<sup>3</sup> organizes tasks into groups using task descriptions and metadata, and improves a separate harness for each group. In our benchmark setup, Automation-Bench groups correspond to business domains; Workspace-Bench groups use output type and workspace requirements; and Toolathlon-GYM groups follow application families. Each specialist is revised as a separate harness implementation. At deployment, task descriptions or metadata determine which frozen specialist to use, with Base used when no specialist is available.

**Parallel sampling.** For  $K = 2$  and  $K = 5$ , we obtain independent Base executions of the same task. A Claude Opus 4.8 selector compares their observable trajectories and chooses one result. Neither reference answers nor grader feedback is available to the selector.

**Sequential refinement.** For  $K = 2$ , Claude Opus 4.8 summarizes process errors visible in the first Base execution. These task-local notes guide a second Base execution, without access to held-out grader feedback or reference answers.

### A.6. Ablation settings

These experiments isolate the roles of routing evidence and inheritance in OO-HARNESS (§5.1).

<sup>3</sup><https://github.com/A-EVO-Lab/a-evolve/tree/release/adaptive-auto-harness>

#### A.6.1. Harness routing

The routing ablation keeps the harness catalogue, executor, grader, and held-out split fixed, varying only the routing input (Table 2). Task-only routing uses task descriptions and metadata; trajectory-based routing also observes the Base execution. The task-only prompt setups are given below.

**Confidence gate.** The router is asked for a specialist identifier and applicability confidence  $c \in [0, 1]$ . For a valid identifier and numeric confidence, the routing procedure selects the specialist when  $c \geq 0.7$ , otherwise Base. Confidence is self-reported, not a calibrated success probability or a grader score.

**AutomationBench.** The prompt includes specialist identifiers with mechanisms truncated to 130 characters, and task identifiers, domains, and user triggers (up to 300 characters each), in batches of 25 tasks:

```
Route each task to ONE specialist (or base)
using ONLY the task description/trigger.
You have no execution trace, tool output,
or score. Each specialist fixes a specific
failure mode of the base agent.

SPECIALISTS (id | mechanism): <catalogue>
TASKS (id | domain | trigger): <task batch>

Pick a specialist only when the description
clearly fits it; otherwise choose base.
Return a confidence in [0,1]. Output only
JSON:
{"<task-id>": {"cluster": "<id-or-base>",
```

```
"confidence": <0..1>}, ...}
```

Missing entries or unknown identifiers select Base; missing confidence defaults to zero.

**Workspace-Bench.** Catalogue entries contain cluster identifiers, routing signatures, and addressed failures. Each task supplies its identifier, persona, difficulty, output-file extensions, dependency-edge count, tested capabilities (up to 80 characters), and task text (up to 500 characters). Batches default to 25 tasks:

Assign each new task to ONE cluster in the fixed catalogue whose description best matches it, using only the task description and metadata. No execution trace, score, or grader feedback is provided.

```
CLUSTERS (id | routing signature |
  failure):
<frozen catalogue>
TASKS (description + metadata): <task
  batch>
```

If no cluster matches well, or confidence is below 0.7, choose leave-on-base.  
Output only JSON: {"routes": {"<task-id>":
 {"cluster":
 "<cluster-id|leave-on-base>",
 "confidence": <0..1>}, ...}}

Missing or invalid identifiers invoke a task-metadata fallback based on output-file type and dependency count; missing confidence defaults to one.

**Toolathlon-GYM.** The following reconstructed template uses task descriptions and declared app/tool metadata with the frozen harness catalogue and the same confidence gate. Catalogue entries describe each specialist’s mechanism and applicability conditions:

Route each Toolathlon-GYM task to ONE specialist in the fixed catalogue or leave-on-base, using only its description and declared app/tool metadata. No Base trajectory, tool output, or grader feedback is provided.

```
SPECIALISTS (id | mechanism | applicability)
:
<frozen catalogue>
TASKS (id | description | apps/tools):
<task batch>
```

Choose a specialist only when the task requirements clearly match its capability. Do not assume that an execution error has occurred. If no specialist clearly fits or confidence is below 0.7, choose leave-on-base.

Return each task exactly once. Output only JSON:

```
{"routes": {"<task-id>": {
  "cluster": "<cluster-id|leave-on-base>",
  "confidence": <0..1>}, ...}}
```

#### A.6.2. Hierarchical structure

This ablation examines how an evolution step builds on previously learned harness code. We compare three separate searches on Workspace-Bench, each learning specialized harnesses for task clusters:

- **Base-reset (no code carry-over).** Each candidate derives directly from Base. The evolution agent is asked to implement one new mechanism without incorporating mechanisms from earlier evolved nodes. Previous execution evidence and reflections remain available to guide the proposal. Thus, each proposal starts afresh in its code implementation while retaining the search’s diagnostic history.
- **Flat (copy-based reuse).** Each candidate also derives directly from Base. When the target cluster already has a deployed harness, the evolution agent is instructed to read its source, copy all its accepted mechanisms into a new file, and then add one new mechanism. The candidate cannot import, delegate to, or inherit from other evolved nodes. Reuse therefore occurs through code copied into the candidate, whose retained behavior is implemented within the module.
- **OO (inheritance).** The target cluster’s currently deployed harness becomes the candidate’s parent; Base is used when the cluster has no specialist. The loader binds this parent class to `_Parent`. Methods that the candidate does not override remain inherited, while an override can call `super()` to compose the parent’s behavior with a new change. The evolution agent can inspect prior source, execution evidence, and reflections, then add a specialized

behavior without needing to copy the parent’s implementation.

**Shared setup and evaluation.** The variants use the same discovery split, initial task clusters, and initial Base execution records. They share the procedures for choosing a target cluster, scoring candidates, accepting revisions, and routing held-out tasks, with the executor and grader fixed. Flat and Base-reset keep the shared helper library read-only during their searches, so candidate changes are written into the new node module.

Each search learns from the 288-task discovery split and freezes its resulting catalogue for one held-out evaluation on Lite-100. The routing procedure is shared, while the learned harnesses and resulting task assignments can differ across searches. Figure 5 reports micro rubric pass for the three resulting systems. Base-reset versus Flat examines carrying forward evolved code; Flat versus OO examines organizing that reuse through inheritance.

### A.7. OOD evaluation configuration

We use application metadata to construct the OOD split in §5.3, retaining 254 Toolathlon-GYM tasks and 49 Toolathlon tasks. We note that the emphasis of Toolathon(-GYM) is on using applications and that different applications could require substantially different skills, tools, or workflows. The curated application distribution is as follows:

- **Training applications:** Google Workspace (Forms, Calendar, and Sheets), HowToCook, Notion, Snowflake, and WooCommerce.
- **Test applications:** Amazon, Canvas, Git/GitHub, Kubernetes, literature research (arXiv and Scholarly/Google Scholar), MySQL, 12306, Redis, Yahoo Finance, and YouTube.

As a result, these application families do not overlap and offer a good controlled experiment setting.

### A.8. Artifact sources and resource reporting

**Sources and terms.** The AutomationBench repository distributes Zapier’s original contributions under the MIT license, with a separate scope

notice for third-party API structures.<sup>4</sup> Workspace-Bench’s code is MIT-licensed.<sup>5</sup> Its full-dataset card lists Apache-2.0; the inspected Lite card does not separately specify a license.<sup>6</sup> Toolathlon-GYM’s root code license is Apache-2.0.<sup>7</sup> The original Toolathlon repository and task-data card do not specify a standard license.<sup>8</sup> Task files, bundled components, and external services may carry separate terms that also govern redistribution.

**API access and AI assistance.** We access the language models through hosted APIs, using Google Cloud Vertex AI as the backend. AI tools assisted manuscript revision and polishing, code inspection, and figure preparation.

**Resources.** Across all benchmarks and methods, the main computational expense is hosted-model API usage for task execution and, where applicable, harness evolution, routing, and model-based evaluation.

## B. Case studies of specialized harnesses

These cases show how OO-HARNESS turns execution needs into concrete code changes and routing choices. We examine document generation on Workspace-Bench, shared completion checks and routing lessons on AutomationBench, and targeted runtime checks on Toolathlon-GYM.

### B.1. Workspace-Bench: generating Word documents

Document-writing tasks require both suitable content and a valid output file. Writing plain text to a .docx path does not produce a Word document.

<sup>4</sup><https://github.com/zapier/AutomationBench/blob/main/LICENSE>

<sup>5</sup><https://github.com/OpenDataBox/Workspace-Bench/blob/main/LICENSE>

<sup>6</sup><https://huggingface.co/datasets/Workspace-Bench/Workspace-Bench>; <https://huggingface.co/datasets/Workspace-Bench/Workspace-Bench-Lite>

<sup>7</sup><https://github.com/eigent-ai/toolathlon-gym/blob/main/LICENSE>

<sup>8</sup><https://github.com/hkust-nlp/Toolathlon>; <https://huggingface.co/datasets/hkust-nlp/Toolathlon>

#### Document-writing backend

`write_file("report.docx", text)`

Fixed executor; change the file backend

| Base harness                                   | Specialized harness                              |
|------------------------------------------------|--------------------------------------------------|
| <b>Default write()</b><br>Encode text as UTF-8 | <b>Override write()</b><br>Render a binary .docx |
| ↓                                              | ↓                                                |
| <b>Text bytes</b><br>report.docx               | <b>Binary document</b><br>report.docx            |

Diagram comparing Base harness and Specialized harness. Base harness uses Default write() to encode text as UTF-8, resulting in Text bytes (report.docx). Specialized harness uses Override write() to render a binary .docx, resulting in a Binary document (report.docx).

Valid file format does not imply correct content.

**Figure 8 | Generating a Word document through the file backend.** For the same illustrative `write_file` call, the base backend saves text under a `.docx` file-name; the specialized backend renders the text into a binary document.

The `office-doc-write` harness addresses this problem by wrapping the file backend and rendering supported text into a binary Word document (Figure 8).

The specialized backend handles direct document writes and can also create a missing requested document from a text draft. In the latter case, it preserves the original text write and leaves any existing target document untouched. If rendering fails, execution falls back to the parent backend. This capability handles the file format; the benchmark separately evaluates whether the content satisfies the task.

The requested output format is often visible in the task description, giving the router a useful cue for selecting this capability. This is consistent with the small difference between task-only and trajectory-based routing on Workspace-Bench.

### B.2. AutomationBench: inherited checks and routing lessons

**Adding execution checks through inheritance.** Business workflows often require changes to application state, but an execution may finish after searching or reading without making an update. An ancestor (s9) addresses this problem with a completion check: when the task requires a write but no mutating API call has occurred, it can request another turn.

Figure 9 shows successive extensions within the `discovery-setup` lineage. Building on s9’s missing-write completion check, s12 adds a reminder near the turn limit when no write has succeeded. Its child s29 retains both mechanisms and adds guidance for unrecoverable errors and repeated unproductive tool results.

**discovery-setup**

```
graph TD; A["s9: completion check  
Before finishing, request another turn  
if no write was attempted"] --> B["s12: near-budget reminder  
Prompt a write near the turn limit  
if no write has succeeded"]; B --> C["s29: tool-error guidance  
Add corrective hints for unrecoverable  
errors or repeated unproductive results"]
```

**s9: completion check**  
Before finishing, request another turn  
if no write was attempted

↓

**s12: near-budget reminder**  
Prompt a write near the turn limit  
if no write has succeeded

↓

**s29: tool-error guidance**  
Add corrective hints for unrecoverable  
errors or repeated unproductive results

Flowchart: Discovery-setup process flow with three sequential steps.

Outlined: inactive ancestors | Filled: active harness

**Figure 9 | Adding execution checks through inheritance.** Successive nodes add a missing-write completion check, a near-budget reminder, and tool-error guidance. Arrows show inheritance. The filled node s29 is active; s9 and s12 are inactive ancestors that supply inherited behavior.

**Using execution evidence to choose a harness.** Routing lessons connect observed execution problems to harness capabilities. For example, a lesson recommends an API error-normalizer when an execution repeatedly encounters query-parsing errors. This harness turns error feedback into instructions for repairing the query (Figure 6c).

Table 4 gives two recorded routing choices. An execution with no writes and repeated service errors is routed to a resource-manifest harness, which supplies connected-service and resource information to guide API exploration. A clean execution with successful writes reuses Base. These examples show how lessons can select a relevant intervention or preserve a clean Base execution.

| Base execution                                                                                                                                                            | Routing lesson                                                                                                                             | Router choice              |
|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|----------------------------|
| A lead-scoring execution makes no writes. HubSpot and Intercom return 401 errors indicating no connected account; a Lead lookup returns 404. The final response is empty. | Repeated connection errors and failed resource lookups suggest that information about connected services and available resources may help. | Resource-manifest harness. |
| Another execution completes three writes, has no errors, and finishes cleanly.                                                                                            | Successful writes and a clean finish support keeping the Base result.                                                                      | Reuse Base.                |

Table 4 | **Execution evidence behind two routing choices.** Examples from an earlier AutomationBench workflow pair observed Base behavior with the applicable routing lesson and the recorded choice.

| <b>Toolathlon-GYM</b>     |                    |                               |                     |                     |                  |               |                   |                  |                  |                     |                      |
|---------------------------|--------------------|-------------------------------|---------------------|---------------------|------------------|---------------|-------------------|------------------|------------------|---------------------|----------------------|
|                           | <b>OO clusters</b> | <b>Task tool/app families</b> |                     |                     |                  |               |                   |                  |                  |                     |                      |
| completeness-finalize     | 1                  |                               |                     |                     |                  | 1             |                   |                  | 3                | 2                   |                      |
| copy-translation-fidelity |                    |                               |                     |                     |                  |               |                   |                  |                  | 1                   |                      |
| email-fidelity            | 1                  |                               |                     |                     |                  |               |                   |                  | 3                |                     |                      |
| excel-formula-literal     | 2                  | 1                             |                     | 1                   |                  | 1             |                   |                  | 10               | 3                   | 2                    |
| notion-structure          |                    |                               |                     |                     |                  | 4             |                   |                  |                  | 1                   |                      |
| sql-overfilter-fullscan   | 2                  |                               |                     |                     |                  |               |                   |                  | 9                | 1                   |                      |
|                           | <i>canvas</i>      | <i>google calendar</i>        | <i>google forms</i> | <i>google sheet</i> | <i>howtocook</i> | <i>notion</i> | <i>rail 12306</i> | <i>scholarly</i> | <i>snowflake</i> | <i>woo commerce</i> | <i>yahoo-finance</i> |

Figure 10 | **Learned task clusters on Toolathlon-GYM.** Rows are learned clusters and columns are evaluated AAH app groups. Cells count shared discovery tasks, showing how a cluster can span several applications. Blank cells are zero; Base and unclustered tasks are omitted.

### B.3. Toolathlon-GYM: refining when and what to check

The learned clusters can span multiple applications (Figure 10). For example, `completeness-finalize` includes tasks using Canvas, Notion, Snowflake, and WooCommerce. The following examples show how evolution refines a shared behavior and adds a check for a particular output.

**Refining when to compress tool output.** An ancestor of the `completeness-finalize` harness shortens unusually long tool responses to limit the amount of text in the execution history. Its child retains this behavior but adds an early-finish condition: after an early completion attempt, any subsequent tool outputs bypass compression. This allows the child to narrow when an inherited intervention applies, using progress observed during execution.

**Checking the saved workbook.** The `excel-formula-literal` harness adds a file check to inherited guidance about writing computed values to spreadsheets (Listing 1). Before finishing, it reads the saved workbook and looks for cells with percentage labels and values strictly between zero and one. It can then request one correction pass, listing the identified cells and proposed values multiplied by 100.

This rule assumes that the task expects percentage points: for example, 20 rather than 0.2 for twenty percent. The instruction asks the executor to change only the listed cells and preserve the rest of the workbook. The harness therefore uses the contents of the produced file to decide whether to request a targeted correction before finishing.