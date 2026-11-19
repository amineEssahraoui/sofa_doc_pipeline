# NewtonRaphsonSolver - Technical Documentation

This document has been generated from supplied evidence. It has not undergone exhaustive factual verification.

## Table of Contents

- 1. Component Overview
- 2. Architecture and Inheritance
- 3. Mathematical Formulation
- 4. Internal Architecture and Execution
- 5. Data Fields and Links
- 6. Diagnostics and Usage

## 1. Component Overview

### Purpose and Role

NewtonRaphsonSolver is a SOFA component that provides a generic mechanism for solving nonlinear equations by means of the Newton‑Raphson iterative method. It belongs to the family of backward ODE solvers and is intended to be linked by higher‑level components that require the resolution of a nonlinear system, such as implicit time integrators or static equilibrium solvers. Within the SOFA architecture the solver receives the current estimate of the unknowns, computes the required Jacobian‑derived linear system, and returns an updated estimate, while exposing stop‑criteria that determine convergence or termination after a maximum number of iterations (SOFA documentation, introduction paragraphs). The component does not operate in isolation; it is a dependency for any module that formulates a nonlinear problem and delegates its solution to NewtonRaphsonSolver (SOFA documentation, “Usage” section).

### Numerical or Physical Problem

The primary mathematical problem addressed by NewtonRaphsonSolver is the root‑finding of a vector‑valued nonlinear function F mapping a k‑dimensional state to a k‑dimensional residual. In physical simulations this corresponds, for example, to enforcing static equilibrium where the sum of forces must vanish; the residual is the net force vector and the Jacobian of F is the stiffness matrix that relates incremental displacements to force variations (SOFA documentation, “Example” paragraph). More generally, any implicit integration scheme that formulates its step as F(x)=0 relies on this component to locate the state x that satisfies the governing equations. The difficulty lies in the nonlinearity of F, which prevents a closed‑form solution and necessitates an iterative approach that can handle high‑dimensional systems typical of deformable body simulations (Scientific Context, *Nonlinear1D.pdf* pp. 22‑24).

### General Approach

NewtonRaphsonSolver implements the classic Newton‑Raphson strategy: starting from an initial guess, it repeatedly linearizes the nonlinear function around the current estimate by evaluating its Jacobian, solves the resulting linear system for the correction, and updates the estimate. Each iteration therefore requires the computation of the derivative (or an approximation thereof) and the solution of a linear system whose matrix is the Jacobian (SOFA documentation, introduction paragraphs). The process continues until one of several convergence criteria is satisfied—such as a sufficiently small residual norm or a maximum iteration count—ensuring that the algorithm stops either when a root has been approximated to the desired tolerance or when further progress is unlikely. The method is known for its quadratic convergence when the initial guess is close to a simple root and the Jacobian is well‑conditioned, but it also demands the solution of a linear system at every step, which can be computationally intensive for large models (Scientific Context, *Nonlinear1D.pdf* pp. 22‑24). By encapsulating this algorithm, NewtonRaphsonSolver offers a reusable, framework‑integrated solution for a broad class of nonlinear problems encountered in interactive physical simulation.

## 2. Architecture and Inheritance

### Class Architecture

- **Namespace / Module**: `sofa::component::odesolver::backward` (the header `NewtonRaphsonSolver.h` is located in `Sofa/Component/ODESolver/Backward/src/sofa/component/odesolver/backward/`).  
- **Class Definition**: `class NewtonRaphsonSolver` is declared in *NewtonRaphsonSolver.h* at line 33 [F1].  
- **Template / Generic Parameters**: The class is **non‑templated**; it directly derives from a concrete base class.  
- **Integration in SOFA**: The component belongs to the **ODESolver → Backward** sub‑module and is intended to be used by higher‑level solvers (e.g., implicit ODE solvers or static solvers) that need a nonlinear equation solver, as described in the official component documentation [official‑doc:Usage].

### Inheritance Hierarchy

| Level | Class | Relationship | Source |
|-------|-------|--------------|--------|
| Direct base | `core::objectmodel::BaseObject` | Single public inheritance (`NewtonRaphsonSolver : public core::objectmodel::BaseObject`) | architecture.classes [F1:33]; parent_dependencies [F1 → BaseObject header] |
| Indirect bases | *Not documented in the supplied evidence* | No indirect base classes can be asserted because the implementation of `BaseObject` is not provided in the current data set. | – |

- **Polymorphism**: `NewtonRaphsonSolver` overrides the virtual methods `init()` and `reset()` declared in `BaseObject` (method signatures in *NewtonRaphsonSolver.h* lines 52‑53 [F1] and implementations in *NewtonRaphsonSolver.cpp* lines 116‑124 and 125‑131 [F2]). This confirms that the component participates in SOFA’s runtime object model through the `BaseObject` interface.

### Inherited and Local Responsibilities

| Responsibility | Origin | Description | Evidence |
|----------------|--------|-------------|----------|
| **Object lifecycle (init / reset)** | Inherited (override) | Called by the SOFA framework to initialise or reset the component state. | `init()` and `reset()` signatures [F1:52‑53]; implementations [F2:116‑131] |
| **Non‑linear solve** | Local | `solve(newton_raphson::BaseNonLinearFunction& function)` performs the Newton‑Raphson iteration on a user‑provided nonlinear function. | Declaration [F1:59]; implementation [F2:202‑400] |
| **Iteration control** | Local | `start()` begins a solving session; `initialConvergence(...)` evaluates the first‑iteration convergence criteria; `measureConvergence(...)` evaluates generic convergence measures; `lineSearchIteration(...)` implements the optional line‑search step. | Declarations [F1:64,66,67,69]; implementations [F2:402‑408,133‑141,143‑171,173‑185] |
| **Data attributes** | Local | Parameters such as `d_maxNbIterationsNewton`, `d_relativeSuccessiveStoppingThreshold`, `d_absoluteResidualStoppingThreshold`, etc., configure iteration limits and stopping criteria. | Structured attributes list, e.g., `d_maxNbIterationsNewton` [F1:38], `d_relativeSuccessiveStoppingThreshold` [F1:39], … |
| **Status reporting** | Local | `d_status` (type `Data<NewtonStatus>`) and residual graph (`d_residualGraph`) expose runtime information to the scene graph. | Structured attributes [F1:47‑48] |
| **Event handling flag** | Inherited (direct) | `f_listening` (from `BaseObject`) determines whether the component processes SOFA events. | Structured attribute `f_listening` [F3:159] |

No other inherited interfaces are observable from the supplied evidence.

### Architectural Dependencies

- **Header‑level includes** (compile‑time dependencies)  
  - From *NewtonRaphsonSolver.h*: `NewtonStatus.h`, `NonLinearFunction.h`, `config.h`, `NewtonRaphsonConvergenceMeasure.h`, `BaseObject.h`, `helper/map.h` [F1 includes].  
  - From *NewtonRaphsonSolver.cpp*: `NewtonRaphsonSolver.h`, various convergence‑measure headers (`AbsoluteConvergenceMeasure.h`, `RelativeEstimateDifferenceMeasure.h`, …), `ScopedAdvancedTimer.h`, `ObjectFactory.h` [F2 includes].

- **Runtime component interactions**  
  - Relies on the **non‑linear function interface** (`newton_raphson::BaseNonLinearFunction`) to evaluate the residual and Jacobian during each Newton step.  
  - Uses **convergence measure objects** (`NewtonRaphsonConvergenceMeasure` and its concrete subclasses) to decide when to stop iterating.  
  - May employ **line‑search** logic (static method `lineSearchIteration`) when the basic Newton step does not produce sufficient decrease.  
  - Communicates status and residual history through the `d_status` and `d_residualGraph` data fields, which can be inspected by other components or the GUI.

- **Scene‑graph relationship**  
  - As a subclass of `BaseObject`, the solver is a **SOFA object** that can be attached to a node in the scene graph. Other components (e.g., implicit ODE solvers, static solvers) link to it via XML or programmatic connections, as indicated in the official documentation [official‑doc:Usage].

- **Factory registration**  
  - The source file includes `sofa/core/ObjectFactory.h`, implying that `NewtonRaphsonSolver` is registered with SOFA’s object factory for dynamic creation from scene files.  

These dependencies define the modular placement of `NewtonRaphsonSolver` within the SOFA architecture: it is a leaf component that provides a Newton‑Raphson nonlinear solver service to higher‑level simulation algorithms while adhering to the generic `BaseObject` lifecycle and data‑exposure mechanisms.

**Local source references for this section**

- `F1`: `Sofa/Component/ODESolver/Backward/src/sofa/component/odesolver/backward/NewtonRaphsonSolver.h`
- `F2`: `Sofa/Component/ODESolver/Backward/src/sofa/component/odesolver/backward/NewtonRaphsonSolver.cpp`
- `F3`: `Sofa/framework/Core/src/sofa/core/objectmodel/BaseObject.h`

## 3. Mathematical Formulation

### Mathematical Problem

The **NewtonRaphsonSolver** component solves a system of nonlinear equations  

\[
F(x)=0 ,\qquad F:\mathbb{R}^{k}\rightarrow\mathbb{R}^{k},
\]

by iteratively refining an estimate of the root \(x\in\mathbb{R}^{k}\).  
The unknown vector \(x\) (the *state*) and the residual vector \(F(x)\) are supplied by a user‑defined function that implements the interface `newton_raphson::BaseNonLinearFunction` (see method `solve` in *NewtonRaphsonSolver.cpp*).  

### Mathematical Formulation

At iteration \(n\) the solver forms the Jacobian matrix  

\[
\nabla_F(x_n)=\frac{\partial F}{\partial x}\bigg|_{x=x_n}\in\mathbb{R}^{k\times k},
\]

and solves the linear system  

\[
\nabla_F(x_n)\,\bigl(x_{n+1}-x_n\bigr) = -F(x_n) \tag{1}
\]

as documented in the official SOFA description【introduction, equation】.  
Denoting the solution of (1) by \(\Delta x\),

\[
\Delta x = x_{n+1}-x_n,
\]

the new approximation is obtained by the update  

\[
x_{n+1}=x_n+\Delta x . \tag{2}
\]

The iteration stops when one (or more) of the following convergence criteria, all exposed as component data, is satisfied:

| Data attribute | Symbol in the formulation | Meaning |
|----------------|---------------------------|---------|
| `relativeSuccessiveStoppingThreshold` | \(\displaystyle \frac{\|F(x_n)\|}{\|F(x_{n-1})\|}\) | Ratio of successive residual norms |
| `relativeInitialStoppingThreshold`   | \(\displaystyle \frac{\|F(x_n)\|}{\|F(x_0)\|}\) | Ratio of current to initial residual norm |
| `absoluteResidualStoppingThreshold` | \(\|F(x_n)\|\) | Absolute residual norm |
| `relativeEstimateDifferenceThreshold`| \(\displaystyle \frac{\|x_n-x_{n-1}\|}{\|x_{n-1}\|}\) | Relative change of the estimate |
| `absoluteEstimateDifferenceThreshold`| \(\|x_n-x_{n-1}\|\) | Absolute change of the estimate |

The maximum number of Newton iterations is limited by the data attribute `maxNbIterationsNewton` (default = 1)【F1, line 38】.  

If the Newton step does not produce a sufficient decrease, an optional line‑search is performed. The line‑search repeats the update with a scaled step length \(\alpha\) (the *lineSearchCoefficient*, default = 0.5) up to `maxNbIterationsLineSearch` times【F1, lines 44‑45】.

### Numerical Algorithm

The algorithm, as described in the component documentation, proceeds as follows:

1. **Initialisation** – `init()` prepares internal state (no algorithmic detail is exposed).  
2. **Start** – `start()` resets iteration counters.  
3. **Iteration** (repeated until convergence or the iteration limit):
   * Evaluate the residual \(F(x_n)\) and, if required, the Jacobian \(\nabla_F(x_n)\) via the supplied `BaseNonLinearFunction`.  
   * Solve the linear system (1) for \(\Delta x\).  
   * Compute a tentative new state \(x_{n+1}=x_n+\Delta x\).  
   * If a line‑search is enabled, call the static method `lineSearchIteration` which scales \(\Delta x\) by the coefficient `lineSearchCoefficient` and recomputes the residual norm, repeating up to `maxNbIterationsLineSearch` times【method_links → lineSearchIteration】.  
   * Evaluate the convergence measures using `measureConvergence`; the method returns `true` when any of the thresholds defined by the data attributes listed above is met【method_links → measureConvergence】.  
   * If convergence is not reached, continue with the next Newton iteration.  
4. **Finalisation** – the solver status (`status`) records whether the process converged, diverged, or stopped because of the iteration limit【F1, line 47】.

The component also provides the option `updateStateWhenDiverged` (default = true) to decide whether the last computed state is kept even if divergence is detected【F1, line 46】, and warning flags `warnWhenLineSearchFails` and `warnWhenDiverge` to emit diagnostic messages【F1, lines 49‑50】.

All steps above are directly documented in the official SOFA component description and reflected in the public C++ interface (methods `init`, `reset`, `solve`, `start`, `initialConvergence`, `measureConvergence`, `lineSearchIteration`). No additional internal algorithmic details are inferred beyond the documented formulation.

**Local source references for this section**

- `F1`: `Sofa/Component/ODESolver/Backward/src/sofa/component/odesolver/backward/NewtonRaphsonSolver.h`
- `F2`: `Sofa/Component/ODESolver/Backward/src/sofa/component/odesolver/backward/NewtonRaphsonSolver.cpp`
- `F3`: `Sofa/framework/Core/src/sofa/core/objectmodel/BaseObject.h`

## 4. Internal Architecture and Execution

### Internal Responsibilities
NewtonRaphsonSolver is a `core::objectmodel::BaseObject`‑derived component that encapsulates the Newton‑Raphson algorithm for solving nonlinear systems. Its primary responsibilities are implemented in the following methods (declarations in F2, implementations in F1):

* **init()** – Calls the parent initializer (`Inherit1::init()`) and marks the component state as Valid when appropriate [F1:116‑124].
* **reset()** – Restores the solver status to the default value and clears the residual graph [F1:125‑131].
* **solve(BaseNonLinearFunction&)** – Orchestrates the full solution process: checks component validity, initializes the algorithm, evaluates the initial residual, drives the Newton iteration loop, performs line‑search, measures convergence with several criteria, updates the status, and records timing information [F1:202‑400].
* **start()** – Sets the internal status to “Running” at the beginning of a solve [F1:402‑408].
* **initialConvergence(...)** – Handles the special case where the initial guess already satisfies the absolute residual threshold, setting the status to “ConvergedEquilibrium” [F1:133‑141].
* **measureConvergence(const NewtonRaphsonConvergenceMeasure&, std::stringstream&)** – Evaluates a single convergence measure, updates the status on success, and formats diagnostic messages [F1:143‑171].
* **lineSearchIteration(BaseNonLinearFunction&, SReal&, SReal)** – Applies a line‑search step: updates the guess, re‑evaluates the residual, and stores the new squared residual norm [F1:173‑185].

Internal state is represented by a set of data attributes defined in F2, e.g.:

* `d_maxNbIterationsNewton` – maximum Newton iterations (default 1) [F2:38].
* `d_relativeSuccessiveStoppingThreshold`, `d_relativeInitialStoppingThreshold`, `d_absoluteResidualStoppingThreshold` – stopping criteria thresholds [F2:39‑41].
* `d_maxNbIterationsLineSearch`, `d_lineSearchCoefficient` – line‑search control [F2:44‑45].
* `d_status` – current solver status (read‑only) [F2:47].
* `d_residualGraph` – graph storing residual values per iteration [F2:48].
* Warning flags `d_warnWhenLineSearchFails`, `d_warnWhenDiverge` [F2:49‑50].

The constructor initializes these attributes, assigns them to UI groups, and configures the residual graph widget [F1:43‑93].

---

### Execution Workflow
The solver execution follows a deterministic sequence:

1. **Component Initialization** – `init()` is called during the scene loading phase, invoking the parent initializer and setting the component state to Valid [F1:116‑124].

2. **Reset (optional)** – `reset()` can be invoked to clear previous results, resetting `d_status` to the default and emptying `d_residualGraph` [F1:125‑131].

3. **Solve Entry** – `solve(function)` is invoked with a concrete `newton_raphson::BaseNonLinearFunction` implementation.
   * Validity check aborts early if the component state is not Valid [F1:202‑206].
   * `start()` sets `d_status` to “Running” [F1:402‑408].

4. **Initial Residual Evaluation**
   * `function.evaluateCurrentGuess()` computes the residual at the initial guess.
   * `function.squaredNormLastEvaluation()` yields `squaredResidualNorm`.
   * The value is stored in `d_residualGraph["residual"]` [F1:215‑227].

5. **Absolute‑Residual Early Exit**
   * If `d_absoluteResidualStoppingThreshold` > 0 and the initial residual is below the squared threshold, `initialConvergence()` is called, setting status to “ConvergedEquilibrium” [F1:229‑236].

6. **Iteration Setup**
   * Convergence‑measure objects are instantiated (relative successive, relative initial, absolute, estimate‑difference) with thresholds taken from the corresponding data attributes [F1:242‑255].
   * Loop counters and limits are read: `maxNbIterationsNewton`, `maxNbIterationsLineSearch` (forced ≥ 1) [F1:260‑263].

7. **Newton Iteration Loop** (`for` over `newtonIterationCount < maxNbIterationsNewton`)
   * **Gradient & Linear Solve** – `function.computeGradientFromCurrentGuess()` and `function.solveLinearEquation()` compute the Newton step [F1:285‑288].
   * **Line Search** – An inner loop iterates up to `maxNbIterationsLineSearch`, calling `lineSearchIteration()` each time and checking whether the new residual decreased (`squaredResidualNorm < previousSquaredResidualNorm`). The step size `lineSearchAlpha` is scaled by `d_lineSearchCoefficient` on failure [F1:291‑311].
   * If line search fails, a warning may be emitted (`d_warnWhenLineSearchFails`) and status set to “DivergedLineSearch”. A fallback evaluation with `alpha = 1` is performed when more than one line‑search iteration is allowed [F1:313‑327].
   * **Residual Logging** – The new residual is appended to the graph [F1:329‑331].
   * **Convergence Checks** – Each convergence measure is updated with the latest residual (and, when applicable, estimate differences) and passed to `measureConvergence()`. On the first measure reporting convergence, `hasConverged` is set and the outer loop breaks [F1:352‑384].
   * **Iteration Reporting** – If `f_printLog` is enabled, detailed iteration information is assembled in `iterationResults` and emitted via `msg_info()` [F1:336‑350].

8. **Post‑Loop Handling**
   * If no measure reported convergence, a warning (controlled by `d_warnWhenDiverge`) is emitted and status set to “DivergedMaxIterations” [F1:386‑393].

9. **Timing & Output**
   * Advanced timers record the number of iterations and final residual magnitude [F1:395‑400].

---

### Delegation and Component Interactions
* **Inheritance** – `NewtonRaphsonSolver` inherits from `core::objectmodel::BaseObject`; the call `Inherit1::init()` in `init()` delegates to the base class initializer [F1:116‑118].
* **External Function Interface** – All algorithmic operations are performed through the abstract `newton_raphson::BaseNonLinearFunction` passed to `solve()`. The solver invokes:
  * `evaluateCurrentGuess()`,
  * `squaredNormLastEvaluation()`,
  * `computeGradientFromCurrentGuess()`,
  * `solveLinearEquation()`,
  * `updateGuessFromLinearSolution(alpha)`,
  * `squaredNormDx()` (estimate‑difference) [F1:215‑227, 285‑288, 291‑295, 311‑313, 357‑359].
* **Convergence Measure Classes** – Instances of `RelativeSuccessiveConvergenceMeasure`, `RelativeInitialConvergenceMeasure`, `AbsoluteConvergenceMeasure`, `AbsoluteEstimateDifferenceMeasure`, and `RelativeEstimateDifferenceMeasure` are created locally in `solve()` and queried via their `isMeasured()`, `hasConverged()`, and `status()` methods. The solver does not own these classes; they are delegated utilities.
* **Graph Access** – `sofa::helper::getWriteAccessor(d_residualGraph)` provides mutable access to the residual graph data structure, which is part of the SOFA data‑field system [F1:219‑221].
* **Logging & Timing** – `msg_info()`, `msg_warning_when()`, and `SCOPED_TIMER` macros delegate to SOFA’s messaging and profiling subsystems. `AdvancedTimer::valSet` records final metrics [F1:395‑400].
* **RAII Helper** – `NewtonIterationRAII newtonIteration(function);` creates a scoped helper that likely manages temporary state of the `function` (implementation not shown), demonstrating delegated resource management.

---

### Execution Modes and Specific Behavior
The solver exhibits several conditional execution paths controlled by its data attributes:

* **Absolute‑Residual Early Exit** – Triggered when `d_absoluteResidualStoppingThreshold > 0` and the initial residual satisfies the threshold [F1:229‑236].
* **Line Search Activation** – Controlled by `d_maxNbIterationsLineSearch` (minimum 1) and `d_lineSearchCoefficient`. If the residual does not decrease after a line‑search step, the algorithm retries with a reduced step size (`lineSearchAlpha *= lineSearchCoefficient`). Failure after the configured number of attempts leads to status “DivergedLineSearch” and optional warning (`d_warnWhenLineSearchFails`) [F1:291‑327].
* **Convergence Criteria Selection** – Each measure is evaluated only if its corresponding threshold is non‑zero (e.g., `relativeEstimateDifferenceMeasure.isMeasured()`). Measures that are not enabled produce a “NOT TESTED” entry in the log when `notMuted()` is true [F1:143‑171].
* **Warning Flags** – `d_warnWhenLineSearchFails` and `d_warnWhenDiverge` gate the emission of warning messages for line‑search failure and overall non‑convergence, respectively [F1:313‑317, 386‑389].
* **Status Updates** – The solver status (`d_status`) is set to distinct `NewtonStatus` values depending on the outcome:
  * “Running” at start,
  * “ConvergedEquilibrium” for initial convergence,
  * Specific convergence statuses returned by each measure,
  * “DivergedLineSearch” on line‑search failure,
  * “DivergedMaxIterations” when the maximum Newton iterations are exhausted [F1:133‑141, 313‑317, 386‑393].
* **No Template Specializations** – The provided source contains a single concrete class; there are no overloads or template specializations influencing execution flow.

All described behaviors are directly observable in the source implementation lines cited above.

**Local source references for this section**

- `F1`: `Sofa/Component/ODESolver/Backward/src/sofa/component/odesolver/backward/NewtonRaphsonSolver.cpp`
- `F2`: `Sofa/Component/ODESolver/Backward/src/sofa/component/odesolver/backward/NewtonRaphsonSolver.h`

## 5. Data Fields and Links

### Local Data Fields

| C++ attribute | Exposed SOFA name | C++ data type | Default value / expression | Functional description | Declaration & initialization references |
|---|---|---|---|---|---|
| `d_maxNbIterationsNewton` | `maxNbIterationsNewton` | `Data<unsigned int>` | `1u` | Maximum number of iterations of the Newton's method if it has not converged. | Declared in **F1** line 38; default reused in constructor **F4** line 44. |
| `d_relativeSuccessiveStoppingThreshold` | `relativeSuccessiveStoppingThreshold` | `Data<SReal>` | `1e-5_sreal` | Threshold for the relative successive progress criterion. The Newton iterations stop when the ratio between the norm of the residual at iteration *k* over the norm at iteration *k‑1* is lower than this threshold. | Declared in **F1** line 39; reused in constructor **F4** line 47. |
| `d_relativeInitialStoppingThreshold` | `relativeInitialStoppingThreshold` | `Data<SReal>` | `1e-5_sreal` | Threshold for the relative initial progress criterion. The Newton iterations stop when the ratio between the norm of the residual at iteration *k* over the norm at iteration 0 is lower than this threshold. | Declared in **F1** line 40; reused in constructor **F4** line 53. |
| `d_absoluteResidualStoppingThreshold` | `absoluteResidualStoppingThreshold` | `Data<SReal>` | `1e-5_sreal` | Threshold for the absolute function‑value stopping criterion. The Newton iterations stop when the norm of the residual at iteration *k* is lower than this threshold. | Declared in **F1** line 41; reused in constructor **F4** line 63. |
| `d_relativeEstimateDifferenceThreshold` | `relativeEstimateDifferenceThreshold` | `Data<SReal>` | `0_sreal` | Threshold for the relative change in root‑estimate criterion. The Newton iterations stop when the difference between two successive estimates divided by the previous estimate is smaller than this threshold. | Declared in **F1** line 42; reused in constructor **F4** line 69. |
| `d_absoluteEstimateDifferenceThreshold` | `absoluteEstimateDifferenceThreshold` | `Data<SReal>` | `0_sreal` | Threshold for the absolute change in root‑estimate criterion. The Newton iterations stop when the difference between two successive estimates is smaller than this threshold. | Declared in **F1** line 43; reused in constructor **F4** line 74. |
| `d_maxNbIterationsLineSearch` | `maxNbIterationsLineSearch` | `Data<unsigned int>` | `1u` | Maximum number of iterations of the line search method if it has not converged. | Declared in **F1** line 44; reused in constructor **F4** line 79. |
| `d_lineSearchCoefficient` | `lineSearchCoefficient` | `Data<SReal>` | `0.5_sreal` | Line search coefficient. | Declared in **F1** line 45; reused in constructor **F4** line 82. |
| `d_updateStateWhenDiverged` | `updateStateWhenDiverged` | `Data<bool>` | `true` | Update the states within the last iteration even if the iterative process is considered diverged. | Declared in **F1** line 46; reused in constructor **F4** line 84. |
| `d_status` | `status` | `Data<NewtonStatus>` | `defaultStatus` | Provides the solver status (exposes `NewtonStatus::dataDescription()`). | Declared in **F1** line 47; reused in constructor **F4** line 88. |
| `d_residualGraph` | `residualGraph` | `Data<std::map<std::string, sofa::type::vector<SReal>>>` | *Not specified* | Graph of the residual over the iterations. | Declared in **F1** line 48; reused in constructor **F4** line 90. |
| `d_warnWhenLineSearchFails` | `warnWhenLineSearchFails` | `Data<bool>` | `true` | Trigger a warning if line search fails. | Declared in **F1** line 49; reused in constructor **F4** line 92. |
| `d_warnWhenDiverge` | `warnWhenDiverge` | `Data<bool>` | `true` | Trigger a warning if Newton‑Raphson diverges. | Declared in **F1** line 50; reused in constructor **F4** line 93. |

### Inherited Data Fields

| C++ attribute | Exposed SOFA name | Owner class | C++ data type | Default value / expression | Functional description | Declaration & initialization references |
|---|---|---|---|---|---|---|
| `f_listening` | `listening` | `core::objectmodel::BaseObject` | `Data<bool>` | `false` | If true, handle the events; otherwise ignore the events. | Declared in **F2** line 159; initialized in **F3** line 37 (constructor body). |

#### Documentation‑Only Data Fields
*No documentation‑only data fields are present for this component.*

### Links and Component References
*No Link fields are defined for `NewtonRaphsonSolver` in the available evidence.*

### Configuration Constraints and Interactions

| Aspect | Details |
|---|---|
| **Read‑only fields** | `d_status` is set to read‑only in the constructor (`d_status.setReadOnly(true);`) – source **F4** line 43. |
| **Constructor‑time UI grouping** | The constructor assigns UI groups: <br>• `Analysis` group for `d_status` and `d_residualGraph`.<br>• `Line Search` group for `d_maxNbIterationsLineSearch` and `d_lineSearchCoefficient`.<br>• `Stopping criteria` group for all stopping‑criterion fields (`d_maxNbIterationsNewton`, `d_relativeSuccessiveStoppingThreshold`, `d_relativeInitialStoppingThreshold`, `d_absoluteResidualStoppingThreshold`, `d_relativeEstimateDifferenceThreshold`, `d_absoluteEstimateDifferenceThreshold`). – source **F4** line 43‑57. |
| **Widget assignment** | `d_residualGraph` is assigned the widget `"graph"` (`d_residualGraph.setWidget("graph");`) – source **F4** line 58. |
| **Required‑field indicators** | No fields are marked as required in the available evidence. |
| **Deprecated parameters** | No deprecated fields are listed in the evidence. |
| **Discrepancies** | The default expressions listed in the structured attributes match the values set/reused in the constructor; no contradictions are observed. |
| **Missing evidence** | The official documentation sections for data fields and links are empty; therefore no additional documentation‑only entries can be provided. |

**Local source references for this section**

- `F1`: `Sofa/Component/ODESolver/Backward/src/sofa/component/odesolver/backward/NewtonRaphsonSolver.h`
- `F2`: `Sofa/framework/Core/src/sofa/core/objectmodel/BaseObject.h`
- `F3`: `Sofa/framework/Core/src/sofa/core/objectmodel/BaseObject.cpp`
- `F4`: `Sofa/Component/ODESolver/Backward/src/sofa/component/odesolver/backward/NewtonRaphsonSolver.cpp`

## 6. Diagnostics and Usage

### Practical Usage and Integration
`NewtonRaphsonSolver` is a non‑linear equation solver that must be linked by another component that requires solving a non‑linear system (e.g., an implicit ODE solver or a static solver) 【usage_documentation:Usage】.  
In XML scenes the component is instantiated and referenced by the solver that will use it, as shown in the documented example 【usage_example】:

```xml
<NewtonRaphsonSolver name="newton"
                     maxNbIterationsNewton="10" absoluteResidualStoppingThreshold="1e-5"
                     maxNbIterationsLineSearch="5" lineSearchCoefficient="0.5"
                     relativeInitialStoppingThreshold="1e-3"
                     absoluteEstimateDifferenceThreshold="1e-5"
                     relativeEstimateDifferenceThreshold="1e-5"/>
<BDFOdeSolver newtonSolver="@newton" order="2" rayleighMass="0.01" rayleighStiffness="0.01" />
```

The solver inherits from `core::objectmodel::BaseObject` 【integration_constraints】 and therefore participates in the standard SOFA component lifecycle (init, reinit, etc.).

### Configuration Guidelines
Key configurable fields are defined in `NewtonRaphsonSolver.h` (F2). Highlights:

| Field | Type | Default | Remarks |
|-------|------|---------|---------|
| `maxNbIterationsNewton` | `Data<unsigned int>` | `1u` | Maximum Newton iterations 【configuration:0】 |
| `maxNbIterationsLineSearch` | `Data<unsigned int>` | `1u` | Maximum line‑search iterations 【configuration:7】 |
| `lineSearchCoefficient` | `Data<SReal>` | `0.5` | Multiplicative factor for line‑search step size 【configuration:8】 |
| `absoluteResidualStoppingThreshold` | `Data<SReal>` | `1e-5` | Absolute residual norm criterion 【configuration:3】 |
| `relativeSuccessiveStoppingThreshold` | `Data<SReal>` | `1e-5` | Relative successive‑ratio criterion 【configuration:1】 |
| `relativeInitialStoppingThreshold` | `Data<SReal>` | `1e-5` | Relative initial‑ratio criterion 【configuration:2】 |
| `relativeEstimateDifferenceThreshold` | `Data<SReal>` | `0` | Relative change in estimate criterion 【configuration:5】 |
| `absoluteEstimateDifferenceThreshold` | `Data<SReal>` | `0` | Absolute change in estimate criterion 【configuration:6】 |
| `warnWhenLineSearchFails` | `Data<bool>` | `true` | Emit a warning if line search fails 【configuration:9】 |
| `warnWhenDiverge` | `Data<bool>` | `true` | Emit a warning if the Newton iteration diverges 【configuration:10】 |
| `status` | `Data<NewtonStatus>` | `defaultStatus` | **Read‑only** (set in constructor) 【configuration_constraints】 |
| `updateStateWhenDiverged` | `Data<bool>` | `true` | Update states even when divergence is detected 【configuration:11】 |

`status` is marked read‑only in the constructor (`d_status.setReadOnly(true)`) 【configuration_constraints】. No fields are documented as deprecated.

### Diagnostics and Troubleshooting
The solver emits diagnostics at several points (see `solve` implementation 【diagnostic_implementations:solve】):

| Condition | Diagnostic emitted | Resulting behavior |
|-----------|-------------------|--------------------|
| Component state invalid (`isComponentStateValid() == false`) | No message; early return | Solver does nothing. |
| Initial residual ≤ absolute threshold | `msg_info()` with “The equation to solve is satisfied …” (via `initialConvergence`) 【diagnostic_implementations:initialConvergence】 | `status` set to `ConvergedEquilibrium`; iteration loop is skipped. |
| Line‑search fails after `maxNbIterationsLineSearch` attempts | `msg_warning_when(d_warnWhenLineSearchFails)` → “Line search failed at Newton iteration …” 【diagnostic_implementations:solve】 | `status` set to `DivergedLineSearch`; if `maxNbIterationsLineSearch > 1` a final line‑search step with α = 1 is performed. |
| Newton iteration does not converge after `maxNbIterationsNewton` | `msg_warning_when(d_warnWhenDiverge)` → “Newton‑Raphson method failed to converge …” 【diagnostic_implementations:solve】 | `status` set to `DivergedMaxIterations`. |
| Any convergence measure (`measureConvergence`) reports success | `msg_info()` with “[CONVERGED] …” and `status` set to the corresponding `NewtonStatus` 【diagnostic_implementations:measureConvergence】 | Solver exits the iteration loop with `hasConverged = true`. |
| Convergence measure not applicable (`!measure.isMeasured()`) and component not muted | `os << “… NOT TESTED”` (internal string, not logged) | No diagnostic emitted; the measure is simply ignored. |

All warnings are controlled by the boolean fields `warnWhenLineSearchFails` and `warnWhenDiverge`. Setting them to `false` suppresses the corresponding messages but does not change the underlying status.

### Limitations and Recommendations
* **Iteration limits** – The solver stops after `maxNbIterationsNewton` Newton steps or `maxNbIterationsLineSearch` line‑search steps. Users should choose values large enough for the expected non‑linearity but aware that excessive limits increase compute time.  
* **Threshold positivity** – The initial‑convergence shortcut is only taken when `absoluteResidualStoppingThreshold > 0` 【diagnostic_implementations:solve】. A non‑positive threshold disables this early‑exit path.  
* **Line‑search fallback** – If line search fails and `maxNbIterationsLineSearch > 1`, a final attempt with step size = 1 is forced; this may still leave the solver in a diverged state.  
* **Read‑only status** – The `status` field cannot be set by the user; it reflects the solver’s internal outcome. Monitoring `status` is the recommended way to detect convergence or divergence.  
* **Numerical preconditions** – Convergence depends on the quality of the Jacobian (`function.computeGradientFromCurrentGuess()`) and the linear solve (`function.solveLinearEquation()`). Poorly conditioned systems may trigger divergence warnings even with generous thresholds.  

**Recommendation:** Enable both warning flags (`warnWhenLineSearchFails` and `warnWhenDiverge`) to obtain immediate feedback, and tune the absolute/relative thresholds based on the scale of the residuals in the specific simulation. Adjust `maxNbIterationsNewton` and `maxNbIterationsLineSearch` only after profiling typical convergence behavior.

**Local source references for this section**

- `F1`: `Sofa/Component/ODESolver/Backward/src/sofa/component/odesolver/backward/NewtonRaphsonSolver.cpp`
- `F2`: `Sofa/Component/ODESolver/Backward/src/sofa/component/odesolver/backward/NewtonRaphsonSolver.h`
- `F3`: `Sofa/framework/Core/src/sofa/core/objectmodel/BaseObject.h`
- `F4`: `Sofa/framework/Core/src/sofa/core/objectmodel/BaseObject.cpp`
