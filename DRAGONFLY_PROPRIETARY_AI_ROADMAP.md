# DragonFly Proprietary AI Roadmap

Date: 2026-10-21. Status: planning and governance foundation; **no data collection, weight download, training, paid inference or production engine change performed**. See the [dependency audit](DRAGONFLY_DEPENDENCY_AUDIT.md) and [self-hosting design](DRAGONFLY_SELF_HOSTING_ARCHITECTURE.md).

## Ownership And Product Boundaries

Separate three goals:

1. **Operational independence:** run inference/storage/identity on owner-controlled hardware without mandatory third-party AI APIs/SaaS.
2. **Model customization:** adapt a commercially reviewed model using datasets DragonFly is permitted to use. Base weights, adapters, runtime, datasets and outputs can have different licenses.
3. **Proprietary model ownership:** establish rights in original code/data/checkpoints and contributor work. Fine-tuning permissively licensed weights does not erase their notices, create exclusive rights in upstream material or grant ownership of every generated asset.

Do not market these goals as already achieved. No tracked root repository license/contributor assignment was found; owner/counsel must establish rights before claiming exclusive ownership or changing licensing. Hardware ownership alone does not remove CUDA/browser/OS intellectual-property constraints.

## Data Provenance Ledger

Every source object/image/mesh should have a stable ID and ledger containing:

| Field group | Required records |
|---|---|
| Origin | Camera-original versus screenshot/derivative/synthetic; creator/organization, capture/import date, country/jurisdiction where appropriate, original URI/location and immutable SHA-256 |
| License and authority | Exact asset license version/text/source/date, attribution/NOTICE obligations, commercial/training/derivative/redistribution rights, expiry/territory restrictions, contributor authority and legal review |
| Consent | Separate consent receipt/version for service processing, optional quality evaluation, optional training and optional publication. User ownership assertions are not proof of all depicted third-party rights |
| Scene metadata | Object/category, lighting/background, transparency/reflection, shadows/clutter, camera pose/calibration, image resolution/EXIF, known physical dimensions and measurement uncertainty |
| Ground truth | Licensed mesh/multi-view/scan origin, scanner/camera calibration, units/axes, masks/silhouettes/detail labels, annotator identity/date/review, ambiguity and label confidence |
| Transformations | Source hash -> exact submitted image hash, EXIF/resize/crop/mask settings, removed metadata, all derived artifact hashes, software/model revision, seed and parameter manifests |
| Lifecycle | Dataset split/version, revocation/deletion state, retention deadline, access logs, training runs/checkpoints using the item and derivative lineage |

Store the ledger in the owner database with encrypted immutable evidence and access controls. Keep photographs and rights records private by default; public evaluation reports must redact personal data, signed URLs, secrets and precise location. Raw upload/debug retention is not an opt-in to training.

## User Consent And Deletion

- Core reconstruction consent must be necessary and clear for the requested service; training consent must be separate, optional, specific and revocable. Refusing training must not silently disable purchased/core reconstruction.
- Explain whether processing uses a hosted provider or owner worker, what crosses a boundary, retention, human review, visibility and whether commercial model training is included. Do not promise third-party deletion or geographic guarantees without a verified provider contract.
- Strip GPS/identity metadata from derived submissions when policy allows, while preserving a protected original/consent receipt for the agreed limited purpose. Define exceptional handling for minors, people, private interiors, medical/personal data, confidential designs and branded/copyrighted objects.
- Implement access/export/deletion requests, revocation and dataset tombstones across original images, masks, feature stores, previews, logs, backups and future training queues. Existing model influence cannot always be removed instantly: document retraining/unlearning limitations and the approved remediation schedule.
- Do not infer permission from a publicly reachable URL, sample library, model marketplace listing or user clicking Generate. NC, ND, research-only, missing-provenance or ambiguous licenses must be quarantined, not automatically ingested.
- Use explicit owner/counsel-approved data-processing and retention policies before any real collection. Jurisdictional privacy/security review remains outstanding; this document is not a legal compliance claim.

## Training Sources And Commercial Restrictions

| Possible source | Acquisition policy / limitations |
|---|---|
| Owner-captured physical-object photos/scans | Document ownership/permissions, safety, privacy, brand/design restrictions and scanner rights. Prefer multi-view ground truth, measured units, matte and reflective/transparent stress scenes |
| User contributions | Explicit separate training opt-in, uploader authority, deletion mapping and contributor terms; no automatic reuse of production debug images |
| Commissioned/scanned data | Written training/derivative/commercial/redistribution grants plus contractor assignment; hardware/service terms and annotations included |
| Public 3D/image datasets, Objaverse, NIH/catalog assets | Verify **each asset or actual selected subset**, upstream attribution and dataset terms. Broad aggregate names or a model card's training-subset description do not clear all underlying assets |
| Synthetic rendered fixtures | Label as synthetic; prove rights in source meshes/materials/HDRIs/textures/renderers. Analytic test silhouettes are software tests, not physical transparent/refraction ground truth |
| Third-party model outputs | Check hosted API/model licenses, geographic clauses, distillation/competitive-model restrictions and input rights before training. Paid generation does not automatically grant permission to build a competing model |

Avoid BRIA non-commercial segmentation weights and research-only renderer code in commercial pipelines unless licensed or replaced. Tencent territory/scale terms and Stability registration/revenue terms are not removed by fine-tuning. MIT-declared TripoSR/TripoSG/TRELLIS weights are candidate starting points only; all auxiliary dependencies still need review.

## Evaluation Before Training

Use the independently preserved `experimental/reconstruction-evaluation` branch (`c32e590ba5244a9d484e2bbc1d3c564bec000a86` at foundation start). Do not merge it into production or this branch as a shortcut. Its corpus separates synthetic drawings, real photographs and screenshot proxies; missing fresh-camera evidence remains pending.

The six-object real-world cohort should include fresh opaque bottle, ceramic mug with handle, transparent cup, metal utensil/container, shoe and mechanical part. Add enough real subjects/backgrounds to test categories beyond a single cup or laboratory image. If the actual cup source is unavailable, a screenshot of its result/input UI is not an acceptable camera original.

For every comparison retain baseline and candidate with identical source/settings/model or explicitly controlled model differences, exact payload hashes, checkpoint revisions, seeds/defaults, durations, peak resources, cost, prediction IDs and saved GLBs. Reuse cached outputs; first run no-cost preprocessing tests, then show exact paid count and estimate before explicit authorization. No paid predictions are authorized by this roadmap.

Evaluate distinct properties:

- **Input isolation:** annotated foreground completeness, background contamination, silhouette IoU, handle/stem/thin-detail recall; absent annotations remain unmeasured and require review. Isolation confidence is not calibrated fidelity.
- **Geometry validity:** mesh loads, finite bounds, faces/vertices, watertightness, connected bodies/surfaces, boundary/non-manifold edges, winding and degeneracy. Hollow cavities and disconnected physical parts must not be conflated.
- **Visual fidelity:** photographed object's recognizable silhouette/shape, missing or duplicated/stacked geometry, openings/handles/edges, reflected/background geometry, and multi-view consistency. A watertight slab can still be a failed cup reconstruction.
- **Physical correctness:** known-dimension calibration, uncertainty, mm editing, GLB meters/STL millimeters, transforms/axes, immutable revisions and export round trip. Uncalibrated inferred bounds are not measurements.
- **Experience/reliability:** actual iPhone/Mobile Safari capture, view/render, calibration, edit, undo/redo/reset, GLB/STL download; restart/cancel/OOM/error recovery and honest job IDs/warnings.
- **Operations:** p50/p95 quality/runtime/cost, API RSS, worker host/VRAM peak, queue delay, power, disk, concurrency, license/rights status and independent offline operation.

Use pre-registered human review rubrics and held-out test subjects; publish failures and sample counts. Unknown image-to-3D camera alignment should result in a documented human comparison, not an invented image-similarity number. Connected-component checks cannot reliably catch a fused duplicate/reflection artifact.

## Staged Model Development

| Phase | Work | Exit criteria | Status |
|---|---|---|---|
| 0: Rights and dependency foundation | Audit all runtime/model/data sources, licenses, consent, ownership and exact artifact hashes | Owner/counsel approve commercially admissible stack and data rules; no missing critical terms | This task supplies evidence and open issues, not legal approval |
| 1: Independent baseline inference | Authorized owner GPU lab running a pinned reviewed model through the inactive local adapter contract | Genuine AI mesh from actual photo, full GLB load, truthful execution receipt, no procedural substitution, reproducible resources and offline runtime | Deferred; no GPU inference or weights downloaded |
| 2: Dataset and measurement | Acquire properly licensed/consented scans and photos; annotate full silhouettes and difficult details | Immutable dataset versions, object-level train/validation/test split, rights-complete held-out category coverage and human rubric | Partially scaffolded separately; real six-object cohort incomplete |
| 3: Controlled customization | Start with low-risk preprocessing/parameter experiments, then adapters/fine-tuning only if measured need exists | Same-input improvement over unchanged baseline without category regressions; retain all rights and rollback receipts | Not started |
| 4: Owner training pipeline | Dataset recipes, distributed training, deterministic manifests, checkpoint registry, failure recovery and evaluation gates | Reproducible training run on owner infrastructure, cost/energy/resource measurements, access/consent/deletion audit | Not started |
| 5: Proprietary components/model | Develop rights-cleared data/model changes, optionally train original architecture/weights if justified | Legal ownership evidence plus independent quality, robustness, operational and safety benchmarks | Research proposal only; no speculative ownership claims |
| 6: Product transition | Explicit opt-in staging/canary, durable storage/identity and owner GPU rollout | Actual device/workflow regression passes, backup restore/failure drills, legal approval and owner-authorized rollback-capable deployment | Not authorized |

Training from scratch is not the default recommendation. Determine dataset/quality gaps and economics first; a custom training run cannot be justified simply by a desire to replace an inference bill. No GPU capacity, training duration, convergence, market-leading quality or final dollar budget is promised without measurements.

## Owner Training Infrastructure

Separate collection/consent, labeling, rendering, training and serving environments. Use owner-controlled versioned object storage, a transactional rights ledger, package/model mirrors, job scheduling, per-run resource budgets, checkpoints and reproducible container manifests. Keep research runs off production GPUs unless explicitly scheduled and capacity-isolated.

Training records should include code commit, base/auxiliary weight hashes/licenses, data manifest/split/consent revisions, transforms, model architecture, optimizer/hyperparameters/seed, hardware/driver/compiler versions, elapsed compute, power/cost estimates, evaluation results, failure logs and checkpoint checksum/signature. Never commit private training photos, checkpoints or access tokens into the application repository.

Use object/scene-level splits so near-duplicate photos, reflected views, synthetic variants and generated derivatives cannot leak across train and test. Track source objects through transformations. Reserve independently captured hard cases, not just the easiest opaque objects, for locked regression evaluation. Record failed samples rather than discarding them to improve average scores.

## Transition Criteria And Decision Owners

Owner must explicitly approve each expenditure, model/data license, optional provider/service, collection campaign, training run, production canary and final migration. Legal/data owner signs rights/consent; engineering owner signs reproducibility/security/rollback; product reviewers sign actual visual/device outcomes.

Do not recommend production promotion unless measurable held-out same-input fidelity improves across the required categories, handles/openings/thin structures and transparent/reflective cases do not regress unacceptably, mesh validity is maintained, and calibration/mm/history/manufacturing/exports retain parity. Actual mobile Safari/iPhone checks, throughput/resource budgets, backup restore, privacy deletion and owner-controlled egress tests must pass.

Maintain Replicate as unchanged fallback routing only under an explicit product policy during qualification, never a silent fallback to unrelated/procedural geometry. A self-hosted adapter must report real errors and return unknown resource/fidelity values honestly. Full retirement of third-party inference keys is a separately authorized milestone after demonstrated stable independent operation, not a side effect of this foundation branch.

## Outstanding Decisions

1. Confirm actual production model/version, territory/user-scale/commercial rights, API contract and historical output-training permissions without exposing credentials.
2. Establish root DragonFly/contributor ownership and the legal entity/jurisdictions serving customers.
3. Supply six fresh real camera originals, dimensions where known, annotation policy and consent receipts; approve paired benchmark cost separately.
4. Select GPU/hardware/runtime after license and compatibility review; authorize downloads only after manifests and budget approval.
5. Decide identity/storage/queue/backup requirements and migration targets; existing stubs are not a completed platform.
6. Review commercial auxiliary-model blockers, unpinned build/runtime dependencies and native binary redistribution notices.

No proposed training or self-hosting phase is enabled by this document. Production and Render remain unchanged, and all current work stops before merge/deployment.