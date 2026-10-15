"""Vector database and semantic retrieval module using ChromaDB."""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from src.config import DEFAULT_NOTES_PATH, CHROMA_PERSIST_DIR

class ContextNoteStore:
    def __init__(self, notes_path: Path = DEFAULT_NOTES_PATH, persist_dir: Optional[Path] = CHROMA_PERSIST_DIR):
        self.notes_path = notes_path
        self.persist_dir = persist_dir
        if persist_dir:
            persist_dir.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(path=str(persist_dir))
        else:
            self.client = chromadb.Client()

        self.collection_name = "freight_context_notes"
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Context notes for freight transport disruptions, tolls, weather and surcharges"}
        )
        self.notes_df = pd.read_csv(notes_path)
        self._index_notes()

    def _index_notes(self):
        """Index all context notes into ChromaDB with rich metadata."""
        # Check if collection already has documents
        if self.collection.count() == len(self.notes_df):
            return

        ids = []
        documents = []
        metadatas = []

        for _, row in self.notes_df.iterrows():
            note_id = str(row['note_id']).strip()
            date_str = str(row['date']).strip()
            applies_to = str(row['applies_to']).strip()
            note_text = str(row['note']).strip()

            doc_text = f"Note ID: {note_id}. Date: {date_str}. Corridor: {applies_to}. Description: {note_text}"

            ids.append(note_id)
            documents.append(doc_text)
            metadatas.append({
                "note_id": note_id,
                "date": date_str,
                "applies_to": applies_to,
                "note_text": note_text
            })

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    def search_relevant_notes(self, route: str, week_of_str: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve notes using semantic search and temporal/route awareness.
        """
        query_text = (
            f"Transporter cost increase, fuel price change, surcharge, toll hike, weather disruption, "
            f"or flooding for corridor {route} around date {week_of_str}."
        )

        results = self.collection.query(
            query_texts=[query_text],
            n_results=top_k
        )

        retrieved = []
        if results and results.get("metadatas") and len(results["metadatas"]) > 0:
            for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
                retrieved.append({
                    "note_id": meta["note_id"],
                    "date": meta["date"],
                    "applies_to": meta["applies_to"],
                    "note_text": meta["note_text"],
                    "distance": dist
                })

        return retrieved

    def get_all_notes(self) -> List[Dict[str, Any]]:
        """Return all indexed context notes."""
        records = []
        for _, row in self.notes_df.iterrows():
            records.append({
                "note_id": str(row['note_id']).strip(),
                "date": str(row['date']).strip(),
                "applies_to": str(row['applies_to']).strip(),
                "note_text": str(row['note']).strip()
            })
        return records

