# Kitchen Vision System — Phased Implementation Plan

**Status:** Reference document — superseded where conflict

This plan turns the [system design and AI/CV lifecycle](Kitchen_Vision_System_Design_and_CV_Lifecycle.md) into an ordered delivery plan. Each phase has a goal, work items, outputs, dependencies, and an exit gate. Move to the next phase when its gate is met; do not treat calendar dates as evidence of model readiness.

> **Canonical plan:** Use `Kitchen_Vision_Plan.md` for current phase numbering, acceptance matrix, and execution decisions. This document is retained for historical phase detail.

## Delivery principles

- Start with one representative camera and offline clips, then add live streams and more cameras.
- Validate camera visibility and data quality before committing to model accuracy targets.
- Keep PPE, utensil counting, platform software, and reporting as separate workstreams with clear interfaces.
- Treat `unclear` as a valid vision result. Missing/low-quality evidence must not become an automatic violation.
- Evaluate on held-out clips split by recording session, time period, or camera.
- Promote model versions through offline evaluation and live shadow operation before enabling alerts.
- Do not claim production performance until the client’s acceptance set and live soak criteria pass.

## Phase overview

| Phase | Name | Main outcome | Depends on |
|---|---|---|---|
| 0 | Scope and data readiness | Signed requirements, camera feasibility, data access | Client decisions |
| 1 | Data, model, and technology selection | Approved data sources, model strategy, stack, and deployment target | Phase 0 |
| 2 | Data and annotation foundation | Versioned pilot dataset and annotation guide | Phase 1 |
| 3 | Baseline CV feasibility | Measured baseline on real kitchen clips | Phase 2 |
| 4 | Model development | Evaluated PPE and utensil model candidates | Phase 3 |
| 5 | Temporal logic and counting | Stable person-level PPE events and deduplicated counts | Phase 4 |
| 6 | Offline end-to-end system | Clip replay through worker, API, database, and dashboard | Phases 0-5; API can start during Phase 3 |
| 7 | Live shadow deployment | Stable live processing with reviewed, non-alerting predictions | Phase 6 |
| 8 | Limited production | Approved alerts, exports, and scheduled email | Phase 7 |
| 9 | Operations and improvement | Monitoring, feedback, retraining, and controlled releases | Phase 8 |

---

## Phase 0 — Scope, camera review, and data readiness

### Goal

Confirm that the desired tasks are observable from the available cameras and define how success will be measured.

### Work items

1. List sites, cameras, camera locations, resolutions, frame rates, viewing angles, and expected number of simultaneous streams.
2. Obtain a small, authorized sample of footage from each candidate camera, covering different shifts and lighting conditions.
3. Inspect pixel size and visibility for heads, hands, masks, hair covers, cups, and plates.
4. Define PPE policy by station: required items, what constitutes a violation, visibility requirements, grace period, and alert cooldown.
5. Select a counting meaning per camera and object class: line crossing, zone entry, or zone occupancy.
6. Decide how stacks, overlaps, and partially hidden items are handled.
7. Confirm processing hardware, storage location, retention period, user roles, and whether inference is local or hosted.
8. Decide licensing constraints for code, pretrained weights, datasets, and deployment.
9. Agree the held-out acceptance clips and target metrics: per-item PPE precision/recall, coverage, unclear rate, false alerts per camera-hour, count error, latency, and uptime.

### Deliverables

- Camera inventory and sample-frame review.
- Signed scope and acceptance matrix.
- Data authorization, privacy, access, and retention decisions.
- Per-camera PPE and counting rules.
- Risk register and chosen pilot camera(s).

### Exit gate

Proceed only when the chosen camera(s) can plausibly show the required PPE regions/items and the count semantics are unambiguous. If not, revise the camera setup or reduce scope before model work.

---

## Phase 1 — Choose the data, models, and technology stack

### Goal

Make explicit, evidence-based choices for the datasets, model approach, software stack, and runtime before building the product around assumptions.

### Data choices

1. Use authorized footage from the actual kitchen cameras as the source of truth for validation and fine-tuning.
2. Evaluate SH17 as a PPE warm start for compatible labels such as person, head, hands, gloves, and masks. It comes from industrial environments, so it cannot replace kitchen examples or cover all kitchen-specific PPE classes.
3. Evaluate COCO/Open Images or another public dataset for utensil warm starts only when its classes and annotations match. Verify the selected checkpoint's class list; do not assume it detects plates because it detects cups.
4. Record data provenance, license, attribution requirements, authorization, retention, and permitted training use.
5. Split evaluation by recording session/time and preferably hold out a camera or shift. Public data is not the acceptance set.

### Model choices

- **Person/PPE:** compare person and body-region localization plus a region classifier (`present`, `absent`, `not_assessable`) against direct PPE detection. The camera view and labels decide which works better. Tracking IDs are temporary and scoped to one camera session; do not infer worker identity.
- **Utensils:** use a separate detector for `cup` and `plate`, plus optional `plate_stack` only if the client defines that policy. Add per-camera object tracking for deduplicated counts.
- **Tracking:** benchmark ByteTrack or an equivalent tracker on representative clips; check ID continuity and counting errors.
- **Detector framework:** benchmark an easy-to-iterate framework against a candidate with license terms acceptable to the client. Ultralytics YOLO11 has AGPL-3.0/Enterprise options; MMDetection is an Apache-2.0 codebase option. Check the exact model weights, dataset, dependencies, and export runtime separately.
- **Inference runtime:** start with PyTorch for training and offline evaluation. Select ONNX Runtime or TensorRT only after profiling the target hardware and verifying compatibility.

### Platform technology choices

| Area | MVP candidate | Selection check |
|---|---|---|
| API | Python + FastAPI | Team familiarity, REST contract, async I/O needs |
| Database | PostgreSQL + SQLAlchemy/Alembic | Transactions, constraints, and time-filtered events |
| Video worker | Python + FFmpeg-backed RTSP decoding | Reconnect behavior, per-camera isolation, bounded queues |
| Dashboard | React + Vite | Event review, filters, charts, camera configuration |
| Evidence storage | Private volume or object store; PostgreSQL for metadata | Access control, retention, deletion, backups |
| Scheduling | APScheduler for one instance | Use a durable queue/scheduler if scale/retry needs require it |
| Packaging | Docker Compose | Target host and GPU runtime compatibility |
| Annotation | CVAT or Label Studio | Export format, review workflow, access controls |
| Experiment/data tracking | Versioned configs/manifests first; MLflow/DVC if volume warrants | Reproducibility and artifact storage |
| Reporting | CSV/email first; PDF/WhatsApp after requirements/provider setup | Acceptance requirements and external dependencies |

### Decision procedure

1. Translate Phase 0 constraints into a decision matrix: task, camera, throughput, hardware, budget, license, privacy, and operator skills.
2. For each dataset/model candidate, record class coverage, domain match, annotation match, license, latency, memory, and failure examples.
3. Run the same small kitchen pilot through candidates and compare quality and speed on the target hardware.
4. Select one primary option and one fallback. Record tradeoffs and why alternatives were rejected.
5. Keep inference behind framework-neutral adapters so a model change does not require rewriting the API or dashboard.

### Deliverables

- `DECISIONS.md` with data, model, framework, runtime, and deployment choices.
- Dataset/checkpoint provenance and license register.
- Candidate benchmark table from representative kitchen clips.
- Architecture decisions for database, storage, and deployment target.
- Approved MVP and deferred-feature list.

### Exit gate

Data and checkpoint provenance/terms are known; a candidate runs on representative footage; runtime hardware and stack are selected; client agrees to PPE and counting semantics.

---

## Phase 2 — Dataset and annotation foundation

### Goal

Create a small, trustworthy kitchen-specific dataset and annotation process before large-scale labeling or fine-tuning.

### Work items

1. Create a private data store; keep raw footage, RTSP credentials, and snapshots out of Git.
2. Extract candidate frames at a task-appropriate rate and remove near-duplicates for annotation efficiency.
3. Select representative examples across cameras, shifts, lighting, staff, occlusion, motion blur, and object sizes.
4. Write annotation rules with positive, negative, occluded, too-small, and ambiguous examples.
5. Use CVAT or Label Studio to label a pilot subset.
6. For PPE, label person instances, head/face and hand regions, region visibility, and item status (`present`, `absent`, `not_assessable`). Do not label an unseen item as absent.
7. For utensils, label cup/plate boxes, optional stack cases, and the ground-truth event that matches the selected counting mode.
8. Have a second reviewer check a sample; resolve disagreements and update the guide.
9. Split by recording session/time and, where feasible, hold out a camera or shift. Freeze the test split.
10. Create a manifest recording source, authorization, camera, time, label version, class names, split, checksums, and license details.

### Deliverables

- `training/DATASET.md` and versioned label guide.
- Pilot train/validation/test manifests.
- Annotated pilot export and quality-review notes.
- Dataset license and provenance register.

### Exit gate

The label guide is understood by annotators, reviewer disagreement is acceptable for the task, the test set is frozen, and the data is representative enough to establish a baseline.

---

## Phase 3 — Baseline models and feasibility report

### Goal

Measure what pretrained models can do on the actual camera views and expose the main sources of error.

### Work items

1. Build a repeatable offline clip runner that saves timestamped predictions and annotated review videos.
2. Verify class maps and licenses for candidate pretrained checkpoints.
3. Run a pretrained person/PPE candidate on labeled clips; use SH17 only as a warm-start/evaluation resource where its labels fit.
4. Run a pretrained utensil candidate; verify it supports the exact classes required, especially plates.
5. Produce per-class metrics and inspect false positives/negatives by camera, region size, lighting, and occlusion.
6. Measure inference speed and memory on the target hardware, if available.
7. Decide whether the dominant issue is camera visibility, labels, domain gap, model capability, or counting semantics.

### Deliverables

- Baseline prediction artifacts and annotated clips.
- `training/RESULTS.md` with initial per-class metrics and failure examples.
- Model/license decision record and hardware profile.
- Updated scope if any requirement is not visually supportable.

### Exit gate

The team can explain what the baseline detects reliably, what it misses, and whether fine-tuning is likely to address the failures. No production accuracy claim is made at this stage.

---

## Phase 4 — Model development and offline evaluation

### Goal

Train and compare kitchen-specific model candidates using reproducible experiments.

### Work items

1. Keep separate PPE/person-region and utensil experiments initially.
2. Fine-tune from a suitable pretrained checkpoint with versioned configuration, random seed, package versions, code commit, and dataset manifest.
3. Add kitchen-specific annotations for hair covers, gloves, masks, and any approved later PPE classes. Add beard/beard-cover only if sufficient representative examples exist.
4. Tune image size and model scale based on object pixel size and measured target-hardware performance.
5. Use realistic augmentations for lighting, blur, scale, and occlusion; review augmented examples to avoid erasing PPE evidence or changing labels incorrectly.
6. Tune per-class confidence thresholds on validation clips, not on the frozen test set.
7. Evaluate a candidate and baseline on the same held-out clips. Report precision, recall, coverage, unclear rate, and false alerts for PPE; detection metrics remain diagnostic.
8. For counting, measure detection quality by object size and scene condition, then retain representative errors for the next labeling round.
9. Package weights, preprocessing, class map, threshold configuration, checksums, runtime requirements, metrics, and license notices.

### Deliverables

- Reproducible training and evaluation commands.
- Versioned candidate model artifacts.
- Per-class and per-camera evaluation report and failure gallery.
- Model card describing intended use and known limits.

### Exit gate

The candidate meets agreed offline targets or the client signs off on a reduced scope/known limitation. The model has not yet passed live operation.

---

## Phase 5 — Temporal PPE decisions and counting logic

### Goal

Convert frame-level detections into stable events and counts that match kitchen operations.

### Work items

1. Add per-camera person tracking and person-to-head/hand association.
2. Implement visibility and minimum-pixel quality gates. Route insufficient or conflicting evidence to `unclear`.
3. Implement a time-based PPE state machine with observation, grace period, violation persistence, cooldown, and track-end behavior.
4. Prevent duplicate PPE events for one worker/item/episode; retain temporary track IDs only within a camera session.
5. Add utensil tracking and per-camera line/zone geometry.
6. For line crossing, require stable pre-crossing and post-crossing positions, count only the configured direction, and mark tracks as counted.
7. For zone entry, require confirmed entry; for occupancy, report a snapshot estimate rather than cumulative flow.
8. Evaluate complete clips for false alerts/hour, event delay, duplicate counts, missed counts, and count bias.
9. Add idempotent event publishing and model/config version metadata.

### Deliverables

- PPE temporal state machine and unit-level fixtures.
- Line/zone counter with camera configuration versioning.
- Clip-level event/count evaluation report.
- Agreed handling for stacks, occlusion, track loss, and unclear evidence.

### Exit gate

End-to-end clip replay produces stable episode events and counts within the agreed definition, with no duplicate event explosion and uncertainty surfaced explicitly.

---

## Phase 6 — Offline end-to-end application

### Goal

Integrate video replay, model inference, event persistence, API, and dashboard before connecting production RTSP streams.

### Work items

1. Implement worker interfaces for frame input, model prediction, tracking, event logic, and publishing.
2. Implement database migrations for sites, cameras, versioned configurations, model releases, compliance events, count events/buckets, health, review feedback, schedules, and audit logs.
3. Implement authenticated FastAPI endpoints for cameras, health, events, counts, review, export, evidence, and schedules.
4. Implement dashboard pages for overview, events, counts, camera setup, reports, and administration.
5. Support clip replay with source timestamps and deterministic model/config selection.
6. Add role checks and private evidence access; redact credentials from logs.
7. Add CSV exports and verify filters/timezone handling. Defer PDF until its report format is specified.
8. Add health status so missing/stale inference cannot display as zero violations.
9. Package API, worker, database, and dashboard with development compose configuration and example configs without secrets.

### Deliverables

- Offline, runnable application using sample clips.
- API schema and database migrations.
- Dashboard preview and event/count exports.
- Example deployment config, setup guide, and initial runbook.

### Exit gate

The offline path reliably transforms a selected clip into expected persisted events/counts, displays them in the UI, enforces authorization, and exports the same filtered records.

---

## Phase 7 — Live RTSP shadow deployment

### Goal

Prove live-stream reliability, resource use, and real-world event quality without sending operational alerts.

### Work items

1. Add per-camera RTSP decoder/reconnect loops with secret references, bounded latest-frame queues, and stale-frame dropping.
2. Add a shared GPU inference scheduler and per-camera tracker state; isolate camera failures.
3. Add stream health state, last-frame time, decoder FPS, inference FPS, queue/drop metrics, latency, and worker heartbeat.
4. Deploy to one or two pilot cameras. Predictions remain shadow-only and visible to reviewers.
5. Compare sampled live outputs with manual review; collect false positives, misses, unclear cases, and count discrepancies.
6. Profile CPU/GPU/memory and storage; tune sampling rates and model size only against measured constraints.
7. Test RTSP interruption, network recovery, DB outage, model load failure, and worker restart.
8. Run the agreed soak test (for example, 24 hours on four cameras only if that deployment target is actually available).
9. Adjust thresholds on a calibration set, then re-evaluate on the frozen test set.

### Deliverables

- Live shadow report with quality and systems metrics.
- Per-camera thresholds and camera readiness matrix.
- Capacity estimate and reconnect/failure test notes.
- Updated operator runbook and rollback procedure.

### Exit gate

Streams remain bounded and recover; latency and uptime meet targets; event quality meets the signed acceptance criteria; reviewers understand remaining limitations.

---

## Phase 8 — Limited production and reporting

### Goal

Enable approved operational use for selected cameras and features.

### Work items

1. Select cameras/items that passed the shadow gate; keep unsupported cameras/items disabled.
2. Enable events and dashboard notifications under the agreed alert policy.
3. Test email summaries, recipient authorization, timezone, retries, and duplicate-send protection.
4. Add scheduled reports with bounded query ranges and audit records.
5. Add WhatsApp only if contractually required and provider credentials/templates are ready.
6. Validate CSV/PDF contents against dashboard filters and retention permissions.
7. Verify backups, restore, evidence retention deletion, secret rotation, and incident contact path.
8. Obtain client sign-off for the acceptance report and known limitations.

### Deliverables

- Limited production release and release manifest.
- Final acceptance report with held-out and live shadow evidence.
- Operator/admin guides, backup/restore notes, privacy/retention settings.
- Scheduled email report configuration; optional WhatsApp integration.

### Exit gate

Client accepts the enabled camera/item set, support process, privacy settings, thresholds, and documented limitations.

---

## Phase 9 — Monitoring, feedback, and retraining

### Goal

Maintain quality as cameras, shifts, uniforms, lighting, and kitchen workflows change.

### Work items

1. Monitor camera availability, stale frames, latency, resource use, unclear rate, reviewer correction rate, count drift, and storage.
2. Review representative errors periodically with authorized reviewers.
3. Promote feedback to training data only after human confirmation and updated annotation/version records.
4. Detect drift by camera and shift; do not automatically retrain on unreviewed predictions.
5. Re-train candidates with a new dataset manifest and compare to a frozen regression suite.
6. Shadow a new model before promotion; keep a rollback path to the prior model/config.
7. Update the model card, results, runbook, licenses, and changelog for each release.

### Deliverables

- Periodic quality/operations report.
- Reviewed labeling backlog and versioned dataset additions.
- Model release changelog and rollback record.

### Exit gate

Each model change is traceable, evaluated, approved, and reversible; system health and quality trends are visible to operators.

---

## Workstream sequencing

| Workstream | Starts | Can run in parallel with | Must wait for |
|---|---|---|---|
| Client requirements and camera audit | Phase 0 | API skeleton planning | Nothing |
| Data/model/technology selection | Phase 1 | API skeleton planning | Phase 0 constraints and sample footage |
| Dataset/annotation | Phase 2 | API/database schema discovery | Data choice, sample footage, and label policy |
| CV baseline/training | Phase 3 | API scaffolding | Labeled pilot data and license review |
| PPE temporal/count logic | Phase 5 | Dashboard implementation | Stable model outputs and counting rules |
| API/database | Late Phase 3 | Model experiments | Event/count contract before final schema |
| Dashboard | Phase 6 | Live worker hardening | API contract and sample event data |
| RTSP and deployment | Phase 6-7 | UI polish | Target hardware and credentials |
| Notifications | Phase 8 | Operations docs | Stable production event data/provider setup |

---

## Project entry checklist

Do not start camera-specific model training until the following are available:

- [ ] Authorized sample videos and camera metadata.
- [ ] PPE policy and visibility rules per station.
- [ ] Written count semantics per camera/class.
- [ ] Annotation guide and held-out split plan.
- [ ] Target hardware and expected camera count.
- [ ] Data, checkpoint, and code license decisions.
- [ ] Privacy, access, and retention requirements.
- [ ] Signed acceptance metrics and review process.

## Completion checklist

- [ ] Reproducible training/evaluation artifacts and model manifest.
- [ ] Per-class/per-camera CV metrics, coverage, unclear rate, and failure examples.
- [ ] Live camera health and inference monitoring.
- [ ] Event/count API and dashboard with role checks.
- [ ] Export/report behavior verified against filters and timezones.
- [ ] Soak, reconnect, failure, backup/restore, and rollback procedures documented.
- [ ] Client acceptance and known limits recorded.
