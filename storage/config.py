from dataclasses import dataclass


@dataclass
class StorageConfig:
    db_path: str = "club_memory_db"
    collection_name: str = "book_club_discussions"
    logs_dir: str = "logs_archive"
    verbose: bool = True
