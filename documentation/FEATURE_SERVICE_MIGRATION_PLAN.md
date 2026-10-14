# Feature UI-Controller-Service Migration Plan

**Status:** PLANNING - implementation has not started  
**Scope:** Incrementally separate feature workflows while retaining shared application infrastructure.

## Decision: migrate in this repository

Perform this migration in the existing Karaoke Studio Pro repository, not in a new project. The current application, tests, packaging configuration, and shared services are the behavior baseline. A separate project would create competing implementations and make it harder to verify compatibility.

Use a dedicated feature branch or an isolated Git worktree for the migration. Keep the current working branch intact, inspect and preserve any pre-existing worktree changes, and merge small, reviewable slices back into the project. Do not create a second application or copy the source tree.

This is a behavior-preserving refactor. Do not combine it with feature redesigns, visual changes, dependency upgrades, or unrelated bug fixes. Each slice should leave the application runnable and testable.

## UI regression automation: use Qt tools, not Playwright

Karaoke Studio Pro is a native PySide6 desktop application, not a web application. Playwright drives browser pages and does not directly discover or operate native Qt widgets. Do not add Playwright by wrapping or rewriting the app UI just to automate these tests.

Use the existing pytest + Qt setup (`qapp` fixture and `QT_QPA_PLATFORM=offscreen`) with `PySide6.QtTest.QTest` for repeatable widget interaction. The current test dependencies do not include pytest-qt; use the existing fixture and QTest directly unless pytest-qt is deliberately added to `documentation/requirements-dev.txt`. These tests should exercise real page widgets and controller wiring while injecting fake services/workers at system boundaries. This verifies UI navigation and user-visible behavior without relying on audio hardware, installed VLC, network access, timing-sensitive downloads, or external services.

Add a separate opt-in Windows desktop end-to-end layer only if tests must launch and interact with the actual application process. Evaluate a native Windows UI automation tool (for example, pywinauto using Qt accessibility/object names) for that layer; it is distinct from Qt widget tests and Playwright. Do not make this extra tooling a prerequisite for the fast all-feature regression suite unless it proves stable in CI.

### Required UI regression coverage

Maintain a feature-to-test checklist/matrix as workflows migrate. The suite must cover every user-facing page and workflow, old and newly migrated, including:

- Sidebar/page navigation, current page and tab selection, disabled/guarded navigation, and page-specific layout/visibility behavior.
- Media Loader file selection/load, URL/download states (with network/download faked), load failures, and history interactions.
- Playback controls, seek/volume/speed/pitch interactions, playback-window range add/remove/clear/apply, and state reset on media changes.
- Audio Studio range and format input, trim/export action, status/progress/success/error/cancel states.
- Video Studio trim, playback window, audio extraction, and widen workflows.
- Convert & Export conversion, normalization, amplify/export, vocal separation, join/merge, and live-preview guards and lifecycle.
- Settings interactions and audio-meter/calibration UI states where they are relevant to the change.

Drive actual widgets/signals through their public interaction surfaces (clicks, text entry, combo/tab selection), then assert visible state and calls/results at the controller/service boundary. Do not test only that a widget exists or that a private method was called. Give important buttons/inputs stable `objectName` values if that makes the UI automation less dependent on labels or layout details.

### Media test data

The required regression suite should be self-contained and deterministic. Prefer short synthetic audio and video fixtures generated in a pytest temporary directory with the configured FFmpeg tool, or checked-in tiny redistributable fixtures when generation is unsuitable. Do not require the user to supply media for normal test runs.

Use fake processing runners/services for most UI tests so failures, progress, cancellation, and success can be covered deterministically. Add targeted integration tests that use generated media and the real FFmpeg/FFprobe path when available; inspect the produced file/streams and duration rather than asserting only that a process returned success. Mark environment-dependent integration tests explicitly and document their prerequisite.

The user may optionally provide representative audio/video samples to reproduce codec-, metadata-, or device-specific issues. Keep supplied/private samples outside version control (for example, an ignored local test-data directory), do not make ordinary CI depend on them, and record the tested properties without exposing private media paths or content.

## Target architecture

```text
Feature UI
   | intent, input, progress display
   v
Feature Controller
   | typed request/result, feature state and lifecycle
   v
Feature Service(s)
   | domain rules and feature-specific operation
   v
Shared Services / Infrastructure
   | player, media lifecycle, job execution, FFprobe, paths, logging
```

### Responsibilities and dependency rules

- **UI pages** create widgets, emit user intent, and display state. They do not build FFmpeg commands, launch subprocesses, or coordinate another feature's controls.
- **Feature controllers** connect one feature's UI to its service API. They own input validation at the UI boundary, feature-specific state transitions, and mapping progress/results/errors to the UI.
- **Feature services** own cohesive workflow rules, input validation that is part of the domain, and feature-specific command construction or orchestration. Use explicit request/result types and distinguish success, failure, and cancellation.
- **Shared services** provide capabilities that multiple features legitimately use. Feature services may depend on narrow shared-service interfaces; they must not manipulate another page's widgets or pass around the whole `KaraokeApp`.
- **Application shell (`main.py`)** is the composition root: it creates shared services and feature controllers, injects dependencies, and connects application-wide lifecycle events. It should not contain feature command builders or workflow rules.
- **Workers and processing runner** execute background work, report progress, and support cancellation. They do not own feature business rules.
- **Utilities** remain stateless, page-agnostic helpers. Reuse `source_code/utils/` rather than duplicating subprocess, FFprobe, media path, splash, or range-row behavior.

One service should own a cohesive workflow, not necessarily each individual button. Keep shared player, media, and job-runner instances; separation means clear ownership and narrow APIs, not duplicate infrastructure.

## Feature ownership map

The target names below are proposed names, not a requirement to create every module. Reuse existing classes where they already provide the right boundary.

| Feature/workflow | UI | Controller ownership | Feature service ownership | Shared dependencies |
|---|---|---|---|---|
| Media loading and history | `ui/media_loader_page.py` | Narrow the existing `MediaController` or split a `MediaLoaderController` | Reuse/refine `FileLoadingService` for safe load lifecycle | `PlayerService`, `AudioService`, settings, logging, FFprobe |
| URL download | Media Loader URL controls | `DownloadController` | Existing `DownloadService` owns download lifecycle | `ProcessThread`, subprocess utilities, settings, logging |
| Playback, seek, volume, speed, pitch | `ui/pitch_page.py`, `ui/playback_bar.py` | Existing `PlaybackController` | Existing `PlayerService` and `RealtimePitchService` own playback engines | Shared loaded-media state, audio monitoring |
| Playback-window ranges | Audio Studio and Video Studio controls | Audio/Video feature controllers call a common playback-window API | `PlaybackWindowService` owns range rules; actual playback remains in `PlaybackController` | `PlayerService`, media duration, range utilities |
| Audio trimming | `ui/audio_studio_page.py` | `AudioStudioController` | `AudioTrimService` owns range validation and audio export command | Processing runner, FFprobe, media paths |
| Video trimming | `ui/video_tools_page.py` | `VideoStudioController` | `VideoTrimService` owns video trim command and validation | Processing runner, FFprobe, media paths |
| Audio extraction and video widening | Video Studio tabs | `VideoStudioController` | Separate `AudioExtractionService` and `VideoWidenService` | Processing runner, FFprobe, media paths |
| Format conversion | `ui/convert_export_page.py` | `ConvertExportController` | `FormatConversionService` | Processing runner, FFprobe, media paths |
| Normalization and amplify/export | Convert & Export tabs | `ConvertExportController` | `NormalizationService` and `AmplifyExportService` | Processing runner, FFprobe, media paths |
| Join and merge | Convert & Export tab | `ConvertExportController` | `JoinMergeService` | Processing runner, FFprobe, media paths |
| Vocal separation | Convert & Export tab | `ConvertExportController` | `VocalSeparationService` orchestrates the existing separator worker | Worker lifecycle, settings, logging |
| Audio monitoring and calibration | Playback bar, meter, settings dialog | Keep app-level setup small; extract feature coordination only if needed | Existing `AudioService` coordinates the analyzer and meter | `AudioAnalyzerThread`, audio meter, settings |
| Navigation and page guards | Sidebar and page tabs | Existing `NavigationController` | No media-processing service | Read-only state/status APIs from relevant controllers |
| Settings and diagnostics | Settings dialog and app shell | Shell/settings orchestration | Existing settings persistence and `LoggingService` | Application lifecycle |

### Shared processing boundary

The current `ProcessingController` contains both feature-specific FFmpeg command builders and generic background-task lifecycle. Separate these responsibilities:

- A shared processing runner owns starting a worker, task identity, progress forwarding, cancellation, cleanup, and success/failure completion.
- Each feature service owns only its own validation, command construction, and workflow-specific outputs.
- Feature controllers turn runner events into page status/progress and expose feature-level cancellation.
- Preserve existing temporary-output, cleanup, splash, and task-completion behavior while extracting it.

Do not replace `ProcessingController` with a new oversized `ProcessingService`. The runner should be deliberately small and generic.

## Migration phases

All phases begin **Not started**. Update this table as work proceeds; link code changes and test results in the relevant implementation-log entry.

| Phase | Status | Scope and completion gate |
|---|---|---|
| 0. Baseline and inventory | Complete (2026-10-03) | Inventoried current feature and test ownership; added `tests/test_ui_regression.py`, offscreen `KaraokeApp` construction/navigation/control-click coverage, and `generated_media_files` audio/video fixture with FFprobe stream checks. Validation: full suite 555 passed, 1 expected platform skip; details and known limits below. No application behavior changed. |
| 1. Define contracts and shared runner | Not started | Add typed request/result or event contracts where useful. Isolate generic job execution from feature commands without changing command arguments or UI behavior. Runner tests cover success, failure, cancellation, cleanup, and progress. Run the full all-feature service/controller/UI regression suite and app-availability smoke check. |
| 2. Audio trimming | Not started | Add `AudioTrimService` and `AudioStudioController`; connect the existing trim UI; remove trim-specific ownership from the shell/generic processing controller. Focused service/controller/Qt UI tests pass, then run the full all-feature regression suite and app-availability smoke check. |
| 3. Playback-window behavior | Not started | Move range collection, validation, and playback-window decisions behind an explicit service/controller API for Audio and Video Studio. Keep playback execution on the shared player. Test empty, inverted, clamped, overlapping, single, and multiple ranges as applicable; then run the full all-feature regression suite and app-availability smoke check. |
| 4. Video Studio workflows | Not started | Extract video trim, audio extraction, and video widening into separate services behind `VideoStudioController`. Validate command arguments and cancellation for each workflow; after each workflow extraction, run the full all-feature service/controller/UI regression suite and app-availability smoke check. |
| 5. Convert & Export workflows | Not started | Extract conversion, normalization, amplify/export, join/merge, and vocal separation one workflow at a time behind `ConvertExportController`. Do not bundle several behavior changes into one extraction. After each workflow extraction, run the full all-feature service/controller/UI regression suite and app-availability smoke check. |
| 6. Playback, media, and download boundaries | Not started | Narrow existing playback, media, and download controllers/services to explicit APIs. Avoid needless rewrites where existing services already own the workflow. Run the full all-feature service/controller/UI regression suite and app-availability smoke check after each independently merged boundary change. |
| 7. Shell cleanup and architecture verification | Not started | Remove obsolete compatibility wiring only when proven unused. Confirm lifecycle, page guards, app startup/shutdown, tests, and PyInstaller imports still work. Run the full all-feature service/controller/UI regression suite and app-availability smoke check before completion. Refresh architecture and structure docs to describe the implemented architecture, not this target prematurely. |

### Phase 0 feature-to-test baseline matrix

This records actual baseline coverage, not a claim that every feature already has full end-to-end tests. UI action tests use the production `KaraokeApp.setup_ui` signal wiring, but replace operation handlers/shared media engines with recorders or fakes to avoid launching work, opening native file dialogs, or requiring devices. Existing unit tests cover the real controller/service logic separately. Fill the noted gaps during the owning feature phase.

| Workflow | Existing logic/test coverage | Qt UI baseline | Remaining end-to-end gaps |
|---|---|---|---|
| Application shell, sidebar, navigation, studio tabs | `test_navigation_controller.py`, `test_ui_components.py` | `test_ui_regression.py`: starts/closes the shell, clicks sidebar navigation and studio buttons, switches each studio's tabs | Modal navigation guard behavior through the real shell; visual layout/accessibility review |
| Media loading, URL download, history | `test_media_controller.py`, `test_file_loading_service.py`, `test_download_service.py` | `test_ui_regression.py`: clicks file-load and download controls, enters URL text, expands history and verifies a populated entry | Native file picker, download completion/failure display, history item activation |
| Playback, seek controls, pitch/speed, audio meter | `test_playback_controller.py`, `test_player_service.py`, `test_realtime_pitch_service.py`, `test_audio_service.py`, `test_audio_analyzer.py`, `test_audio_meter.py` | `test_ui_regression.py`: clicks transport controls, pitch/speed adjustments, mute, volume keyboard adjustment | Real VLC playback/seek and physical audio analysis/output |
| Audio Studio trimming and playback window | `test_processing_controller.py`, `test_playback_controller.py`, `test_ui_components.py` | `test_ui_regression.py`: clicks trim/range/download actions, selects a trim format, adds and applies/clears playback ranges | Real export completion, progress/error/cancel rendering, native audio-file selection |
| Video Studio trim, extraction, widen, playback window | `test_processing_controller.py`, `test_playback_controller.py`, `test_video_frame.py` | `test_ui_regression.py`: clicks trim, extraction, widen, and playback-window controls and tabs | Real video decode/export results, progress/error/cancel rendering, video playback |
| Convert & Export conversion, normalization, separator, join/merge, amplify | `test_processing_controller.py`, `test_audio_separator_thread.py` | `test_ui_regression.py`: clicks each workflow action and checks live-preview stop starts disabled | Real operation results and progress/error/cancel states; multi-file selection dialogs; preview audio behavior |
| Settings and audio calibration | `test_settings_dialog.py`, `test_audio_service.py`, `test_audio_meter.py` | `test_ui_regression.py`: verifies the settings entry point is wired | Dialog-field interaction through the main shell; real calibration/hardware behavior |
| Generated media baseline | No prior shared media fixture | `test_ui_regression.py`'s `generated_media_files` fixture creates short WAV and MP4 inputs with bundled/system FFmpeg and verifies their stream types with FFprobe | Using generated files through real player/export workflows; add targeted integration tests in the phase that owns each workflow |

**Phase 0 smoke-check boundary:** the shell is constructed, shown, navigated, and closed under offscreen Qt with fake player/audio/download services. The generated fixtures prove local media creation/probing. This does **not** claim real VLC playback, physical audio-device behavior, or real export workflows passed; those require targeted integration/manual checks during the corresponding phases.

## Standard procedure for each feature slice

1. **Inspect first:** Read `documentation/FILE_DEPENDENCIES.md`, this plan, the target UI/controller/service, tests, and relevant feature-specific instruction files. Check `git status`; never overwrite unrelated changes.
2. **Capture behavior:** Add or identify regression tests for externally observable behavior, including command arguments, state transitions, failure paths, cancellation, and cleanup.
3. **Define a narrow contract:** Specify typed request/result/progress/error data. Inject only the shared dependencies needed by the feature.
4. **Extract without redesign:** Move one workflow at a time. Preserve UI labels, formats, output naming, command behavior, progress, error visibility, and lifecycle.
5. **Test the seams:** Test the feature service independently, the controller with fake services, and Qt signal/wiring behavior where applicable.
6. **Remove old ownership:** Only after the new path is tested, remove duplicate handlers/state/command construction from the main window or generic controller.
7. **Validate the slice:** Run focused tests, then the complete all-feature service/controller/Qt UI regression suite, applicable generated-media integration tests, and app-availability smoke check before starting another workflow. Run `py_compile` on changed modules when useful.
8. **Update docs and packaging:** Keep the five synchronized docs aligned. Add hidden imports to `build_system/KaraokeStudioPro.spec` when new modules require them; update folder listings only for actual files.
9. **Report status:** Update this plan's phase status, implementation-log entry, exact all-feature regression and app-smoke results, remaining blockers, and next slice.

## Regression safeguards

- Keep one shared `PlayerService`, media lifecycle, settings source, logger, and processing runner where they are application-wide resources.
- Do not make a feature service depend on Qt widgets, a page dictionary, or the full `KaraokeApp`.
- Do not let feature controllers import or mutate another feature's controller internals.
- Keep UI and playback-window indices stable unless a separately tested requirement changes them.
- Surface errors through the established UI/logging path; do not silently use success-shaped defaults.
- Keep tests for previously fixed regressions and add a test for every bug found during migration before or with its fix.
- At the end of every phase—and after every individual workflow extraction within a phase that contains multiple workflows—run regressions across all existing and newly migrated features, not just the code touched in that slice.
- Confirm application availability after each phase by launching the app from source and exercising a documented smoke checklist for startup, navigation, media load, playback, and the migrated workflow. Where an interactive/manual check is required, record it explicitly rather than claiming automation covered it.
- If the complete regression suite or app-availability check fails, the phase is not complete. Fix the regression or clearly report the blocker; do not proceed to the next phase as though the app were verified.
- Avoid broad exception handling, unrelated formatting, bulk renames, and replacing working behavior just to match proposed class names.
- Do not update the architecture docs to claim a phase is implemented until its code and tests are actually complete.

## Test and build gates

Follow the commands in `DEVELOPMENT.md` and `documentation/TESTING.md`. At minimum:

- Focused tests for the feature service, controller, and relevant UI wiring pass.
- Full all-feature regression suite passes at the end of every phase and after each independently extracted workflow within a multi-workflow phase. It must include unit/service/controller coverage and automated Qt UI navigation and workflow interaction for both migrated/new paths and existing/unmigrated features.
- Every user-facing feature in the ownership map has a corresponding automated UI test or a documented reason and manual substitute. The feature-to-test matrix is reviewed at each phase gate; no feature is considered covered merely because its page opens.
- Applicable generated-media integration tests pass for changed media-processing workflows. The core UI suite remains deterministic and does not require user-provided media, audio hardware, network access, or a GUI display.
- Application-availability check passes at the end of every phase: source app launches and automated Qt UI tests exercise core navigation, media load/playback paths, and the phase's changed workflow. Record any manual or Windows process-level steps and outcomes.
- Changed Python modules pass `py_compile` or the repository's equivalent static validation.
- The application starts from source after composition-root changes and before any phase is marked complete.
- Run a distribution build after module/package or PyInstaller configuration changes, subject to the required bundled tools and model cache.
- Any failure is reported with its actual output; do not mark a phase complete based on a proxy check. A focused test run alone is not sufficient evidence that the rest of the application remains available.

## Instructions for a future implementation agent

Treat this file as the migration's scope and sequencing reference, not as evidence that the migration has already happened.

Before implementation:

1. Read this file and all five synchronized project documents.
2. Inspect the current branch, worktree, relevant source, tests, and repository-specific editing instructions.
3. Confirm the requested phase/slice and report any mismatch between this plan and current code before expanding scope. Preserve the full service/controller/UI regression suite, applicable media integration tests, and app-availability gates regardless of which phase is requested.

During implementation:

1. Work on one feature workflow per slice. Start with Phase 0 if no current inventory and test baseline are recorded.
2. Preserve unrelated user changes. Do not commit unless explicitly asked.
3. Make the smallest complete extraction that establishes the stated boundary and its tests.
4. At phase end, run and report the complete regression suite for all old and new features—including automated Qt UI navigation and workflow interactions—plus applicable generated-media integration tests and the app-availability check. Update status only when all phase gates pass; otherwise record partial work and blockers.

At completion, report changed files, behavior preserved, focused and full service/controller/UI regression results, UI feature-matrix coverage, applicable media integration and app-availability results, build checks when applicable, phase status, any known limitations, and the next recommended slice. Never represent the application as verified/available when required automation or a gate was skipped or failed.
