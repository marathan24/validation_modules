# Improving LLM Reasoning with Naptha Validation Modules

Evaluating and selecting the highest quality reasoning paths.

## 📖 Overview

Validation Modules is used to evaluate the quality and correctness of LLM-generated reasoning paths. It implements a multi-stage validation process that verifies, scores, compares, and selects the best reasoning from multiple candidate solutions.

### Key Features

- **Multi-stage Validation**: Applies a rigorous evaluation process to verify reasoning correctness
- **Scoring System**: Rates the quality of reasoning paths on a 1-10 scale
- **Comparative Analysis**: Directly compares multiple solutions to identify strengths and weaknesses
- **Voting Mechanism**: Uses an ensemble approach to select the optimal solution
- **Answer Extraction**: Identifies and extracts the final answer from validated reasoning

## 🧩 How It Works

The Validation Modules system works through a multi-stage process:

1. **Verification Stage**: Each reasoning path is rigorously evaluated for logical soundness, relevance to the original problem, and factual accuracy.

2. **Scoring Stage**: Valid reasoning paths (or all paths if none pass verification) are scored on a scale of 1-10 based on quality, correctness, and completeness.

3. **Selection Stage**: The system uses both direct comparison and voting mechanisms to determine the optimal solution:
   - Comparison: The top-scoring solutions are directly compared head-to-head
   - Voting: Multiple solutions are evaluated collectively to identify the best option
   
4. **Answer Extraction**: The final numeric answer is extracted from the selected best reasoning path.


## 🗂️ Project Structure

```
validation_modules/
├── __init__.py
├── configs/
│   ├── deployment.json       # Deployment configuration
│   └── llm_configs.json      # LLM configuration
├── prompt.py                 # Validation prompt templates
├── run.py                    # Main implementation
├── schemas.py                # Input/output schemas
└── test.jsonl                # Test examples
```

## 🛠️ Installation

### Prerequisites

- Python 3.12+ (check .toml file for specific requirements)
- Poetry
- Naptha SDK
- Pydantic

### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/marathan24/validation_modules.git
   cd validation_modules
   ```

2. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

3. Set up environment variables:
   ```bash
   # Create a .env file with your keys
   echo "OPENAI_API_KEY=your_api_key_here" > .env
   echo "NODE_URL=your_node_url" >> .env
   echo "PRIVATE_KEY=your_private_key" >> .env
   ```

## 📋 Usage

### Starting the Node (on your local machine)

You need to clone the node repository and start the node: [Naptha Node Repository](https://github.com/NapthaAI/naptha-node)

```bash
bash launch.sh
```

The node will start on localhost:7001 by default. If it doesn't, try:

```bash
./docker-ctl.sh down
./launch.sh
```

Wait for some time until the node is up and running. You can check the logs using:

```bash
./docker-ctl.sh logs
```

### Running as a Standalone Module

You can run the module directly using Python:

```bash
poetry run python validation_modules/run.py
```

### Deploying as a Naptha Agent

Register the module as a Naptha agent:

```bash
naptha agents validation_modules -c 'description="LLM validation modules" parameters="{\"func_name\": \"str\", \"problem\": \"str\", \"thoughts\": \"List\"}" module_url="https://github.com/marathan24/validation_modules"'
```

Release a versioned tag:

```bash
git tag v0.2
git push origin v0.2
```

Update the agent with the version:

```bash
naptha agents validation_modules -u "module_version='v0.2'"
```

### Running the Agent

Execute the agent with specific parameters:

```bash
naptha run agent:validation_modules -p '{"func_name":"validate","problem":"Validate that the sum of the first 100 positive integers is 5050","thoughts":["Strategy: To solve this problem, I need to find the sum of the first 100 positive integers. Answer: I will use the formula n(n+1)/2 where n is the number of terms. Calculating 100*101/2 gives 5050, which is the answer."]}'
```

## 📊 Input Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `func_name` | string | The function name to execute (validate) | Required |
| `problem` | string | The problem to validate reasoning against | Required |
| `thoughts` | List[string] | Multiple reasoning paths to evaluate | Required |

## 📝 Prompt Templates

The system includes several prompt templates for different validation tasks:

- **Verifier Prompt**: Evaluates reasoning for question relevance, logical progression, factual accuracy, completeness, and critical assessment
- **Score Prompt**: Rates the quality of reasoning on a 1-10 scale
- **Compare Prompt**: Directly compares two reasoning paths to determine which is more correct
- **Vote Prompt**: Evaluates multiple reasoning paths to select the most promising one

## 🔄 How the Code Works

1. **Verification Process**: Each thought is evaluated using the verifier prompt. Only thoughts deemed valid continue to the next stage.

2. **Scoring Process**: Valid thoughts (or all thoughts if none are valid) are scored using the score prompt on a scale from 1 to 10.

3. **Selection Process**:
   - If multiple valid thoughts exist, the system compares the top-scoring thoughts directly
   - For three or more thoughts, a voting mechanism is also used
   - The system combines these approaches to select the overall best thought

4. **Answer Extraction**: The system extracts the final numeric answer from the selected best thought using regex pattern matching.

5. **Error Handling**: The code includes robust error handling to ensure stability, with detailed logging for troubleshooting.

## 🔗 Integration with Reasoning Modules

Validation Modules is designed to work with [Reasoning Modules](https://github.com/marathan24/reasoning_modules) as part of orchestrator pipeline:

1. Reasoning Modules generates multiple reasoning paths for a given problem
2. Validation Modules evaluates these paths and selects the best one
3. The combined system delivers high-quality, validated reasoning results

## Acknowledgements

- Naptha Node and Naptha SDK for the agent framework
- Research on validation and verification of AI reasoning