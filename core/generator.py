# core/generator.py
from openai import OpenAI
import logging
from utils.config import GENERATOR_MODEL, load_api_key
from core.memory_manager import MemoryManager # Import to use type hinting

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define max scenes per episode to prevent runaway generation
MAX_SCENES_PER_EPISODE = 10

class EpisodicGenerator:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        self.model = GENERATOR_MODEL
        
    def _generate_scene(self, episode_number, scene_number, episode_summary, character_info, context_summary, relevant_chunks, previous_scene_summary):
        """Generates a single scene."""
        logging.info(f"--- Generating Scene {scene_number} for Episode {episode_number} ---")

        prompt = f"""
        You are a screenwriter AI writing Scene {scene_number} of Episode {episode_number}.

        Overall Episode Goal / Summary: {episode_summary}

        Context from Past Episodes & World:
        {context_summary}

        Characters Potentially Involved (refer to their state/motivations):
        {character_info}

        Relevant Snippets from Past (use if helpful):
        {relevant_chunks}

        Summary of Previous Scene (Scene {scene_number-1}) in this Episode:
        {previous_scene_summary if scene_number > 1 else 'This is the first scene.'}

        Instructions for Scene {scene_number}:
        - Write ONLY Scene {scene_number} in standard screenplay format (SCENE HEADING, Action, CHARACTER, Dialogue).
        - The scene should logically follow the previous scene and work towards the overall Episode Goal.
        - Keep character actions and dialogue consistent with their established traits and the situation.
        - Focus on advancing the plot, revealing information, or developing characters relevant to this episode's goal.
        - Keep the scene concise (e.g., 100-400 words).
        - **Crucially**: Do NOT write subsequent scenes. Only output the content for Scene {scene_number}.
        - If you think the episode goal is met or it's a natural conclusion point, you can make this the final scene. Add a comment like "# EPISODE END" at the very end if so.

        Begin Scene {scene_number}:
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"You are writing Scene {scene_number} of Episode {episode_number}."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.75,  # Slightly higher temp for scene creativity
                max_tokens=700  # Limit tokens per scene
            )
            scene_script = response.choices[0].message.content.strip()
            logging.info(f"--- Scene {scene_number} Generated (approx. {len(scene_script.split())} words) ---")

            # Basic check if LLM indicated episode end
            episode_complete = scene_script.endswith("# EPISODE END")
            
            return scene_script, previous_scene_summary + "\n\n" + scene_script, episode_complete
            
        except Exception as e:
            logging.error(f"Error generating Scene {scene_number}: {e}")
            return f"Error generating Scene {scene_number}", "Error", True  # Signal episode end on error
    
    def generate_episode_script(self, episode_number, episode_summary, context_summary, character_info, relevant_chunks):
        """Generates a full episode by generating scenes sequentially."""
        logging.info(f"--- Beginning Episode {episode_number} Generation ---")
        logging.info(f"Episode Goal: {episode_summary}")
        
        full_episode_script = []
        scene_number = 1
        previous_scenes_summary = ""
        episode_complete = False
        
        while scene_number <= MAX_SCENES_PER_EPISODE and not episode_complete:
            scene_script, updated_summary, episode_complete = self._generate_scene(
                episode_number, 
                scene_number, 
                episode_summary,
                character_info,
                context_summary,
                relevant_chunks,
                previous_scenes_summary
            )
            
            if "Error generating Scene" in scene_script:
                full_episode_script.append(f"ERROR GENERATING SCENE {scene_number}: Generation stopped.")
                break
                
            full_episode_script.append(scene_script)
            previous_scenes_summary = updated_summary
            scene_number += 1
            
            # Check if we've hit our scene limit
            if scene_number > MAX_SCENES_PER_EPISODE and not episode_complete:
                full_episode_script.append("# SCENE LIMIT REACHED - EPISODE INCOMPLETE")
                logging.warning(f"Episode {episode_number} hit maximum scene limit ({MAX_SCENES_PER_EPISODE})")
        
        logging.info(f"--- Episode {episode_number} Generation Complete ({len(full_episode_script)} scenes) ---")
        return "\n\n".join(full_episode_script)