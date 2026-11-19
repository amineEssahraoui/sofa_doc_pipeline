# CGLinearSolver - Technical Documentation

This document has been generated from supplied evidence. It has not undergone exhaustive factual verification.

**Incomplete generation. Missing or rejected sections:** 6. Diagnostics and Usage.

## Table of Contents

- 1. Component Overview
- 2. Architecture and Inheritance
- 3. Mathematical Formulation
- 4. Internal Architecture and Execution
- 5. Data Fields and Links
- 6. Diagnostics and Usage

## 1. Component Overview

### Purpose and Role

The CGLinearSolver is a component classified in the **LinearSolver** category. Its documented purpose is to provide a generic solution mechanism for linear systems of the form A x = b, without requiring any prior knowledge about the structure of the system [A]. Within the SOFA architecture the solver sits downstream of an integration scheme that assembles the right‑hand side vector b and upstream of a MechanicalObject that stores the state variables to be updated. It therefore acts as the bridge that translates the forces computed by the integration step into the displacement or velocity increments needed by the mechanical state [B].

### Numerical or Physical Problem

In many SOFA simulations, especially those employing implicit time integration, the discretized equations of motion lead to a linear system that couples mass, damping and stiffness contributions (α M + β B + γ K) δv = b [faure_springer12.pdf pp. 17‑18]. Solving this system is essential to obtain stable updates of velocities or positions when the underlying forces are stiff or when large time steps are used. The physical problem thus reduces to finding the unknown vector δv that satisfies equilibrium under the assembled forces, which mathematically corresponds to solving a sparse, symmetric (often positive‑definite) linear system arising from finite element or other discretizations [faure_springer12.pdf pp. 17‑18].

### General Approach

The CGLinearSolver implements the classic conjugate gradient algorithm, an iterative method that builds a sequence of mutually conjugate search directions from the residual r = b − A xᵏ [official documentation introduction paragraph 2]. At each iteration the residual is used to generate a new direction, and the solution estimate is updated along this direction, progressively reducing the residual norm. Because the method relies only on matrix‑vector products, it can operate efficiently on the sparse matrices typical of SOFA simulations [faure_springer12.pdf pp. 18]. The iterative nature means that the solver does not guarantee an exact solution; instead, convergence is controlled by user‑specified iteration limits, tolerance and threshold values, which must be chosen relative to the degrees of freedom of the model [official documentation usage paragraph 2‑3]. This approach enables a trade‑off between computational cost and solution accuracy, making the CGLinearSolver suitable for large‑scale, sparsely populated systems encountered in implicit dynamics.

## 2. Architecture and Inheritance

### Class Architecture

| Aspect | Detail |
|--------|--------|
| **C++ class** | `CGLinearSolver` (template `<TMatrix, TVector>`) |
| **Namespace** | `sofa::component::linearsolver::iterative` |
| **SOFA module** | `Sofa.Component.LinearSolver.Iterative` |
| **Header** | `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/CGLinearSolver.h` (class declared at line 34)【F1】 |
| **Template parameters** | `TMatrix` – matrix type, `TVector` – vector type (as required by the generic `MatrixLinearSolver` base). |
| **Integration point** | Implements the generic linear‑solver interface used by the SOFA simulation graph; the solver is invoked by mechanical visitors during the resolution of the linear system \(A x = b\). |
| **Local data members** | `d_smallDenominatorThreshold` (Data<Real>) and `d_warmStart` (Data<bool>) declared in the header at lines 47‑48【F1】. |
| **Source files** | Header (F1), implementation (F2), inline definitions (F3). |

### Inheritance Hierarchy

*Direct base classes* (as defined in the class declaration)  

1. `sofa::component::linearsolver::MatrixLinearSolver<TMatrix, TVector>` – resolved via header `sofa/component/linearsolver/iterative/MatrixLinearSolver.h`【parent_dependencies】.  
2. `sofa::core::behavior::IterativeSolver` – resolved via header `sofa/core/behavior/IterativeSolver.h`【parent_dependencies】.  

*Indirect base classes*  

- The direct bases themselves may derive from other SOFA core classes, but those relationships are not present in the supplied evidence and therefore are not listed here.  

*Polymorphism*  

- `CGLinearSolver` overrides the virtual methods `init()`, `reinit()`, and `solve(...)` declared in its base classes (see method signatures in the header)【F1】.  

### Inherited and Local Responsibilities

| Responsibility | Origin | Description |
|----------------|--------|-------------|
| **Iterative control** (maximum iterations, convergence tolerance, residual graph) | Inherited directly from `sofa::core::behavior::IterativeSolver` (Data members `d_maxIter`, `d_tolerance`, `d_graph` at lines 45‑51 in `IterativeSolver.h`)【F5】 | Provides generic iterative‑solver parameters used by all iterative solvers. |
| **Matrix‑solver infrastructure** (parallel inverse product flag, factorization invalidation flag) | Inherited directly from `sofa::component::linearsolver::MatrixLinearSolver` (Data members `d_parallelInverseProduct` at line 247 and `d_factorizationInvalidation` at line 336 in `MatrixLinearSolver.h`)【F4】 | Supplies utilities common to matrix‑based linear solvers (e.g., handling of matrix factorization caching). |
| **Conjugate‑gradient specific data** | Local to `CGLinearSolver` (`d_smallDenominatorThreshold`, `d_warmStart` at lines 47‑48 in `CGLinearSolver.h`)【F1】 | Controls CG‑specific numerical safeguards and optional warm‑start behavior. |
| **CG step computations** (`cgstep_beta`, `cgstep_alpha`) | Local methods declared inline in the header (lines 56 and 59)【F1】 and defined in the inline file `CGLinearSolver.inl` (lines 314‑319 and 322‑329)【F3】 | Implements the core CG update formulas. |
| **Solver lifecycle** (`init()`, `reinit()`, `solve(...)`) | `init()` and `solve(...)` are overridden locally (definitions in `CGLinearSolver.inl` lines 46‑65 and 69‑311)【F3】; `reinit()` is an inline empty override (line 66)【F1】 | Sets up the solver, performs the CG iteration, and integrates with the SOFA execution pipeline. |

### Architectural Dependencies

| Dependency type | Source | Reason / Role |
|-----------------|--------|---------------|
| **Header includes (compile‑time)** | `CGLinearSolver.h` includes `config.h`, `MatrixLinearSolver.h`, `IterativeSolver.h`, `helper/map.h`【includes – F1】 | Provides base class definitions, configuration macros, and utility containers. |
| **Implementation includes** | `CGLinearSolver.cpp` includes `CGLinearSolver.inl`, linear‑algebra headers (`FullMatrix.h`, `SparseMatrix.h`, `CompressedRowSparseMatrix.h`), `ObjectFactory.h`, and `MechanicalVMultiOpVisitor.h`【includes – F2】 | Gives access to concrete matrix types, factory registration, and the visitor used to traverse the mechanical graph during CG iterations. |
| **Inline definitions** | `CGLinearSolver.inl` includes the header itself, `MechanicalVisitor.h`, and timing helpers (`AdvancedTimer.h`, `ScopedAdvancedTimer.h`)【includes – F3】 | Enables in‑line expansion of performance‑critical CG steps and optional profiling. |
| **Component interactions** | The solver is invoked by mechanical visitors (`MechanicalVisitor`, `MechanicalVMultiOpVisitor`) that compute matrix‑vector products on the scene graph; it operates on a `Matrix` and `Vector` supplied by the surrounding simulation components (e.g., `MechanicalObject`). This relationship is implied by the includes of visitor headers and by the documented usage pattern in the official component description (requires an integration scheme above and a `MechanicalObject` below in the scene graph)【official_documentation – introduction & usage】. |
| **Module dependencies** | Belongs to the `Sofa.Component.LinearSolver.Iterative` module and depends on the core behavior module (`sofa::core::behavior`) and the linear‑algebra module (`sofa::linearalgebra`). These dependencies are reflected by the include paths and by the inheritance from `IterativeSolver`. |

*Note:* The evidence does not detail runtime service registration (e.g., `ObjectFactory` usage) beyond the inclusion of the header; therefore, no further component‑level dependencies are asserted.

**Local source references for this section**

- `F1`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/CGLinearSolver.h`
- `F2`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/CGLinearSolver.cpp`
- `F3`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/CGLinearSolver.inl`
- `F4`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/MatrixLinearSolver.h`
- `F5`: `Sofa/framework/Core/src/sofa/core/behavior/IterativeSolver.h`

## 3. Mathematical Formulation

### Mathematical Problem

The **CGLinearSolver** component solves a linear system  

\[
\mathbf{A}\,x = b ,
\]

where  

* \(\mathbf{A}\) is a square matrix supplied to the solver,  
* \(x\) is the unknown vector of degrees of freedom, and  
* \(b\) is the right‑hand side vector that is assumed to have been assembled by the simulation (e.g., in `computeForce()`).  

The component makes no a‑priori assumptions on \(\mathbf{A}\) beyond those required by the conjugate‑gradient method (see the scientific reference).  This problem statement is documented in the SOFA component description【official_documentation.introduction[0].text】.

### Mathematical Formulation

The conjugate‑gradient (CG) method iteratively builds a sequence of approximations \(\{x^{k}\}\) using the residual  

\[
r^{k}= b - \mathbf{A}\,x^{k},
\]

and a set of mutually **A‑conjugate** search directions \(\{p^{k}\}\).  At each iteration the algorithm computes scalar coefficients  

\[
\alpha^{k}= \frac{(r^{k})^{\!\top} r^{k}}{(p^{k})^{\!\top}\mathbf{A}\,p^{k}}, \qquad
\beta^{k}= \frac{(r^{k+1})^{\!\top} r^{k+1}}{(r^{k})^{\!\top} r^{k}} .
\]

The updates are  

\[
\begin{aligned}
x^{k+1} &= x^{k} + \alpha^{k} p^{k},\\
r^{k+1} &= r^{k} - \alpha^{k}\,\mathbf{A}\,p^{k},\\
p^{k+1} &= r^{k+1} + \beta^{k} p^{k}.
\end{aligned}
\]

The iteration stops when either  

* \(\|r^{k+1}\| \le \text{tolerance}\) (data field `tolerance`), or  
* the number of iterations reaches the limit `iterations`, or  
* the denominator \((p^{k})^{\!\top}\mathbf{A}\,p^{k}\) falls below the threshold `threshold` (data field `d_smallDenominatorThreshold`).  

These quantities are exposed as SOFA data fields:

| Data field | Meaning | Source |
|------------|---------|--------|
| `iterations` | maximum number of CG steps | `IterativeSolver::d_maxIter` in **F5** |
| `tolerance` | convergence criterion on the residual norm | `IterativeSolver::d_tolerance` in **F5** |
| `threshold` | minimum admissible value of \((p^{\top} A p)\) to avoid division by a small denominator | `CGLinearSolver::d_smallDenominatorThreshold` in **F1** |
| `warmStart` | if true, the previous solution is used as the initial guess for the next solve | `CGLinearSolver::d_warmStart` in **F1** |

The CG algorithm is implemented through the public method  

```cpp
void solve(Matrix& A, Vector& x, Vector& b) override;   // declared in F1:69, defined in F3:69‑311
```  

which orchestrates the iteration using the helper functions  

* `cgstep_alpha` – performs the \(\alpha\) update (signature in **F1**:59, definition in **F3**:322‑329)  
* `cgstep_beta`  – performs the \(\beta\) update (signature in **F1**:56, definition in **F3**:314‑319)  

### Numerical Algorithm

The documented algorithm follows the classic conjugate‑gradient scheme:

1. **Initialization** (`init()` in **F1**:65, defined in **F3**:46‑65) – allocate vectors, optionally set the initial guess (`warmStart`).  
2. **Compute initial residual** \(r^{0}=b-\mathbf{A}x^{0}\) and set the first direction \(p^{0}=r^{0}\).  
3. **Iterative loop** (performed inside `solve`) – for each iteration \(k\):
   * Compute \(\alpha^{k}\) and update the solution and residual using `cgstep_alpha`.  
   * Test convergence against `tolerance` or the denominator threshold (`threshold`).  
   * If not converged, compute \(\beta^{k}\) and update the search direction using `cgstep_beta`.  
4. **Termination** – stop when convergence criteria are satisfied or the maximum number of iterations (`iterations`) is reached.  

The algorithmic steps are described in the component’s official documentation (introduction paragraphs)【official_documentation.introduction[1].text】 and are consistent with the standard CG method as presented in the scientific reference *“An Introduction to the Conjugate Gradient Method”* (Shewchuk, 1994)【scientific_context.component_specific[0].text】.  

All cited parameters (`iterations`, `tolerance`, `threshold`, `warmStart`) are directly linked to the corresponding SOFA data fields, and the method signatures (`solve`, `cgstep_alpha`, `cgstep_beta`) provide the verified C++ interfaces that expose the algorithm to the framework.

**Local source references for this section**

- `F1`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/CGLinearSolver.h`
- `F2`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/CGLinearSolver.cpp`
- `F3`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/CGLinearSolver.inl`
- `F4`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/MatrixLinearSolver.h`
- `F5`: `Sofa/framework/Core/src/sofa/core/behavior/IterativeSolver.h`

## 4. Internal Architecture and Execution

### Internal Responsibilities
The **CGLinearSolver** class implements the conjugate‑gradient algorithm for solving \(A x = b\). Its core responsibilities are provided by the following methods:

* **init()** – validates data fields (`tolerance`, `threshold`), issues warnings for negative values, and resets runtime state (`timeStepCount`, `equilibriumReached`). Implementation in *F2* lines 46‑65【F2,46-65】.  
* **reinit()** – overridden as a no‑op (empty body) in *F3* line 66【F3,66】.  
* **solve(Matrix& A, Vector& x, Vector& b)** – performs the full CG iteration, allocating temporary vectors, handling warm‑start, computing residuals, checking convergence criteria, updating solution and residual, and managing the diagnostic graph. Full implementation in *F2* lines 69‑311【F2,69-311】.  
* **cgstep_beta(...)** – updates the conjugate direction `p` as `p = beta * p + r`. Generic version in *F2* lines 314‑319【F2,314-319】; specialized version for `GraphScatteredMatrix/Vector` in *F1* lines 40‑44【F1,40-44】.  
* **cgstep_alpha(...)** – updates solution `x` and residual `r` using the step size `alpha`. Generic version in *F2* lines 322‑329【F2,322-329】; specialized version for `GraphScatteredMatrix/Vector` in *F1* lines 46‑59【F1,46-59】.

Internal state consists of:
* **d_smallDenominatorThreshold** (`threshold`) – minimal allowed denominator before early termination (default 1e‑5) – defined in *F3* line 47【F3,47】.  
* **d_warmStart** (`warmStart`) – flag controlling whether the previous solution `x` is reused – defined in *F3* line 48【F3,48】.  
* Inherited from **IterativeSolver**:  
  * **d_maxIter** (`iterations`) – maximum number of CG iterations (default 25) – defined in *F4* line 45 and default source *F5* line 28【F4,45】【F5,28】.  
  * **d_tolerance** (`tolerance`) – convergence tolerance (default 1e‑5) – defined in *F4* line 48 and default source *F5* line 29【F4,48】【F5,29】.  
  * **d_graph** (`graph`) – container for diagnostic data – defined in *F4* line 51【F4,51】.  
* **timeStepCount** – number of solve calls performed (reset in `init`).  
* **equilibriumReached** – flag indicating whether convergence was achieved in the previous step.

### Execution Workflow
The `solve` method follows this exact sequence:

1. **Visitor‑based vector allocation** – creates a `TempVectorContainer` (`vtmp`) and three temporary vectors `p`, `q`, `r` (lines 73‑77)【F2,73-77】.  
2. **Initial residual** –  
   * If `warmStart` is true, compute `r = b - A*x` (lines 84‑87)【F2,84-87】.  
   * Otherwise, clear `x` and set `r = b` (lines 89‑91)【F2,89-91】.  
3. **Norm of RHS** – `normb = b.norm()` (line 93)【F2,93】.  
4. **Graph initialization** – edit `d_graph`, push initial error = 1, clear denominator vector (lines 95‑104)【F2,95-104】.  
5. **Main iteration loop** – runs while `nb_iter ≤ d_maxIter` (line 108)【F2,108】. For each iteration:  
   * Compute `rho = r·r` (line 119)【F2,119】.  
   * Compute error `err = sqrt(rho)/normb` and store in graph (lines 122‑127)【F2,122-127】.  
   * **Tolerance check** – if `err ≤ d_tolerance` break (lines 129‑152)【F2,129-152】.  
   * **Direction update** – first iteration sets `p = r`; later iterations compute `beta = rho / rho_1` and call `cgstep_beta` (lines 155‑166)【F2,155-166】.  
   * Compute matrix‑vector product `q = A * p` (line 176)【F2,176】.  
   * Compute denominator `den = p·q` and store in graph (lines 179‑181)【F2,179-181】.  
   * **Denominator threshold check** – if `|den| ≤ threshold` break (lines 183‑209)【F2,183-209】.  
   * Compute step size `alpha = rho / den` (line 212)【F2,212】.  
   * Update solution and residual via `cgstep_alpha` (line 215)【F2,215】.  
   * Store current `rho` into `rho_1` for next iteration (line 226)【F2,226】.  
6. **Zero‑RHS branch** – if `normb == 0`, a separate handling path evaluates denominator once and may issue warnings (lines 236‑260)【F2,236-260】.  
7. **Finalization** – stop timer, end graph edit, increment `timeStepCount`, record iteration count, output final messages, and delete temporary vectors (lines 262‑285)【F2,262-285】.

All control flow (break conditions, warnings) follows the exact code paths shown; no additional implicit steps are introduced.

### Delegation and Component Interactions
* **Inheritance** – `CGLinearSolver` derives from `MatrixLinearSolver<TMatrix,TVector>` and `IterativeSolver`. Calls to `Inherit1::init()` (line 48 of `init`) delegate initialization to the base `IterativeSolver` implementation【F2,48】.  
* **TempVectorContainer** – provided by the base `MatrixLinearSolver` (via `Inherit`) to manage temporary vectors; allocation and deletion are performed through `vtmp.createTempVector()` and `vtmp.deleteTempVector()` (lines 73‑77 and 282‑284)【F2,73-77】【F2,282-284】.  
* **Matrix‑vector product** – `q = A * p` uses the overloaded `operator*` of the matrix type `TMatrix`. For assembled matrices this is a direct multiplication; for non‑assembled (`GraphScattered`) matrices the operation triggers visitors that call `addDForce` on force fields (comment in source lines 176‑179)【F2,176-179】.  
* **MechanicalVMultiOpVisitor** – invoked only in the specialized `cgstep_alpha` for `GraphScatteredMatrix/Vector` (lines 46‑59 of *F1*) to apply the updates `x += alpha·p` and `r -= alpha·q` via a visitor pattern【F1,46-59】.  
* **Graph data** – `d_graph` is edited via `beginEdit()`/`endEdit()` to store error and denominator histories (lines 95‑104 and 268‑270)【F2,95-104】【F2,268-270】.  
* **AdvancedTimer** – timing sections `CG-Solve` are started and stopped (lines 112, 262)【F2,112】【F2,262】.  
* **Message logging** – `msg_info()`, `msg_warning()` are used throughout to report status, errors, and convergence information (multiple lines).  

### Execution Modes and Specific Behavior
* **Warm‑start mode** – Controlled by `d_warmStart`. When true, the initial residual is computed as `r = b - A*x`; otherwise `x` is cleared and `r = b`. This conditional is at lines 84‑91【F2,84-91】.  
* **Threshold‑based early termination** – If the denominator `den` satisfies `|den| ≤ d_smallDenominatorThreshold`, the solver stops after at least one iteration (lines 183‑209)【F2,183-209】. The threshold value is configurable via the `threshold` data field (default 1e‑5).  
* **Tolerance‑based convergence** – Solver stops when `err ≤ d_tolerance` (lines 129‑152)【F2,129-152】. The tolerance is a configurable data field (default 1e‑5).  
* **Zero‑RHS handling** – When `normb == 0`, the algorithm skips the main loop and performs a single denominator check (lines 236‑260)【F2,236-260】.  
* **Template specialization** – For generic matrix/vector types (`TMatrix`, `TVector`), `cgstep_beta` and `cgstep_alpha` use simple scalar/vector arithmetic (lines 314‑329 in *F2*). For the specific `GraphScatteredMatrix/Vector` specialization, `cgstep_alpha` employs a `MechanicalVMultiOpVisitor` to apply updates through the visitor mechanism (lines 46‑59 in *F1*)【F2,314-329】【F1,46-59】.  
* **Denominator zero** – If `den == 0.0`, a warning is issued and the iteration loop breaks immediately (lines 219‑222)【F2,219-222】.  
* **Reinit behavior** – The `reinit()` method is overridden as an empty function, meaning no additional state reset occurs between simulation steps (line 66 in *F3*)【F3,66】.  

All conditional paths, configuration effects, and specialization differences are directly reflected in the cited source code.

**Local source references for this section**

- `F1`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/CGLinearSolver.cpp`
- `F2`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/CGLinearSolver.inl`
- `F3`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/CGLinearSolver.h`
- `F4`: `Sofa/framework/Core/src/sofa/core/behavior/IterativeSolver.h`
- `F5`: `Sofa/framework/Core/src/sofa/core/behavior/IterativeSolver.cpp`

## 5. Data Fields and Links

### Local Data Fields
| C++ attribute | Exposed SOFA name | C++ type | Default value / expression | Functional description | Declaration & initialization references |
|---|---|---|---|---|---|
| `d_smallDenominatorThreshold` | `threshold` | `Data<Real>` | `(Real)1e-5` | Minimum value of the denominator \\((p^T A p)\\) in the Conjugate Gradient solution | Declared in **F1** line 47; default expression from structured attribute; marked required in constructor – see **F6** line 36 and constructor body **F6** line 41 |
| `d_warmStart` | `warmStart` | `Data<bool>` | `false` | Use previous solution as initial solution, which may improve the initial guess if the system evolves smoothly | Declared in **F1** line 48; default expression from structured attribute; constructor reference **F6** line 37 |

### Inherited Data Fields
| C++ attribute | Exposed SOFA name | Owner class | C++ type | Default value / expression | Functional description | Declaration & initialization references |
|---|---|---|---|---|---|---|
| `d_parallelInverseProduct` | `parallelInverseProduct` | `MatrixLinearSolver<Matrix,Vector,NoThreadManager>` | `Data<bool>` | `false` | Parallelize the computation of the product \\(J·M^{-1}·J^T\\) where *M* is the matrix of the linear system and *J* any compatible matrix | Declared in **F2** line 247; default from structured attribute; initialized in **F3** line 39 |
| `d_factorizationInvalidation` | `factorizationInvalidation` | `MatrixLinearSolver<Matrix,Vector,NoThreadManager>` | `Data<bool>` (protected) | `false` | Internal data for detection of cache invalidation of the matrix factorization | Declared in **F2** line 336; default from structured attribute; initialized in **F3** line 45 |
| `d_maxIter` | `iterations` | `IterativeSolver` | `Data<unsigned>` | `static_cast<sofa::Size>(25)` | Maximum number of iterations | Declared in **F4** line 45; default from structured attribute; initialized in **F5** line 28; marked required in constructor – **F6** line 39 |
| `d_tolerance` | `tolerance` | `IterativeSolver` | `Data<SReal>` | `static_cast<SReal>(1e-5)` | Desired convergence accuracy | Declared in **F4** line 48; default from structured attribute; initialized in **F5** line 29; marked required in constructor – **F6** line 40 |
| `d_graph` | `graph` | `IterativeSolver` | `Data<std::map<std::string, sofa::type::vector<SReal>>>` | *Not specified* | Residual graph | Declared in **F4** line 51; default not specified; initialized in **F5** line 30 |

#### Documentation‑Only Data Fields
The official component documentation lists additional parameters for which no C++ ownership or inheritance has been verified in the supplied source.

| Exposed SOFA name | Default value | Description | Documentation reference |
|---|---|---|---|
| `name` | `unnamed` | Object name | D1 |
| `printLog` | `0` | If true, emits extra messages at runtime. | D1 |
| `tags` | *(empty)* | List of the subsets the object belongs to. | D1 |
| `bbox` | *(empty)* | This object bounding box. | D1 |
| `componentState` | `Undefined` | The state of the component among (Dirty, Valid, Undefined, Loading, Invalid). | D1 |
| `listening` | `0` | If true, handle the events, otherwise ignore the events. | D1 |
| `nbThreads` | `0` | Number of threads for the main task scheduler (0 = number of cores; negative = cores‑N). | D1 |
| `taskSchedulerType` | `_default` | Type of task scheduler to use. | D1 |

*Note: C++ ownership and inheritance origin for the above fields remain unverified.*

### Links and Component References

#### Documentation‑Only Links
| Link name | Destination type | Purpose / description | Documentation reference |
|---|---|---|---|
| `context` | `BaseContext` | Graph Node containing this object (or `BaseContext::getDefault()` if no graph is used). | D1 |
| `slaves` | `BaseComponent` | Sub‑objects used internally by this object. | D1 |
| `master` | `BaseComponent` | `nullptr` for regular objects, or master object for which this object is a sub‑object. | D1 |
| `linearSystem` | `TypedMatrixLinearSystem<CompressedRowSparseMatrixMat2x2d>` | The linear system to solve. | D2 |
| `linearSystem` | `TypedMatrixLinearSystem<CompressedRowSparseMatrixMat3x3d>` | The linear system to solve. | D3 |
| `linearSystem` | `TypedMatrixLinearSystem<CompressedRowSparseMatrixMat4x4d>` | The linear system to solve. | D4 |
| `linearSystem` | `TypedMatrixLinearSystem<CompressedRowSparseMatrixMat6x6d>` | The linear system to solve. | D5 |
| `linearSystem` | `TypedMatrixLinearSystem<CompressedRowSparseMatrixMat8x8d>` | The linear system to solve. | D6 |
| `linearSystem` | `TypedMatrixLinearSystem<CompressedRowSparseMatrixd>` | The linear system to solve. | D7 |
| `linearSystem` | `TypedMatrixLinearSystem<FullMatrix>` | The linear system to solve. | D8 |
| `linearSystem` | `TypedMatrixLinearSystem<GraphScattered>` | The linear system to solve. | D9 |
| `linearSystem` | `TypedMatrixLinearSystem<SparseMatrix>` | The linear system to solve. | D10 |

*No verified C++ Link declarations were found for `CGLinearSolver` in the supplied source.*

### Configuration Constraints and Interactions
* **Required‑field indicators** – The constructor of `CGLinearSolver` explicitly marks the following data fields as required: `d_maxIter`, `d_tolerance`, and `d_smallDenominatorThreshold` (see **F6** constructor body lines 39‑41).  
* **Read‑only fields** – No fields are declared read‑only in the available evidence.  
* **Deprecated parameters** – None are listed in the supplied evidence.  
* **Discrepancies** – All defaults observed in the C++ code match the defaults documented in the official component page (e.g., `threshold` = 1e‑5, `warmStart` = 0, `iterations` = 25, etc.). No contradictions were identified.  
* **Missing evidence** – Ownership and inheritance details for the documentation‑only data fields (e.g., `name`, `printLog`, …) and for the listed links are not present in the provided source files. Consequently, they are reported only as documentation‑only entries.

**Local source references for this section**

- `F1`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/CGLinearSolver.h`
- `F2`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/MatrixLinearSolver.h`
- `F3`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/MatrixLinearSolver.inl`
- `F4`: `Sofa/framework/Core/src/sofa/core/behavior/IterativeSolver.h`
- `F5`: `Sofa/framework/Core/src/sofa/core/behavior/IterativeSolver.cpp`
- `F6`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/CGLinearSolver.inl`

## 6. Diagnostics and Usage

### Practical Usage and Integration
The **CGLinearSolver** implements the conjugate‑gradient algorithm and must be placed in a scene graph **below** a `MechanicalObject` that stores the system state and **above** an integration scheme (e.g., `EulerImplicitIntegrationScheme`) that provides the right‑hand side vector `b` via `computeForce()` 【usage_documentation】.  

Typical integration requirements are documented in the “Usage” section of the component description, which states that an integration scheme must precede the solver in the scene graph and a `MechanicalObject` must follow it【usage_documentation】.  

A documented XML scene illustrating a minimal configuration is provided in the component’s examples. The excerpt below shows the required plugins, the integration scheme, the solver with its main data fields, and the mechanical state 【usage_example】:

```xml
<Node name="root" dt="0.02" gravity="0 -10 0">
    <RequiredPlugin pluginName="Sofa.Component.Constraint.Projective"/>
    <RequiredPlugin pluginName="Sofa.Component.LinearSolver.Iterative"/>
    <RequiredPlugin pluginName="Sofa.Component.Mass"/>
    <RequiredPlugin pluginName="Sofa.Component.IntegrationScheme.Backward"/>
    <RequiredPlugin pluginName="Sofa.Component.SolidMechanics.FEM.Elastic"/>
    <RequiredPlugin pluginName="Sofa.Component.StateContainer"/>
    <RequiredPlugin pluginName="Sofa.Component.Topology.Container.Grid"/>
    <RequiredPlugin pluginName="Sofa.Component.Visual"/>
    <VisualStyle displayFlags="showBehaviorModels showForceFields"/>
    <DefaultAnimationLoop/>

    <Node>
        <EulerImplicitIntegrationScheme name="eulerimplicit_odesolver"
                                        printLog="false"
                                        rayleighStiffness="0.1"
                                        rayleighMass="0.1"/>
        <CGLinearSolver iterations="100"
                         tolerance="1e-20"
                         threshold="1e-20"
                         warmStart="1"/>
        <MechanicalObject/>
        <!-- additional components omitted for brevity -->
    </Node>
</Node>
```

No other usage examples are supplied in the evidence.

### Configuration Guidelines
The solver inherits several data fields from `IterativeSolver` and `MatrixLinearSolver`. The most relevant fields are:

| Data field | Owner | Type | Default | Required? | Remarks |
|------------|-------|------|---------|-----------|---------|
| `iterations` (`d_maxIter`) | `IterativeSolver` | `Data<unsigned>` | `25` (static cast)【configuration】 | **Yes** – set via `iterations` attribute【configuration_constraints】 | Maximum number of CG iterations. |
| `tolerance` (`d_tolerance`) | `IterativeSolver` | `Data<SReal>` | `1e-5`【configuration】 | **Yes** – set via `tolerance` attribute【configuration_constraints】 | Desired relative residual error; must be non‑negative (negative values are replaced by the default at init). |
| `threshold` (`d_smallDenominatorThreshold`) | `CGLinearSolver` | `Data<Real>` | `1e-5`【configuration】 | **Yes** – set via `threshold` attribute【configuration_constraints】 | Minimum allowed value of the denominator `pᵀ A p`; negative values are replaced by the default at init. |
| `warmStart` (`d_warmStart`) | `CGLinearSolver` | `Data<bool>` | `false`【configuration】 | No | If true, the previous solution is used as the initial guess. |
| `parallelInverseProduct` (`d_parallelInverseProduct`) | `MatrixLinearSolver` (inherited) | `Data<bool>` | `false`【configuration】 | No | Enables parallel computation of `J·M⁻¹·Jᵀ`. |
| `factorizationInvalidation` (`d_factorizationInvalidation`) | `MatrixLinearSolver` (inherited) | `Data<bool>` | `false`【configuration】 | No | Internal cache‑invalidation flag. |

All three required fields (`iterations`, `tolerance`, `threshold`) are explicitly marked as required in the constructor of `CGLinearSolver`【configuration_constraints】.  

When configuring `tolerance` and `threshold`, the documentation advises that their values should be chosen in relation to the degrees of freedom (DOFs) and typically be close to the square of the expected DOF error【usage_documentation】.

### Diagnostics and Troubleshooting
The implementation emits several diagnostics during initialization and solving:

| Condition | Emitted message | Source location | Behaviour |
|-----------|----------------|----------------|-----------|
| `tolerance` < 0 (init) | `'tolerance' must be a positive value` … `default value used: 1e-5` | `CGLinearSolver::init` lines 46‑55【diagnostic_implementations】 | The value is reset to `1e-5`. |
| `threshold` < 0 (init) | `'threshold' must be a positive value` … `default value used: 1e-5` | `CGLinearSolver::init` lines 56‑65【diagnostic_implementations】 | The value is reset to `1e-5`. |
| Relative error `err` ≤ `tolerance` at first iteration and first time step | `tolerance reached at first iteration of CG` … `Check the 'tolerance' data field, you might decrease it` | `solve` loop, lines 115‑124【diagnostic_implementations】 | Warning only; solver stops early. |
| Relative error `err` ≤ `tolerance` after ≥ 1 iteration | `error = …, tolerance = …` (info) | `solve` loop, lines 129‑138【diagnostic_implementations】 | Solver terminates with `endcond = "tolerance"`. |
| Denominator `den` ≤ `threshold` at first iteration and first time step | `denominator threshold reached at first iteration of CG` … `Check the 'threshold' data field, you might decrease it` | `solve` loop, lines 166‑176【diagnostic_implementations】 | Warning only; solver stops early. |
| Denominator `den` ≤ `threshold` after ≥ 1 iteration | `den = …, smallDenominatorThreshold = …, err = …` (info) | `solve` loop, lines 181‑191【diagnostic_implementations】 | Solver terminates with `endcond = "threshold"`. |
| Denominator `den` == 0 | `den = 0.0, break the iterations` (warning) | `solve` loop, lines 197‑202【diagnostic_implementations】 | Iteration loop aborts. |
| Computed error `err` is NaN | `assert(!std::isnan(err));` | `solve` loop, line 108【diagnostic_implementations】 | Program aborts if the assertion fails. |
| No forces (‖b‖ = 0) | `null norm of vector b` (info) and optional threshold check | `solve` else‑branch, lines 215‑236【diagnostic_implementations】 | Solver performs a single check of the denominator; otherwise terminates without iteration. |

No explicit error codes are defined; the solver relies on warnings, info messages, and the `assert` to signal abnormal conditions.

### Limitations and Recommendations
* **Iterative nature** – The CGLinearSolver provides an approximate solution; convergence depends on system conditioning and on the chosen `iterations`, `tolerance`, and `threshold` values【usage_documentation】.  
* **Positive parameters** – `tolerance` and `threshold` must be non‑negative; negative user values are silently replaced by the default `1e-5` during `init`【diagnostic_implementations】.  
* **Denominator safety** – A zero denominator aborts the iteration loop, and a denominator below `threshold` triggers early termination. Users should ensure that the matrix is positive‑definite and well‑scaled to avoid frequent threshold warnings.  
* **Warm‑start usage** – Enabling `warmStart` reuses the previous solution as the initial guess, which can improve convergence for smoothly evolving systems but may also propagate errors if the previous solution is poor.  
* **Integration scheme requirement** – The solver assumes that an integration scheme upstream has already computed the RHS vector `b`. Absence of such a scheme leads to undefined residuals.  
* **No exact solution guarantee** – As noted in the component description, an exact solution cannot be guaranteed; the solver stops when either the tolerance or denominator threshold is met, or when the maximum iteration count is reached【usage_documentation】.  

**Recommendation:** Start with the default values (`iterations=25`, `tolerance=1e-5`, `threshold=1e-5`), verify that the residual norm decreases, and then adjust `iterations` upward or `tolerance`/`threshold` downward only after confirming that the system matrix is well‑conditioned. Use `warmStart` only when the simulation exhibits smooth temporal evolution.

**Local source references for this section**

- `F1`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/CGLinearSolver.inl`
- `F2`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/CGLinearSolver.h`
- `F3`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/MatrixLinearSolver.h`
- `F4`: `Sofa/Component/LinearSolver/Iterative/src/sofa/component/linearsolver/iterative/MatrixLinearSolver.inl`
- `F5`: `Sofa/framework/Core/src/sofa/core/behavior/IterativeSolver.h`
- `F6`: `Sofa/framework/Core/src/sofa/core/behavior/IterativeSolver.cpp`
