import hashlib

from talking_parrot.io.media_hasher import MediaHasher


class TestMediaHasher:
    def test_returns_64_char_hex_string(self, tmp_path):
        f = tmp_path / "test.mp4"
        f.write_bytes(b"some content")
        result = MediaHasher.hash(str(f))
        assert len(result) == 64
        assert result == result.lower()
        int(result, 16)  # must be valid hex

    def test_same_content_same_hash(self, tmp_path):
        content = b"identical content" * 100
        f1 = tmp_path / "a.mp4"
        f2 = tmp_path / "b.mp4"
        f1.write_bytes(content)
        f2.write_bytes(content)
        assert MediaHasher.hash(str(f1)) == MediaHasher.hash(str(f2))

    def test_different_content_different_hash(self, tmp_path):
        f1 = tmp_path / "a.mp4"
        f2 = tmp_path / "b.mp4"
        f1.write_bytes(b"content a")
        f2.write_bytes(b"content b")
        assert MediaHasher.hash(str(f1)) != MediaHasher.hash(str(f2))

    def test_matches_hashlib_sha256(self, tmp_path):
        content = b"verify me" * 1000
        f = tmp_path / "file.mp4"
        f.write_bytes(content)
        expected = hashlib.sha256(content).hexdigest()
        assert MediaHasher.hash(str(f)) == expected
