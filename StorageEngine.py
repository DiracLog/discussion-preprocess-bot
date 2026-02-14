import chromadb
from datetime import datetime
import hashlib
import os
import json
import uuid


class StorageMind:
    def __init__(self, db_path="club_memory_db", logs_dir="logs_archive"):
        """
        Initializes the Vector Database (ChromaDB).
        Args:
            db_path: Folder where data will be saved locally.
        """
        print(f"⏳ Opening Brain at '{db_path}'...")
        # PersistentClient saves data to disk so it survives restarts
        self.client = chromadb.PersistentClient(path=db_path)

        # Create or Get the collection (Table)
        self.collection = self.client.get_or_create_collection(name="book_club_discussions")
        print("✅ Brain Loaded. Memory count:", self.collection.count())

        self.logs_dir = logs_dir
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)
            print(f"📁 Created cold storage at: {self.logs_dir}")

    def save_log_to_disk(self, transcript, analysis, user_name="Unknown"):
        """
        Saves the raw data to a JSON file and returns the ID.
        Call this BEFORE saving to Vector DB.
        """
        # Generate the Master ID for this session
        session_id = str(uuid.uuid4())
        timestamp = int(datetime.now().timestamp())

        # The full raw record
        log_entry = {
            "id": session_id,
            "timestamp": timestamp,
            "user": user_name,
            "transcript": transcript,  # The full text!
            "analysis": analysis  # The structured data
        }

        # Save to file
        filename = f"{self.logs_dir}/log_{timestamp}_{session_id}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(log_entry, f, ensure_ascii=False, indent=2)

        print(f"📄 Log saved to disk: {filename}")
        return session_id  # <--- RETURN THIS so we can pass it to Vectors!

    def save_analysis(self, analysis_json, original_transcription, speaker_id="Unknown", meeting_date=None,
                      full_log_id=None):
        """
        Saves the structured data into the Vector DB.

        Args:
            analysis_json (dict): A SINGLE review object (title, mark, arguments, etc.)
            original_transcription (str): The raw text context.
            speaker_id (str): Fallback speaker (usually list of all participants).
            meeting_date (str): YYYY-MM-DD.
            full_log_id (str): The UUID/Filename of the complete JSON log on disk (Cold Storage).
        """
        # --- ROBUST EXTRACTION ---

        # 1. Handle Speaker (CRITICAL CHANGE)
        # Prioritize the speaker identified by the LLM inside the JSON.
        # If missing, fall back to the generic list passed by the bot.
        specific_speaker = analysis_json.get("speaker")
        if specific_speaker:
            final_speaker = specific_speaker
        else:
            final_speaker = speaker_id

        # 2. Handle Title (Can be string OR list)
        raw_title = analysis_json.get("title") or "Unknown Title"
        if isinstance(raw_title, list):
            title = ", ".join([str(t) for t in raw_title])
        else:
            title = str(raw_title)

        # 3. Handle Sentiment
        sentiment = analysis_json.get("sentiment") or "neutral"

        # 4. Handle Mark (Int)
        mark = analysis_json.get("mark")
        if mark is None:
            mark = 0
        else:
            try:
                mark = int(mark)
            except:
                mark = 0

        # 5. Handle "Is Inferred Score" (New Field)
        is_inferred = analysis_json.get("is_inferred_score", False)

        # 6. Handle Arguments
        arguments = analysis_json.get("arguments", [])
        if isinstance(arguments, str):
            arguments = [arguments]

        if meeting_date is None:
            meeting_date = datetime.now().strftime("%Y-%m-%d")

        print(f"💾 Saving {len(arguments)} thoughts about '{title}' by {final_speaker}...")

        documents = []
        metadatas = []
        ids = []

        for arg in arguments:
            # The thought itself is the vector
            documents.append(arg)

            # Create a deterministic ID based on content to prevent duplicates
            # We include the log_id so different sessions are unique even if arguments are identical
            unique_string = f"{full_log_id}_{title}_{arg}"
            deterministic_id = hashlib.md5(unique_string.encode()).hexdigest()

            # Metadata for filtering
            metadatas.append({
                "title": title,
                "sentiment": sentiment,
                "mark": mark,
                "is_inferred_score": is_inferred,
                "full_log_id": str(full_log_id),
                "speaker": final_speaker,  # <--- Now uses the specific speaker
                "date": meeting_date,
                "timestamp": datetime.now().isoformat(),
                "source_snippet": original_transcription[:100] + "..."
            })

            # Unique ID for this specific argument vector
            ids.append(deterministic_id)

        if documents:
            self.collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print("✅ Saved successfully!")
        else:
            print("⚠️ No arguments found to save.")

    def search_memory(self, query_text, filter_user=None, n_results=3):
        """
        Args:
            query_text (str): The semantic topic.
            filter_user (str): speaker to filter for (Optional).
        """
        print(f"\n🔎 Searching for '{query_text}' (Filter: {filter_user})...")

        # Basic query
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results * 2  # Fetch more candidates to filter manually if needed
        )

        clean_results = []

        # Chroma returns [[doc1, doc2]] for documents and metadatas
        if not results['documents']:
            return []

        doc_list = results['documents'][0]
        meta_list = results['metadatas'][0]

        for i in range(len(doc_list)):
            doc = doc_list[i]
            meta = meta_list[i]

            # Manual Filter Logic
            if filter_user:
                stored_speaker = meta.get('speaker', "")
                # Simple substring match (e.g. "Andrii" matches "Andrii")
                if filter_user.lower() not in stored_speaker.lower():
                    continue

            clean_results.append({
                'text': doc,
                'metadata': meta
            })

            if len(clean_results) >= n_results:
                break

        return clean_results

    def reset_memory(self):
        """
        DANGER: Completely wipes the database.
        """
        print("\n⚠️ WARNING: Wiping all memories...")
        try:
            self.client.delete_collection(name="book_club_discussions")
        except ValueError:
            pass

        self.collection = self.client.get_or_create_collection(name="book_club_discussions")
        print("✅ Memory wiped clean. The Brain is empty.")

    def get_full_context(self, full_log_id):
        """
        Retrieves the complete original transcript from Cold Storage (JSON).
        """
        search_dir = self.logs_dir

        for filename in os.listdir(search_dir):
            if full_log_id in filename:
                full_path = os.path.join(search_dir, filename)
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        return data['transcript']
                except Exception as e:
                    return f"Error reading log: {e}"

        return "⚠️ Error: Original log file not found."


if __name__ == "__main__":
    db = StorageMind()