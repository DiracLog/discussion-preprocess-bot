import chromadb
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from storage.config import StorageConfig


class StorageMind:

    def __init__(self, config: StorageConfig = StorageConfig()):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO if config.verbose else logging.WARNING)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            self.logger.addHandler(handler)

        self._init_filesystem()
        self._init_database()

    # ---------------- INIT ----------------

    def _init_filesystem(self):
        os.makedirs(self.config.logs_dir, exist_ok=True)

    def _init_database(self):
        self.client = chromadb.PersistentClient(path=self.config.db_path)
        self.collection = self.client.get_or_create_collection(
            name=self.config.collection_name
        )

    # ---------------- LOG STORAGE ----------------

    def archive_session_log(self, transcript: str, analysis: Any, user_name: str) -> str:
        session_id = str(uuid.uuid4())
        timestamp = int(datetime.now().timestamp())

        data = {
            "id": session_id,
            "timestamp": timestamp,
            "user": user_name,
            "transcript": transcript,
            "analysis": analysis
        }

        path = os.path.join(self.config.logs_dir, f"log_{timestamp}_{session_id}.json")

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return session_id

    # ---------------- VECTOR STORAGE ----------------

    def store_insights(self, analysis_item: Dict[str, Any], original_transcription: str,
                       speaker_id: str, full_log_id: str):

        arguments = analysis_item.get("arguments", [])
        if isinstance(arguments, str):
            arguments = [arguments]

        documents = []
        metadatas = []
        ids = []

        for arg in arguments:
            unique = f"{full_log_id}_{analysis_item.get('title')}_{arg}"
            doc_id = hashlib.md5(unique.encode()).hexdigest()

            documents.append(arg)
            metadatas.append({
                "speaker": speaker_id,
                "title": analysis_item.get("title"),
                "full_log_id": full_log_id
            })
            ids.append(doc_id)

        if documents:
            self.collection.upsert(documents=documents, metadatas=metadatas, ids=ids)

    # ---------------- SEARCH ----------------

    def search(self, query_text: str, filter_user: Optional[str] = None,
               n_results: int = 3) -> List[Dict[str, Any]]:

        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        clean = []

        for doc, meta in zip(docs, metas):
            if filter_user:
                if filter_user.lower() not in str(meta.get("speaker", "")).lower():
                    continue

            clean.append({"text": doc, "metadata": meta})

        return clean
