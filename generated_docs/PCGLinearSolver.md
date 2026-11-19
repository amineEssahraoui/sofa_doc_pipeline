# PCGLinearSolver - Technical Documentation

This document has been generated from supplied evidence. It has not undergone exhaustive factual verification.

**Incomplete generation. Missing or rejected sections:** 3. Mathematical Formulation.

## Table of Contents

- 1. Component Overview
- 2. Architecture and Inheritance
- 4. Internal Architecture and Execution
- 3. Mathematical Formulation
- 5. Data Fields and Links
- 6. Diagnostics and Usage

## 1. Component Overview

### Purpose and Role

The PCGLinearSolver is a linear‑solver component that applies the preconditioned conjugate‑gradient (PCG) iterative algorithm to resolve systems of linear equations arising in simulation pipelines. It belongs to the iterative linear‑solver family within the SOFA framework and is located in the sofa::component::linearsolver::iterative namespace 【SOFA Evidence: official_documentation → introduction】. As a component, it is intended to be connected to other simulation objects that provide the matrix‑vector product and optional preconditioner, thereby serving as the computational engine that supplies the solution vector needed by implicit integration schemes or static equilibrium calculations 【SOFA Evidence: official_documentation → sections → GraphScattered】.

### Numerical or Physical Problem

In many SOFA simulations, implicit time integration or static analysis leads to linear systems of the form A δ = b, where A encodes mass, damping, and stiffness contributions of the mechanical model and b represents external forces or constraint terms. Solving these systems efficiently is essential for stability when dealing with stiff forces, large time steps, or complex constraint projections. The PCGLinearSolver addresses this need by providing a method capable of handling large, sparse, symmetric‑positive‑definite matrices that commonly arise from discretized continuum mechanics formulations 【Scientific Context: faure_springer12.pdf, pp. 17‑18】.

### General Approach

The component implements the classic conjugate‑gradient method, an iterative technique that builds a sequence of search directions conjugate with respect to the system matrix, thereby minimizing the quadratic error functional without explicitly forming the matrix. By incorporating a preconditioner—typically a matrix that approximates A and is inexpensive to invert—the algorithm accelerates convergence, especially for ill‑conditioned problems. Within SOFA, the matrix‑vector products required by the CG iterations are obtained through visitor‑based traversals of the scene graph, allowing the solver to operate on the assembled stiffness representation without materializing the full matrix 【Scientific Context: faure_springer12.pdf, pp. 17‑18】. The preconditioned variant follows the same conceptual steps but applies the preconditioner to the residual at each iteration, improving robustness for stiff or poorly scaled systems 【Scientific Context: painless-conjugate-gradient (1).pdf, pp. 54‑54】. This high‑level algorithmic strategy enables the PCGLinearSolver to provide a scalable, memory‑efficient solution mechanism for the linear systems that underpin implicit dynamics and static equilibrium in SOFA.

## 2. Architecture and Inheritance

### Class Architecture

- **Fully‑qualified name**: `sofa::component::linearsolver::iterative::PCGLinearSolver<TMatrix,TVector>`  
- **Namespace**: `sofa::component::linearsolver::iterative` (module *Sofa.Component.LinearSolver.Iterative*) – documented in the component’s official page【SOFA Evidence】(official_documentation.introduction).  
- **Template parameters**: `TMatrix` (matrix type) and `TVector` (vector type).  
- **Header**: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/PCGLinearSolver.h` (class declared at line 37)【SOFA Evidence】(architecture.classes[0]).  
- **Implementation files**:  
  * `PCGLinearSolver.cpp` (runtime logic, includes the inlined implementation)【SOFA Evidence】(includes for F2).  
  * `PCGLinearSolver.inl` (template definitions, e.g., `solve`, `init`, etc.)【SOFA Evidence】(method_links).  

The class is a **template component** that conforms to SOFA’s component registration mechanism (via `ObjectFactory` in `PCGLinearSolver.cpp`), enabling it to be instantiated from a scene description.

### Inheritance Hierarchy

#### Direct base classes (as defined in the source)

| Base class | Header (resolved) | Relationship |
|------------|-------------------|--------------|
| `sofa::component::linearsolver::MatrixLinearSolver<TMatrix,TVector>` | `sofa/component/linearsolver/iterative/MatrixLinearSolver.h` | public inheritance (direct)【SOFA Evidence】(parent_dependencies entry 1) |
| `sofa::core::behavior::IterativeSolver` | `sofa/core/behavior/IterativeSolver.h` | public inheritance (direct)【SOFA Evidence】(parent_dependencies entry 2) |

These two parents are the **only** direct bases verified in the C++ source (line 37 of `PCGLinearSolver.h`). No additional indirect bases are inferred; any further ancestry would require explicit evidence, which is not present.

#### Indirect inheritance

- No indirect base classes are documented in the supplied evidence. Consequently, the hierarchy is limited to the two direct parents above.

### Inherited and Local Responsibilities

| Responsibility | Origin | Description (as reflected by the code) |
|----------------|--------|----------------------------------------|
| **Iterative control** (max iterations, tolerance, residual graph) | `IterativeSolver` (inherited) – data members `d_maxIter`, `d_tolerance`, `d_graph`【SOFA Evidence】(structured_attributes lines 45‑51, source F5) | Provides generic iterative‑solver parameters and event handling required by all iterative solvers. |
| **Matrix‑level handling** (parallel inverse product flag, factorization invalidation) | `MatrixLinearSolver` (inherited) – data members `d_parallelInverseProduct`, `d_factorizationInvalidation`【SOFA Evidence】(structured_attributes lines 247,336, source F4) | Supplies utilities for matrix‑specific optimizations and cache management common to matrix‑based solvers. |
| **Preconditioner usage flag** | `PCGLinearSolver` (local) – data member `d_use_precond`【SOFA Evidence】(structured_attributes line 53, source F1) | Enables or disables the preconditioner specific to the PCG algorithm. |
| **Core solver methods** (`solve`, `init`, `bwdInit`, `ensureRequiredLinearSystemType`, `handleEvent`, `checkLinearSystem`) | `PCGLinearSolver` (local overrides) – declared in `PCGLinearSolver.h` (lines 57‑81)【SOFA Evidence】(method_links) and defined in `PCGLinearSolver.inl` (various line ranges)【SOFA Evidence】(method_links) | Implements the preconditioned conjugate‑gradient algorithm, initialization, backward‑initialization, system‑type checking, event handling, and validation. These methods satisfy the pure‑virtual interface of `IterativeSolver` and/or `LinearSolver`. |
| **Algorithmic steps** (`cgstep_beta`, `cgstep_alpha`) | `PCGLinearSolver` (local inline helpers) – declared in `PCGLinearSolver.h` (lines 73, 77) and defined both in the header and the inl file【SOFA Evidence】(method_links) | Small inline utilities used internally by the PCG iteration. |

Thus, **local responsibilities** are the PCG‑specific algorithmic implementation and the preconditioner flag, while **inherited responsibilities** provide generic iterative‑solver configuration and matrix‑level utilities.

### Architectural Dependencies

| Dependency type | Source (header include) | Role in the component |
|-----------------|--------------------------|-----------------------|
| **IterativeSolver base** | `sofa/core/behavior/IterativeSolver.h` (included in `PCGLinearSolver.h`)【SOFA Evidence】(includes for F1) | Supplies the abstract iterative‑solver interface (`solve`, `init`, etc.). |
| **LinearSolver base** | `sofa/core/behavior/LinearSolver.h` (included in `PCGLinearSolver.h`)【SOFA Evidence】(includes for F1) | Provides the generic linear‑solver contract used by the framework. |
| **MatrixLinearSolver** | `sofa/component/linearsolver/iterative/MatrixLinearSolver.h` (included in `PCGLinearSolver.h`)【SOFA Evidence】(includes for F1) | Offers matrix‑specific helper functions and data members. |
| **Configuration macro** | `sofa/component/linearsolver/iterative/config.h` (included in `PCGLinearSolver.h`)【SOFA Evidence】(includes for F1) | Handles module‑level configuration (e.g., export macros). |
| **Helper utilities** | `sofa/helper/map.h`, `cmath` (both in `PCGLinearSolver.h` and `.inl`)【SOFA Evidence】(includes for F1, F3) | Provide standard containers and mathematical functions used by the implementation. |
| **ObjectFactory registration** | `sofa/core/ObjectFactory.h` (included in `PCGLinearSolver.cpp`)【SOFA Evidence】(includes for F2) | Registers the component with SOFA’s runtime factory, enabling scene‑graph creation. |
| **Matrix‑free system support** | `sofa/component/linearsystem/MatrixFreeSystem.h` (included in `PCGLinearSolver.cpp`)【SOFA Evidence】(includes for F2) | Allows the solver to operate on matrix‑free linear systems when required. |
| **Advanced timing utilities** | `sofa/helper/AdvancedTimer.h`, `sofa/helper/ScopedAdvancedTimer.h` (included in `PCGLinearSolver.inl`)【SOFA Evidence】(includes for F3) | Used for performance measurement of the solver steps. |
| **Event handling** | `sofa/simulation/events/AnimateBeginEvent.h` (included in `PCGLinearSolver.inl`)【SOFA Evidence】(includes for F3) | Enables the solver to react to simulation events (e.g., start of a new time step). |

These dependencies illustrate that **PCGLinearSolver** sits at the intersection of the generic iterative‑solver framework (`IterativeSolver`), matrix‑oriented utilities (`MatrixLinearSolver`), and the broader SOFA component registration and event system. Data flow follows the classic linear‑solver pattern: the `solve` method receives a system matrix `M`, a solution vector `x`, and a right‑hand side vector `b`, processes them using the PCG algorithm, and writes the result back into `x`. The component can be attached to any linear system that matches the required matrix and vector types, as enforced by `ensureRequiredLinearSystemType()`.

---  

*All statements are directly supported by the supplied SOFA source code and official component documentation.*

**Local source references for this section**

- `F1`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/PCGLinearSolver.h`
- `F2`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/PCGLinearSolver.cpp`
- `F3`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/PCGLinearSolver.inl`
- `F4`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/MatrixLinearSolver.h`
- `F5`: `Sofa/framework/Core/src/sofa/core/behavior/IterativeSolver.h`

## 3. Mathematical Formulation

### Mathematical Problem  

The **PCGLinearSolver** component solves a linear system  

$$
\mathbf{M}\,\mathbf{x}= \mathbf{b},
$$

where $\mathbf{M}$ is a symmetric positive‑definite (SPD) matrix, $\mathbf{x}$ the unknown vector, and $\mathbf{b}$ the right‑hand side.  The solver is intended for large, sparse systems that arise in SOFA simulations and therefore uses an iterative method rather than a direct factorisation 【SOFA Evidence: official documentation – introduction】.  

### Mathematical Formulation  

The preconditioned conjugate gradient (PCG) method seeks a sequence $\{\mathbf{x}_k\}$ that minimizes the quadratic functional  

$$
\Phi(\mathbf{x}) = \tfrac{1}{2}\mathbf{x}^{\!\top}\mathbf{M}\mathbf{x} - \mathbf{x}^{\!\top}\mathbf{b},
$$

subject to the SPD property of $\mathbf{M}$.  Introducing a preconditioner $\mathbf{P}\approx\mathbf{M}$ (typically SPD), the PCG iteration reads  

$$
\begin{aligned}
\mathbf{r}_0 &= \mathbf{b} - \mathbf{M}\mathbf{x}_0, \\
\mathbf{z}_0 &= \mathbf{P}^{-1}\mathbf{r}_0, \\
\mathbf{p}_0 &= \mathbf{z}_0, \\
\alpha_k &= \frac{\mathbf{r}_k^{\!\top}\mathbf{z}_k}{\mathbf{p}_k^{\!\top}\mathbf{M}\mathbf{p}_k}, \\
\mathbf{x}_{k+1} &= \mathbf{x}_k + \alpha_k \mathbf{p}_k, \\
\mathbf{r}_{k+1} &= \mathbf{r}_k - \alpha_k \mathbf{M}\mathbf{p}_k, \\
\mathbf{z}_{k+1} &= \mathbf{P}^{-1}\mathbf{r}_{k+1}, \\
\beta_k &= \frac{\mathbf{r}_{k+1}^{\!\top}\mathbf{z}_{k+1}}{\mathbf{r}_k^{\!\top}\mathbf{z}_k}, \\
\mathbf{p}_{k+1} &= \mathbf{z}_{k+1} + \beta_k \mathbf{p}_k .
\end{aligned}
$$

The iteration stops when either  

$$
\|\mathbf{r}_k\| \le \text{tolerance} \quad\text{or}\quad k \ge \text{maxIter},
$$

where *tolerance* and *maxIter* are user‑configurable parameters 【SOFA Evidence: structured_attributes – d_tolerance (line 48, F4)】 and 【SOFA Evidence: structured_attributes – d_maxIter (line 45, F4)】.  

The component provides a Boolean flag **use_precond** that enables or disables the preconditioning step 【SOFA Evidence: structured_attributes – d_use_precond (line 53, F1)】.  

#### Relation to the source code  

* The update of the search direction $\mathbf{p}$ with the scalar $\beta$ is performed by the inline method  

  ```cpp
  inline void cgstep_beta(Vector& p, Vector& r, Real beta);
  ```  

  declared in *PCGLinearSolver.h* (line 73, F1) and defined in the same file (lines 85‑89, F1) 【SOFA Evidence: method_links – cgstep_beta】.  

* The update of the solution vector $\mathbf{x}$ with the scalar $\alpha$ is performed by  

  ```cpp
  inline void cgstep_alpha(Vector& x, Vector& p, Real alpha);
  ```  

  declared (line 77, F1) and defined (lines 92‑95, F1) 【SOFA Evidence: method_links – cgstep_alpha】.  

These methods correspond directly to the $\alpha_k$ and $\beta_k$ formulas above.

### Numerical Algorithm  

The **PCGLinearSolver** implements the standard preconditioned conjugate gradient algorithm as described in the scientific literature on CG (e.g., Shewchuk’s “Painless Conjugate Gradient” 【Scientific Context: painless‑conjugate‑gradient (1).pdf, pp. 47‑48】).  The algorithm proceeds as follows:

1. **Initialisation** (`init()` – line 58, F1) creates the initial residual $\mathbf{r}_0$ and, if `use_precond` is true, applies the preconditioner $\mathbf{P}^{-1}$ to obtain $\mathbf{z}_0$.  
2. **Iteration loop** (`solve(Matrix& M, Vector& x, Vector& b)` – line 57, F1) repeats the PCG steps until the convergence criteria (tolerance or maxIter) are satisfied.  
3. **Direction update** uses `cgstep_beta` to compute $\beta_k$ and update the search direction $\mathbf{p}_{k+1}$.  
4. **Solution update** uses `cgstep_alpha` to compute $\alpha_k$ and update the solution $\mathbf{x}_{k+1}$.  
5. **Residual check** (`checkLinearSystem()` – line 81, F1) verifies that the linear system remains compatible with the solver’s requirements (SPD matrix, appropriate preconditioner).  

When `use_precond` is false, the preconditioning step is omitted, and the algorithm reduces to the classic conjugate gradient method.  The maximum number of iterations and the convergence tolerance are exposed as SOFA data fields `iterations` and `tolerance` 【SOFA Evidence: structured_attributes – d_maxIter, d_tolerance】, allowing the user to control the stopping criteria.  

All of the above steps are documented in the component’s official description (“Linear solver using the preconditioned conjugate gradient iterative algorithm”) 【SOFA Evidence: official documentation – introduction】 and are consistent with the standard PCG theory presented in the cited scientific reference.

## 4. Internal Architecture and Execution

### Internal Responsibilities
The `PCGLinearSolver` class provides a preconditioned conjugate gradient solver. Its key public methods are declared in **PCGLinearSolver.h** (F2) – `solve` [57], `init` [58], `bwdInit` [59], `ensureRequiredLinearSystemType` [69], `cgstep_beta` [73], `cgstep_alpha` [77], `handleEvent` [79] and `checkLinearSystem` [81].  
- **solve** performs the PCG iteration, managing temporary vectors (`r`, `w`, `s`), residual norms, and graph logging (implemented in **PCGLinearSolver.inl** F1 lines 174‑257).  
- **init** initializes the solver, validates the preconditioner link, and calls `ensureRequiredLinearSystemType` (F1 lines 50‑95).  
- **bwdInit** links the preconditioner’s linear system to the solver’s `PreconditionedMatrixFreeSystem` (F1 lines 116‑140).  
- **ensureRequiredLinearSystemType** checks that the attached linear system is a `PreconditionedMatrixFreeSystem` (F1 lines 98‑113).  
- **cgstep_alpha** and **cgstep_beta** implement the vector updates for the PCG algorithm; generic versions are in **PCGLinearSolver.h** (F2 lines 85‑95) and specialized versions for `GraphScatteredMatrix/Vector` are in **PCGLinearSolver.inl** (F1 lines 143‑152).  
- **handleEvent** resets the Newton iteration counter and clears the error graph at the start of a simulation step (F1 lines 155‑164).  
- **checkLinearSystem** ensures a `PreconditionedMatrixFreeSystem` is created when none is provided (F1 lines 167‑171).  

Internal state includes:
- `d_use_precond` (bool, default true) controlling preconditioner usage (F2 line 53).  
- Iteration limit `d_maxIter` and tolerance `d_tolerance` inherited from `IterativeSolver` (F3 lines 45, 48).  
- Graph data `d_graph` for error tracking (F3 line 51).  
- Runtime flags `first`, `newton_iter`, `next_refresh_step` initialized in the constructor (F1 lines 38‑43).  
- Link `l_preconditioner` to an external linear solver (F1 line 40).

### Execution Workflow
1. **Component initialization** – `init()` calls the base `MatrixLinearSolver` initializer, validates the preconditioner link, and invokes `ensureRequiredLinearSystemType` (F1 lines 50‑95). If the component state is valid, `first` is set true and the component state becomes `Valid`.  
2. **Backward initialization** – `bwdInit()` links the preconditioner’s linear system to the solver’s `PreconditionedMatrixFreeSystem` (F1 lines 116‑140).  
3. **Event handling** – At each `AnimateBeginEvent`, `handleEvent()` resets `newton_iter` and clears the error graph (F1 lines 155‑164).  
4. **Solve call** – `solve(M,x,b)` creates a temporary vector container (`vtmp`) and obtains three temporary vectors `r`, `w`, `s` (F1 lines 174‑257).  
   - Computes initial residual `r = b - M*x` using `cgstep_beta` (line 179‑182).  
   - If `d_use_precond` is true and a preconditioner is linked, applies the preconditioner to obtain `w` (lines 184‑191). Otherwise `w = r`.  
   - Computes residual norm `r_norm = r·w` and logs the normalized error in `d_graph` (lines 193‑197).  
5. **Iterative loop** – While `iter ≤ d_maxIter` and `r_norm > tol` (where `tol = d_tolerance * b·b`, lines 199‑200):  
   - Computes `s = M * w` and step size `alpha = r_norm / (w·s)` (lines 202‑205).  
   - Updates solution `x` and residual `r` via `cgstep_alpha` (lines 207‑210).  
   - Applies preconditioner to the new residual if enabled (lines 212‑219) or copies `r` to `s`.  
   - Updates `r_norm`, logs error, computes `beta = r_norm / deltaOld`, and updates search direction `w` via `cgstep_beta` (lines 221‑232).  
   - Increments `iter`.  
6. **Finalization** – Ends graph edit, releases temporary vectors, and records the iteration count (lines 234‑241).  

The loop terminates when the residual norm falls below the tolerance or the maximum iteration count is reached.

### Delegation and Component Interactions
`PCGLinearSolver` inherits from `MatrixLinearSolver<TMatrix,TVector>` and `IterativeSolver` (class list in F2).  
- `init()` delegates to `MatrixLinearSolver::init()` via `Inherit1::init()` (F1 line 50).  
- Iteration parameters (`d_maxIter`, `d_tolerance`, `d_graph`) are accessed from the `IterativeSolver` base (F3).  
- The preconditioner link `l_preconditioner` is a `Link` to another linear solver; its `solveSystem()` method is invoked during preconditioning steps (solve method lines 186‑191, 214‑219).  
- `ensureRequiredLinearSystemType()` and `bwdInit()` perform dynamic casts to `PreconditionedMatrixFreeSystem<TMatrix,TVector>` and set the `l_preconditionerSystem` link, establishing a bidirectional relationship between the solver and the preconditioner’s linear system (F1 lines 98‑113, 124‑132).  
- `checkLinearSystem()` uses the templated helper `doCheckLinearSystem` from `IterativeSolver` to create a compatible linear system if missing (F1 lines 167‑171).  

### Execution Modes and Specific Behavior
- **Preconditioner usage** is controlled by `d_use_precond` and the presence of a linked preconditioner. When both are true, the solver executes the preconditioning block; otherwise it falls back to an unpreconditioned CG step (solve method conditional blocks lines 184‑191 and 212‑219).  
- **Iteration termination** depends on two configurable parameters: `d_maxIter` (default 25, F3 line 45) and `d_tolerance` (default 1e‑5, F3 line 48). The loop condition combines both (lines 199‑200).  
- **Template specialization**: For the generic `TMatrix/TVector` case, `cgstep_alpha` and `cgstep_beta` are defined in **PCGLinearSolver.h** (F2 lines 85‑95). Specialized implementations for `GraphScatteredMatrix/GraphScatteredVector` are provided in **PCGLinearSolver.inl** (F1 lines 143‑152), using the `eq` method for `beta` updates while reusing the generic `alpha` update.  
- **Graph logging**: Errors are stored in `d_graph` under keys `"Error N"` where `N` is the Newton iteration count; this behavior is triggered at each `solve` call and cleared on `AnimateBeginEvent` (solve lines 191‑197, handleEvent lines 155‑164).  
- **Component state handling**: Invalid states are set when the preconditioner link is missing or incompatible (init lines 66‑78) or when the linear system type check fails (ensureRequiredLinearSystemType lines 106‑112).  

These conditional paths and specializations define the solver’s configurable execution modes.

**Local source references for this section**

- `F1`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/PCGLinearSolver.inl`
- `F2`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/PCGLinearSolver.h`
- `F3`: `Sofa/framework/Core/src/sofa/core/behavior/IterativeSolver.h`
- `F4`: `Sofa/framework/Core/src/sofa/core/behavior/IterativeSolver.cpp`

## 5. Data Fields and Links

### Local Data Fields
| C++ attribute | Exposed SOFA name | C++ type | Default value / expression | Functional description | Declaration / Initialization |
|---|---|---|---|---|---|
| `d_use_precond` | `use_precond` | `Data<bool>` | `true` | Use a preconditioner | Declared in **F1** (line 53) – local origin. Default expression from constructor evidence in **F6** (line 39)【source_files:F1】【constructor_evidence:sofa_parameters】 |

### Inherited Data Fields
| C++ attribute | Exposed SOFA name | Owner class | C++ type | Default value / expression | Functional description | Declaration / Initialization |
|---|---|---|---|---|---|---|
| `d_parallelInverseProduct` | `parallelInverseProduct` | `MatrixLinearSolver<Matrix,Vector,NoThreadManager>` | `Data<bool>` | `false` | Parallelize the computation of the product *J·M⁻¹·Jᵀ* where *M* is the matrix of the linear system and *J* any compatible matrix | Declared in **F2** (line 247) – inherited_direct. Initialized in **F3** (line 39)【source_files:F2】【source_files:F3】 |
| `d_factorizationInvalidation` | `factorizationInvalidation` | `MatrixLinearSolver<Matrix,Vector,NoThreadManager>` | `Data<bool>` (protected) | `false` | Internal data for the detection of cache invalidation of the matrix factorization | Declared in **F2** (line 336) – inherited_direct. Initialized in **F3** (line 45)【source_files:F2】【source_files:F3】 |
| `d_maxIter` | `iterations` | `IterativeSolver` | `Data<unsigned>` | `static_cast<sofa::Size>(25)` | Maximum number of iterations | Declared in **F4** (line 45) – inherited_direct. Initialized in **F5** (line 28)【source_files:F4】【source_files:F5】 |
| `d_tolerance` | `tolerance` | `IterativeSolver` | `Data<SReal>` | `static_cast<SReal>(1e-5)` | Desired convergence accuracy | Declared in **F4** (line 48) – inherited_direct. Initialized in **F5** (line 29)【source_files:F4】【source_files:F5】 |
| `d_graph` | `graph` | `IterativeSolver` | `Data<std::map<std::string, sofa::type::vector<SReal>>>` | *Not specified* | Residual graph | Declared in **F4** (line 51) – inherited_direct. No explicit default (null)【source_files:F4】 |

#### Documentation-Only Data Fields
The official component documentation lists additional data fields that are not verified in the supplied C++ sources. Their C++ ownership and inheritance origin remain unverified.

| Exposed SOFA name | Documented default | Description | Documentation reference |
|---|---|---|---|
| `name` | `unnamed` | Object name | D1 |
| `printLog` | `0` | If true, emits extra messages at runtime. | D1 |
| `tags` | *(empty)* | List of the subsets the object belongs to | D1 |
| `bbox` | *(empty)* | This object bounding box | D1 |
| `componentState` | `Undefined` | The state of the component among (Dirty, Valid, Undefined, Loading, Invalid). | D1 |
| `listening` | `0` | If true, handle the events, otherwise ignore the events | D1 |
| `nbThreads` | `0` | Number of threads for the main task scheduler (0 = number of cores, -n = cores‑n). | D1 |
| `taskSchedulerType` | `_default` | Type of task scheduler to use. | D1 |

### Links and Component References

#### Verified C++ Links
| C++ attribute | Exposed SOFA name | Owner class (origin) | Link type / destination type | Flags | Purpose | Declaration reference |
|---|---|---|---|---|---|---|
| `l_preconditioner` | `preconditioner` | `PCGLinearSolver` (local) | `SingleLink<PCGLinearSolver, sofa::core::behavior::LinearSolver, BaseLink::FLAG_STOREPATH \| BaseLink::FLAG_STRONGLINK>` | `FLAG_STOREPATH`, `FLAG_STRONGLINK` | Link towards the linear solver used to precondition the conjugate gradient | Declared in **F1** (line 54)【source_files:F1】; initialized in constructor **F6** (line 40)【constructor_evidence:link_fields】 |

#### Documentation-Only Links
| Exposed SOFA name | Destination type | Description | Documentation reference |
|---|---|---|---|
| `context` | `BaseContext` | Graph Node containing this object (or `BaseContext::getDefault()` if no graph is used) | D1 |
| `slaves` | `BaseComponent` | Sub‑objects used internally by this object | D1 |
| `master` | `BaseComponent` | `nullptr` for regular objects, or master object for which this object is a sub‑object | D1 |
| `linearSystem` | `TypedMatrixLinearSystem<GraphScattered>` | The linear system to solve | D1 |
| `preconditioner` | `LinearSolver` | Link towards the linear solver used to precondition the conjugate gradient | D1 (already covered by verified C++ link) |

### Configuration Constraints and Interactions

* **Required‑field indicators** – None of the documented fields are marked as required in the constructor evidence.  
* **Read‑only fields / constructor modifications** – No read‑only fields are identified; the constructor only sets `first = true` and enables event listening (`this->f_listening.setValue(true)`).  
* **Deprecated parameters** –  

| C++ attribute | Exposed SOFA name | Deprecated since | Removal version | Replacement message | Source |
|---|---|---|---|---|---|
| `d_update_step` | `update_step` | v25.12 | v26.06 | “Instead, use the Data 'assemblingRate' in the associated PreconditionedMatrixFreeSystem” | Declared in **F1** (line 55); deprecation handled in constructor **F6** (line 41)【constructor_evidence:deprecated_fields】 |

* **Discrepancies** – No contradictions were found between the C++ defaults and the values documented in the official component page (e.g., `use_precond` default `true` ↔ documentation default `1`).  

* **Missing evidence** – For many generic component fields (e.g., `name`, `printLog`, `nbThreads`) the C++ source does not expose corresponding `Data` declarations in the provided files; they are therefore listed only as documentation‑only fields.

**Local source references for this section**

- `F1`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/PCGLinearSolver.h`
- `F2`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/MatrixLinearSolver.h`
- `F3`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/MatrixLinearSolver.inl`
- `F4`: `Sofa/framework/Core/src/sofa/core/behavior/IterativeSolver.h`
- `F5`: `Sofa/framework/Core/src/sofa/core/behavior/IterativeSolver.cpp`
- `F6`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/PCGLinearSolver.inl`

## 6. Diagnostics and Usage

### Practical Usage and Integration
The **PCGLinearSolver** implements a preconditioned conjugate‑gradient iterative algorithm for solving linear systems [usage documentation]. It inherits from `MatrixLinearSolver` and `IterativeSolver` [F2 line 37] and therefore expects a linear system of type `PreconditionedMatrixFreeSystem` [F1 lines 98‑113].  

During initialization the component checks the optional preconditioner link [F1 lines 50‑95]:
* If the link is empty, an informational message is emitted and the solver runs as an un‑preconditioned CG solver.
* If the link is set but resolves to `nullptr`, an error is reported and the component state is marked **Invalid**.
* If the linked preconditioner is templated on `GraphScattered`, an error is reported and the component is marked **Invalid**.

When both the PCG solver and a valid preconditioner are present, `bwdInit` links the preconditioner’s linear system to the PCG’s `PreconditionedMatrixFreeSystem` [F1 lines 116‑140]; this link is required for the preconditioner matrix assembly.

No concrete usage example containing this component is provided in the supplied documentation; therefore none can be reproduced here.

### Configuration Guidelines
| Parameter | Sofa name | Type | Default | Origin | Remarks |
|-----------|-----------|------|---------|--------|---------|
| `use_precond` | `use_precond` | `Data<bool>` | `true` | local (PCGLinearSolver) | Enables/disables the preconditioner [F2 line 53]. |
| `iterations` | `iterations` | `Data<unsigned>` | `25` | inherited (IterativeSolver) | Maximum number of CG iterations [F5 line 45]. |
| `tolerance` | `tolerance` | `Data<SReal>` | `1e‑5` | inherited (IterativeSolver) | Desired convergence accuracy [F5 line 48]. |
| `parallelInverseProduct` | `parallelInverseProduct` | `Data<bool>` | `false` | inherited (MatrixLinearSolver) | Parallelizes the product `J*M⁻¹*Jᵀ` [F3 line 247]. |
| `factorizationInvalidation` | `factorizationInvalidation` | `Data<bool>` | `false` | inherited (MatrixLinearSolver) | Internal cache‑invalidation flag [F3 line 336]. |
| `graph` | `graph` | `Data<std::map<std::string, sofa::type::vector<SReal>>>` | – | inherited (IterativeSolver) | Stores the residual graph for diagnostics [F5 line 51]. |

A deprecated field `update_step` is present but removed in version v26.06; users should instead use the `assemblingRate` data of the associated `PreconditionedMatrixFreeSystem` [F1 deprecated_fields record line 41].

### Diagnostics and Troubleshooting
| Diagnostic | Trigger | Observed behavior | Corrective action (if any) |
|------------|---------|-------------------|----------------------------|
| **Info**: “Link … should be set to precondition the conjugate gradient.” | `l_preconditioner` link empty | Solver runs without preconditioning. | Provide a valid preconditioner link if preconditioning is desired. [F1 lines 50‑55] |
| **Error**: “No preconditioner found at path …” | `l_preconditioner` linked but `nullptr` | Component state set to **Invalid**; solver not usable. | Ensure the preconditioner component exists and the path is correct. [F1 lines 57‑62] |
| **Error**: “Cannot use the preconditioner … because it is templated on GraphScatteredType” | Preconditioner type is `GraphScattered` | Component state set to **Invalid**. | Use a preconditioner with a compatible template (non‑GraphScattered). [F1 lines 63‑68] |
| **Error**: “This linear solver is designed to work with a … linear system, but a … was found” | Linear system not a `PreconditionedMatrixFreeSystem` | Component state set to **Invalid**. | Replace the linear system with a `PreconditionedMatrixFreeSystem`. [F1 lines 98‑113] |
| **Convergence stop** | Residual norm `r_norm` ≤ `tolerance` or `iter` > `iterations` | Loop exits; solution returned (may be approximate). | Adjust `tolerance` (lower for higher accuracy) or increase `iterations` if convergence is not reached. [F1 lines 174‑257] |

No additional warnings or assertions are emitted by the current implementation.

### Limitations and Recommendations
* **Supported linear system** – The solver is verified only with `PreconditionedMatrixFreeSystem`; using any other system type triggers an error [F1 lines 98‑113].  
* **Preconditioner compatibility** – A preconditioner must be linked and must not be templated on `GraphScattered`. Failure to meet these constraints invalidates the component [F1 lines 57‑68].  
* **Numerical preconditions** – Convergence depends on the spectral properties of the matrix and on the chosen tolerance and maximum iteration count. The solver does not guarantee convergence if the matrix is ill‑conditioned or if `iterations` is too low.  
* **Parallel product** – The `parallelInverseProduct` flag is available but defaults to `false`; enabling it requires a thread‑safe environment and may affect performance.  
* **Deprecation** – The `update_step` field is deprecated; users should migrate to `assemblingRate` in the associated preconditioner system.  

**Recommendations**:  
1. Use a compatible preconditioner and verify the link path during scene setup.  
2. Prefer `PreconditionedMatrixFreeSystem` as the linear system type.  
3. Start with the default tolerance (`1e‑5`) and increase `iterations` only if the residual graph shows stagnation.  
4. Enable `parallelInverseProduct` only after confirming thread‑safety of the surrounding simulation.  

All statements are derived directly from the supplied SOFA source files and documentation.

**Local source references for this section**

- `F1`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/PCGLinearSolver.inl`
- `F2`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/PCGLinearSolver.h`
- `F3`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/MatrixLinearSolver.h`
- `F4`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/MatrixLinearSolver.inl`
- `F5`: `Sofa/framework/Core/src/sofa/core/behavior/IterativeSolver.h`
- `F6`: `Sofa/framework/Core/src/sofa/core/behavior/IterativeSolver.cpp`
