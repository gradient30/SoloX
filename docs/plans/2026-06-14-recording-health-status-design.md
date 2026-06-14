# Recording Health Status Design

## Context

The 2026-06-14 18:31 report ran for 17:49 but produced a 0-byte `record.mkv` and no `record.mp4`. Logs show recording started successfully and the failure was only detected at report generation time, after waiting for finalization. This points to a source recording failure or lost recorder process, not an MP4 remux problem or a file-size-only problem.

## Design

Add a lightweight recording health layer around the existing scrcpy recorder.

- Track active recording metadata in `Scrcpy`: start time, target file, device, quality, last error, and whether the recorder process is alive.
- Add `/apm/record/status` so the UI can poll elapsed time, process state, file size, and risk level.
- Add visible top-page status: "已录时长 HH:MM:SS" with warning at 15 minutes and danger at 30 minutes.
- Preserve current recording flow. This phase does not force-stop long recordings and does not split recordings.
- When recording fails, write `record_error` to `result.json` so report pages can expose the reason instead of silently showing no video.
- Increase stop/finalize wait adaptively for longer sessions, but still surface invalid or zero-byte source files clearly.

## Risk Rules

- 0-15 minutes: normal.
- 15-30 minutes: warning. User can continue, but long single-file recording is higher risk.
- 30+ minutes: danger. Recommend ending the task and generating a report.

## Deferred

Segmented recording and MP4 concat are deliberately deferred. They are more robust for very long sessions but require a larger recorder lifecycle change.
