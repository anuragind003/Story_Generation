# core/planner.py
from openai import OpenAI
import logging
import json
from utils.config import PLANNER_MODEL, load_api_key

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class StoryPlanner:
    """Creates story outlines and episode plans based on user input"""
    
    def __init__(self, api_key):
        """Initialize with API key for language model access"""
        self.client = OpenAI(api_key=api_key)
        self.model = PLANNER_MODEL  # Using the more capable model for planning
        
    def generate_initial_plan(self, user_input):
        """Generate a complete story plan from user input"""
        logging.info("Generating initial story plan from user input")
        
        num_episodes = 5  # Default episode count for testing
        prompt = f"""
        You are a skilled story planner that organizes stories into episodic formats.
        
        Create a structured story arc for a {num_episodes}-episode story based on this input:
        "{user_input}"
        
        Format your response as JSON with these components:
        1. "title": A compelling title for the story 
        2. "premise": A 2-3 sentence summary of the core concept
        3. "setting": Brief description of where/when the story takes place
        4. "characters": Array of main characters, each with:
           - "name": Character name
           - "description": Brief character description
           - "motivation": What drives this character
        5. "master_outline": Array with exactly {num_episodes} episodes, each containing:
           - "episode": Episode number (1 to {num_episodes})
           - "title": Episode title
           - "summary": 1-2 paragraph summary of this episode's content
           - "key_points": Array of 2-3 key plot points or events in this episode
        
        Create a story that's engaging, has clear character arcs, and resolves by the final episode.
        The story should work well in audio format.
        
        IMPORTANT: Return ONLY the valid JSON object.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a story planning assistant that creates well-structured outlines. Return ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                # Adding json format explicitly
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            # Get the content of the response
            plan_json = response.choices[0].message.content
            
            # Debug logging - see what we received
            logging.info(f"Received response from OpenAI. Content length: {len(plan_json)}")
            if len(plan_json) < 100:  # If it's suspiciously short, log the entire content
                logging.info(f"Response content: {plan_json}")
            
            # Ensure we have content before trying to parse
            if not plan_json or len(plan_json.strip()) == 0:
                logging.error("Received empty response from OpenAI")
                return None
                
            # Parse the JSON
            try:
                plan = json.loads(plan_json)
                logging.info(f"Generated story plan: '{plan.get('title', 'Untitled')}' with {len(plan.get('master_outline', []))} episodes")
                return plan
            except json.JSONDecodeError as je:
                # More detailed JSON error logging
                logging.error(f"JSON decode error: {je}")
                logging.error(f"First 200 chars of content: {plan_json[:200]}")
                return None
            
        except Exception as e:
            logging.error(f"Error generating story plan: {e}")
            return None
            
    def refine_episode_plan(self, episode_number, episode_plan, context_from_memory):
        """Refine a specific episode plan based on context from previous episodes"""
        logging.info(f"Refining plan for Episode {episode_number} with up-to-date context")
        
        prompt = f"""
        You are a story editor refining an episode plan using the latest story context.
        
        EPISODE TO REFINE: Episode {episode_number}
        
        ORIGINAL EPISODE PLAN:
        Title: {episode_plan.get('title')}
        Summary: {episode_plan.get('summary')}
        Key Points: {', '.join(episode_plan.get('key_points', []))}
        
        CURRENT STORY CONTEXT (from previous episodes):
        {context_from_memory}
        
        Based on this context, enhance the episode plan to maintain continuity and strengthen the narrative.
        Return a JSON object with these fields:
        - "title": Episode title (may be updated)
        - "summary": Updated episode summary (1-2 paragraphs)
        - "key_points": Array of 3-5 key events that should happen in this episode
        - "characters": Array of character names who should appear in this episode
        - "continuity_notes": Important connections to previous episodes
        
        IMPORTANT: Return ONLY the valid JSON object.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a story editor specializing in narrative coherence and continuity."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.5
            )
            
            refined_json = response.choices[0].message.content
            refined_plan = json.loads(refined_json)
            
            logging.info(f"Successfully refined plan for Episode {episode_number}")
            return refined_plan
            
        except Exception as e:
            logging.error(f"Error refining episode plan: {e}")
            return None
            
    def store_plan(self, story_plan, memory_manager):
        """Store the story plan in the memory manager"""
        logging.info("Storing story plan in memory")
        
        if not story_plan:
            logging.error("No story plan to store")
            return False
            
        try:
            # Store characters
            for character in story_plan.get('characters', []):
                memory_manager.update_character_state(
                    character.get('name', 'Unknown'),
                    f"Description: {character.get('description', '')}. Motivation: {character.get('motivation', '')}",
                    0  # Episode 0 means "initial planning"
                )
            
            # Store initial plot points from episode outlines
            for episode in story_plan.get('master_outline', []):
                # Store episode objective as a plot point
                plot_summary = f"Episode {episode.get('episode')} objective: {episode.get('summary')}"
                memory_manager.add_plot_point(
                    plot_summary,
                    status="planned",
                    episode_added=0  # Episode 0 means "initial planning"
                )
                
                # Store key points as individual plot points
                for point in episode.get('key_points', []):
                    plot_summary = f"Episode {episode.get('episode')} key point: {point}"
                    memory_manager.add_plot_point(
                        plot_summary,
                        status="planned",
                        episode_added=0  # Episode 0 means "initial planning"
                    )
            
            # Store the story premise and setting as a document
            overview_text = f"""
            STORY TITLE: {story_plan.get('title', 'Untitled')}
            
            PREMISE: {story_plan.get('premise', 'No premise specified')}
            
            SETTING: {story_plan.get('setting', 'No setting specified')}
            """
            
            memory_manager.add_document_chunks(
                overview_text,
                metadata={"type": "story_overview", "episode": 0}
            )
            
            logging.info("Story plan successfully stored in memory")
            return True
            
        except Exception as e:
            logging.error(f"Error storing story plan in memory: {e}")
            return False