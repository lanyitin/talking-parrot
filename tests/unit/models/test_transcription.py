from talking_parrot.models.transcription import (
    TranscriptionMetrics,
    TranscriptionResult,
)


class TestTranscriptionMetrics:
    def test_metrics_accessible_by_attribute(self):
        m = TranscriptionMetrics(
            avg_logprob=-0.5,
            compression_ratio=1.2,
            no_speech_prob=0.05,
            repetition_ratio=0.01,
        )
        assert isinstance(m.avg_logprob, float)
        assert isinstance(m.compression_ratio, float)
        assert isinstance(m.no_speech_prob, float)
        assert isinstance(m.repetition_ratio, float)


class TestTranscriptionResult:
    def test_result_fields_present(self):
        m = TranscriptionMetrics(
            avg_logprob=-0.5,
            compression_ratio=1.2,
            no_speech_prob=0.05,
            repetition_ratio=0.01,
        )
        r = TranscriptionResult(
            chunk_index=0,
            start_ms=0,
            end_ms=1000,
            text="hello",
            language="en",
            model_used="tiny",
            metrics=m,
            aligned_tokens=None,
        )
        assert r.metrics.avg_logprob == -0.5
        assert r.aligned_tokens is None
