# Studio Phases 3 and 4: unified plan

**Date:** 2026-10-02
**Status:** working document, not yet validated with the client or the factory

This plan merges two research reports on the cadrage's Phase 3 (Sketch-to-Color studio) and Phase 4 (autonomous collection assistant):

- **Opus report:** "Noe Noah Studio — Phases 3 & 4 Research" (Claude Opus 5.5). It is the backbone of this plan.
- **Gemini report:** "Eyewear AI Design Stack Research" (Gemini 3.1 Pro). Its strongest points are folded in.
- **Review changes:** four amendments to the Opus plan, made after reading both against [the cadrage](cadrage_projet_radar_tendances_studio_ia_lunetterie.md).

Each section says where its content comes from. The external claims in both reports have not been checked on the web; the ones this plan depends on are listed under [Verify before building](#verify-before-building).

**Phase numbering.** "Phase 3" and "Phase 4" here follow the cadrage's roadmap. [build-plan.md](build-plan.md) uses the same numbers for social media and catalogue comparison. The two roadmaps need reconciling before this work is scheduled.

---

## 1. Core decisions

1. **Colour and lamination are computed, not generated.** *(Opus)* Each zone is rendered from the supplier's own swatch data, and lamination stripes are drawn from the layer stack. A diffusion model is never the source of truth for a colour or an edge. The cadrage requires renders based on real stock, and diffusion models drift on colour and invent plausible stripes.
2. **Diffusion is the finishing pass, and it is expected, not optional.** *(Review change to Opus)* The cadrage asks for photorealistic gloss and reflections. A flat compositor alone will probably not deliver that, so the finishing pass is part of the MVP. It runs inside locked masks and its output is checked against the swatch colours.
3. **The layer stack is a first-class data object.** *(Opus)* A lamination is an ordered list of SKUs with thicknesses, not a picture. Rendering, manufacturing checks and Phase 4 suggestions all read it.
4. **Manufacturing guardrails are a deterministic rules engine.** *(Opus)* Minimum thicknesses, hinge anchoring and tolerances are geometry checks. An LLM may explain a violation; it never decides one.
5. **LLMs orchestrate; they do not paint and they do not judge feasibility.** *(Both)* They extract catalogues, turn trend data into constraints, and write the rationale for a proposal.
6. **Every proposal is bound to stock.** *(Both)* A colour choice is a real SKU in an available thickness. The LLM reaches stock only through a query against the material database, so it cannot name a SKU that does not exist.
7. **Phase 4 suggests palettes and laminations, not new frame shapes.** *(Review change to Gemini)* This is the cadrage's wording. Shape generation through a brand LoRA is deferred.
8. **A designer approves everything.** *(Opus)* "Autonomous" means autonomous drafting. Every accept and reject is logged from the first day, because that record is what later scoring is trained on.

---

## 2. Prerequisite: the material database

This is the cadrage's Phase 2 deliverable, and nothing below works without it. *(Opus, with the cadrage's three-level colour nomenclature)*

**Per SKU:** supplier, code (Palier 3), name, collection, type (monocolour, havana, multilayer, laminated, gradient), available thicknesses, sheet sizes, minimum order, a flag for SKUs not made in temple thickness, swatch images (front-lit, back-lit, edge), measured Lab value, translucency class, embedding vector.

**Ingestion order:**

1. Structured files first (XLSX or a supplier feed), where a supplier publishes one.
2. PDF catalogues through a document parser plus a vision LLM that maps swatch image to code, name and thickness, with a human review queue.
3. Physical sample cases scanned under controlled light with a colour checker. Only these produce a "colour-verified" reference; PDF swatches are print and screen approximations.

---

## 3. Phase 3 walkthrough: Sketch-to-Color studio

### Step 1. Sketch in
The designer uploads a black-and-white technical drawing, vector (SVG, DXF) or bitmap. Bitmaps are vectorised and cleaned. The result is always stored as vectors. *(Both)*

### Step 2. Draw lamination zones
The designer traces zones by hand over the sketch; the cadrage specifies manual delimitation. Each zone is a closed path. Click-to-select with a segmentation model is a later convenience, not an MVP item, because line sketches are not the natural images those models are trained on. *(Opus; SAM demoted from Gemini's "required")*

### Step 3. Give the sketch its depth *(Review change)*
A front view does not contain what lamination stripes depend on. The editor asks for:

- section thickness of the front and of the temples,
- bevel profile on the edges where layers will show,
- the layer stack per zone: ordered SKUs with nominal and finished thickness.

Without these inputs the stripes would be guessed, which is the failure this plan exists to avoid.

### Step 4. Assign materials
Each zone gets a stack built from the material database. Face, temples, hinges and lenses are chosen separately. Only SKUs available in the needed thickness are offered.

### Step 5. Manufacturing check
The rules engine runs on every save. Starting rules *(Opus)*:

- endpiece width is at least the selected hinge's minimum width in plastic,
- no hinge pocket straddles a glue line unless the factory approves it,
- finished thickness covers groove depth plus a wall on both sides,
- temple stack thickness covers the core wire plus a wall,
- the engine models the stack **after** planing and polishing, since outer layers lose material and stripe proportions change.

All values are per factory and must be co-written with the manufacturer.

### Step 6. Deterministic render
- Each zone is filled from its swatch texture.
- Lamination stripes are drawn from the stack and the bevel geometry.
- A 2.5D or 3D extrusion gives gloss and translucency (physically based material with transmission, thickness and clearcoat).

**Patterned acetates need texture synthesis.** *(Review change)* Tortoiseshell and havana do not repeat. Tiling a small swatch photo looks fake, so these SKUs need a larger scan or a synthesised, non-repeating texture.

### Step 7. Photographic finishing
The deterministic render goes through an image model for lighting and reflections only. The recipe is Gemini's, used as a finishing pass instead of as the generator:

- line-art conditioning locks the silhouette,
- depth conditioning carries the acetate thickness,
- the swatch image is injected per zone through an image-prompt adapter,
- zone masks and edge pixels are locked,
- low denoise strength, so the model re-lights and does not repaint.

### Step 8. Colour verification
Each zone of the finished image is sampled, converted to CIELAB and compared with the swatch reference (ΔE2000). Small drift is corrected per zone; above a threshold the image is rejected. Thresholds are calibrated with physical swatches. Every render is labelled "illustrative" or "colour-verified", and the raw swatch is always shown beside it. *(Opus)*

### Step 9. Export
- **Tech pack:** SKU list, layer stacks, hinge, bill of materials, renders. *(Opus)*
- **DXF and SVG of the outline and zone boundaries**, for import into the factory's CAD (Rhino and Grasshopper are common in eyewear) and from there to CAM. *(Gemini)* This is what keeps an approved design from being a dead-end image. The studio stops at the vector export; toolpaths stay with the factory.

---

## 4. Phase 4 walkthrough: collection assistant

**Starting version** *(Review change: simpler than either report)*

1. **Read the market signal that already exists.** The radar computes frequent colour pairings from lamination tags (`color_pairings` in [retail.py](../backend/app/scoring/retail.py)), flags best-sellers, and stores supplier codes. That is the "market correlations" input the cadrage asks for.
2. **Generate candidates from stock only.** Enumerate stacks and palettes from in-stock SKUs in the needed thicknesses.
3. **Filter with the Phase 3 rules engine.** A candidate that fails a manufacturing rule is never shown.
4. **Rank.** Score by trend strength, colour harmony (in CIELAB or OKLCH) and distance to the brand's signature models.
5. **Render and verify** through Phase 3 steps 6 to 8.
6. **Present a ranked board.** Each proposal carries its trend justification *(Gemini)*, written by the LLM from the radar's numbers.
7. **Designer selects; decisions are logged.**

**Later, once the logged decisions exist**

- Trained scorers on accept and reject history. *(Opus)*
- An agent framework and long-running workflows, if the simple loop proves limiting. *(Opus)*
- A brand style LoRA, trained only on images Noé & Noah owns. *(Both)*

**Brand DNA** is built in two layers *(Opus)*: structured descriptors measured from the signature library (lens width to height ratio, bridge, endpiece shape, temple profile) and image embeddings. Compatibility rules between shapes and materials come from designer interviews.

---

## 5. Stack

The repo already runs FastAPI, SQLAlchemy and Alembic on the backend and Next.js with React on the frontend, so the studio extends the existing application.

| Layer | MVP choice | Notes |
|---|---|---|
| Editor | 2D canvas library in the existing React frontend | Paper.js has the strongest path booleans; Konva the best interactive layers; Fabric.js has native SVG serialisation *(Gemini)*. Decide with a one-day spike on zone drawing and SVG round-trip. |
| 3D preview | Three.js physically based material | Canvas for editing, WebGL only for the viewer *(both)* |
| Sketch ingestion | Vectoriser plus OpenCV cleanup | Manual tracing stays the fallback |
| Renderer | 2.5D compositor in Python or a WebGL shader | Blender headless for hero renders later |
| Finishing | ComfyUI or Diffusers pipeline on serverless GPU | Apache-licensed base model for self-hosting |
| Rules engine | Python with pydantic and Shapely | Versioned, co-owned by the factory |
| Catalogue ingestion | XLSX import, document parser, vision LLM, review UI | |
| Database | PostgreSQL with pgvector | The repo defaults to SQLite today; embeddings need the move |
| Phase 4 LLM | The provider already used for article extraction | Tool calls against the stock database only |

---

## 6. First milestone: rendering bake-off

Four weeks, about ten real Noé & Noah sketches *(Opus)*, comparing:

1. the 2.5D compositor alone,
2. the 3D physically based extrusion,
3. the compositor plus diffusion finishing,
4. a commercial sketch-to-render tool as an outside benchmark.

**Measured:** per-zone ΔE2000, lamination-edge accuracy against a physical sample, designer preference. The result settles how much finishing the MVP needs and which editor inputs in step 3 are really required.

The cadrage already lists the two inputs this needs: a test set of 20 black-and-white sketches and 2 to 3 supplier catalogues.

---

## Verify before building

- **Mazzucchelli's 2026 catalogue as XLSX.** The Opus report states it; the ingestion order depends on it.
- **Hinge minimum widths and sheet thicknesses.** The starting values come from a hinge maker's catalogue and maker blogs, not from a standard. They are placeholders until the factory signs the rule pack.
- **Model licences.** Check the licence of every base model and segmentation model at build time; several popular weights are non-commercial.
- **The Black Eyewear and Google Cloud case** cited by Gemini as a precedent for encoding a founder's taste. Worth reading if it holds up; not checked.

## Open questions for the client

- **Does the Asia exclusion cover suppliers?** The cadrage excludes Asia as a market. The Opus report proposes Japanese and Chinese acetate suppliers as catalogue sources, and both reports cite Chinese OEM pages for manufacturing figures.
- **Which factory co-owns the manufacturing rules,** and which hinge references does it use?
- **What does "prêtes pour l'échantillonnage" require as a file?** A tech pack, a DXF, or both.
- **Which roadmap governs:** the cadrage's phases or the build plan's.

## Left out on purpose

- Generating new frame shapes with a LoRA (outside the cadrage's Phase 4).
- CAM and G-code generation (the factory's job, downstream of the DXF).
- RAG over manufacturing rules and stock (structured data is queried directly).
- Virtual try-on (downstream of an approved design; a possible partnership, not a build).
