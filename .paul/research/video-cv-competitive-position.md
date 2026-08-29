# Research: Video-CV competitors vs the tethered encoder — and can we do video segmentation?

*Created 2026-08-28 · Two parallel agents: web landscape (general-purpose) + codebase feasibility (Explore).*
*Status: findings for review. Nothing here is integrated into a plan or the code.*

---

## 0. The headline, before anything else

**1. "Time Drop" is not a computer-vision company.** Two real companies share that name and neither
does CV:

- **TIMEDROP Technology, LLC** (Brentwood TN, https://www.timedrop.com/) — *meet-results analytics*.
  Upload results, track progression. Invite-only landing page, no product, no pricing, no camera,
  no sensor mentioned anywhere. Co-founder Matthew Lattin.
- **Time Drops LLC** (https://time-drops.com/) — *wireless meet-timing buttons*, ~$670/system,
  integrates with SwimTopia/Swimcloud. Pure hardware timing, zero analytics.

If you pitch against "Time Drop" to a coach, they will hear the timing-button company. The threat you
are actually thinking of is one of **SenSwim**, **AIM Systems**, **SwimMate**, or **DeepDASH** (§1).

**2. The real threat is not a startup — it is DeepDASH**, a published, validated, multi-lane video
system from Swimming Australia that produces *instantaneous* velocity for up to 10 lanes across all
four strokes, with **97.4% F1 stroke detection**. It has been benchmarked **directly against a
waist-mounted tethered speedometer** — i.e. against your exact device class.

**3. That benchmark, and one older paper, are the two documents that matter most to you.** One says
video and tether disagree by ±0.38 m/s (free) to ±0.92 m/s (breast) at 95% LOA. The other concludes
the *tether* was the inaccurate instrument. Details in §3. **Neither is a comfortable read and you
should read them.**

**4. Yes, you can do video segmentation — and you already built most of it twice.** The sync
plumbing, the ground-truth loop, and the boundary-precedence seam are all mature. What is missing is
compute: no `cv2`, no `torch`, no GPU, no worker, and **the backend has literally never read a video
byte back out of storage**. Details in §5.

---

## 1. The actual competitive set

### Direct CV swim analytics

| Company | What it measures | Deployment | Price | Validation |
|---|---|---|---|---|
| **SenSwim** (IL) | speed, stroke count/rate, DPS, underwater distance, turns, dive depth | ceiling/wall cameras, **above waterline only** | not published; positions as "affordable" | none published |
| **AIM Systems** (SE) | pure swimming velocity, head/hip depth, breakout distance, DPC L-vs-R, turn time | **12 underwater + 11 above-water 100 Hz cameras** | not published | none published |
| **SwimMate** | splits, stroke count/rate, breathing; **no intra-stroke velocity claim** | poolside stand, edge compute, **24 swimmers / 3 lanes** | **revenue share, ~12mo payback, 4-wk buyback trial** | self-reported: timing ≤0.3 s, strokes ±1, <1 s latency |
| **FINIS LaneVision** | claims real-time + underwater velocity via ARKit | **a phone** | consumer app | none; mixed App Store reviews |
| **DeepDASH** (Swimming Australia) | **instantaneous velocity, 10 lanes, all 4 strokes** | 1× UHD camera + cone calibration | research | **peer-reviewed, F1 97.4%** |
| **SwimInsights / SwimScanner / iSWIM** | splits, underwater, dive reaction | phone video upload | **$5.99–$8.99/mo**, or $100/2yr | none |

### The two facts in that table that should change your thinking

- **SwimMate's business model removes the club's capital risk entirely** (revenue share + buyback
  guarantee). That is a harder sell to beat than a better number.
- **The price anchor is already $6–9/month.** A coach who has seen iSWIM will not hear
  "$300 device + $20/swimmer/month" as cheap, regardless of whether iSWIM is any good.

### Encoder competitors you may be under-weighting

These matter more than the CV startups, because they are *you*:

- **APLab Speed RT** (IT) — *"a small winch with an **encoder** placed on the starting post"*, USB
  real-time to PC, syncs to video via BioMovie Speed. Functionally identical to Swimnetics.
- **Swimsportec speedometer** — retail via Sport-Thieme, 27 m cord, 0–3 m/s.
- **Ergotest MuscleLab laser** — contactless body-velocity tracking. **No cord, no slack artefact.**
  This, not video, is the encoder's technical successor.
- **The Race Club sells velocity-meter testing at $1,000/session** ($1,800 with a pressure meter),
  always synchronised with side-on video. Read that two ways: strong evidence your signal has real
  perceived value, *and* evidence the market has been served as a boutique service for years without
  anyone productising it.

### The one encouraging data point

**FINIS — the biggest brand in swim equipment — shipped a phone-CV velocity app in 2020 and it did
not take the market.** SenSwim has been selling since ~2019 to the Israeli national team and has not
visibly won. Video CV in swimming has had six years and has not consolidated.

---

## 2. What the pose-estimation literature actually reports

Vendor claims and published numbers diverge sharply. The published numbers:

**SwimXYZ** (ACM MIG '23) — 3.4M synthetic frames, ViTPose finetuned, evaluated on *real* footage:

| PCK threshold | Off-the-shelf | Finetuned |
|---|---|---|
| @1 | 13% | **32%** |
| @5 | 46% | **71%** |
| @10 | 67% | 85% |

Read that honestly: after finetuning on 3.4 million frames, **only 71% of keypoints land within 5%
of body scale**. Off-the-shelf is near-useless.

**SwimmerNET** (Sensors 2023) — the best-case underwater result: mean error ~1 mm, SD ~10 mm. The
caveats *are* the finding: GoPro **10 cm below the surface**, 4K@120fps, trained on **2,021 frames
from ONE swimmer in ONE pool**; 0.5–3% frame failures rising to ~5% on external data; degraded by
*"bubbles, splashes and reflections"*; **0.8 s per frame — not real-time**.

**Markerless mocap reviews (2025):** sagittal joint-angle errors 3–15°, transverse 3–57°; multiple
reviews flag water as *not yet suitable*.

**Documented failure modes:** bubbles/spray at limb entry, surface refraction, waterline occlusion,
frequent left/right limb swapping, multi-swimmer overlap. Even Folio3 — a CV vendor *selling* this —
headlines with *"Most swimming AI tools break at the water's edge."*

---

## 3. ⚠ The head-to-head: video vs tethered speedometer

**This is the section to actually sit with.**

### 3.1 Scott, Elsworthy, Brackley, Elipot & Kean (2024), *Sports Biomechanics*

"Agreement between an automated video-based system and tethered system to measure instantaneous
swimming velocity." DOI 10.1080/14763141.2024.2388572

n=22 competitive swimmers, 25 m max each of 4 strokes. Video = DeepDASH, single UHD camera @50 Hz,
tracking the **head**. Tether = waist-belt speedometer at the **hip**. ~9,580 paired points/stroke.

| Stroke | Bias (m/s) | 95% LOA | RMSE |
|---|---|---|---|
| Backstroke | 0.02 | −0.24 … 0.26 | 0.13 |
| Freestyle | 0.01 | −0.36 … 0.38 | 0.19 |
| Butterfly | 0.03 | −0.51 … 0.53 | 0.27 |
| Breaststroke | 0.04 | −0.88 … 0.92 | **0.46** |

Mean bias is trivial — they agree on *average* speed. But on a signal averaging ~0.94–1.5 m/s,
**±0.38 m/s in freestyle is ±25–30%, and breaststroke is ~±95%**. The two systems **do not produce
the same intra-cycle trace**, and neither has been shown to be the truth.

The authors name **two** causes: different landmarks (head vs hip — the hip undulates far more), and
*"Swimmers kicking the tether is a limitation of tethered speedometers, which can lead to measurement
errors."* Their practical advice: don't alternate systems for absolute targets; track **relative
change**.

### 3.2 ⚠ van Houwelingen et al. (2018), *Sports Engineering* — the paper you will not enjoy

"Automated LED tracking to measure instantaneous velocities in swimming." Open access at
https://pure.tue.nl/ws/portalfiles/portal/113457165/Houwelingen2018_Article_AutomatedLEDTrackingToMeasureI.pdf

Four in-wall cameras @50 fps, hip-mounted LED, vs a Swimsportec speedometer @32.5 Hz. Verbatim:

- *"The raw speedometer signal contains more noise"* — needed a 4th-order Butterworth @5 Hz. LED
  tracking needed no preprocessing.
- *"the signal degrades … when the distance to the speedometer increases."*
- The butterfly second velocity peak was **entirely missing** from the speedometer; breaststroke's
  was attenuated. Verdict: *"the LED analysis is correct, and the observed differences with the
  speedometer are due to inaccuracy of the speedometer."*
- The mechanism: *"the speedometer measurement is not sensitive to sudden accelerations when the cord
  has slack, causing not all variations in horizontal speed to be observed, or even the appearance of
  additional fluctuations due to unwanted extra degrees of freedom of the cord."*
- Mean velocity LED / speedometer: fly 1.27/1.16, back 1.11/1.06, breast 0.94/0.85, free 1.25/1.17 —
  **the tether read ~0.08–0.11 m/s low in every stroke.**

Caveats that are real: n=1, 2018, a *marker* (LED) not markerless, and a four-camera in-wall rig.
**But the mechanism is a physics claim about your device class, not a statistical fluke, and it is
independently corroborated** by the tether-kick artefacts in Scott 2024.

**Video's own failure in the same paper:** in back and free the hip LED broke the waterline during
body roll for ~15 frames (0.3 s), punching a hole in the trace. Your encoder loses nothing there.

### 3.3 Stop making the "video only gives splits" argument

It is factually wrong and a knowledgeable coach or sports scientist will catch it. DeepDASH produces
instantaneous velocity for 10 lanes. AIM claims pure swimming velocity at 100 Hz. What *is* true:

- **Temporal:** validated video runs 50 fps (Scott, van Houwelingen) or 100 fps (AIM). You deliver
  ~89.5 Hz. Your advantage is **~2× at best and shrinking.** Do not build the pitch on it.
- Homography tracking error at 1.6 m/s ≈ 0.07 m/s — *better* than the ±0.19–0.46 RMSE disagreement,
  which implies the gap is landmark + artefact, not camera resolution.
- Drone CV: stroke duration max error 0.3 s, velocity max error 0.35 m/s — coarse.
- **SwimMate, the most commercially concrete poolside product, does not claim intra-stroke velocity
  at all.** That is where the honest line sits today.

---

## 4. The strategic answer to "what advantage remains?"

### 4.1 What the encoder genuinely wins

1. **⭐ No calibration, no venue model, ever.** Murky outdoor 25-yard pool, 4pm sun glare, tile
   pattern, turbidity — irrelevant. **No CV system on this list can say that.** Every video system
   needs cones/flags/homography *per venue*; SenSwim needs the coach to drag-and-drop lane
   assignments before tracking resolves. **This is your most durable moat and it is under-used in
   your positioning.**
2. **Direct kinematic measurement, not inference.** A count is a count. No model, no domain gap, no
   dataset bias, no failure that varies with swimsuit colour. A sports scientist grants this instantly.
3. **No occlusion floor.** Splash, bubbles, body roll, the waterline — the exact things that cost
   van Houwelingen 0.3 s of trace.
4. **Cost to first measurement.** $56 BOM / $300 device vs a 23-camera install or a poolside
   edge-compute stand.
5. **Bootable in 30 seconds by one coach.** No IT, no ceiling mounts, no aquatics-director conversation.
6. Temporal density — real, but only ~2×, and closing.

### 4.2 ⚠ What video wins, and you have to accept these

1. **It sees the hands. You measure the waist.** Propulsion happens at hands and feet. Catch, dropped
   elbow, entry angle, kick amplitude, head position — **all invisible to an encoder, all native to
   video.** Swimnetics can never produce these.
2. **Turns.** The cord physically prevents them — named as a speedometer limitation in the
   peer-reviewed literature. Turns are 20–30% of a short-course race. Video owns them completely.
3. **Competition.** You cannot tether a swimmer at a meet. **The moment a coach wants to analyse an
   actual race, you are out of the conversation.**
4. **Multi-swimmer, passive, every practice.** DeepDASH 10 lanes; SwimMate 24 swimmers. You do one
   swimmer, one rep, with setup.
5. **The visual record.** Coaches trust pictures. Every source here pairs numbers with footage.
6. **Zero athlete burden.** No belt, no cord, no "does this slow me down" conversation.

### 4.3 ⚠ The internal contradiction in the business model

Point 4 above is not just a competitive weakness — **a $20/swimmer/month recurring tier is priced
like a passive monitor, but the tether is a periodic test protocol.** One swimmer, one rep, block
setup, reset. The recurring-revenue logic fits the thing video does and you don't. This is worth its
own decision, separate from any CV work.

### 4.4 Does the moat erode? Yes, unevenly.

**Fast:** the coarse-metric market — splits, stroke rate, DPS, underwater distance, turn time,
breakout — is **already lost**. iSWIM charges $5.99/month. SwimMate does 24 swimmers at <1 s latency
on edge hardware. Anything you sell in that category is commodity. And the data scarcity behind
those weak PCK numbers is being solved (SwimXYZ synthesised 3.4M frames; five vendors are
accumulating real labelled footage). Data problems close.

**Slow:** refraction, bubbles, the waterline, glare and turbidity are **not model-capacity problems**.
SwimmerNET needed a camera 10 cm underwater in a clear pool with one swimmer, and will still need
that in 2031. Calibration burden is structural — better models don't place your cones. Every venue is
a new tail to climb.

**Verdict: your moat is not accuracy and not intra-cycle velocity** — both are contested, and one
published paper says your instrument is the less accurate one. **Your moat is deployment friction and
cost-to-first-measurement.** That is real for 2–5 years. Not for 10.

### 4.5 The hybrid, which the market has already validated three times

- **The Race Club sells exactly this for $1,000/session**: velocity meter + synchronised side-on video.
- **APLab ships exactly this**: encoder-on-a-winch + BioMovie Speed video sync.
- **van Houwelingen argues for it**: *"It is of added value to have the corresponding LED tracking
  data, which could be incorporated in the analysis of the speedometer data."*

**The strongest version for you is not "encoder + video display." It is "encoder as automatic
labeller."** The encoder produces exactly what video CV struggles to get: a dense, unambiguous,
per-cycle temporal segmentation. That is training data. Ship 200 encoders, collect synchronised
encoder+video pairs, and you own the only labelled intra-cycle velocity dataset in the sport.
**You already half-built the seam** (`GET /annotations/export`, `segmentation_reliable`).

---

## 5. Can you do video-based segmentation? — codebase feasibility

### 5.1 What already exists (more than expected)

**Video storage & model.** Two homes, deliberately not unified: `sessions.video_path` +
`sessions.video_origin_s` for the phone clip, and the `session_videos` table
(`patch_12_session_videos.sql`) for up to `MAX_EXTERNAL_VIDEOS = 3` externals — **4 synced angles per
session**. Private `videos` bucket, `MAX_VIDEO_BYTES = 50 MB` (`api.py:1204`), pre-buffer 413 check.
Live census (Phase 82 probe): **65 of 99 sessions carry video**, 2,512 MB across 102 files.

**⚠ Time sync is solved, in both directions.** One formula, `sessionTime = origin_s + video.currentTime`
(`VideoPane.js:20`, `TraceOverlay.js:206`, `CameraTile.js:79/103`). Two paths to `origin_s`:

- **Phone: end-anchor** `origin = sessionDuration − videoDuration` (Phase 44-03). Start-anchoring on
  `recordAsync()` was ~2 s wrong because of camera warm-up; end-anchor works because recording and
  filming stop on the same tap.
- **External: manual two-point align** — `origin = traceClickTime − video.currentTime`
  (`CameraTile.js:164`), 2 dp, ±0.1 s nudge.

**This is the load-bearing fact for CV feasibility: a video-derived event at video time `tv` already
maps onto the encoder clock as `origin_s + tv`.**

**Ground truth is mature.** `session_annotations` stores four boundary times + `stroke_marks_s`, all
**as seconds on the session clock, never indices** (`annotations.py:28`). Seconds → indices happens in
exactly one place (`annotation_to_overrides`). **Everything downstream already speaks the same units
video does.** A coach's video-frame observation already lands in the DB and drives a full 47-metric
recompute today (`PUT /annotations` → `compute_session_metrics(manual=...)` → `_rebuild_phases`).

**The boundary seam is clean.** `phase_metrics.resolve_boundaries` (⚠ in `phase_metrics.py:143`, not
`metrics.py`) already emits per-key provenance: `manual` > `detected` > `auto` > `none`. Boundaries
resolve **once** onto `ctx.bounds`; all 47 metrics read from there. One change propagates to all 47.

### 5.2 Integration cost, concretely

**Adding a `"video"` source between `manual` and `detected` — LOW.**

- `PhaseContext` is a dataclass with `= None`-defaulted late fields specifically so new fields don't
  break existing construction; `video_phases: dict | None = None` is one line.
- ~5 guard edits: the seed loop needs a `manual → video → seed` middle branch, and each detector guard
  widens from `if sources[key] != "manual"` to `not in ("manual","video")`. **`underwater_start_s` is
  the awkward one** — its branch is an `if manual is not None / else detect`, so it needs restructuring
  rather than widening. Miss a guard and the detector silently overwrites the video answer.
- **⚠ Three `PhaseContext` construction sites** (`api.py:219`, `api.py:1105` `_rebuild_phases`,
  `tools/backfill_phases.py`). Thread a new field at fewer than all three and it nulls across the whole
  library — **this is the exact bug 75-06 shipped**, which left two metrics 0/99.
- Frontend: `PhaseReportCard.js:111` `windowSourceNote()` has a hardcoded 3-branch ladder; needs a 4th.
- `SCHEMA_VERSION` ticks by convention.

**Adding video-derived *cycles* — MEDIUM-HIGH.** `compute_session_metrics(manual=...)` (`metrics.py:1492`)
takes a flat index-override dict with **no provenance field**. A CV cycle set would either masquerade
as `manual` (flipping `segmentation_reliable = True` and lying in the UI) or need a new parameter plus
a provenance channel that doesn't exist. `segmentation_reliable` is a **boolean, not an enum** — it
cannot express "video". And `PUT /annotations` currently owns `metrics_json.cycles` unilaterally.

### 5.3 ⚠ What is completely missing

- **No Python video/CV dependency anywhere.** `requirements.txt` is numpy/scipy/PyWavelets/pandas/
  plotly/matplotlib/anthropic/streamlit/fastapi/uvicorn/supabase/stumpy/stripe. No `opencv`, `torch`,
  `mediapipe`, `ultralytics`, `onnxruntime`, `ffmpeg-python`, `av`. `scikit-learn` exists only in
  `requirements-notebook.txt`.
- **⚠ The backend has never read a video byte back.** Every `storage.from_("videos")` call is
  `.upload()`, `.remove()`, or `.create_signed_url()`. **There is no `.download()` anywhere.** Video
  bytes touch Python once, on upload (`await file.read()`), and are forwarded straight to storage.
  Video is purely a frontend concern today.
- **No compute infra.** `Procfile` is a single `uvicorn` web dyno. No GPU, no worker, no queue
  (no Celery/RQ/arq/Dramatiq). Every endpoint is synchronous; `POST /process` does its DSP inline.
- **No frame access on the server.** No frame-extraction endpoint. The *only* pixel processing in the
  entire product is `grabThumb()` canvas grabs and `jsQR` slate decoding — **in the browser**.
- **No camera metadata.** `session_videos` carries only `storage_path`, `origin_s`, free-text `label`,
  `created_at`. **No fps** — `CameraTile.js:7` hardcodes `FRAME_S = 1/30`, so a 60 fps GoPro steps two
  frames per press. No resolution, codec, angle, mount, view, lens/FOV, calibration, or scale — despite
  the repo having footage directories literally named `Side_underwater/`, `Aerial/`, etc.
- **No labels a CV model could train on.** Annotations are encoder-timeline *event times* — no boxes,
  no keypoints, no per-frame labels, no video-axis spans. ~43 sessions × 4 boundaries + ~40 marks =
  a few thousand timestamps, zero frames. **Backstroke 0 annotations, dolphin kicks 0.**
- **Operational:** free tier is already over quota (2.53 GB vs 1 GB); video is 2,512 of 2,529 MB.

### 5.4 ⚠ You already built this twice, and killed it twice

- `pose_extraction.py` imports `cv2`, `torch`, and `transformers.VitPoseForPoseEstimation`, runs
  ViTPose-L per frame and writes a COCO17-keypoint CSV time-aligned to the encoder by an **LED flash
  frame**. Plus `video_sync.py`, `merge_streams.py`, `scripts/visualize_pose.py`, `pose/AP.csv`,
  `pose/AP_annotated.mp4` (55 MB), `AP.mp4` (60 MB). **None of it is importable** — the libraries are
  in no requirements file. DATA-FLOW.md:529 classifies them: *"Vision pipeline exploration. Not wired
  to anything."*
- `vision_pipeline_plan.md` opens: *"**(Off-roadmap — video analysis permanently deferred)** … Video
  analysis adds cost and complexity without meaningful accuracy gains over the encoder-only approach."*
  It is nonetheless a detailed 11 KB RTMPose + SwimXYZ blueprint (LED sync circuit, MMPose setup).
- `CameraTile.js:26`: *"⚠ No push-off / dive detection anywhere (removed 71-02, D10) — alignment is
  coach-controlled."* **An automatic video-detection feature was built and then deliberately removed.**

**Before starting a third attempt, read `vision_pipeline_plan.md` and find out what changed.**

### 5.5 The cheapest useful version, if you want one

Not a recommendation — an observation about what the seams permit. The cost curve is steep and the
low end is genuinely cheap:

| Tier | What | Cost |
|---|---|---|
| A | **Nothing new.** Coach marks boundaries on video in fullscreen — *already shipped* (Phase 81) | 0 |
| B | Client-side heuristic in the browser (frame-differencing for splash onset at dive/breakout), coach confirms | small; no Python, no infra |
| C | Server-side pose → boundary detector | needs `.download()`, cv2/torch, a worker, a GPU, and **labelled frames you do not have** |

Tier B is where the asymmetry lives: the browser already decodes frames (`grabThumb`, `jsQR`), the
timeline mapping already exists, and the boundary seam takes a fourth source cheaply.

---

## 6. Tethered-swimming validity — is your signal defensible?

**⚠ First, a definitional correction you must make.** The literature uses "tethered swimming" for
three different things:

- **Fully tethered** — anchored, swims in place against a load cell. Measures **force**. Not you.
- **Semi-tethered / resisted** — moves against added load. Measures **load–velocity**. Not you.
- **Cable speedometer / velocity meter** — free-running unloaded line on a spring spool. **This is you.**

Citing fully-tethered force literature to defend a speedometer is a category error a sports scientist
will catch instantly.

**Is the speedometer accepted? Yes.** The IVV scoping review (Bioengineering 2023, PMC10044880) finds
**mechanical devices = 56% of studies, 82% of those cable speedometers.** Barbosa et al. validated a
mechanical speedometer against video digitising on all three criteria (paired t α≥0.05, R²≥0.49,
Bland–Altman ≥80% within ±1.96 SD).

**But do not call it the gold standard.** The review's nominal gold standard is **centre of mass**,
and it is explicit that the hip *overestimates*: *"Hip error magnitude should also be considered
because it overestimates swimming velocity and, consequently, the IVV of the four conventional
swimming techniques."* **Your IVV numbers are systematically inflated relative to the field's own
reference.** Say so in your own docs before someone else does.

**Does the tether alter mechanics?** For fully tethered: *"differences in stroke mechanics can occur
… but there is no evidence to suggest that they affect swimming performance."* For resisted: validity
decays with load (r 0.929 → 0.403 as load rises). An unloaded speedometer sits at the favourable end —
**but that is an inference, not a measurement.** `[UNVERIFIED — no study found isolating the kinematic
effect of an unloaded speedometer cord.]`

### ⚠ 6.1 The uncomfortable one: does IVV actually matter?

**This is contested, and it is your core product claim.**

The standard theory (*"lower IVV = less drag = better"*) is opposed by: *"faster swimmers showed lower
IVV in breaststroke, while elite swimmers showed a higher maximal peak velocity in a stroke cycle,
resulting in higher IVV in breaststroke"* and *"The literature presents conflicting results … showing
both higher and lower values in elite swimmers … might be explained by individual differences in drag
profile and might not be directly related to the velocity variation itself."* There is even a paper
questioning whether CV is a valid IVV measure at all.

**"Lower IVV = better swimmer" is not settled science.** Your defensible framing is **within-athlete
change over time**, not cross-athlete ranking or absolute thresholds — which is exactly the doctrine
already recorded in PROJECT.md ("within-athlete contrast, no absolute thresholds") and in the
attention-allocation reframe. **Hold that line.** Do not let the product drift into "your IVV is 0.14,
elite is 0.11."

---

## 7. Where the honest answer is "video wins"

| Capability | Winner | Why |
|---|---|---|
| Splits, stroke rate, DPS, stroke count | **Video, decisively** | ±1 stroke, <1 s latency, 24 swimmers, $6–9/mo |
| Underwater distance, breakout, **turn time** | **Video, decisively** | The cord physically cannot do turns |
| Every-practice passive monitoring | **Video** | No setup, whole squad |
| Race / competition analysis | **Video, by default** | Cannot tether at a meet |
| Technique cues (catch, elbow, entry, head) | **Video, exclusively** | You see the waist only |
| Coach trust / explainability | **Video** | Coaches believe pictures |
| Price anchoring | **Video** | $5.99/mo already exists |
| Intra-cycle velocity waveform | **Contested** | ±0.19–0.46 RMSE; one paper says the *tether* distorts it |
| Zero-calibration, any venue, any water | **Encoder, durably** | Physics, not model capacity |
| Cost to first measurement | **Encoder** | $300 vs a camera install |
| Ground-truth labelling for CV training | **Encoder** | The asymmetric asset |

---

## 8. Candidate next actions (for review — none of these are decided)

1. **⭐ Run the cord-drag study.** 20 swimmers, 25 m free, cord vs no cord, compare stroke rate,
   stroke length, and 25 m time. Cheap, publishable, and it permanently closes the biggest hole in
   your defensibility. `[UNVERIFIED in the literature — nobody has done it.]`
2. **⭐ Measure and publish your own slack-artefact rate.** van Houwelingen's charge is specific and
   mechanical. If your retraction maintains tension and you can show it, you neutralise the one paper
   that says your instrument is the inaccurate one. **If you cannot, you need to know before a
   customer's sports scientist finds it.** You already have 43 annotated sessions to look at.
3. **Stop selling metrics video already owns** (splits, stroke rate, DPS, underwater distance). The
   defensible product is the within-cycle trace, the phase decomposition on it, and **change over
   time for one athlete** — plus the labelled dataset that falls out.
4. **Reposition the pitch onto deployment friction**, not accuracy. "Works in your murky outdoor pool
   at 4pm with no cones, no calibration, no ceiling mounts" is a claim no CV vendor can make.
5. **Read `vision_pipeline_plan.md` before any CV work**, and decide explicitly whether Tier B
   (browser-side splash-onset heuristic, coach-confirmed) is worth it. Tier C is not currently
   reachable — no labelled frames, no worker, no GPU.
6. **Resolve the recurring-revenue contradiction** (§4.3). A per-swimmer monthly price implies passive
   monitoring; the tether is a test protocol.
7. **Correct "Time Drop" in your own competitive notes** before it reaches a pitch.

---

## 9. Explicitly unverified

- Whether TIMEDROP Technology LLC has a CV roadmap behind its invite wall (about/features 404).
- Pricing for SenSwim, AIM Systems, CONTEMPLAS, APLab Speed RT, Swimsportec, Ergotest MuscleLab —
  none published.
- **Any independent validation of AIM Systems, SenSwim, SwimMate, LaneVision, SwimInsights,
  SwimScanner or iSWIM. None of them publishes one.** All accuracy claims are self-reported.
- Added hydrodynamic drag of an unloaded speedometer cord — no isolating study found.
- Chinese/Japanese swim-specific CV beyond SenseTime InnoMotion (broadcast-oriented).

## Key sources

- Scott et al. 2024 — https://www.tandfonline.com/doi/full/10.1080/14763141.2024.2388572 · https://commons.nmu.edu/isbs/vol41/iss1/96/
- van Houwelingen et al. 2018 — https://pure.tue.nl/ws/portalfiles/portal/113457165/Houwelingen2018_Article_AutomatedLEDTrackingToMeasureI.pdf
- DeepDASH (Hall et al. 2020) — https://link.springer.com/article/10.1007/s00521-020-05485-3
- IVV scoping review — https://pmc.ncbi.nlm.nih.gov/articles/PMC10044880/
- IMU vs speedometer — https://doi.org/10.3390/bioengineering11080757
- SwimXYZ — https://arxiv.org/html/2310.04360 · SwimmerNET — https://pmc.ncbi.nlm.nih.gov/articles/PMC9966167/
- SenSwim https://www.senswim.com/ · AIM https://aimsystems.se/features/ · SwimMate https://swimai.net/
- APLab Speed RT https://www.aplab.it/en/projects/speed-rt-velocity-meter.html · Race Club https://theraceclub.com/swim-coaching-services/
- TIMEDROP https://www.timedrop.com/ · Time Drops https://time-drops.com/
