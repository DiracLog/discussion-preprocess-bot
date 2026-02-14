from typing import List


class TextChunker:
    def __init__(self, chunk_size: int, overlap: int):
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")

        self.chunk_size = chunk_size
        self.overlap = overlap

    def split(self, text: str) -> List[str]:
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            chunks.append(text[start:end])

            if end == text_len:
                break

            start += self.chunk_size - self.overlap

        return chunks
