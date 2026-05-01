import hashlib

_CHUNK_SIZE = 65536


class MediaHasher:
    @staticmethod
    def hash(path: str) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as fh:
            while chunk := fh.read(_CHUNK_SIZE):
                digest.update(chunk)
        return digest.hexdigest()
