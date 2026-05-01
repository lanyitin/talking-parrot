"""VAD (Voice Activity Detection) subsystem.

Exposes the ``VADBackend`` abstract interface and the ``RawVadFrame`` value object.
Concrete backend implementations live in sub-modules:

- ``talking_parrot.vad.ten_vad`` — TEN VAD backend
- ``talking_parrot.vad.silero_vad`` — Silero VAD backend
"""

from talking_parrot.vad.backend import VADBackend

__all__ = ["VADBackend"]
