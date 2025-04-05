# ui/app.py
# coding: utf-8
import streamlit as st
import sys
import os

# Add the parent directory to Python's path so we can import 'core'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Now we can import from core
from core.pipeline import StoryPipeline
import logging # Import logging

# Configure logging for Streamlit (optional, helps debug)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Custom styling
st.set_page_config(
    page_title="AI Story Pipeline",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        margin-bottom: 0.5rem;
    }
    .subheader {
        font-size: 1.2rem;
        color: #424242;
        margin-bottom: 2rem;
    }
    .story-title {
        font-size: 1.8rem;
        color: #1E88E5;
        margin-bottom: 0.5rem;
    }
    .episode-title {
        font-size: 1.5rem;
        color: #1E88E5;
        margin-top: 1rem;
    }
    .story-prompt {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        width: 100%;
        display: inline-block;
    }
    .navigation-btn {
        font-weight: bold;
    }
    .info-box {
        background-color: #e8f4f8;
        border-radius: 5px;
        padding: 15px;
        margin-bottom: 15px;
        width: 100%;
        display: inline-block;
    }
    /* Remove script-box class as we're using st.code() instead */
    
    /* Fix any container width issues */
    .stMarkdown {
        width: 100%;
    }
    .stButton {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# App title and intro with better styling
st.markdown('<h1 class="main-header">AI Story Pipeline</h1>', unsafe_allow_html=True)
st.markdown('<p class="subheader">Generate episodic stories powered by AI. Create a new story with a prompt, then generate episodes one by one.</p>', unsafe_allow_html=True)

# Initialize session state variables if they don't exist
if 'pipeline' not in st.session_state:
    st.session_state.pipeline = None
if 'story_plan' not in st.session_state:
    st.session_state.story_plan = None
if 'current_episode' not in st.session_state:
    st.session_state.current_episode = 1
if 'episodes_generated' not in st.session_state:
    st.session_state.episodes_generated = {}

# Function to initialize the pipeline
def initialize_pipeline():
    try:
        st.session_state.pipeline = StoryPipeline()
        return True
    except Exception as e:
        st.error(f"Failed to initialize pipeline: {str(e)}")
        return False

# Function to plan a new story
def plan_story(user_input):
    if st.session_state.pipeline is None:
        if not initialize_pipeline():
            return False
    
    with st.spinner("Planning your story..."):
        success = st.session_state.pipeline.plan_story(user_input)
        if success:
            st.session_state.story_plan = st.session_state.pipeline.story_plan
            st.session_state.current_episode = 1
            st.session_state.episodes_generated = {}
            return True
        else:
            st.error("Failed to generate story plan")
            return False

# Function to generate an episode
def generate_episode(episode_number):
    if st.session_state.pipeline is None or st.session_state.story_plan is None:
        st.error("Please plan a story first")
        return
    
    with st.spinner(f"Generating Episode {episode_number}..."):
        script, critique = st.session_state.pipeline.generate_episode(episode_number)
        if script:
            st.session_state.episodes_generated[episode_number] = {
                "script": script,
                "critique": critique
            }
            return True
        else:
            st.error(f"Failed to generate Episode {episode_number}")
            return False

# Create a sidebar for story planning
with st.sidebar:
    st.header("Story Creation")
    
    # Add genre selection for better prompting
    genre = st.selectbox(
        "Select Genre",
        ["Science Fiction", "Fantasy", "Mystery", "Romance", "Adventure", "Horror", "Other"]
    )
    
    # More visually appealing prompt area
    st.markdown('<div class="story-prompt">', unsafe_allow_html=True)
    user_input = st.text_area(
        "Enter your story premise:",
        "A team of explorers discovers an ancient alien artifact on a distant moon.",
        height=100
    )
    
    # Add some example prompt elements
    if st.checkbox("Add prompt elements", value=False):
        setting = st.text_input("Setting:", "")
        protagonist = st.text_input("Main Character:", "")
        conflict = st.text_input("Central Conflict:", "")
        
        # Combine elements if provided
        if setting or protagonist or conflict:
            combined_elements = []
            if genre != "Other": combined_elements.append(f"A {genre.lower()} story about")
            if protagonist: combined_elements.append(f"a character named {protagonist}")
            if setting: combined_elements.append(f"in {setting}")
            if conflict: combined_elements.append(f"who {conflict}")
            if combined_elements:
                enhanced_prompt = " ".join(combined_elements)
                st.session_state.enhanced_prompt = enhanced_prompt
                st.info(f"Enhanced prompt: {enhanced_prompt}")
                if st.button("Use Enhanced Prompt"):
                    user_input = enhanced_prompt
    st.markdown('</div>', unsafe_allow_html=True)
    
    # More attention-grabbing button
    if st.button("🚀 Create New Story", use_container_width=True):
        plan_story(user_input)
    
    # Display story info with better styling if available
    if st.session_state.story_plan:
        st.markdown(f'<h2 class="story-title">{st.session_state.story_plan.get("title", "Untitled Story")}</h2>', unsafe_allow_html=True)
        
        # Show premise in a nice box
        st.markdown('<div class="info-box">', unsafe_allow_html=True)
        st.markdown("**Premise:**")
        st.write(st.session_state.story_plan.get("premise", ""))
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Show setting similarly
        if "setting" in st.session_state.story_plan:
            st.markdown('<div class="info-box">', unsafe_allow_html=True)
            st.markdown("**Setting:**")
            st.write(st.session_state.story_plan.get("setting", ""))
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Episode selector with progress indicator
        st.subheader("Episodes")
        episodes = st.session_state.story_plan.get("master_outline", [])
        episode_titles = [f"Episode {ep.get('episode')}: {ep.get('title')}" for ep in episodes]
        
        # Add visual progress tracking
        total_episodes = len(episodes)
        generated_count = len(st.session_state.episodes_generated)
        st.progress(generated_count / total_episodes if total_episodes > 0 else 0)
        st.write(f"Generated: {generated_count}/{total_episodes} episodes")
        
        selected_episode = st.selectbox("Select an episode:", episode_titles, index=st.session_state.current_episode - 1)
        selected_index = episode_titles.index(selected_episode) + 1
        
        # Enhanced generation button
        button_text = "Generate Selected Episode"
        if selected_index in st.session_state.episodes_generated:
            button_text = "View Episode"
        
        if st.button(button_text, use_container_width=True):
            if selected_index in st.session_state.episodes_generated:
                st.success(f"Showing Episode {selected_index}")
            else:
                generate_episode(selected_index)
            
            st.session_state.current_episode = selected_index
            st.rerun()

# Main content area with improved UI
if st.session_state.story_plan:
    # Display the current episode details
    current_ep = st.session_state.current_episode
    episodes = st.session_state.story_plan.get("master_outline", [])
    
    # Find the episode details
    episode_details = None
    for ep in episodes:
        if ep.get("episode") == current_ep:
            episode_details = ep
            break
    
    if episode_details:
        # Create a better episode header with visual indicators
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f'<h2 class="episode-title">Episode {current_ep}: {episode_details.get("title", "Untitled")}</h2>', unsafe_allow_html=True)
        
        with col2:
            # Show status indicator
            if current_ep in st.session_state.episodes_generated:
                st.success("✓ Generated")
            else:
                st.info("⌛ Not Generated")
        
        # Show episode plan/outline in an expander with better formatting
        with st.expander("Episode Outline", expanded=True if current_ep not in st.session_state.episodes_generated else False):
            st.markdown("### Summary")
            st.write(episode_details.get("summary", "No summary available"))
            
            st.markdown("### Key Points")
            for point in episode_details.get("key_points", []):
                st.markdown(f"- {point}")
        
        # Show the generated episode content if available
        if current_ep in st.session_state.episodes_generated:
            episode_data = st.session_state.episodes_generated[current_ep]
            
            # Script content with better styling
            st.subheader("Generated Script")
            
            # Add tabs for different views
            tab1, tab2 = st.tabs(["Script", "AI Critique"])
            
            with tab1:
                # Don't use HTML for script display as it can cause formatting issues
                st.code(episode_data["script"], language=None)
                
                # Add download button for the script
                st.download_button(
                    label="Download Script",
                    data=episode_data["script"],
                    file_name=f"episode_{current_ep}_script.txt",
                    mime="text/plain"
                )
            
            with tab2:
                st.markdown('<div class="info-box">', unsafe_allow_html=True)
                st.write(episode_data["critique"])
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Navigation buttons with improved styling
            st.markdown("<br>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if current_ep > 1:
                    if st.button("← Previous Episode", use_container_width=True):
                        st.session_state.current_episode = current_ep - 1
                        st.rerun()
            
            with col2:
                # Regenerate button
                if st.button("🔄 Regenerate", use_container_width=True):
                    with st.spinner(f"Regenerating Episode {current_ep}..."):
                        generate_episode(current_ep)
                        st.rerun()
            
            with col3:
                if current_ep < len(episodes):
                    if st.button("Next Episode →", use_container_width=True):
                        # Automatically generate next episode if not already generated
                        if current_ep + 1 not in st.session_state.episodes_generated:
                            generate_episode(current_ep + 1)
                        
                        st.session_state.current_episode = current_ep + 1
                        st.rerun()
        else:
            # Show a button to generate this episode
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(f"✨ Generate Episode {current_ep}", use_container_width=True):
                generate_episode(current_ep)
                st.rerun()
else:
    # Show a more engaging welcome screen
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.info("👋 Welcome to AI Story Pipeline! Get started by creating your first story.")
    st.markdown("**How it works:**")
    st.markdown("1. Enter a story prompt in the sidebar")
    st.markdown("2. Click 'Create New Story' to generate a complete story plan")
    st.markdown("3. Generate episodes one by one to build your complete story")
    st.markdown("4. Download your episodes or view AI critiques")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Sample prompts as cards in columns
    st.subheader("Quick Start with Sample Prompts")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="info-box">', unsafe_allow_html=True)
        st.markdown("**Fantasy Adventure**")
        st.write("A young apprentice mage accidentally teleports their entire village to another realm.")
        if st.button("Use This Prompt", key="fantasy", use_container_width=True):
            prompt = "A fantasy adventure about a young apprentice mage who accidentally teleports their entire village to another realm."
            st.sidebar.text_area("Enter your story premise:", prompt)
            plan_story(prompt)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="info-box">', unsafe_allow_html=True)
        st.markdown("**Mystery**")
        st.write("A lighthouse keeper discovers an ancient secret hidden in their small coastal town's history.")
        if st.button("Use This Prompt", key="mystery", use_container_width=True):
            prompt = "A mystery story set in a small coastal town where the lighthouse keeper discovers an ancient secret hidden in the town's history."
            st.sidebar.text_area("Enter your story premise:", prompt)
            plan_story(prompt)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="info-box">', unsafe_allow_html=True)
        st.markdown("**Romance**")
        st.write("Two rival food truck owners compete for business but gradually fall in love.")
        if st.button("Use This Prompt", key="romance", use_container_width=True):
            prompt = "A romantic comedy about two rival food truck owners who compete for business but gradually fall in love."
            st.sidebar.text_area("Enter your story premise:", prompt)
            plan_story(prompt)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Showcase section
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Why Use AI Story Pipeline?")
    
    features_col1, features_col2 = st.columns(2)
    
    with features_col1:
        st.markdown("✨ **Complete Story Planning**")
        st.write("Generate coherent multi-episode stories with well-developed characters and plot arcs")
        
        st.markdown("📝 **Professional Scripts**")
        st.write("Create ready-to-produce episode scripts with proper formatting")
    
    with features_col2:
        st.markdown("🔄 **Continuous Context**")
        st.write("AI remembers characters, plot points, and events across episodes")
        
        st.markdown("👁️ **AI Critical Review**")
        st.write("Each episode comes with an AI critique for quality assurance")

# Better footer information
st.markdown("---")
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown("""
    **AI Story Pipeline** | Made with ❤️ using Streamlit and OpenAI
    
    Generate complete episodic stories for audio, screenplay, or text formats.
    """)

with col2:
    st.markdown("**Version:** 1.0")
    current_year = 2025  # You could use datetime.now().year for dynamic year
    st.markdown(f"© {current_year} KUKU_FM")