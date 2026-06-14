# Recording MKV Remux Design

**Goal:** Make Android game recording reliable on Windows while preserving browser playback in reports.

**Confirmed Problems:** Current code still records directly to `record.mp4` and depends on Windows Ctrl+C delivery to let scrcpy write the MP4 `moov` atom. `docs/视频问题.md` records repeated failures for that path. Current code also marks MKV as browser-playable, while existing acceptance tests and user feedback show MKV duration and seeking are unreliable in the browser.

**Chosen Approach:** Record with scrcpy into `record.mkv`, then after stop run `ffmpeg -c copy -movflags +faststart` to produce `record.mp4`. Only a validated MP4 is browser playable. MKV remains a fallback artifact for the system player, not the HTML5 player.

**Dependency Strategy:** Detect ffmpeg before starting recording. Search order is `SOLOX_FFMPEG`, bundled project paths under `solox/public/ffmpeg/`, then `PATH`. If ffmpeg is unavailable, `/apm/record/start` fails with an actionable message instead of starting a recording that cannot become a browser-playable report video.

**Risk Controls:** Do not reintroduce `screenrecord` for games, do not depend on MP4 Ctrl+Break finalization, and keep stderr redirected to `scrcpy_record.log`. The remux step is no-reencode, so quality is preserved and runtime overhead should be small.

