# AI Debate System

An evidence-informed, multi-agent debate application. Enter a topic, choose a debate length, and let AI agents argue both sides before a judge evaluates their reasoning.

The Streamlit interface displays the debate transcript, source material, score breakdown, and final decision. Reports can be downloaded as JSON or CSV. A command-line interface is also available.

## Features

- Pro and Against agents produce opening arguments and rebuttals across 1 to 10 rounds.
- Topic evidence is retrieved from Wikipedia and shown with links to the source articles.
- A Judge agent evaluates both sides on logic, clarity, and examples, then provides a winner and rationale.
- Choose an Ollama, OpenAI, or mock model backend in the Streamlit sidebar.
- Export debate results, evidence, scores, and transcript as JSON or CSV.
- Run debates from either the Streamlit UI or the command line.

## Requirements

- Python 3.11 or newer
- Internet access to retrieve evidence from the Wikipedia API
- For the Ollama backend: [Ollama](https://ollama.com/download) installed and running, plus a supported model pulled locally
- For the OpenAI backend: an OpenAI API key and the optional `openai` Python package

## Setup

From the project directory, create and activate a virtual environment, then install the dependencies:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On macOS or Linux, activate the environment with:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Ollama (default backend)

Install Ollama, start its local service, then pull a model. The default is `phi3:mini`:

```bash
ollama pull phi3:mini
```

To use another model, set `OLLAMA_MODEL` before starting the application. The UI offers a list of model choices for the Ollama backend.

### OpenAI (optional)

Install the optional package and provide an API key through an environment variable:

```powershell
python -m pip install openai
$env:OPENAI_API_KEY = "your-api-key"
```

On macOS or Linux:

```bash
python -m pip install openai
export OPENAI_API_KEY="your-api-key"
```

Select the OpenAI backend in the Streamlit sidebar. Never commit a real API key; `.env` files are excluded by `.gitignore`.

### Mock backend

Choose `mock` in the UI to run with deterministic local sample responses without configuring an LLM provider. Evidence retrieval still requires internet access.

## Run the application

Start the Streamlit interface:

```bash
streamlit run ui/app.py
```

## Deploy on Streamlit Community Cloud

1. Push this project to a GitHub repository. Keep `.streamlit/secrets.toml` and API keys out of the repository.
2. Open [Streamlit Community Cloud](https://share.streamlit.io/deploy), choose **Create app**, and select the repository and branch.
3. Set the app file path to `ui/app.py`, then deploy.

The app uses the mock backend when no provider is configured, so the deployed UI can run without an API key. To enable OpenAI, add these values under the app's **Settings → Secrets** before or after deployment:

```toml
LLM_BACKEND = "openai"
OPENAI_API_KEY = "your-api-key"
OPENAI_MODEL = "gpt-4o-mini"
```

The OpenAI package is included in `requirements.txt`. Ollama requires a separate reachable Ollama service, so the local Ollama backend is not available from Community Cloud by default.

Or start the command-line application:

```bash
python main.py
```

The CLI prompts for a debate topic and a round count between 1 and 10. In the UI, enter a topic, select the round count and model backend, then choose **Launch Debate**.

## Configuration

Configuration can be supplied through environment variables:

| Variable | Purpose | Default |
| --- | --- | --- |
| `OLLAMA_MODEL` | Default Ollama model | `phi3:mini` |
| `LLM_BACKEND` | Initial backend (`ollama`, `openai`, or `mock`) | `ollama` |
| `LLM_MODEL` | Initial model selection | Value of `OLLAMA_MODEL` |
| `DEBATE_DEFAULT_ROUNDS` | Config value; the UI currently starts at two rounds and the CLI prompts for a value | `2` |
| `OPENAI_API_KEY` | OpenAI authentication key | Not set |
| `OPENAI_MODEL` | Default OpenAI model when selected | `gpt-4o-mini` |

The Streamlit UI starts with two rounds and lets you select a supported backend and model in the sidebar.

## Tests

Run the test suite with:

```bash
python -m unittest discover -s tests -v
```

## Project structure

```text
agents/                 Pro, Against, and Judge agents
core/                   Debate orchestration, configuration, memory, and reports
tests/                  Unit and enterprise feature tests
ui/app.py               Streamlit application
utils/evidence/         Wikipedia evidence retrieval
utils/llm_model/        Model provider integration and response handling
utils/prompts/          Agent and judge prompts
utils/json_formatter/   Structured response formatting
main.py                 Command-line entry point
requirements.txt        Required Python packages
```

## Notes

- Debate output is generated by language models and should be treated as assistance, not authoritative advice.
- Wikipedia excerpts provide context for a debate; review the linked articles and other sources when accuracy matters.
- The OpenAI package is optional and is not included in `requirements.txt`.
