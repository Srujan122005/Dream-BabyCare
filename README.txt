This file contains instructions for developers about adding local video files.

Note for maintainers:
- Do not include raw Windows paths or backslashes here; keep example commands generic.
- If you need to store copy/move examples, prefer forward slashes (POSIX) or provide escaped backslashes.

Example (POSIX-style):
  cp /path/to/your/video.mp4 static/videos/diapering/diapering_video_1.mp4

This file intentionally avoids raw Windows paths so the Jinja lexer does not attempt to decode escape sequences.

If you need the original Windows command, store it outside the `templates/` directory.