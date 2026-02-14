import chromadb
import hashlib
import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional


# ---------------------- CONFIG ----------------------

@dataclass
class StorageConfig:
    db_path: str = "club_memory_db"
    collection_name: str = "book_club_discussions"
    logs_dir: str = "logs_archive"
    # Determines if we want to print verbose logs
    verbose: bool = True


# ---------------------- MAIN CLASS ----------------------

class StorageMind:
    def __init__(self, config: StorageConfig = StorageConfig()):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO if config.verbose else logging.WARNING)

        # Ensure handlers don't duplicate if re-initialized
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self._init_filesystem()
        self._init_database()

    # ---------------------- INITIALIZATION ----------------------

    def _init_filesystem(self):
        """Ensures local storage directories exist."""
        if not os.path.exists(self.config.logs_dir):
            os.makedirs(self.config.logs_dir)
            self.logger.info(f"📁 Created cold storage at: {self.config.logs_dir}")

    def _init_database(self):
        """Connects to ChromaDB and loads the collection."""
        self.logger.info(f"⏳ Opening Brain at '{self.config.db_path}'...")
        try:
            self.client = chromadb.PersistentClient(path=self.config.db_path)
            self.collection = self.client.get_or_create_collection(name=self.config.collection_name)
            count = self.collection.count()
            self.logger.info(f"✅ Brain Loaded. Memory count: {count}")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize ChromaDB: {e}")
            raise e

    # ---------------------- PUBLIC API ----------------------

    def archive_session_log(self, transcript: str, analysis: Any, user_name: str = "Unknown") -> str:
        """
        Saves the raw session data to a JSON file (Cold Storage).
        Returns the unique Session ID.
        """
        session_id = str(uuid.uuid4())
        timestamp = int(datetime.now().timestamp())

        log_entry = {
            "id": session_id,
            "timestamp": timestamp,
            "user": user_name,
            "transcript": transcript,
            "analysis": analysis
        }

        filename = f"log_{timestamp}_{session_id}.json"
        filepath = os.path.join(self.config.logs_dir, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(log_entry, f, ensure_ascii=False, indent=2)
            self.logger.info(f"📄 Log archived: {filename}")
            return session_id
        except Exception as e:
            self.logger.error(f"❌ Failed to archive log: {e}")
            return session_id  # Return ID anyway so flow continues

    def store_insights(self, analysis_item: Dict[str, Any], original_transcription: str,
                       speaker_id: str = "Unknown", meeting_date: Optional[str] = None,
                       full_log_id: Optional[str] = None) -> None:
        """
        Extracts arguments from an analysis item and saves them as vectors.
        Replaces 'save_analysis'.
        """
        # 1. Sanitize Inputs
        meta_base = self._extract_metadata_base(analysis_item, speaker_id, meeting_date, full_log_id)
        arguments = self._extract_arguments(analysis_item)

        if not arguments:
            self.logger.warning(f"⚠️ No arguments found to save for '{meta_base['title']}'.")
            return

        self.logger.info(
            f"💾 Saving {len(arguments)} thoughts about '{meta_base['title']}' by {meta_base['speaker']}...")

        # 2. Prepare Batch
        documents = []
        metadatas = []
        ids = []

        for arg in arguments:
            # Create a deterministic ID to prevent duplicates for the exact same thought in the same session
            unique_string = f"{full_log_id}_{meta_base['title']}_{arg}"
            doc_id = hashlib.md5(unique_string.encode()).hexdigest()

            # Metadata copy for this specific document
            meta = meta_base.copy()
            meta["source_snippet"] = original_transcription[:100] + "..."

            documents.append(arg)
            metadatas.append(meta)
            ids.append(doc_id)

        # 3. Upsert to DB
        if documents:
            self.collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            self.logger.info("✅ Insights saved successfully!")

    def search(self, query_text: str, filter_user: Optional[str] = None, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Semantic search with optional user filtering.
        """
        self.logger.info(f"🔎 Searching for '{query_text}' (Filter: {filter_user})...")

        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results * 2  # Fetch extra to handle post-filtering
        )

        clean_results = []

        if not results['documents']:
            return []

        doc_list = results['documents'][0]
        meta_list = results['metadatas'][0]

        for i, (doc, meta) in enumerate(zip(doc_list, meta_list)):
            # Manual Filter Logic (Chroma's where clause is strict, soft filtering is safer for partial matches)
            if filter_user:
                stored_speaker = str(meta.get('speaker', ""))
                if filter_user.lower() not in stored_speaker.lower():
                    continue

            clean_results.append({
                'text': doc,
                'metadata': meta
            })

            if len(clean_results) >= n_results:
                break

        return clean_results

    def retrieve_transcript(self, full_log_id: str) -> str:
        """Retrieves full text from cold storage by ID."""
        for filename in os.listdir(self.config.logs_dir):
            if full_log_id in filename:
                full_path = os.path.join(self.config.logs_dir, filename)
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        return data.get('transcript', "")
                except Exception as e:
                    self.logger.error(f"Error reading log file: {e}")
                    return ""
        return "⚠️ Original log file not found."

    def nuke_db(self):
        """DANGER: Completely wipes the database."""
        self.logger.warning("⚠️ Wiping all memories...")
        try:
            self.client.delete_collection(name=self.config.collection_name)
        except ValueError:
            pass  # Collection didn't exist

        self.collection = self.client.get_or_create_collection(name=self.config.collection_name)
        self.logger.info("✅ Memory wiped clean.")

    # ---------------------- INTERNAL HELPERS ----------------------

    def _extract_arguments(self, analysis_item: Dict[str, Any]) -> List[str]:
        """Normalizes arguments into a list of strings."""
        args = analysis_item.get("arguments", [])
        if isinstance(args, str):
            return [args]
        return args

    def _extract_metadata_base(self, item: Dict[str, Any], speaker_id: str, date: Optional[str],
                               log_id: Optional[str]) -> Dict[str, Any]:
        """
        Sanitizes and prepares base metadata.
        Handles missing keys, None values, and list flattening.
        """
        # 1. Speaker: Prefer item-specific speaker, fall back to global
        final_speaker = item.get("speaker") or speaker_id

        # 2. Title: Handle synonyms and lists
        raw_title = item.get("title") or item.get("book_title") or "Unknown Title"
        title = ", ".join([str(t) for t in raw_title]) if isinstance(raw_title, list) else str(raw_title)

        # 3. Sentiment
        sentiment = item.get("sentiment") or "neutral"

        # 4. Mark: Ensure int
        try:
            mark = int(item.get("mark") or 0)
        except (ValueError, TypeError):
            mark = 0

        # 5. Boolean flags
        is_inferred = bool(item.get("is_inferred_score", False))

        # 6. Date
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        return {
            "title": title,
            "sentiment": sentiment,
            "mark": mark,
            "is_inferred_score": is_inferred,
            "full_log_id": str(log_id or ""),
            "speaker": final_speaker,
            "date": date,
            "timestamp": datetime.now().isoformat()
        }


# ---------------------- ENTRY POINT ----------------------

if __name__ == "__main__":
    # Test suite
    logging.basicConfig(level=logging.INFO)
    db = StorageMind()

    # Mock data
    mock_data = {
        "title": ["Dune", "Dune Part 2"],
        "sentiment": "positive",
        "arguments": ["Great visuals", "Slow pacing"],
        "mark": None,
        "speaker": "TestUser"
    }

    # Test save
    log_id = db.archive_session_log("Raw transcript...", mock_data, "Tester")
    db.store_insights(mock_data, "Raw transcript...", full_log_id=log_id)

    # Test search
    results = db.search("visuals")
    for res in results:
        print(f"Found: {res['text']} (Meta: {res['metadata']})")