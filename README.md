# Story Generation

The **Story Generation** is a tool for generating episodic stories powered by AI. It allows users to create story plans, generate episodes, and manage characters and plot points with continuous context across episodes.

## Features

- **Story Planning**: Generate coherent multi-episode story outlines with well-developed characters and plot arcs.
- **Episode Generation**: Create professional-quality scripts for each episode.
- **Continuous Context**: AI remembers characters, plot points, and events across episodes.
- **AI Critique**: Each episode comes with an AI-generated critique for quality assurance.
- **Interactive UI**: User-friendly interface built with Streamlit for planning and generating stories.

## Project Structure

```
ai_story_pipeline/
├── core/
│   ├── generator.py         # Handles episodic script generation
│   ├── memory_manager.py    # Manages persistent memory for characters and plots
│   ├── pipeline.py          # Orchestrates the story generation process
│   ├── planner.py           # Creates story outlines and episode plans
│   ├── refiner.py           # Refines scripts and updates memory
│   └── __init__.py          # Marks the directory as a Python package
├── memory/
│   ├── db/
│   │   ├── characters.json  # Database of characters and their state history
│   │   ├── counter.json     # Counter for tracking unique IDs
│   │   ├── plots.json       # Database of plot points and their status
│   │   └── vector_store/    # Vector store for memory persistence
├── ui/
│   ├── app.py               # Streamlit-based user interface
│   └── __init__.py          # Marks the directory as a Python package
├── utils/
│   ├── config.py            # Configuration utilities
│   └── __init__.py          # Marks the directory as a Python package
├── requirements.txt         # Python dependencies
└── README.md                # Project documentation
```

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/anuragind003/Story_Generation.git
   cd ai_story_pipeline
   ```

2. Create a virtual environment and activate it:

   ```bash
   python -m venv venv
   venv\Scripts\activate  # On Windows
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Set up the `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key
   ```

## Usage

1. Run the Streamlit app:

   ```bash
   streamlit run ui/app.py
   ```

2. Open the app in your browser and start creating stories:
   - Enter a story premise in the sidebar.
   - Generate a story plan.
   - Generate episodes one by one.
   - View AI critiques and download scripts.

## Dependencies

- Python 3.8+
- [OpenAI](https://pypi.org/project/openai/) >= 1.5.0
- [Streamlit](https://streamlit.io/)
- [LangChain](https://www.langchain.com/)
- [ChromaDB](https://www.trychroma.com/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## License

This project is licensed under the MIT License.

## Acknowledgments
- Powered by OpenAI and Streamlit.
