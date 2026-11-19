# BarycentricMapping - Technical Documentation

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

BarycentricMapping is a linear mapping component defined in the *sofa::component::mapping::linear* namespace. It belongs to the Sofa.Component.Mapping.Linear category and implements a mapping that expresses the state of a child mechanical object in terms of barycentric coordinates relative to the cells of its parent object. Within the SOFA scene‑graph, the component establishes a data flow from the parent’s degrees of freedom to the child, allowing the child to inherit deformations through the computed barycentric weights [SOFA Evidence – official documentation, introduction paragraph].

### Numerical or Physical Problem

The component addresses the problem of transferring geometric and physical quantities (such as positions, velocities, or forces) from a coarse or differently discretized parent mesh to a finer or otherwise distinct child mesh. This situation commonly arises when multiple representations of the same physical object are required—for example, a simplified mesh for collision detection and a detailed mesh for visual rendering. The underlying scientific challenge is to interpolate values defined on the parent cells to arbitrary points inside those cells while preserving continuity and consistency of the physical fields [Scientific Context – barycentric‑coordinates.pdf, pages 1‑3].

### General Approach

BarycentricMapping resolves the interpolation task by computing barycentric coordinates of each child point with respect to the enclosing cell of the parent mesh. These coordinates serve as weighting factors that sum to unity and are non‑negative for points inside the cell. The child’s quantities are then obtained as a weighted combination of the corresponding parent quantities, ensuring that the interpolation reproduces the exact values at the cell vertices and varies smoothly inside the cell. This conceptual algorithm leverages the geometric properties of barycentric coordinates to provide a robust and mathematically sound mapping between the two meshes [Scientific Context – barycentric‑coordinates.pdf, pages 1‑3].

## 2. Architecture and Inheritance

### Class Architecture

- **Namespace / Module**: `sofa::component::mapping::linear` – the class is part of the **Sofa.Component.Mapping.Linear** module (source file *F1*: `Sofa/Component/Mapping/Linear/src/sofa/component/mapping/linear/BarycentricMapping.h`).  
- **Template Parameters**: `BarycentricMapping<TIn, TOut>` is a class template that follows the same template signature as its base `LinearMapping<TIn,TOut>` (see the class declaration at line 40 of *F1*).  
- **Header / Source Layout**  
  - Declaration: `BarycentricMapping.h` (*F1*).  
  - Inline implementation helpers: `BarycentricMapping.inl` (*F3*).  
  - Out‑of‑line definitions: `BarycentricMapping.cpp` (*F2*).  

The class is a **mapping component** that converts mechanical states from a parent model to a child model using barycentric coordinates.

### Inheritance Hierarchy

| Level | Class | Relationship | Source |
|-------|-------|--------------|--------|
| Direct | `LinearMapping<TIn,TOut>` | **public** inheritance (CRTP) | class declaration line 40, *F1* |
| Indirect | *Not explicitly documented in the supplied C++ sources* | – | – |

> **Discrepancy note** – The official documentation lists `CRTPLinearMapping` as a documented parent (see *official_documentation.template_groups[0].documented_parents*). The C++ source, however, shows a direct inheritance from `LinearMapping<TIn,TOut>` (see *architecture.classes*). According to rule 5, the implementation evidence takes precedence; the documentation discrepancy is recorded here.

### Inherited and Local Responsibilities

#### Inherited interfaces (from `LinearMapping<TIn,TOut>` and its ancestors)

- **Mapping lifecycle**: `init()`, `reinit()` – overridden in `BarycentricMapping` (declarations at lines 71‑72 of *F1*, definitions in *F3* lines 239‑278).  
- **Mechanical mapping operations**: `apply`, `applyJ`, `applyJT` (both mechanical‑parameter and constraint‑parameter overloads) – overridden (declarations lines 73‑76 of *F1*, definitions in *F3* lines 293‑328 and 372‑381).  
- **Visualization**: `draw(const core::visual::VisualParams*)` – overridden (declaration line 80 of *F1*, definition lines 349‑368 of *F3*).  
- **Topology change handling**: `handleTopologyChange(core::topology::Topology*)` – overridden (declaration line 81 of *F1*, definition lines 385‑393 of *F3*).  
- **Matrix accessors**: `getJ()`, `getJs()` – declared (lines 78‑79 of *F1*) but not implemented in the supplied files (status *unresolved*).  

These methods constitute the generic mapping contract defined by the base class hierarchy.

#### Local responsibilities (implemented uniquely in `BarycentricMapping`)

- **Barycentric mapper creation**: `createMapperFromTopology()` – builds a topology‑specific mapper (definition lines 141‑236 of *F3*).  
- **Topology population**: `populateTopologies()` – registers the required topologies (definition lines 111‑138 of *F3*).  
- **Mapper initialization**: `initMapper()` – finalizes the mapper after topology is known (definition lines 281‑290 of *F3*).  
- **Accessor to the concrete mapper**: `getMapper()` – inline accessor (inline definition lines 84‑87 of *F1*).  
- **Data field**: `d_useRestPosition` – a public `Data<bool>` controlling whether rest positions are used for initialization (declared line 65 of *F1*).  

These members provide the barycentric‑specific behavior that distinguishes the component from other linear mappings.

### Architectural Dependencies

#### Compile‑time (header) dependencies

- `sofa/component/mapping/linear/config.h` – module configuration.  
- `sofa/component/mapping/linear/LinearMapping.h` – base class definition (declared in *F1* includes).  
- `sofa/component/mapping/linear/BarycentricMappers/TopologyBarycentricMapper.h` – generic topology mapper interface.  
- `sofa/core/Mapping.h` – core mapping abstract base.  
- `sofa/core/topology/BaseMeshTopology.h` – topology base class used for mapper selection.  
- `sofa/defaulttype/VecTypes.h`, `sofa/type/vector.h` – vector and container types.  

Additional includes in the implementation files (*F2* and *F3*) bring in:

- Specific topology mapper headers (e.g., `BarycentricMapperMeshTopology.h`, `BarycentricMapperRegularGridTopology.h`, …) required to instantiate the correct mapper for the parent topology.  
- `sofa/linearalgebra/EigenSparseMatrix.h` – sparse matrix support for Jacobian handling.  
- `sofa/core/visual/VisualParams.h`, `sofa/core/behavior/MechanicalState.h` – used in `draw` and mapping operations.  
- `sofa/simulation/Simulation.h` – access to the simulation context during mapper creation.  

#### Runtime / scene‑graph dependencies

- **Topologies**: The component interacts with various topology containers (mesh, regular grid, sparse grid, edge set, triangle set, quad set, tetrahedron set, hexahedron set) through the mapper classes listed above.  
- **Mechanical states**: Mapping functions operate on `Data<typename In::VecCoord>` and `Data<typename Out::VecCoord>` (and their derivative counterparts), linking the parent and child mechanical states.  
- **Visual parameters**: `draw` uses `core::visual::VisualParams` to render mapping information.  

These dependencies reflect the component’s role within SOFA’s scene‑graph architecture: it sits between a **parent mechanical model** (source topology) and a **child mechanical model**, translating positions, velocities, and forces via barycentric coordinates.  

*Scientific Context*: The modular, component‑based design described in the SOFA framework (e.g., scene‑graph‑based multi‑model representation) underpins this architecture, allowing the mapping component to be swapped or reconfigured without affecting other parts of the simulation (see *faure_springer12.pdf* pages 2‑5).

**Local source references for this section**

- `F1`: `Sofa/Component/Mapping/Linear/src/sofa/component/mapping/linear/BarycentricMapping.h`
- `F2`: `Sofa/Component/Mapping/Linear/src/sofa/component/mapping/linear/BarycentricMapping.cpp`
- `F3`: `Sofa/Component/Mapping/Linear/src/sofa/component/mapping/linear/BarycentricMapping.inl`

## 3. Mathematical Formulation

### Mathematical Problem

The **BarycentricMapping** component implements a linear mapping from a *parent* mechanical model to a *child* model.  
For each degree of freedom (position, velocity, etc.) of a child node, the unknown quantity $\mathbf{x}^{\text{out}}$ is expressed as a weighted sum of the corresponding quantities $\mathbf{x}^{\text{in}}_k$ of the parent nodes that belong to the same topological cell (e.g., a triangle or tetrahedron).  
The weights are the **barycentric coordinates** of the child point with respect to that cell.

Formally, the problem is to find, for every child node $i$,

```math
\mathbf{x}^{\text{out}}_i = \sum_{k=1}^{N_c} \lambda_{ik}\,\mathbf{x}^{\text{in}}_{c_k},
```

where  

* $N_c$ – number of vertices of the parent cell containing the child point,  
* $c_k$ – index of the $k$-th parent vertex of that cell,  
* $\lambda_{ik}$ – barycentric coordinate of child node $i$ relative to vertex $c_k$ (see Scientific Context below),  
* $\mathbf{x}^{\text{in}}_{c_k}$ – input (parent) quantity (position, velocity, …),  
* $\mathbf{x}^{\text{out}}_i$ – output (child) quantity to be produced.

The same linear relation is used for the Jacobian‑vector products (`applyJ`) and the transpose Jacobian‑vector products (`applyJT`) required by SOFA’s mechanical solvers.

*Source:* SOFA documentation states that the component “Mapping using barycentric coordinates of the child with respect to cells of its parent”【SOFA Documentation】.

### Mathematical Formulation

#### Barycentric coordinates

For a point $P$ inside a simplex (segment, triangle, tetrahedron) with vertices $\{V_1,\dots,V_{N_c}\}$, the barycentric coordinates $\{\lambda_k\}$ satisfy  

```math
\sum_{k=1}^{N_c} \lambda_k = 1,\qquad
\lambda_k \ge 0 \;\;(\text{inside the simplex}),
```

and the geometric interpolation property  

```math
P = \sum_{k=1}^{N_c} \lambda_k V_k .
```

In 2‑D (triangle) the coordinates can be expressed by area ratios  

```math
\lambda_1 = \frac{\operatorname{area}(P V_2 V_3)}{\operatorname{area}(V_1 V_2 V_3)},\quad
\lambda_2 = \frac{\operatorname{area}(V_1 P V_3)}{\operatorname{area}(V_1 V_2 V_3)},\quad
\lambda_3 = \frac{\operatorname{area}(V_1 V_2 P)}{\operatorname{area}(V_1 V_2 V_3)},
```

and analogously in 3‑D by volume ratios.  
These definitions are described in the scientific reference *barycentric‑coordinates.pdf* (pages 1‑3)【Scientific Context: barycentric‑coordinates.pdf p.1‑3】.

#### Mapping equations

Given the barycentric matrix $\Lambda \in \mathbb{R}^{N_{\text{out}}\times N_{\text{in}}}$ whose entry $\Lambda_{ik}= \lambda_{ik}$ (zero if parent vertex $k$ does not belong to the cell of child node $i$), the mapping reads  

```math
\boxed{\; \mathbf{X}^{\text{out}} = \Lambda \,\mathbf{X}^{\text{in}} \;}
```

where $\mathbf{X}^{\text{in}}$ and $\mathbf{X}^{\text{out}}$ are column vectors stacking all input and output DOFs respectively.  

The Jacobian of the mapping is precisely the matrix $\Lambda$; consequently  

* **applyJ** computes $\mathbf{Y}^{\text{out}} = \Lambda \,\mathbf{Y}^{\text{in}}$ for derivative vectors,  
* **applyJT** computes $\mathbf{Y}^{\text{in}} = \Lambda^{\!\top} \mathbf{Y}^{\text{out}}$ for adjoint vectors.

*Source:* The component’s C++ interface declares these operations (`apply`, `applyJ`, `applyJT`) in *BarycentricMapping.h* (methods `apply`, `applyJ`, `applyJT` lines 73‑76)【F1:71‑76】. The implementation files confirm that the same linear combination is performed, although the bodies are not examined for internal algorithmic detail【F2:293‑303】【F2:306‑315】【F2:319‑328】.

### Numerical Algorithm

The documented algorithm consists of the following high‑level steps (as inferred from the public method list and the component description):

1. **Topology analysis** – `populateTopologies()` builds the correspondence between child nodes and parent cells.  
2. **Barycentric weight computation** – `createMapperFromTopology()` evaluates the barycentric coordinates $\lambda_{ik}$ for each child node with respect to its parent cell (using the geometric definitions from the scientific context).  
3. **Matrix assembly** – the weights are stored in a sparse linear mapper (accessible via `getMapper()`).  
4. **Linear evaluation** – `apply()` (and the derivative variants `applyJ`, `applyJT`) multiply the input vector(s) by the pre‑computed weight matrix to produce the output.

These steps are documented by the presence of the corresponding methods in the source files:

* `populateTopologies()` – defined in *BarycentricMapping.inl* lines 111‑138【F2:111‑138】.  
* `createMapperFromTopology()` – defined in *BarycentricMapping.inl* lines 141‑236【F2:141‑236】.  
* `apply`, `applyJ`, `applyJT` – definitions in *BarycentricMapping.inl* lines 293‑328【F2:293‑328】.  

The component does **not** expose any additional algorithmic parameters beyond the optional `useRestPosition` flag (`d_useRestPosition`), which selects whether the rest positions of the models are used during the initial weight computation (default `false`)【F1:65】.

*Note:* The exact numerical procedure for computing the barycentric coordinates (e.g., area‑based formulas, solving a small linear system) is not detailed in the supplied SOFA source or documentation; therefore it is not asserted here. The description above reflects only the officially documented mapping relationship and the verified C++ interfaces.

**Local source references for this section**

- `F1`: `Sofa/Component/Mapping/Linear/src/sofa/component/mapping/linear/BarycentricMapping.h`
- `F2`: `Sofa/Component/Mapping/Linear/src/sofa/component/mapping/linear/BarycentricMapping.inl`

## 4. Internal Architecture and Execution

### Internal Responsibilities
The `BarycentricMapping` class derives from `LinearMapping<TIn,TOut>` and manages a topology‑based mapper that computes barycentric coordinates between an input and an output mechanical state. Its key internal members are:

* `d_useRestPosition` – a boolean flag (default false) controlling whether the mapper is initialized with rest positions or current positions [SOFA Evidence, F2 line 65].
* `d_mapper` – a link to a `TopologyBarycentricMapper` instance created according to the input topology [SOFA Evidence, F2 line 77].
* `d_input_topology` / `d_output_topology` – links to the input and output `BaseMeshTopology` containers [SOFA Evidence, F2 lines 78‑79].
* `internalMatrix` – an `EigenSparseMatrix` allocated in each constructor for internal linear algebra use [SOFA Evidence, F1 line 74‑79].

Principal methods and their responsibilities:

| Method | Responsibility | Source |
|--------|----------------|--------|
| `init()` | Sets component state to *Invalid*, calls base init, populates topologies, creates a mapper if missing, initializes the mapper, then marks the component *Valid* | [F1 239‑268] |
| `reinit()` | Clears the existing mapper and re‑initializes it | [F1 271‑278] |
| `apply()` | Resizes the mapper to the output model and applies the mapping to positions | [F1 293‑303] |
| `applyJ()` | Applies the Jacobian (velocity) mapping | [F1 306‑315] |
| `applyJT()` (mechanical) | Applies the transpose Jacobian (force) mapping for velocities | [F1 319‑328] |
| `applyJT()` (constraint) | Applies the transpose Jacobian for constraint matrices | [F1 372‑381] |
| `draw()` | Visualises output points and mapping lines when display flags are enabled | [F1 349‑368] |
| `handleTopologyChange()` | Forwards topology modifications to the internal mapper | [F1 385‑393] |
| `populateTopologies()` | Retrieves or validates input/output topologies from the surrounding context | [F1 111‑138] |
| `createMapperFromTopology()` | Instantiates a concrete mapper class based on the concrete type of the input topology (regular grid, sparse grid, mesh, etc.) | [F1 141‑236] |
| `initMapper()` | Calls the mapper’s `init` with either rest or current positions depending on `d_useRestPosition` | [F1 281‑290] |
| `getMapper()` | Returns the raw pointer to the internal mapper | [F2 84‑87] |

### Execution Workflow
1. **Construction** – The constructor allocates `internalMatrix` and, if a mapper is supplied, registers it as a slave [F1 74‑79]. When only an input topology is given, `populateTopologies()` and `createMapperFromTopology()` are invoked immediately [Constructor F1 89‑94].
2. **Component Initialization (`init`)** –  
   * Component state set to *Invalid* [239].  
   * Base class `LinearMapping` initialization via `Inherit1::init()` [239].  
   * `populateTopologies()` ensures `d_input_topology` and `d_output_topology` are valid [239‑268].  
   * If `d_mapper` is null, `createMapperFromTopology()` attempts to build a suitable mapper [239‑268].  
   * When a mapper exists and the output model is present, `initMapper()` configures it with the appropriate positions [239‑268].  
   * Component state finally set to *Valid* [268].
3. **Re‑initialization (`reinit`)** – Clears the existing mapper and re‑calls `initMapper()` to reflect any topology changes [271‑278].
4. **Simulation Step** –  
   * `apply()` maps positions from the input to the output model [293‑303].  
   * `applyJ()` maps velocities (or derivatives) [306‑315].  
   * `applyJT()` (mechanical) maps forces back to the input [319‑328]; the overload with `ConstraintParams` maps constraint matrices [372‑381].
5. **Visualization** – `draw()` renders output points and, if a mapper is present, the mapping lines [349‑368].
6. **Topology Updates** – When the scene topology changes, `handleTopologyChange()` forwards the change to the mapper for internal updates [385‑393].

The workflow terminates when the component is destroyed; the allocated `internalMatrix` is released by the destructor (implicit in the class definition).

### Delegation and Component Interactions
* **Inheritance** – `BarycentricMapping` inherits from `LinearMapping<TIn,TOut>`; base initialization is delegated to `Inherit1::init()` [init F1 239].  
* **Slave Registration** – Whenever a mapper is created (`createMapperFromTopology`) it is added as a slave to the mapping component via `this->addSlave(d_mapper.get())` [createMapperFromTopology F1 236‑241].  
* **Mapper Interface** – All mapping operations (`apply`, `applyJ`, `applyJT`, `draw`, `processTopologicalChanges`) are delegated to the concrete `TopologyBarycentricMapper` instance stored in `d_mapper`. The component does not implement the mathematical operations itself.  
* **Topology Containers** – `populateTopologies()` queries the surrounding context (`fromModel->getContext()->get(topology)`) to obtain `BaseMeshTopology` objects for both input and output models [populateTopologies F1 111‑138].  
* **External Objects** – The mapper classes (`BarycentricMapperRegularGridTopology`, `BarycentricMapperMeshTopology`, etc.) are instantiated via `sofa::core::objectmodel::New<>` and receive the topology containers as arguments [createMapperFromTopology F1 151‑236].

### Execution Modes and Specific Behavior
* **Mapper Selection** – `createMapperFromTopology()` chooses a mapper based on runtime type checks (`is_a<...>`). Different branches handle regular grids, sparse grids, and generic mesh topologies, each creating a distinct mapper class [createMapperFromTopology F1 151‑236]. The `goto end;` statements ensure only one mapper is instantiated.
* **Rest‑Position Mode** – If the data attribute `useRestPosition` is true, `initMapper()` initializes the mapper with rest positions; otherwise it uses current positions [initMapper F1 281‑290].
* **Null‑Mapper Guard** – All mapping methods (`apply`, `applyJ`, `applyJT`, `draw`) first verify `d_mapper != nullptr` before delegating, preventing crashes when no compatible topology is found [apply F1 293‑303; applyJ F1 306‑315; applyJT F1 319‑328; draw F1 349‑368].
* **Overloaded `applyJT`** – Two overloads exist: one for `MechanicalParams` (velocity/force mapping) and one for `ConstraintParams` (constraint matrix mapping). Both forward to the mapper but accept different data types [applyJT F1 319‑328 and F1 372‑381].
* **Visualization Flag** – `draw()` early‑exits if `vparams->displayFlags().getShowMappings()` is false or if the component state is not *Valid* [draw F1 349‑368].
* **Topology Change Propagation** – `handleTopologyChange()` forwards the changed topology to the mapper, passing current positions of both models [handleTopologyChange F1 385‑393].

These conditional paths and overloads define the component’s execution modes, all directly reflected in the source implementation.

**Local source references for this section**

- `F1`: `Sofa/Component/Mapping/Linear/src/sofa/component/mapping/linear/BarycentricMapping.inl`
- `F2`: `Sofa/Component/Mapping/Linear/src/sofa/component/mapping/linear/BarycentricMapping.h`

## 5. Data Fields and Links

### Local Data Fields
| C++ attribute | Exposed SOFA name | C++ type | Default value / expression | Functional description | Declaration / Initialization |
|---|---|---|---|---|---|
| `d_useRestPosition` | `useRestPosition` | `Data< bool >` | `false` (default_expression) | Use the rest position of the input and output models to initialize the mapping | Declared in **F1** at line 65 (origin *local*)【source_files:F1】; default expression taken from the structured attribute; also referenced in the constructor of **F2** (lines 76 & 91)【constructor_evidence:sofa_parameters】 |

### Inherited Data Fields
No verified inherited `SOFA_Data` fields are present in the supplied C++ evidence for `BarycentricMapping`. The component derives from `LinearMapping<TIn,TOut>`, but the specific data fields inherited from that base class are not listed in the available source files.

#### Documentation‑Only Data Fields
| Exposed SOFA name | Documented default | Functional description | Documentation reference |
|---|---|---|---|
| `name` | `unnamed` | object name | D1 |
| `printLog` | `0` | if true, emits extra messages at runtime. | D1 |
| `tags` | *(empty)* | list of the subsets the object belongs to | D1 |
| `bbox` | *(empty)* | this object bounding box | D1 |
| `componentState` | `Undefined` | The state of the component among (Dirty, Valid, Undefined, Loading, Invalid). | D1 |
| `listening` | `0` | if true, handle the events, otherwise ignore the events | D1 |
| `mapForces` | `1` | Are forces mapped ? | D1 |
| `mapConstraints` | `1` | Are constraints mapped ? | D1 |
| `mapMasses` | `1` | Are masses mapped ? | D1 |
| `mapMatrices` | `0` | Are matrix explicit mapped? | D1 |
| `applyRestPosition` | `0` | set to true to apply this mapping to restPosition at init | D1 |
| `useRestPosition` | `0` | Use the rest position of the input and output models to initialize the mapping | D1 |

*The C++ ownership and inheritance origin of the above fields are not verified in the provided source code.*

### Links and Component References

#### Verified C++ Links
| C++ attribute | Exposed SOFA name | Owner class (origin) | Link type | Destination type | Purpose / description | Verified flags | Declaration / Constructor sources |
|---|---|---|---|---|---|---|---|
| `d_mapper` | `mapper` | `BarycentricMapping` (local) | `SingleLink<BarycentricMapping<In,Out>, Mapper, BaseLink::FLAG_STRONGLINK>` | `Mapper` (template‑dependent) | Internal mapper created depending on the type of topology | `FLAG_STRONGLINK` | Declared in **F1** line 67【source_files:F1】; initialized in **F2** constructor lines 77 & 92 with `initLink("mapper","Internal mapper created depending on the type of topology")`【constructor_evidence:link_fields】 |
| `d_input_topology` | `input_topology` | `BarycentricMapping` (local) | `SingleLink<BarycentricMapping<In,Out>, BaseMeshTopology, BaseLink::FLAG_STRONGLINK>` | `BaseMeshTopology` | Input topology container (usually the surrounding domain). | `FLAG_STRONGLINK` | Declared in **F1** line 68【source_files:F1】; initialized in **F2** constructor lines 78 & 93 with `initLink("input_topology","Input topology container (usually the surrounding domain).")`【constructor_evidence:link_fields】 |
| `d_output_topology` | `output_topology` | `BarycentricMapping` (local) | `SingleLink<BarycentricMapping<In,Out>, BaseMeshTopology, BaseLink::FLAG_STRONGLINK>` | `BaseMeshTopology` | Output topology container (usually the immersed domain). | `FLAG_STRONGLINK` | Declared in **F1** line 69【source_files:F1】; initialized in **F2** constructor lines 79 & 94 with `initLink("output_topology","Output topology container (usually the immersed domain).")`【constructor_evidence:link_fields】 |

#### Documentation‑Only Links
| Exposed SOFA name | Destination type (as documented) | Purpose / description | Documentation reference |
|---|---|---|---|
| `context` | `BaseContext` | Graph Node containing this object (or `BaseContext::getDefault()` if no graph is used) | D1 |
| `slaves` | `BaseComponent` | Sub‑objects used internally by this object | D1 |
| `master` | `BaseComponent` | `nullptr` for regular objects, or master object for which this object is one sub‑object | D1 |
| `input` | `State<Vec3d>` | Input object to map | D1 |
| `output` | `State<Rigid3d>` | Output object to map | D2 |
| `mapper` | `TopologyBarycentricMapper<Vec3d,Rigid3d>` | Internal mapper created depending on the type of topology | D2 |
| `input_topology` | `BaseMeshTopology` | Input topology container (usually the surrounding domain). | D1 |
| `output_topology` | `BaseMeshTopology` | Output topology container (usually the immersed domain). | D1 |
| `output` | `State<Vec3d>` | Output object to map | D3 |
| `mapper` | `TopologyBarycentricMapper<Vec3d,Vec3d>` | Internal mapper created depending on the type of topology | D3 |

*These links are described in the official documentation but are not present as explicit C++ `Link` declarations in the supplied source files.*

### Configuration Constraints and Interactions
- **Required‑field indicators:** None reported in the constructor evidence.  
- **Read‑only fields / constructor modifications:** No fields are marked read‑only; the only constructor‑time modification observed is the optional addition of a slave mapper when a non‑null `mapper` pointer is passed (see **F2** constructor body lines 74‑76).  
- **Deprecated parameters:** No deprecated fields are listed in either the C++ evidence or the official documentation.  
- **Discrepancies:** The `useRestPosition` field appears both as a locally declared `Data<bool>` with default `false` (C++ evidence) and as a documented data field with default `0` (documentation). These defaults are equivalent (`0` → `false`), so no real conflict exists.  
- **Missing evidence:** The inheritance chain (`LinearMapping<TIn,TOut>`) may provide additional data fields and links, but such members are not present in the supplied source files; consequently they are reported only as documentation‑only items.

**Local source references for this section**

- `F1`: `Sofa/Component/Mapping/Linear/src/sofa/component/mapping/linear/BarycentricMapping.h`
- `F2`: `Sofa/Component/Mapping/Linear/src/sofa/component/mapping/linear/BarycentricMapping.inl`

## 6. Diagnostics and Usage

### Practical Usage and Integration
`BarycentricMapping` maps the degrees of freedom of a child model to the barycentric coordinates of its parent cells. It requires a **mechanical state** for both the source (`fromModel`) and the target (`toModel`) and relies on topology containers that describe the surrounding (input) and immersed (output) domains. The component automatically creates an internal mapper based on the type of the input topology (regular grid, sparse grid, mesh, etc.) — see the implementation of `createMapperFromTopology` (F1:141‑236).

A documented scene demonstrates typical integration:

```xml
<Node name="Collision">
    <MechanicalObject name="collisMecha" src="@../../meshLoader" />
    <TriangleSetTopologyContainer src="@../../meshLoader" />
    <TriangleCollisionModel />
    <LineCollisionModel />
    <PointCollisionModel />
    <BarycentricMapping />
</Node>

<Node name="Visualization">
    <OglModel name="VisualModel1" src="@../../meshLoader" useNormals="0" />
    <TriangleSetTopologyContainer src="@../../meshLoader" />
    <BarycentricMapping />
</Node>
```

The example (validated as documented, runtime‑unverified) shows the component placed under a node that provides both a mechanical object and a topology container, and it is required to load the `Sofa.Component.Mapping.Linear` plugin (usage_example section). No additional parameters are needed for basic operation.

### Configuration Guidelines
- **`useRestPosition`** (`d_useRestPosition`) – Data\<bool\>, default `false`. When set to `true`, the mapper is initialized with the rest positions of the input and output models instead of the current positions (initMapper implementation, F1:281‑290). This attribute is local to `BarycentricMapping` (configuration entry, F2:65).
- **Topology links** – `input_topology` and `output_topology` are internal links initialized in the constructors (F1:74‑79). If not explicitly set, `populateTopologies()` attempts to retrieve the nearest `BaseMeshTopology` from the context of the associated mechanical states (F1:111‑138). No explicit user‑visible fields are required; the component will infer them when possible.
- **Mapper link** – `mapper` can be provided manually; otherwise it is created automatically by `createMapperFromTopology()` (F1:74‑79, 141‑236). This link is optional and read‑only from the user perspective.
- No deprecated fields are documented for this component.

### Diagnostics and Troubleshooting
| Trigger | Diagnostic emitted | Observed behavior | Evidence |
|---|---|---|---|
| No compatible input topology found after `createMapperFromTopology()` | `msg_error() << "No compatible input topology found. …"` | `init()` aborts, leaving the component state **Invalid**; subsequent mapping calls are ignored. | `init` implementation (F1:239‑268) |
| Missing input mechanical state or topology during `populateTopologies()` | `msg_error() << "No input mechanical state found …"` or `msg_error() << "No input topology found …"` | The component cannot infer `input_topology`; mapping will remain invalid. | `populateTopologies` (F1:111‑138) |
| Missing output mechanical state during `populateTopologies()` | `msg_error() << "No output mechanical state found …"` | `output_topology` remains unset; mapping may still work if the mapper does not need it, but the component state stays **Invalid**. | `populateTopologies` (F1:111‑138) |
| `d_mapper` remains `nullptr` after topology analysis | No explicit error (the earlier “No compatible input topology” error applies). | `init()` returns early; component stays **Invalid**. | `init` (F1:239‑268) |
| Component state not **Valid** when `draw()` is called | Early return from `draw()` (no visual output). | No mapping visualization is rendered. | `draw` implementation (F1:349‑368) |
| Successful mapper creation | `msg_info() << "Creating …Mapper"` (e.g., “Creating SparseGridMapper”) | Component proceeds to `initMapper()` and sets state to **Valid**. | `createMapperFromTopology` (F1:141‑236) |

No warnings or assertions beyond the explicit `msg_error`/`msg_info` calls are present in the supplied source.

### Limitations and Recommendations
- **Topology compatibility** – The mapper only supports input topologies derived from `BaseMeshTopology`. Supported concrete types include `RegularGridTopology`, `SparseGridTopology`, and mesh topologies with non‑zero element counts (hexas, tetras, quads, triangles, edges). If the input topology does not match any of these, a generic `MeshMapper` is used, which may be less efficient. This behavior is defined in `createMapperFromTopology` (F1:141‑236).
- **Volume requirement** – For regular and sparse grids, the topology must report `hasVolume()` = `true`; otherwise the mapper is not created (F1:151‑162, 176‑187). Users should ensure volumetric grids when mapping 3‑D positions.
- **Component state** – The component is considered operational only after `init()` sets `ComponentState::Valid`. Calls to mapping functions (`apply`, `applyJ`, etc.) silently do nothing if `d_mapper` is `nullptr`. Verify the component state in logs if mapping appears inactive.
- **Rest‑position usage** – Enabling `useRestPosition` changes the data used for initialization but does not affect runtime mapping; it is intended for scenarios where the rest configuration must be preserved. Set this flag only when the rest positions are meaningful for the simulation.
- **Plugin dependencies** – The example shows that several plugins (e.g., `Sofa.Component.Mapping.Linear`, `Sofa.Component.Topology.Container.Grid`) must be loaded for the required topology types. Ensure these plugins are declared in the scene’s `<RequiredPlugin>` list.

Following these recommendations—providing a compatible input topology, verifying that the component reaches a **Valid** state, and loading the necessary plugins—will ensure reliable operation of `BarycentricMapping`.

**Local source references for this section**

- `F1`: `Sofa/Component/Mapping/Linear/src/sofa/component/mapping/linear/BarycentricMapping.inl`
- `F2`: `Sofa/Component/Mapping/Linear/src/sofa/component/mapping/linear/BarycentricMapping.h`
