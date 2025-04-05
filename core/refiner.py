# core/refiner.py
from openai import OpenAI
import json
import logging
from utils.config import REFINER_MODEL, UPDATER_MODEL, load_api_key
from core.memory_manager import MemoryManager # Type hinting

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Refiner:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        self.refiner_model = REFINER_MODEL
        self.updater_model = UPDATER_MODEL # Use potentially cheaper model for extraction

    def critique_episode(self, script_text, episode_number, episode_summary, memory_manager: MemoryManager):
        """Reviews the generated script using an LLM as a critic."""
        logging.info(f"--- Reviewing Script for Episode {episode_number} ---")

        # Retrieve relevant context for the critic
        context_summary = memory_manager.get_context_summary(episode_number) # Get state *before* this ep
        # Maybe retrieve specific plot points mentioned

        prompt = f"""
        You are a script editor reviewing the following draft script for Episode {episode_number}.

        Episode Goal/Summary: {episode_summary}

        Established Context (Characters, Active Plots before this episode):
        {context_summary}

        Script Draft:
        --- START SCRIPT ---
        {script_text}
        --- END SCRIPT ---

        Please evaluate the script based on these criteria:
        1. **Continuity**: Does the script contradict established facts from the context (character knowledge, location, plot statuses)? Point out specific inconsistencies if any.
        2. **Consistency**: Are character actions and dialogue consistent with their established personalities and motivations (as described in the context)?
        3. **Plot Advancement**: Does the script meaningfully advance the plot towards the stated Episode Goal?
        4. **Pacing/Engagement**: (Optional) Briefly comment on the pacing or if the script feels engaging.

        Provide concise feedback. Start with an overall assessment (e.g., "Looks good", "Minor issues found", "Major inconsistencies"). Then list specific points if necessary.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.refiner_model,
                messages=[
                    {"role": "system", "content": "You are a meticulous script editor focused on continuity and consistency."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3, # Low temp for analytical tasks
                max_tokens=500
            )
            critique = response.choices[0].message.content
            logging.info(f"--- Critique for Episode {episode_number} ---\n{critique}\n-----------------")
            # In a more advanced system, you could parse this critique and trigger revisions
            # For now, we just return the critique alongside the original script.
            return script_text, critique # Return original script + critique

        except Exception as e:
            logging.error(f"Error calling OpenAI for script review (Episode {episode_number}):{e}", exc_info=True)
            return script_text, "Error generating critique." # Return original script + error message

    def update_memory_from_script(self, script_text, episode_number, memory_manager: MemoryManager):
        """Parses script, extracts info using LLM (JSON), and updates memory."""
        logging.info(f"--- Updating Memory from Episode {episode_number} Script ---")

        # 1. Chunk the script for analysis and RAG storage
        script_chunks = memory_manager.text_splitter.split_text(script_text)
        logging.info(f"Split script into {len(script_chunks)} chunks for analysis and storage.")

        # 2. Extract Structured Information using LLM (JSON mode)
        # Process the first chunk or a summary instead of the whole script
        # This prevents token limit issues
        
        # Create a summary or use first part of script
        script_for_analysis = script_chunks[0] if script_chunks else script_text[:4000]
        
        extraction_prompt = f"""
        Analyze the first part of the script for Episode {episode_number}. Extract key information updates as a valid JSON object.
        
        Script Text (First Segment):
        --- START SCRIPT ---
        {script_for_analysis}
        --- END SCRIPT ---
        
        Identify the following and structure them in JSON:
        -"character_updates": (Array of Objects) List characters whose state changed significantly. Include:
            - "name": (String) Character name
            - "state_change": (String) Description of the new state
        -"plot_updates": (Array of Objects) List existing plot points (by summary or ID if known) whose status changed.
        - "new_plot_points": (Array of Strings) List summaries of any *new* major plot threads or quests introduced
        - "key_event_summary": (String) A brief (1-2 sentence) summary of what appears to be happening in this episode.
        
        If no updates are found for a category, provide an empty array [].
        Output *only* the valid JSON object.
        """
        
        extracted_info = None
        try:
            response = self.client.chat.completions.create(
                model=self.updater_model, # Use potentially cheaper model
                messages=[
                    {"role": "system", "content": "You are an AI assistant extracting structured data from scripts. Output *only* valid JSON."},
                    {"role": "user", "content": extraction_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1, # Low temp for extraction
                max_tokens=1500  # Adjust based on script length
            )
            info_json_str = response.choices[0].message.content
            extracted_info = json.loads(info_json_str)
            logging.info(f"Successfully extracted information JSON from script Ep {episode_number}.")
            # logging.debug(f"Extracted Info: {json.dumps(extracted_info, indent=2)}")

        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON response during memory update extraction: {e}")
            logging.error(f"Received text: {info_json_str}")
            # Continue without structured updates, but log error
        except Exception as e:
            logging.error(f"Error calling OpenAI for memory update extraction (Episode {episode_number}): {e}", exc_info=True)
            # Continue without structured updates

        # 3. Update Databases based on extracted info
        if extracted_info:
            # Update characters
            for update in extracted_info.get("character_updates", []):
                memory_manager.update_character_state(update.get("name"), update.get("state_change"), episode_number)

            # Update existing plot points
            for update in extracted_info.get("plot_updates", []):
                plot_id = update.get("plot_summary_or_id")
                new_status = update.get("new_status")
                if isinstance(plot_id, int): # If LLM correctly identified an ID
                    memory_manager.update_plot_status(plot_id, new_status, episode_number)
                elif isinstance(plot_id, str):
                    # TODO: Need a way to map summary back to ID reliably
                    logging.warning(f"Plot update provided summary '{plot_id}' instead of ID. Mapping not implemented. Status not updated.")
                    pass # Add logic here if needed

            # Add new plot points
            for summary in extracted_info.get("new_plot_points", []):
                memory_manager.add_plot_point(summary, episode_added=episode_number)

        # 4. Add Script Chunks to Vector Store for RAG
        base_metadata = {"episode": episode_number, "type": "script_chunk"}
        if extracted_info and extracted_info.get("key_event_summary"):
            # Add summary to metadata of all chunks, or just first/last
            base_metadata["ep_key_event_summary"] = extracted_info["key_event_summary"]

        # Use the specialized method that handles reinit
        memory_manager.add_chunks_to_vector_store(script_chunks, episode_number)

        logging.info(f"Memory update process for Episode {episode_number} complete.")