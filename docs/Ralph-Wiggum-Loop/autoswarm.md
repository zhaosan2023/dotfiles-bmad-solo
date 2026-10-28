

# AutoSwarm: Automating Agent Swarms

**Zhonghang Li Zongwei Li Chao Huang**

The University of Hong Kong

{bjdwh.zzh, zongwei9888, chaohuang75}@gmail.com

## Abstract

Large language model (LLM) agents increasingly automate complex tasks, with multi-agent systems seeking further performance gains through specialization and collaboration. However, distributing work across agents does not automatically yield complementary contributions, and inter-agent dependencies can turn local errors into task failure. To address these challenges, we propose AutoSwarm, a multi-agent framework for collaborative problem solving. Collaboration formation jointly defines responsibility boundaries and conditions for acceptance and downstream use, grounding capability allocation in contributions that other agents can assess and integrate toward a shared objective. Execution coordination couples agents’ local progress through a shared state, using dependencies and supervisory relationships to govern agent activation, result handoffs, and integration while adapting subsequent actions to review feedback and emerging blockers. Experiments spanning long-horizon programming, interactive planning, and professional financial analysis demonstrate AutoSwarm’s advantages over single-agent baselines and existing multi-agent frameworks. Source code is available at <https://github.com/HKUDS/AutoSwarm>.

## 1 Introduction

Recent advances in large language models (LLMs) have enabled increasingly capable instruction following and interactive problem solving (Ouyang et al., 2022; Yao et al., 2023). By combining language-based reasoning with tools and environmental feedback, LLM agents can gather information, formulate plans, and take actions toward user-specified goals. This paradigm supports the automation of tasks that extend beyond a single response, including information seeking, data analysis, and software development. Such tasks require investigation, execution, and verification to work together over a sequence of decisions and actions.

**Task:** develop an open-world multiplayer RPG with a 40-hour story, cross-platform, running smoothly on mid-range phones

### 1 More agents ≠ complementary contributions

|                            |                                    |                                 |
|----------------------------|------------------------------------|---------------------------------|
| <b>Lore writer</b><br>lore | <b>Quest designer</b><br>main plot | <b>Level designer</b><br>levels |
|----------------------------|------------------------------------|---------------------------------|

*both own the main plot*

plot: king is villain ⚡ plot: king is ally → build which story?

### 2 Local view ≠ global task: errors accumulate

|                  |                  |                  |
|------------------|------------------|------------------|
| create world art | build open world | test performance |
|------------------|------------------|------------------|

builds on → builds on

|                                                   |                                                      |                                                    |
|---------------------------------------------------|------------------------------------------------------|----------------------------------------------------|
| 4K art used unchecked<br><i>unverified result</i> | “lower res?” → no reply<br><i>unanswered request</i> | “phone lag” → no fix<br><i>unaddressed finding</i> |
|---------------------------------------------------|------------------------------------------------------|----------------------------------------------------|

Infographic: Comparison of two multi-agent development workflows for an RPG game.

Figure 1: Motivation for AutoSwarm: Responsibility Misalignment and Fragile Dependencies

Many existing LLM agents approach these tasks through a single reasoning-and-action loop. Re-Act interleaves reasoning with actions and observations to update plans during interaction (Yao et al., 2023), while SWE-agent equips an agent with interfaces for navigating repositories, editing files, and executing tests (Yang et al., 2024). Such designs enable one agent to handle multiple stages of a task while retaining a unified execution history. However, the same agent remains responsible for gathering evidence, interpreting requirements, and carrying out different kinds of work. As task scope expands, this concentration of responsibilities can limit how thoroughly different parts of the task are addressed. Execution-trace analyses report cases in which single-agent investigation lacks breadth, whereas coordinated agents examine complementary evidence and achieve better performance (Kim et al., 2025). These findings motivate using multiple agents to distribute responsibilities and provide complementary contributions.

Multi-agent methods pursue this goal through role specialization, structured workflows, and adaptive orchestration. MetaGPT assigns domain re-

sponsibilities and uses standardized procedures to organize work and verify intermediate results (Hong et al., 2024). AgentVerse combines expert recruitment, collaborative decision-making, execution, and evaluation, adjusting its group composition based on feedback (Chen et al., 2024). Magentic-One uses an orchestrator to delegate work to specialized agents, monitor progress, and revise plans when execution encounters difficulties (Fourney et al., 2024). In practice, collaboration remains vulnerable to mismatches between task requirements and work assignments, as well as failures to coordinate dependent activities, which can limit the gains from distributing work across agents (Kim et al., 2025; Cemri et al., 2025).

These limitations give rise to two connected challenges, illustrated in Figure 1. **First, increasing the number of agents does not automatically yield complementary contributions.** Additional agents create opportunities for specialization and complementary work, but these benefits depend on how responsibilities are assigned and connected. Splitting work by role or step can still leave overlapping responsibilities, missing requirements, or unclear handoffs. The system must define collaboration boundaries according to the task, matching suitable capabilities to concrete responsibilities and specifying the expected outputs and conditions for their acceptance and downstream use. **Second, dependencies among agents can turn local errors and blockers into task failure.** Once work is distributed, agents hold partial information and progress at different rates, yet rely on one another’s results to continue. An unverified result may be adopted downstream, a review finding may never lead to a revision, or an unanswered request may stall dependent work. Coordination must identify such problems as they arise and determine which work can proceed, which needs correction, and who should resolve the blocker.

To address these challenges, we propose AutoSwarm, a multi-agent framework for collaborative problem solving. The framework comprises two components: collaboration formation and execution coordination. Collaboration formation grounds specialization in the contributions needed by the shared objective, defining responsibility boundaries together with the conditions for acceptance and downstream use so that agents’ outputs can support one another. Execution coordination maintains a shared state of contribution progress and dependencies to determine the next actions

across the team. Independent contributions can proceed concurrently, and accepted results enable dependent work to advance. Review feedback and emerging blockers update the same state, adjusting subsequent actions and identifying the agents responsible for execution, revision, or integration. We conduct experiments on three benchmarks spanning multiple domains and task types: LongCLI-Bench (Feng et al., 2026), Plancraft (Dagan et al., 2025), and APEX-Agents 1.1 (Vidgen et al., 2026; Bennett et al., 2026). The results show that AutoSwarm improves task completion over single-agent baselines and existing multi-agent frameworks, with consistent gains across different LLM backbones. Our contributions are:

- We formulate collaboration at the level of inter-dependent contributions, linking capability allocation to conditions for acceptance and downstream use. This makes the intended use of a result part of its delegation, turning specialization into contributions that other agents can assess and integrate toward the shared objective.
- We develop execution coordination that makes the conditions for result handoffs govern downstream progress. Review findings and execution blockers update the shared state controlling dependency release, revision, and integration, making correction part of the execution logic and preventing unaccepted results from releasing dependent work.
- Experiments on three benchmarks covering diverse domains and task types validate the effectiveness of AutoSwarm. The results show higher task completion than single-agent baselines and existing multi-agent frameworks, highlighting the value of task-specific organization and coordinated execution for multi-agent collaboration.

## 2 Preliminaries

We consider an agentic task described by  $(d, \mathcal{E})$ , where  $d$  specifies the objective and requirements in natural language, and  $\mathcal{E}$  is the environment provided for execution. The environment includes the initial context, relevant resources, and available tools, and supports interaction throughout task execution. The required output  $y$  is a task result, such as an answer, a generated artifact, or a completed change to the environment.

We describe an agent swarm by a set of available LLM agents  $\mathcal{A}$  and a collaboration mechanism  $\Omega$ . Their collective execution induces the task-level

input-output relation

$$y \sim P_{\mathcal{A},\Omega}(\cdot \mid d, \mathcal{E}), \quad (1)$$

where  $P_{\mathcal{A},\Omega}$  denotes the distribution of task results under  $\Omega$ . Our focus is how collaboration organizes available capabilities and coordinates interdependent work to satisfy the task’s requirements.

In AutoSwarm, collaboration is described by an organization  $\mathcal{O}$ , a delegation graph  $\mathcal{G}_t$ , and a shared execution state  $s_t$ , where  $t$  indexes coordination updates. Organization  $\mathcal{O}$  assigns available agents to task-specific responsibilities and supervisory relationships before execution. Each graph node is a task unit binding a scoped goal to an assigned agent, an expected result, acceptance conditions, and a parent objective; edges encode required result handoffs. State  $s_t$  records unit lifecycles, outputs, assessments, terminal outcomes, pending actions, and unresolved requests. Their evolution follows

$$(\mathcal{G}_{t+1}, s_{t+1}) = \Phi_{\mathcal{O}}(\mathcal{G}_t, s_t; e_t), \quad (2)$$

where  $e_t$  denotes a new delegation, a submitted result, review feedback, or a coordination blocker. The transition  $\Phi_{\mathcal{O}}$  adds or revises task units and handoff conditions, uses current evidence to release dependencies or require revision, and assigns pending actions in execution, review, revision, and integration. Unresolved information requests or failed prerequisites prompt supervisory coordination within the same transition. The organization remains fixed while the delegation graph and execution state adapt. Integration combines accepted contributions into  $y$  and assesses them against the original requirements. The next section specifies how these relationships are formed and how their evolution is coordinated.

## 3 Methodology

We propose AutoSwarm, a multi-agent framework comprising collaboration formation and execution coordination, as shown in Figure 2. Collaboration formation connects available capabilities to responsibilities and represents delegated contributions as task units. Execution coordination couples local task execution through dependencies and supervisory relationships. Explicit goal relationships and a shared execution state connect individual reasoning and result handoffs to the overall objective.

### 3.1 Collaboration Formation

Additional agents contribute to a task through distinct, connected responsibilities. AutoSwarm estab-

lishes a team around the task’s functional needs and translates its responsibilities into task units with scoped goals, explicit outputs, and relationships. The supervisory hierarchy establishes accountability for these goals, while result dependencies specify how contributions support one another.

#### 3.1.1 Adaptive Team Composition

A catalogue of agent profiles offers available capabilities, but the task determines which functions are needed and how they should interact. Given the task description  $d$  and environment  $\mathcal{E}$ , a planning model proposes a team according to task complexity, required expertise, and requested responsiveness and output quality. The plan specifies responsibilities, expected contributions, ownership of generated artifacts, required inputs, and supervisory relationships. Each role is justified by the contribution that would be lost if it were removed or merged with another role. This ties team composition to complementary task functions.

Profiles are selected jointly against the proposed responsibilities and their relationships. A suitable profile is retained or refined into instructions for its assigned role, removing irrelevant duties, invented qualifications, incompatible output conventions, and unsupported numerical assumptions. Each role is assigned an agent with the required tools and execution capabilities. Supervisory relationships define the direct-supervisor hierarchy used for delegation and review. The team is established before execution; later adaptation updates delegated goals and their relationships.

#### 3.1.2 Structured Task Delegation

A role describes expertise, while collaboration requires a scoped contribution that another agent can use. We introduce the *task unit* as the basic unit of delegation: it binds a goal to an assigned agent, an expected result, and the conditions for handing that result over. A supervising agent can create multiple units for an objective, and an agent can receive multiple units associated with different parent objectives. Task assignment therefore relates agents to contributions rather than assigning one agent a single indivisible task.

Each unit has a *responsible agent*, which executes and revises its contribution, and a *supervising agent*, which retains accountability for its parent objective. By default, the supervising agent is the responsible agent’s direct supervisor and reviews its submitted result. A specialized reviewer can be

**shared execution state**  
activate · execute · assess · integrate

**Collaboration Formation**

**1 Team composition**

task  $d$  → profiles → planner → supervisor → **team  $\mathcal{A}$**  (fixed before execution)

**2 Structured task delegation**

**task unit  $g_5$** : goal, agent  $\pi_t(g)$ , supervisor, criteria  $C_g^t$ , needs  $g_3$ , result  $z_g^t$

units  $\mathcal{V}_t$ :  $g_1, g_2, g_3, g_4, g_5$

→ dependency  $(h, g) \in \mathcal{D}_t$  | assignment  $\pi_t: \mathcal{V}_t \rightarrow \mathcal{A}$  | delegation

**Execution Coordination**

**3 State-based task execution**

**READY** → **IN PROGRESS** → **IN REVIEW** → **DONE**

*feedback*

**Start once inputs are accepted**:  $g_1$  in progress,  $g_2$  in progress,  $g_4$  ready · waiting for  $g_1, g_2$ ,  $g_3$  in progress

**Accept if checks pass**: content, evidence, limitations, approves

**Integrate**: accepted children into the parent result →  **$g_0$  result**

**4 Event-driven interaction**

async message · reply resumes

timeout / failure → clarify, replace, revise  $\mathcal{D}_t$

replies and fixes update  $s_t$

parent integration →  **$g_0$**  → **result for  $d$**

Flowchart: System architecture for task collaboration formation, structured delegation, and execution coordination.

Figure 2: Overview of the proposed AutoSwarm framework.

explicitly assigned while the supervisor retains integration responsibility. These functions are relative to a unit: an agent can execute the units assigned to it and supervise units delegated to others.

**(i) Contribution boundaries.** Each unit specifies its scope, expected output, and ownership of generated artifacts. The assignment identifies the parent requirement it addresses and the inputs it needs. These boundaries assign production and revision to a responsible agent, while the delegating agent remains accountable for integrating contributions.

**(ii) Acceptance requirements.** The delegating agent specifies task-specific criteria for required content, supporting evidence, and the assumptions or limitations accompanying the output. These criteria guide execution, review, and correction, connecting the contribution to its downstream use.

**(iii) Dependencies and review.** A dependency specifies the result needed for another unit to proceed; a review relationship identifies the agent assessing whether that result meets its acceptance criteria. These relationships separate production, assessment, and consumption while connecting each handoff to explicit criteria for downstream use.

The delegation graph  $\mathcal{G}_t = (\mathcal{V}_t, \mathcal{D}_t)$  contains task units as nodes. Assignment is represented by a many-to-one mapping  $\pi_t : \mathcal{V}_t \rightarrow \mathcal{A}$ ;  $\pi_t(g)$  is the agent responsible for unit  $g$ . Each unit also records its supervisor, parent objective, output requirements, and acceptance conditions  $C_g^t$ . An edge  $(h, g) \in \mathcal{D}_t$  specifies that executing  $g$  requires the accepted result of  $h$ . Information exchange can occur without creating an execution dependency.

Delegation extends or revises this graph as agents develop their contributions. New units preserve their connection to the parent objective and

specify the corresponding outputs and dependencies. A handoff conveys the result, supporting evidence, remaining limitations, and intended use. The supervisor assesses whether the contributions collectively address the objective and can be integrated into a coherent result.

### 3.2 Execution Coordination

Distributed responsibilities require productive local execution and consistent progress across connected task units. AutoSwarm coordinates both through the shared execution state: it records what each unit has achieved, what remains unresolved, and which action should follow. The same mechanism connects execution to review and integration, and accommodates blockers arising during interaction.

#### 3.2.1 State-Based Task Execution

Tracking progress by task unit connects an agent’s local work to the contributions needed elsewhere. Local execution describes one unit’s lifecycle; global coordination governs interactions between agents across their units.

**Local execution.** Each unit  $g$  follows a lifecycle described by  $q_t(g)$ :

- (i) READY.** The assigned unit awaits activation for execution or revision.
- (ii) IN PROGRESS.** The responsible agent interprets the goal and uses tools in  $\mathcal{E}$  to develop or revise its result. Execution can remain paused while necessary information or inputs are pending.
- (iii) IN REVIEW.** A submitted candidate awaits an assessment decision. Corrective feedback returns the unit to READY with its prior output and revision instructions.

**(iv) DONE.** The unit has terminated with success, failure, or cancellation, retaining its output and the recorded outcome.

The unit retains its goal, observations, output, and feedback across turns. Global coordination determines activation, assessment, and inter-agent handoffs.

**Global coordination.** Coordination links agents through their delegated task units, review relationships, and required result handoffs. The shared state  $s_t$  gives a joint view of progress across  $\mathcal{G}_t$  and determines which agent should execute, assess, or integrate a contribution. Each action receives context assembled from the relevant unit’s goal, current inputs, prior output, and feedback.

A designated reviewer, normally the direct supervisor, assesses the contribution and its supporting evidence  $z_g^t$ . Acceptance is

$$a_t(g) = C_g^t(z_g^t) \wedge R_t(g), \quad (3)$$

where  $C_g^t$  checks the output and evidence requirements,  $R_t(g)$  records review approval, and  $a_t(g) \in \{0, 1\}$  indicates acceptance. This decision governs successful closure and the result’s availability to other agents. Failed or cancelled units retain  $a_t(g) = 0$ ; terminal closure alone does not supply an accepted input.

Required result handoffs determine dependent execution:

$$\eta_t(g) = \bigwedge_{(h,g) \in \mathcal{D}_t} a_t(h). \quad (4)$$

Global coordination releases a unit from READY to IN PROGRESS through this gate, with  $\eta_t(g) = 1$  and the necessary information available. For task units  $g \in \mathcal{V}_t$ , result dependencies define the frontier

$$\mathcal{F}_t = \{g \mid q_t(g) = \text{READY}, \eta_t(g) = 1\}. \quad (5)$$

Units without required predecessors satisfy the result condition. Independent eligible units can advance concurrently, and an agent can execute one unit while others assigned to it await input or review. Supervisors can assess child contributions while their parent units remain pending.

Acceptance updates eligibility for connected dependents; new delegations and revised requirements update the graph and shared state together. Revised requirements invalidate prior acceptance and preserve the existing output for reassessment. Integration develops a parent result from accepted

child contributions, reconciles their conclusions, and checks parent requirements before submitting it for review. Execution, assessment, revision, and integration thus connect local lifecycles through explicit interactions between agents.

#### 3.2.2 Event-Driven Interaction

Execution reveals information gaps and decisions beyond the declared result dependencies. AutoSwarm addresses these emerging needs through scoped messages and execution events linked to an affected unit, relevant evidence, and the role responsible for the next action. Messages carry their task context and interaction intent, with replies linked to the corresponding requests. Ordinary communication is asynchronous; explicit response requirements associate necessary waiting with the affected action. Actionable messages and execution events activate the relevant agent with the context needed to respond, including roles whose earlier assignments have ended.

Replies and results update the shared state and resume pending actions. Timeouts and unsuccessful contributions activate the supervisor with the unresolved issue and its context. The supervisor coordinates clarification, corrective or replacement contributions, and justified dependency revisions, updating the available inputs, next action, and responsible role together. Failed inputs remain unaccepted, and unrecoverable branches terminate as failures. Appendix A.1 specifies the communication and supervisory mechanisms.

## 4 Experiments

We evaluate AutoSwarm by addressing the following five research questions:

- **RQ1:** How does AutoSwarm compare with single-agent systems on long-horizon tasks?
- **RQ2:** How does AutoSwarm perform compared with existing multi-agent frameworks?
- **RQ3:** How well does AutoSwarm generalize to a specialized professional domain?
- **RQ4:** How do collaboration architectures and key mechanisms affect performance?
- **RQ5:** How does AutoSwarm improve multi-agent collaboration during execution?

RQ5 case studies appear in Appendix A.4.

### 4.1 Experimental Setup

#### 4.1.1 Benchmarks

We use three benchmarks spanning long-horizon programming, interactive planning, and professional financial analysis.

**(i) LongCLI-Bench.** LongCLI-Bench (Feng et al., 2026) evaluates long-horizon programming in command-line environments. Its 20 tasks span four engineering categories: implementation from scratch, feature addition, bug fixing, and refactoring. They cover six domains: system programming, web development, data engineering, machine learning, applications, and DevOps. Agents receive a repository and requirements in an isolated environment; executable tests check their code and environment state. Overall Pass Rate, our primary metric, is the fraction passing both Fail-to-Pass (F2P) and Pass-to-Pass (P2P) suites in full. F2P Pass and P2P Pass give the fractions passing each suite in full, assessing requirements and preservation of existing behavior and protected files.

**(ii) Plancraft.** Plancraft (Dagan et al., 2025) evaluates planning in a deterministic Minecraft crafting simulator. Given an initial inventory and target item, agents move and smelt items and observe the updated inventory. Crafting chains vary in complexity; missing resources can make goals infeasible. We evaluate the small test subset of 117 problems: 97 solvable and 20 unsolvable. Task success rate is the fraction producing the target item or correctly identifying an infeasible goal. Overall success rate covers all problems; Solvable and Unsolvable success rates cover their respective subsets.

**(iii) APEX-Agents 1.1.** We select the *Investment Banking Analyst* subset of APEX-Agents 1.1 (Vidgen et al., 2026; Bennett et al., 2026). Its 80 tasks require finding financial inputs and analytical conventions across spreadsheets, documents, and communications, then computing results or creating and updating financial artifacts. Tasks provide prompts, files, and application tools in a project environment. A judge evaluates outputs and artifacts against expert-authored binary rubric criteria. Mean Score averages the proportion of satisfied criteria across tasks; Pass@1 is the fraction satisfying all criteria in one attempt.

#### 4.1.2 Baselines and Configurations

**(i) Single-agent comparisons.** For RQ1, we compare AutoSwarm with Claude Code using MiniMax-M3 and DeepSeek-V4-Flash, and with

Codex using GPT-5.6-Luna at max reasoning effort. AutoSwarm organizes multiple instances of the corresponding baseline agent with the same backbone. Each configuration is evaluated twice on all 20 tasks, and we report arithmetic mean pass rates. We also include reference results from Feng et al. (2026): GPT-5.3-Codex with Codex, Claude-Opus-4.6 with Claude Code, and DeepSeek-V3.1, GLM-4.6, and Qwen3-235B-A22B with OpenHands.

**(ii) Multi-agent comparisons.** For RQ2, we compare AutoSwarm with AutoGen (Wu et al., 2024), MetaGPT (Hong et al., 2024), Teamwork, the team-discussion framework of Pappu et al. (2026), and Codex (ultra), which uses Codex’s built-in sub-agent orchestration (OpenAI, 2026). Codex at max provides a single-agent reference. All RQ2 configurations use GPT-5.6-Luna at max reasoning effort, except Codex (ultra), which uses ultra mode; each is evaluated once on all 117 problems.

**(iii) Professional-domain references.** For RQ3, AutoSwarm uses GPT-5.6-Luna with max reasoning effort and is run once on each of the 80 tasks. We compare it with official reference scores for GPT-5.6-Luna, DeepSeek-V4.1-Flash, Gemini 3.1 Pro, GLM-5.1, GPT-6-Luna, MiniMax-M3, and Muse Spark 1.2 on the same subset (Mercor, 2026).

**(iv) Collaboration architectures.** For RQ4, we implement four architectures adapted from Kim et al. (2025). Independent agents operate in parallel in a shared environment without member message exchange or an LLM aggregator. Decentralized uses three rounds of all-member discussion, followed by voting over final answer strings and submission by an existing member. Centralized uses one coordinator and three members with star-shaped communication. Hybrid adds one peer exchange after the initial member execution to the centralized procedure. All configurations use GPT-5.6-Luna with max reasoning effort and are evaluated once on the 117 Plancraft-small problems.

### 4.2 Long-Horizon Performance (RQ1)

To assess whether AutoSwarm improves completion over extended execution, we compare it with baseline agents on LongCLI-Bench. Figure 3 reports two-run means and published references.

**Long-horizon gains.** AutoSwarm improves overall Pass Rate by 10.0, 12.5, and 15.0 percentage points for MiniMax-M3, DeepSeek-V4-Flash, and GPT-5.6-Luna, respectively, averaging 12.5 points. Gains recur in both runs for each backbone.

| Model              | Method                    | Pass Rate | F2P Pass | P2P Pass | Pass Rate ↑           | F2P ↑ | P2P ↑ |
|--------------------|---------------------------|-----------|----------|----------|-----------------------|-------|-------|
| GPT-5.3-Codex      | Codex                     |           |          |          | 15.00                 | 18.30 | 86.70 |
| Claude-Opus-4.6    | Claude Code               |           |          |          | 16.70                 | 20.00 | 78.30 |
| DeepSeek-V3.1      | OpenHands                 |           |          |          | 5.00                  | 11.70 | 88.30 |
| GLM-4.6            | OpenHands                 |           |          |          | 6.70                  | 11.70 | 83.30 |
| Qwen3-235B-A22B    | OpenHands                 |           |          |          | 6.70                  | 13.30 | 81.70 |
| MiniMax-M3         | Claude Code               |           |          |          | 32.50                 | 35.00 | 82.50 |
|                    | <b>AutoSwarm</b>          |           |          |          | <b>42.50 (+10.00)</b> | 57.50 | 75.00 |
| DeepSeek-V4-Flash  | Claude Code               |           |          |          | 45.00                 | 62.50 | 82.50 |
|                    | <b>AutoSwarm</b>          |           |          |          | <b>57.50 (+12.50)</b> | 62.50 | 92.50 |
| GPT-5.6-Luna (max) | Codex                     |           |          |          | 52.50                 | 65.00 | 80.00 |
|                    | <b>AutoSwarm</b>          |           |          |          | <b>67.50 (+15.00)</b> | 72.50 | 87.50 |
|                    | Pass Rate + F2P + P2P (%) | 0         | 50       | 100      | 150                   | 200   | 250   |

Figure 3: LongCLI-Bench results (%).

These results support its combined collaboration formation and execution coordination: contribution boundaries and acceptance requirements align delegated work with the objective, while shared-state review, revision, and dependent handoffs connect contributions to joint F2P/P2P completion.

**Adaptability across models.** Overall gains across three backbones support the adaptability of AutoSwarm’s responsibility assignment and shared-state execution control. DeepSeek-V4-Flash improves P2P Pass by 10.0 points while maintaining F2P Pass, and GPT-5.6-Luna improves both by 7.5 points, suggesting that review and dependency-aware integration help reconcile implementation and preservation requirements. MiniMax-M3 achieves a 22.5-point F2P gain with a slight P2P decline. Trace analysis attributes this to more frequent protected-file modifications; newly completed tasks more than offset the losses.

### 4.3 Multi-Agent Comparison (RQ2)

To assess gains beyond existing agent systems, we compare AutoSwarm with Codex configurations and multi-agent methods on Plancraft-small (Figure 4). AutoSwarm reaches 74.36% success, improving on Codex (60.68%) by 13.68 percentage points, while Codex (ultra) falls to 58.97%. Ultra’s decline highlights the challenge of aligning distributed contributions with shared context and dependencies. AutoSwarm governs execution through accepted results and dependency status.

Compared with existing multi-agent methods, AutoSwarm outperforms AutoGen, MetaGPT, and Teamwork, exceeding the strongest baseline, Team-

This chart compares the overall success rate (%) and solvability (%) of several models. The x-axis represents the overall success rate from 58 to 78. A horizontal line at 50.52% represents the baseline for solvability.

| Model            | Overall success rate (%) | Solvable (%) |
|------------------|--------------------------|--------------|
| <b>AutoSwarm</b> | <b>74.36</b>             | <b>69.07</b> |
| Teamwork         | 63.25                    | 55.67        |
| MetaGPT          | 61.54                    | 53.61        |
| AutoGen          | 60.68                    | 52.58        |
| Codex (ultra)    | 58.97                    | 50.52        |
| Codex            | 60.68                    | 52.58        |

Annotations: AutoSwarm shows a +11.11 vs. best baseline and +13.68 vs. Codex. Codex (ultra) is shown with a 58.97 value.

Overall success rate (%)

Other chart: Comparison of overall success rate and solvability across different models.

Figure 4: Plancraft-small success rates (%).

work, by 11.11 points. MetaGPT emphasizes SOP-based role workflows (Hong et al., 2024), while Teamwork uses discussion and answer aggregation (Pappu et al., 2026). AutoSwarm couples delegation and acceptance criteria with dynamically updated dependencies and assessed result handoffs. All configurations correctly identify the 20 unsolvable problems, so gains come entirely from solvable goals: 69.07% success for AutoSwarm versus 55.67% for Teamwork, supporting coordination that carries contributions through execution.

### 4.4 Professional Generalization (RQ3)

To assess professional generalization, we evaluate AutoSwarm on the Investment Banking Analyst subset of APEX-Agents 1.1 against official model references (Table 1).

AutoSwarm improves Mean Score and Pass@1 over the official GPT-5.6-Luna reference by 6.09 and 5.95 percentage points, respectively. It

Table 1: APEX-Agents 1.1 banking results (%).

| Model               | Effort | Mean Score $\uparrow$ | Pass@1 $\uparrow$ |
|---------------------|--------|-----------------------|-------------------|
| DeepSeek-V4.1-Flash | Max    | 43.20                 | 38.80             |
| Gemini 3.1 Pro      | High   | 45.20                 | 38.00             |
| GLM-5.1             | –      | 46.80                 | 39.60             |
| GPT-6-Luna          | Max    | 45.50                 | 38.80             |
| MiniMax-M3          | High   | 42.50                 | 36.90             |
| Muse Spark 1.2      | xHigh  | 31.50                 | 23.40             |
| GPT-5.6-Luna        | Max    | 40.90                 | 35.30             |
| <b>AutoSwarm</b>    | Max    | <b>46.99</b>          | <b>41.25</b>      |

Overall Solv. Unsolv.

*Component ablation*

| Component        | Overall      | Solv.        | Unsolv.       |
|------------------|--------------|--------------|---------------|
| <b>AutoSwarm</b> | <b>74.36</b> | <b>69.07</b> | <b>100.00</b> |
| w/o CS           | 70.09        | 63.92        | 100.00        |
| w/o SR           | 61.54        | 53.61        | 100.00        |

*Collaboration topology*

| Topology      | Overall | Solv. | Unsolv. |
|---------------|---------|-------|---------|
| Independent   | 70.09   | 65.98 | 90.00   |
| Decentralized | 39.32   | 27.84 | 95.00   |
| Centralized   | 48.72   | 42.27 | 80.00   |
| Hybrid        | 52.14   | 45.36 | 85.00   |
| Codex         | 60.68   | 52.58 | 100.00  |

0 20 40 60 80

Overall success (%)

A horizontal bar chart showing the overall success percentage for different components and collaboration topologies. The chart includes a table of the exact values for each category.

|                               | Overall      | Solv.        | Unsolv.       |
|-------------------------------|--------------|--------------|---------------|
| <b>Component ablation</b>     |              |              |               |
| <b>AutoSwarm</b>              | <b>74.36</b> | <b>69.07</b> | <b>100.00</b> |
| w/o CS                        | 70.09        | 63.92        | 100.00        |
| w/o SR                        | 61.54        | 53.61        | 100.00        |
| <i>Collaboration topology</i> |              |              |               |
| Independent                   | 70.09        | 65.98        | 90.00         |
| Decentralized                 | 39.32        | 27.84        | 95.00         |
| Centralized                   | 48.72        | 42.27        | 80.00         |
| Hybrid                        | 52.14        | 45.36        | 85.00         |
| Codex                         | 60.68        | 52.58        | 100.00        |

Bar chart: Overall success percentage across different components and collaboration topologies.

Figure 5: Plancraft-small ablation results (%).

achieves the highest listed Pass@1 (41.25%), exceeding GLM-5.1 by 1.65 points. Higher complete rubric fulfillment highlights joint requirement satisfaction: explicit contribution requirements and dependent handoffs connect evidence across artifacts, while integration checks whether accepted outputs satisfy the overall objective. These results support generalization beyond programming and planning to professional analysis.

### 4.5 Collaboration Design (RQ4)

To assess collaboration design, we compare four architectures adapted from Kim et al. (2025) and two AutoSwarm variants on Plancraft-small (Figure 5). The architecture comparison examines different communication and control structures, while the mechanism ablations assess how explicit contribution requirements and supervisory review support coordinated execution. The variants remove *contribution specifications* (CS), which define outputs, supporting evidence, and acceptance criteria, or *supervisory review* (SR), which assesses results before integration. Other mechanisms remain; see Appendix A.3.1.

**Architecture comparison.** Independent is the strongest architectural baseline (70.09%), outperforming Codex (60.68%) without member communication. In contrast, Decentralized, Centralized, and Hybrid attain 39.32%, 48.72%, and 52.14%, respectively, all below Codex. Adding peer exchange to Centralized improves success by 3.42 points, but remains insufficient to close the gap to Independent. Under this evaluation protocol, richer communication and centralized control alone do not ensure effective collaboration. AutoSwarm reaches 74.36%, surpassing Independent by 4.27 points overall and 3.09 points on solvable problems, while correctly identifying all infeasible goals. Rather than relying on communication topology alone, its contribution specifications clarify what agents must deliver, while shared execution state and assessed handoffs govern how their results advance dependent work.

**Mechanism ablations.** Removing CS lowers success to 70.09%, with five fewer solvable problems completed despite retaining the team, goals, and dependencies. Predefined outputs and evidence criteria help execution and review produce contributions suited to downstream use. Removing SR reduces success by 12.82 points to 61.54%, near Codex’s 60.68% despite preserved contribution specifications. This loss highlights how assessment triggers revision and governs which results enter integration and dependent work. Both variants retain 100% unsolvable success, locating their impact in completing feasible goals.

## 5 Conclusion

We presented AutoSwarm, a framework for improving LLM agent performance by turning individual capabilities into coordinated contributions toward a shared objective. Collaboration formation establishes distinct responsibilities and specifies what each agent should produce, together with the conditions for accepting and using its results. Building on these conditions, execution coordination links contribution progress and dependencies through a shared state to guide execution, review, revision, and integration. Feedback and emerging blockers update this state, allowing the team to adjust subsequent actions as execution unfolds. Evaluations across three benchmarks show higher task completion than single-agent baselines and existing multi-agent frameworks, with consistent gains across different LLM backbones.

## References

Austin Bennett, Bertie Vidgen, Arnav Garg, and Akul Datta. 2026. Introducing APEX-Agents 1.1. Mercor blog, September 8, 2026.

Mert Cemri, Melissa Z Pan, Shuyi Yang, Lakshya A Agrawal, Bhavya Chopra, Rishabh Tiwari, Kurt Keutzer, Aditya Parameswaran, Dan Klein, Kannan Ramchandran, Matei A Zaharia, Joseph Gonzalez, and Ion Stoica. 2025. Why do multi-agent LLM systems fail? In *Advances in Neural Information Processing Systems*, volume 38. Curran Associates, Inc. Datasets and Benchmarks Track.

Weize Chen, Yusheng Su, Jingwei Zuo, Cheng Yang, Chenfei Yuan, Chi-Min Chan, Heyang Yu, Yaxi Lu, Yi-Hsin Hung, Chen Qian, Yujia Qin, Xin Cong, Ruobing Xie, Zhiyuan Liu, Maosong Sun, and Jie Zhou. 2024. AgentVerse: Facilitating multi-agent collaboration and exploring emergent behaviors. In *International Conference on Learning Representations*.

Gautier Dagan, Frank Keller, and Alex Lascarides. 2025. Plancraft: an evaluation dataset for planning with LLM agents. In *Second Conference on Language Modeling*.

Yukang Feng, Jianwen Sun, Zelai Yang, Jiaxin Ai, Chuanhao Li, Zizhen Li, Fanrui Zhang, Kang He, Rui Ma, Jifan Lin, Jie Sun, Yang Xiao, Sizhuo Zhou, Wenxiao Wu, Yiming Liu, Pengfei Liu, Shenglin Zhang, and Kaipeng Zhang. 2026. LongCLI-Bench: A preliminary benchmark and study for long-horizon agentic programming in command-line interfaces. In *Findings of the Association for Computational Linguistics: ACL 2026*, San Diego, California, United States. Association for Computational Linguistics.

Adam Fourney, Gagan Bansal, Hussein Mozannar, Cheng Tan, Eduardo Salinas, Erkang Zhu, Friederike Niedtner, Grace Proebsting, Griffin Bassman, Jack Gerrits, Jacob Alber, Peter Chang, Ricky Loynd, Robert West, Victor Dibia, Ahmed Awadallah, Ece Kamar, Rafah Hosn, and Saleema Amershi. 2024. *Magentic-One: A generalist multi-agent system for solving complex tasks*. *Preprint*, arXiv:2411.04468.

Hongliang He, Wenlin Yao, Kaixin Ma, Wenhao Yu, Yong Dai, Hongming Zhang, Zhenzhong Lan, and Dong Yu. 2024. WebVoyager: Building an end-to-end web agent with large multimodal models. In *Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)*. Association for Computational Linguistics.

Sirui Hong, Mingchen Zhuge, Jonathan Chen, Xiawu Zheng, Yuheng Cheng, Jinlin Wang, Ceyao Zhang, Zili Wang, Steven Yau, Zijuan Lin, Liyang Zhou, Chenyu Ran, Lingfeng Xiao, Chenglin Wu, and Jürgen Schmidhuber. 2024. MetaGPT: Meta programming for a multi-agent collaborative framework. In *International Conference on Learning Representations*, volume 2024.

Yubin Kim, Ken Gu, Chanwoo Park, Chunjong Park, Samuel Schmidgall, A. Ali Heydari, Yao Yan, Zhihan Zhang, Yuchen Zhuang, Yun Liu, Mark Malhotra, Paul Pu Liang, Hae Won Park, Yuzhe Yang, Xuhai Xu, Yilun Du, Shwetak Patel, Tim Althoff, Daniel McDuff, and Xin Liu. 2025. *Towards a science of scaling agent systems*. *Preprint*, arXiv:2512.08296.

Guohao Li, Hasan Hammoud, Hani Itani, Dmitrii Khizbullin, and Bernard Ghanem. 2023. CAMEL: Communicative agents for “mind” exploration of large language model society. In *Advances in Neural Information Processing Systems*, volume 36. Curran Associates, Inc.

Mercor. 2026. *APEX-Agents: Investment Banking Analyst*. APEX-Agents 1.1 leaderboard. <https://www.mercor.com/apex/apex-agents-leaderboard/investment-banking-analyst-agent/>. Accessed October 13, 2026.

OpenAI. 2026. *Subagents*. ChatGPT and Codex documentation. <https://learn.chatgpt.com/docs/agent-configuration/subagents>. Accessed October 13, 2026.

Long Ouyang, Jeffrey Wu, Xu Jiang, Diogo Almeida, Carroll Wainwright, Pamela Mishkin, Chong Zhang, Sandhini Agarwal, Katarina Slama, Alex Ray, John Schulman, Jacob Hilton, Fraser Kelton, Luke Miller, Maddie Simens, Amanda Askell, Peter Welinder, Paul F Christiano, Jan Leike, and Ryan Lowe. 2022. Training language models to follow instructions with human feedback. In *Advances in Neural Information Processing Systems*, volume 35. Curran Associates, Inc.

Aneesh Pappu, Batu El, Hancheng Cao, Carmelo di Nolfo, Yanchao Sun, Meng Cao, and James Zou. 2026. Multi-agent teams hold experts back. In *Proceedings of the 43rd International Conference on Machine Learning*, volume 306 of *Proceedings of Machine Learning Research*. PMLR.

Chen Qian, Wei Liu, Hongzhang Liu, Nuo Chen, Yufan Dang, Jiahao Li, Cheng Yang, Weize Chen, Yusheng Su, Xin Cong, Juyuan Xu, Dahai Li, Zhiyuan Liu, and Maosong Sun. 2024. ChatDev: Communicative agents for software development. In *Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)*. Association for Computational Linguistics.

Chen Qian, Zihao Xie, Yifei Wang, Wei Liu, Kunlun Zhu, Hanchen Xia, Yufan Dang, Zhuoyun Du, Weize Chen, Cheng Yang, Zhiyuan Liu, and Maosong Sun. 2025. Scaling large language model-based multi-agent collaboration. In *International Conference on Learning Representations*.

Timo Schick, Jane Dwivedi-Yu, Roberto Dessì, Roberta Raileanu, Maria Lomeli, Eric Hambro, Luke Zettlemoyer, Nicola Cancedda, and Thomas Scialom. 2023. Toolformer: Language models can teach themselves to use tools. In *Advances in Neural Information Processing Systems*, volume 36. Curran Associates, Inc.

Noah Shinn, Federico Cassano, Ashwin Gopinath, Karthik Narasimhan, and Shunyu Yao. 2023. Reflexion: Language agents with verbal reinforcement learning. In *Advances in Neural Information Processing Systems*, volume 36. Curran Associates, Inc.

Bertie Vidgen, Austin Mann, Abby Fennelly, John Wright Stanly, Lucas Rothman, Marco Burstein, Julien Benchek, David Ostrofsky, Anirudh Ravichandran, Debnil Sur, Neel Venugopal, Alannah Hsia, Isaac Robinson, Calix Huang, Olivia Varones, Daniyal Khan, Michael Haines, Austin Bridges, Jesse Boyle, and 5 others. 2026. *APEX-Agents*. *Preprint*, arXiv:2601.14242.

Xingyao Wang, Yangyi Chen, Lifan Yuan, Yizhe Zhang, Yunzhu Li, Hao Peng, and Heng Ji. 2024. Executable code actions elicit better LLM agents. In *Proceedings of the 41st International Conference on Machine Learning*, volume 235 of *Proceedings of Machine Learning Research*. PMLR.

Zora Zhiruo Wang, Jiayuan Mao, Daniel Fried, and Graham Neubig. 2025. Agent workflow memory. In *Proceedings of the 42nd International Conference on Machine Learning*, volume 267 of *Proceedings of Machine Learning Research*. PMLR.

Qingyun Wu, Gagan Bansal, Jieyu Zhang, Yiran Wu, Beibin Li, Erkang Zhu, Li Jiang, Xiaoyun Zhang, Shaokun Zhang, Jiale Liu, Ahmed Hassan Awadallah, Ryen W. White, Doug Burger, and Chi Wang. 2024. AutoGen: Enabling next-gen LLM applications via multi-agent conversations. In *First Conference on Language Modeling*.

John Yang, Carlos Jimenez, Alexander Wettig, Kilian Lieret, Shunyu Yao, Karthik Narasimhan, and Ofir Press. 2024. SWE-agent: Agent-computer interfaces enable automated software engineering. In *Advances in Neural Information Processing Systems*, volume 37. Curran Associates, Inc.

Ke Yang, Yao Liu, Sapana Chaudhary, Rasool Fakoor, Pratik Chaudhari, George Karypis, and Huzefa Rangwala. 2025. AgentOccam: A simple yet strong baseline for LLM-based web agents. In *International Conference on Learning Representations*.

Shunyu Yao, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran, Karthik Narasimhan, and Yuan Cao. 2023.

ReAct: Synergizing reasoning and acting in language models. In *International Conference on Learning Representations*.

Guibin Zhang, Luyang Niu, Junfeng Fang, Kun Wang, Lei Bai, and Xiang Wang. 2025a. Multi-agent architecture search via agentic supernet. In *Proceedings of the 42nd International Conference on Machine Learning*, volume 267 of *Proceedings of Machine Learning Research*. PMLR.

Guibin Zhang, Yanwei Yue, Xiangguo Sun, Guancheng Wan, Miao Yu, Junfeng Fang, Kun Wang, Tianlong Chen, and Dawei Cheng. 2025b. G-Designer: Architecting multi-agent communication topologies via graph neural networks. In *Proceedings of the 42nd International Conference on Machine Learning*, volume 267 of *Proceedings of Machine Learning Research*. PMLR.

Jiayi Zhang, Jinyu Xiang, Zhaoyang Yu, Fengwei Teng, Xiong-Hui Chen, Jiaqi Chen, Mingchen Zhuge, Xin Cheng, Sirui Hong, Jinlin Wang, Bingnan Zheng, Bang Liu, Yuyu Luo, and Chenglin Wu. 2025c. AFlow: Automating agentic workflow generation. In *International Conference on Learning Representations*.

Boyuan Zheng, Boyu Gou, Jihyung Kil, Huan Sun, and Yu Su. 2024. GPT-4V(ision) is a generalist web agent, if grounded. In *Proceedings of the 41st International Conference on Machine Learning*, volume 235 of *Proceedings of Machine Learning Research*. PMLR.

Andy Zhou, Kai Yan, Michal Shlapentokh-Rothman, Haohan Wang, and Yu-Xiong Wang. 2024. Language agent tree search unifies reasoning, acting, and planning in language models. In *Proceedings of the 41st International Conference on Machine Learning*, volume 235 of *Proceedings of Machine Learning Research*. PMLR.

Mingchen Zhuge, Wenyi Wang, Louis Kirsch, Francesco Faccio, Dmitrii Khizbullin, and Jürgen Schmidhuber. 2024. GPTSwarm: Language agents as optimizable graphs. In *Proceedings of the 41st International Conference on Machine Learning*, volume 235 of *Proceedings of Machine Learning Research*. PMLR.

## A Supplementary Material

This appendix provides additional methodological details, reviews related work, and documents supplementary experimental configurations. It concludes with paired case studies illustrating how AutoSwarm’s collaboration mechanisms affect execution.

### A.1 Methodological Details

This section expands AutoSwarm’s interaction mechanisms underlying Sections 3.1.2 and 3.2. These mechanisms associate communication with task responsibilities and connect emerging coordination needs to the shared execution state.

#### A.1.1 Asynchronous Communication

Agents communicate through persistent, role-addressed messages. A message identifies its sender and recipient, the associated task unit or parent objective, its interaction intent, and its content. It also retains its sending time, response requirement, and any connection to an earlier request. The content provides the question, decision, progress update, or result notification together with the evidence or artifact references needed to interpret it. These associations preserve the link between an exchange and the contribution it concerns when an agent participates in several task units.

Ordinary messages are delivered asynchronously, allowing the sender to continue independent work. A request can explicitly require a response before a particular decision proceeds. This requirement establishes a response obligation and records the pending question, intended recipient, waiting interval, and continuation or supervisory pathway. Replies reference the original request, so arrival is checked against the unresolved exchange. Acknowledging receipt records that a message was seen; satisfying an explicit response obligation requires a linked reply. Both sent and received correspondence remain available for later reasoning, review, and supervisory decisions.

#### A.1.2 Role Activation and Context

Incoming messages and execution events are associated with the role capable of taking the next action. Informational updates contribute to the relevant context, whereas requests, required review, and unresolved decisions create pending response or supervisory actions. These actions retain their

unit and parent-objective associations. The context supplied for an action includes the current objective, expected contribution, available results, relevant correspondence, and any prior output or correction feedback. This ties the agent’s next reasoning step to the specific obligation it needs to address.

Activation follows the continuing responsibilities of a role. A new actionable exchange can activate an agent after its previous assignment has ended, using the role’s retained context and the new request. An occupied agent receives the pending action in its subsequent execution context; other eligible agents can continue their work. The role’s activation and the lifecycle of a particular contribution are tracked separately, so a new response obligation can be handled without treating every completed contribution as unfinished. Message associations and recent interaction history identify repeated deliveries or recurring exchanges, providing guards against redundant activation.

#### A.1.3 Waiting and Supervisory Decisions

Explicit waiting is attached to the information needed for a pending action. The waiting record retains the original request, expected respondent, unresolved response requirements, and the context for continuation. Matched replies are added to the requesting agent’s context and resolve the corresponding obligations. Execution remains suspended while required replies are outstanding; unrelated execution, assessment, and integration remain eligible. Before establishing a required wait, the mechanism checks that the recipient can respond without first depending on completion of the requesting contribution. This check addresses circular waiting introduced by an unsuitable recipient relationship.

Configured waiting intervals support timeout handling. Expiration preserves the unresolved question and elapsed waiting context for the configured continuation or supervisory action. A continuation carries the unresolved limitation into subsequent reasoning; it does not mark a missing required result as accepted. Supervisory attention is directed to the responsible agent’s superior with the original objective, requested information, intended respondent, and available evidence. The supervisor can seek clarification, assign a replacement contribution, or revise an obsolete dependency while retaining accountability for the parent requirements. Its decision determines the next responsible role

and updates the affected unit’s pending action and available inputs.

#### A.1.4 Review and Dependency Updates

Result handoffs connect an output to its parent requirement and acceptance conditions. The review context contains the candidate result, supporting evidence, artifact references, assumptions, and remaining limitations. The reviewer is normally the responsible agent’s direct supervisor; an explicitly assigned specialist can assess the result while the supervisor retains integration responsibility. Review feedback identifies deficiencies relative to the required contribution, and revision resumes with the previous output and the requested corrections. Contributions specified to omit separate review retain their output and evidence checks, represented by  $R_t(g) = 1$  in Equation 3.

Acceptance releases only the result dependencies that are satisfied under the current graph and unit requirements. Additional required inputs suspend affected execution, and changes to the required contribution invalidate prior acceptance for reassessment. Failed or cancelled units have terminal outcomes but supply no accepted ordinary input. Their partial evidence and failure context support a supervisory decision once the remaining required contributions have completed or cannot progress. The supervisor can arrange replacement contributions, explicitly revise obsolete dependency relationships, or close branches that cannot satisfy the requirements. Ordinary dependent execution remains subject to Equation 4; activating the supervisor for a decision does not itself release these dependencies.

### A.2 Related Work

#### A.2.1 LLM Agents

LLM agents extend language generation into interactive problem solving by combining reasoning, tool use, and environmental observations. Early approaches establish this connection through interleaved reasoning and acting, learned tool invocation, or executable code as a unified action space (Yao et al., 2023; Schick et al., 2023; Wang et al., 2024). Subsequent work strengthens sequential decision-making through feedback-based reflection and search over alternative trajectories (Shinn et al., 2023; Zhou et al., 2024). Experience can also guide later execution: reusable workflow memories abstract common routines from completed interactions (Wang et al., 2025). In parallel, in-

terface design grounds language-model decisions in concrete environments. Software agents use repository-oriented commands to navigate, edit, and test code (Yang et al., 2024), while multimodal web agents combine visual observations with executable browser actions (Zheng et al., 2024; He et al., 2024). More recent work aligns observation and action representations with the language model’s capabilities to improve navigation (Yang et al., 2025). However, concentrating investigation, implementation, and verification within one agent can still limit coverage as task requirements grow, motivating task-specific collaboration beyond a single execution process.

#### A.2.2 Multi-Agent Systems

Multi-agent systems improve task-solving effectiveness through specialization, interaction, and adaptive orchestration. Role-conditioned dialogue and configurable conversation patterns provide abstractions for cooperative problem solving (Li et al., 2023; Wu et al., 2024). Organization-inspired workflows further connect specialized stages through standardized outputs and communication protocols (Hong et al., 2024; Qian et al., 2024), while adaptive recruitment aligns expert teams with the current goal and evaluation feedback (Chen et al., 2024). Graph-based approaches make the collaboration structure itself a modeling target: GPTSwarm optimizes prompts and connectivity, G-Designer generates task-aware communication topologies, and MacNet orchestrates interactions over directed acyclic networks (Zhuge et al., 2024; Zhang et al., 2025b; Qian et al., 2025). Automated design extends this idea to searching executable workflows and sampling query-dependent architectures from an agentic supernet (Zhang et al., 2025c,a), allowing collaboration structures to be selected according to the problem. Despite advances in team and communication design, collaboration remains vulnerable to misaligned responsibilities and insufficiently verified handoffs (Cemri et al., 2025), motivating AutoSwarm’s explicit connection between contribution requirements and dependency-controlled execution.

### A.3 Additional Experimental Details

#### A.3.1 Collaboration Configurations

**Architectural comparisons.** We adapt the four architectures in Kim et al. (2025) to the shared Plancraft environment. Independent agents execute in parallel without member message exchange or

an LLM aggregator; their actions affect the common environment state. Decentralized uses three rounds of all-member discussion, followed by voting over final answer strings and submission by an existing member. Centralized uses one coordinator and three members with star-shaped communication. Hybrid follows the centralized procedure and adds one peer exchange after the initial member execution. These settings compare complete collaboration procedures, including their communication and result-submission policies.

**Mechanism variants.** The variant without CS replaces explicit deliverable requirements, supporting-evidence requirements, and acceptance conditions with ordinary goal descriptions. It retains the original team, goal assignments, dependencies, and execution process. Review remains active but proceeds without predefined contribution standards. The variant without SR retains contribution specifications and the other execution mechanisms; supervisors integrate submitted contributions without reviewing them first, eliminating rejection and corrective feedback from this assessment stage. Both variants use the same benchmark instructions and success criteria as the complete framework. Each configuration uses GPT-5.6-Luna with max reasoning effort and is evaluated in one complete run on all 117 problems.

### A.4 Collaboration Case Study (RQ5)

To examine how AutoSwarm’s mechanisms operate during execution, we inspect five selected paired trajectories: three Plancraft problems and two LongCLI-Bench tasks. Each pair compares AutoSwarm with a single agent using the same backbone and tools. The Plancraft examples come from the hint-free case-study run with a 30-step environment limit.

**Contribution coverage.** Explicit responsibility boundaries and output requirements make special-

ization useful to the shared objective. In the piston case, a recipe specialist supplied a complete material-conversion and assembly plan that the supervising agent used to reach the goal; the single agent confused crafting with smelting. In the DeepSeek-V4-Flash buffer-pool case, the single agent implemented the buffer core and page guards but left the required LRU-K replacer as an empty stub, indicating a gap in tracking completion across interrelated modules. AutoSwarm assigned the replacer, page guards, and buffer core to distinct owners, with their outputs independently tested during integration. These handoffs provided both reusable evidence and coverage of required functionality.

**Dependency-aware execution.** Separating information gathering from state modification made resource use follow established prerequisites. In the sticky-piston case, the single agent smelted the only log into charcoal and then incorrectly declared the goal infeasible. AutoSwarm’s recipe contribution established the plank prerequisite, and the supervising agent converted the log accordingly before assembly. The benefit arose in execution ordering: consuming prerequisite evidence before acting preserved a scarce input for the feasible plan.

**Verification and completion.** The MiniMax-M3 Scheme case shows how verification supports correction even when initial reasoning is flawed. The assigned specialist initially reproduced the single agent’s duplicate-binding error, but focused tests exposed it, prompting a repair that the supervising agent independently confirmed. The golden-chestplate case extends checking to the final environment state: the single agent stopped with the target in the crafting output slot, while AutoSwarm’s plan required collection into inventory before completion. Scoped testing, supervisory confirmation, and explicit completion requirements therefore addressed both implementation defects and premature termination.