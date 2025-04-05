# core/memory_manager.py
import logging
import os
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MemoryManager:
    """Manages the story's persistent memory using vector and relational storage"""
    
    def __init__(self, api_key=None, db_path="memory/db"):
        """Initialize memory manager with vector store and relational data"""
        self.api_key = api_key
        self.db_path = db_path
        
        # Ensure directory exists
        os.makedirs(self.db_path, exist_ok=True)
        
        # Text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        
        # Initialize vector store with OpenAI embeddings if API key provided
        if api_key:
            try:
                self.embeddings = OpenAIEmbeddings(openai_api_key=api_key)
                vector_store_path = os.path.join(self.db_path, "vector_store")
                os.makedirs(vector_store_path, exist_ok=True)  # Ensure directory exists
                self.vector_store = Chroma(
                    persist_directory=vector_store_path,
                    embedding_function=self.embeddings
                )
                logging.info(f"Vector store initialized at {vector_store_path}")
            except Exception as e:
                logging.error(f"Failed to initialize vector store: {str(e)}", exc_info=True)
                self.vector_store = None
        else:
            logging.warning("No API key provided. Vector store not initialized.")
            self.vector_store = None
            
        # Initialize character and plot tracking (simple in-memory dict for now)
        # In a production system, this would be a sqlite DB or similar
        self.characters = {}
        self.plot_points = {}
        self.plot_counter = 0  # For assigning unique IDs to plot points
        
        # Load existing data if available
        self._load_persistent_data()
            
    def _load_persistent_data(self):
        """Load character and plot data from disk if available"""
        char_path = os.path.join(self.db_path, "characters.json")
        plot_path = os.path.join(self.db_path, "plots.json")
        counter_path = os.path.join(self.db_path, "counter.json")
        
        try:
            if os.path.exists(char_path):
                with open(char_path, 'r') as f:
                    self.characters = json.load(f)
                logging.info(f"Loaded {len(self.characters)} characters from persistent storage.")
                
            if os.path.exists(plot_path):
                with open(plot_path, 'r') as f:
                    self.plot_points = json.load(f)
                logging.info(f"Loaded {len(self.plot_points)} plot points from persistent storage.")
                
            if os.path.exists(counter_path):
                with open(counter_path, 'r') as f:
                    counter_data = json.load(f)
                    self.plot_counter = counter_data.get("plot_counter", 0)
                logging.info(f"Loaded counter state. Plot counter: {self.plot_counter}")
        except Exception as e:
            logging.error(f"Error loading persistent data: {e}")
            
    def _save_persistent_data(self):
        """Save character and plot data to disk"""
        char_path = os.path.join(self.db_path, "characters.json")
        plot_path = os.path.join(self.db_path, "plots.json")
        counter_path = os.path.join(self.db_path, "counter.json")
        
        try:
            with open(char_path, 'w') as f:
                json.dump(self.characters, f, indent=2)
                
            with open(plot_path, 'w') as f:
                json.dump(self.plot_points, f, indent=2)
                
            with open(counter_path, 'w') as f:
                json.dump({"plot_counter": self.plot_counter}, f, indent=2)
                
            logging.info("Saved persistent memory data to disk.")
        except Exception as e:
            logging.error(f"Error saving persistent data: {e}")
            
    def add_document_chunks(self, text, metadata=None):
        """Add text chunks to vector store with metadata"""
        if not self.vector_store:
            logging.warning("Vector store not initialized. Cannot add document.")
            return False
            
        try:
            # Check if text is already split into chunks
            if isinstance(text, list):
                chunks = text
            else:
                chunks = [text]  # Single chunk, treat as list
                
            # Add to vector store
            self.vector_store.add_texts(
                texts=chunks,
                metadatas=[metadata] * len(chunks) if metadata else None
            )
            self.vector_store.persist()  # Save changes
            return True
        except Exception as e:
            logging.error(f"Error adding document to vector store: {e}")
            return False
            
    def search_similar(self, query, limit=5):
        """Search for similar content in the vector store"""
        if not self.vector_store:
            logging.warning("Vector store not initialized. Cannot search.")
            return []
            
        try:
            results = self.vector_store.similarity_search(query, k=limit)
            return results
        except Exception as e:
            logging.error(f"Error searching vector store: {e}")
            return []
            
    def update_character_state(self, character_name, state_change, episode_number):
        """Update a character's state with a new change"""
        if character_name not in self.characters:
            self.characters[character_name] = {
                "name": character_name,
                "first_appearance": episode_number,
                "state_history": []
            }
            
        # Add new state to history
        self.characters[character_name]["state_history"].append({
            "episode": episode_number,
            "change": state_change
        })
        
        # Save changes
        self._save_persistent_data()
        logging.info(f"Updated character '{character_name}' with new state in episode {episode_number}")
            
    def add_plot_point(self, summary, status="introduced", episode_added=None):
        """Add a new plot point/thread to track"""
        self.plot_counter += 1
        plot_id = self.plot_counter
        
        self.plot_points[str(plot_id)] = {
            "id": plot_id,
            "summary": summary,
            "status": status,
            "episode_added": episode_added,
            "status_history": [
                {"episode": episode_added, "status": status}
            ]
        }
        
        # Save changes
        self._save_persistent_data()
        logging.info(f"Added new plot point (ID: {plot_id}) in episode {episode_added}")
        return plot_id
            
    def update_plot_status(self, plot_id, new_status, episode_number):
        """Update a plot point's status"""
        plot_id_str = str(plot_id)  # Convert to string for dict key
        
        if plot_id_str not in self.plot_points:
            logging.warning(f"Plot point ID {plot_id} not found. Cannot update status.")
            return False
            
        # Add new status to history
        self.plot_points[plot_id_str]["status"] = new_status
        self.plot_points[plot_id_str]["status_history"].append({
            "episode": episode_number,
            "status": new_status
        })
        
        # Save changes
        self._save_persistent_data()
        logging.info(f"Updated plot point (ID: {plot_id}) status to '{new_status}' in episode {episode_number}")
        return True
            
    def get_character_summaries(self):
        """Get summary information for all characters"""
        summaries = []
        
        for char_name, char_data in self.characters.items():
            # Get most recent state changes (up to last 3)
            recent_changes = char_data.get("state_history", [])[-3:]
            changes_text = "; ".join([f"Episode {change['episode']}: {change['change']}" 
                                    for change in recent_changes])
            
            summary = f"{char_name}: First appeared in Episode {char_data.get('first_appearance')}. "
            if changes_text:
                summary += f"Recent state: {changes_text}"
            
            summaries.append(summary)
            
        return "\n".join(summaries) if summaries else "No character information available."
            
    def get_active_plot_points(self):
        """Get all active/in-progress plot points"""
        active_plots = {}
        
        for plot_id, plot_data in self.plot_points.items():
            # Include plots that aren't resolved/completed
            if plot_data.get("status") not in ["resolved", "completed", "abandoned"]:
                active_plots[plot_id] = plot_data
                
        return active_plots
            
    def get_context_summary(self, episode_number):
        """Generate a summary of context relevant to a specific episode"""
        # Summarize characters that have appeared before this episode
        character_summary = []
        for char_name, char_data in self.characters.items():
            if char_data.get("first_appearance", float("inf")) < episode_number:
                # Get state changes before this episode
                relevant_history = [change for change in char_data.get("state_history", [])
                                  if change.get("episode", float("inf")) < episode_number]
                
                if relevant_history:
                    last_states = relevant_history[-2:]  # Last 2 states before this episode
                    states_text = "; ".join([f"Episode {change['episode']}: {change['change']}" 
                                          for change in last_states])
                    
                    summary = f"{char_name}: {states_text}"
                    character_summary.append(summary)
        
        # Summarize active plot points as of the start of this episode
        plot_summary = []
        for plot_id, plot_data in self.plot_points.items():
            if plot_data.get("episode_added", float("inf")) < episode_number:
                # Get status history before this episode
                relevant_status = [status for status in plot_data.get("status_history", [])
                                 if status.get("episode", float("inf")) < episode_number]
                
                if relevant_status:
                    latest_status = relevant_status[-1]
                    summary = f"Plot: {plot_data.get('summary')} - Status as of Episode {latest_status['episode']}: {latest_status['status']}"
                    plot_summary.append(summary)
        
        # Combine summaries
        full_summary = "CHARACTER CONTEXT:\n" + "\n".join(character_summary) if character_summary else "No prior character information."
        full_summary += "\n\nPLOT CONTEXT:\n" + "\n".join(plot_summary) if plot_summary else "\n\nNo prior plot points."
        
        return full_summary
            
    def get_relevant_chunks(self, query, limit=5):
        """Get relevant text chunks based on a query"""
        if not self.vector_store:
            logging.warning("Vector store not initialized. Cannot retrieve relevant chunks.")
            return "No vector store available for retrieving relevant content."
            
        try:
            results = self.vector_store.similarity_search(query, k=limit)
            chunks_text = []
            
            for i, doc in enumerate(results):
                # Add metadata about source
                source_info = f"[From Episode {doc.metadata.get('episode', 'unknown')}"
                if 'chunk_index' in doc.metadata:
                    source_info += f", Chunk {doc.metadata['chunk_index']}"
                source_info += "]"
                
                # Format chunk with source info
                chunks_text.append(f"Relevant Context {i+1} {source_info}:\n{doc.page_content}\n")
                
            return "\n".join(chunks_text)
        except Exception as e:
            logging.error(f"Error retrieving relevant chunks: {e}")
            return "Error retrieving relevant context."
            
    def close(self):
        """Close any open connections and save data"""
        if hasattr(self, 'vector_store') and self.vector_store:
            try:
                self.vector_store.persist()
                logging.info("Vector store persisted successfully.")
            except Exception as e:
                logging.error(f"Error persisting vector store: {e}")
                
        # Save character and plot data
        self._save_persistent_data()
        logging.info("Memory manager closed and data saved.")
        
    def add_chunks_to_vector_store(self, chunks, episode_number):
        """Add text chunks to vector store with proper reinitialization if needed"""
        try:
            # Force re-initialization of vector store if needed
            if not hasattr(self, 'vector_store') or self.vector_store is None:
                logging.info("Attempting to reinitialize vector store")
                self.embeddings = OpenAIEmbeddings(openai_api_key=self.api_key)
                vector_store_path = os.path.join(self.db_path, "vector_store")
                
                # Create a fresh directory
                if os.path.exists(vector_store_path):
                    import shutil
                    shutil.rmtree(vector_store_path)
                
                os.makedirs(vector_store_path, exist_ok=True)
                
                # Create new Chroma instance with explicit client settings
                from chromadb.config import Settings
                import chromadb
                
                client = chromadb.PersistentClient(
                    path=vector_store_path,
                    settings=Settings(anonymized_telemetry=False)
                )
                
                self.vector_store = Chroma(
                    persist_directory=vector_store_path,
                    embedding_function=self.embeddings,
                    client=client
                )
                
            # Add chunks to vector store (process valid chunks only)
            if chunks and len(chunks) > 0:
                # Filter out empty chunks
                valid_chunks = [c for c in chunks if c and len(c.strip()) > 0]
                
                if valid_chunks:
                    # Add metadata to each chunk
                    metadatas = []
                    for i, _ in enumerate(valid_chunks):
                        metadatas.append({"episode": episode_number, "chunk_index": i, "type": "script_chunk"})
                        
                    # Add to vector store - with newer versions of Chroma, persistence is automatic 
                    # when using PersistentClient
                    self.vector_store.add_texts(texts=valid_chunks, metadatas=metadatas)
                    # No need to call persist() - it doesn't exist in your version
                    logging.info(f"Added {len(valid_chunks)} chunks to vector store")
                    return True
                    
            return False
                
        except Exception as e:
            logging.error(f"Error in add_chunks_to_vector_store: {str(e)}", exc_info=True)
            return False