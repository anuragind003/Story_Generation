import logging
from core.planner import StoryPlanner
from core.generator import EpisodicGenerator
from core.memory_manager import MemoryManager
from core.refiner import Refiner
from utils.config import load_api_key

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class StoryPipeline:
    """Main pipeline class that orchestrates the story generation process."""
    
    def __init__(self):
        """Initialize the pipeline components with API key."""
        self.api_key = load_api_key()
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Check .env file or environment variables.")
        
        # Initialize components
        self.planner = StoryPlanner(self.api_key)
        self.generator = EpisodicGenerator(self.api_key)
        self.refiner = Refiner(self.api_key)
        self.memory = MemoryManager(api_key=self.api_key)  # Pass the API key here
        
        # Store state
        self.story_plan = None
        self.generated_episodes = {}  # { episode_num: {"script": "", "critique": ""} }
        
        logging.info("Story Pipeline initialized successfully.")
    
    def plan_story(self, user_input):
        """Plan a story based on user input and store in memory."""
        if not user_input:
            logging.error("No user input provided for planning.")
            return False
            
        self.story_plan = self.planner.generate_initial_plan(user_input)
        if not self.story_plan:
            logging.error("Failed to generate story plan.")
            return False
            
        # Store plan in memory
        if not self.planner.store_plan(self.story_plan, self.memory):
            logging.error("Failed to store story plan in memory.")
            return False
            
        logging.info("Story plan generated and stored successfully.")
        return True
    
    def generate_episode(self, episode_number):
        """Generate a specific episode's script and critique."""
        if not self.story_plan:
            logging.error("No story plan exists. Call plan_story() first.")
            return None, "No story plan exists."
            
        # Check if episode exists in plan
        episode_in_plan = False
        episode_summary = ""
        for ep in self.story_plan.get("master_outline", []):
            if ep.get("episode") == episode_number:
                episode_in_plan = True
                episode_summary = ep.get("summary", "")
                break
                
        if not episode_in_plan:
            logging.error(f"Episode {episode_number} not found in story plan.")
            return None, f"Episode {episode_number} not found in story plan."
        
        # Get context from memory
        context_summary = self.memory.get_context_summary(episode_number)
        character_info = self.memory.get_character_summaries()
        relevant_chunks = self.memory.get_relevant_chunks(episode_summary, 5)
        
        # Generate script
        script = self.generator.generate_episode_script(
            episode_number, 
            episode_summary, 
            context_summary, 
            character_info, 
            relevant_chunks
        )
        
        if not script or "Error generating script" in script:
            logging.error(f"Failed to generate script for Episode {episode_number}.")
            return script, "Generation failed, no critique available."
        
        # Generate critique - FIX: Pass the memory manager as the fourth argument
        critique = self.refiner.critique_episode(script, episode_number, episode_summary, self.memory)
        
        # Update memory with new content
        self.refiner.update_memory_from_script(script, episode_number, self.memory)
        
        # Store results
        self.generated_episodes[episode_number] = {
            "script": script,
            "critique": critique
        }
        
        logging.info(f"Episode {episode_number} generated and stored.")
        return script, critique
    
    def get_episode_data(self, episode_number):
        """Retrieve data for a specific episode."""
        return self.generated_episodes.get(episode_number, None)
    
    def close_memory(self):
        """Close memory connections."""
        if hasattr(self, 'memory') and self.memory:
            self.memory.close()
            logging.info("Memory connections closed.")