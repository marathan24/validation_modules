import logging
import os
from dotenv import load_dotenv
from typing import Dict
import asyncio
import json, random

from naptha_sdk.inference import InferenceClient
from naptha_sdk.schemas import AgentDeployment, AgentRunInput, KBRunInput
from naptha_sdk.user import sign_consumer_id, get_private_key_from_pem

from schemas import ReasoningInput, SystemPromptSchema

# Import the exact GSM8K prompts (we use them for reasoning)
# (They are reused here as our reasoning prompts.)
standard_prompt = '''
Answer the following math problem. Your response should conclude with "the answer is n", where n is a number:
{input}
'''

cot_prompt = '''
Answer the following question: {input}
Make a strategy, then write. Your output should be in the following format:

Strategy:
Your strategy about how to answer the question.

Answer:
Your answer to the question. It should end with "the answer is n", where n is a number.
'''



logger = logging.getLogger(__name__)

class ReasoningAgent:
    async def create(self, deployment: AgentDeployment, *args, **kwargs):
        self.deployment = deployment
        self.system_prompt = SystemPromptSchema(role=self.deployment.config.system_prompt["role"])
        self.inference_client = InferenceClient(self.deployment.node)
    
    async def run(self, module_run: AgentRunInput, *args, **kwargs):
        problem = module_run.inputs.problem
        
        # --- Step 1: Initial Generation ---
        initial_prompt = standard_prompt.format(input=problem)
        messages = [
            {"role": "system", "content": self.system_prompt.role},
            {"role": "user", "content": initial_prompt}
        ]
        logger.info("Sending initial prompt: %s", messages)
        response_initial = await self.inference_client.run_inference({
            "model": self.deployment.config.llm_config.model,
            "messages": messages,
            "temperature": self.deployment.config.llm_config.temperature,
            "max_tokens": self.deployment.config.llm_config.max_tokens
        })
        initial_thought = response_initial.choices[0].message.content
        logger.info("Initial thought: %s", initial_thought)
        
        # --- Step 2: Chain-of-Thought Refinement ---
        cot_prompt_text = cot_prompt.format(input=problem, previous=initial_thought)
        messages = [
            {"role": "system", "content": self.system_prompt.role},
            {"role": "user", "content": cot_prompt_text}
        ]
        logger.info("Sending CoT prompt: %s", messages)
        response_cot = await self.inference_client.run_inference({
            "model": self.deployment.config.llm_config.model,
            "messages": messages,
            "temperature": self.deployment.config.llm_config.temperature,
            "max_tokens": self.deployment.config.llm_config.max_tokens
        })
        cot_thought = response_cot.choices[0].message.content
        logger.info("CoT output: %s", cot_thought)
        
        return cot_thought

async def run(module_run: Dict, *args, **kwargs):
    module_run = AgentRunInput(**module_run)
    module_run.inputs = ReasoningInput(**module_run.inputs)
    reasoning_agent = ReasoningAgent()
    await reasoning_agent.create(module_run.deployment)
    result = await reasoning_agent.run(module_run)
    return result

if __name__ == "__main__":
    import asyncio
    from naptha_sdk.client.naptha import Naptha
    from naptha_sdk.configs import setup_module_deployment

    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    naptha = Naptha()

    deployment = asyncio.run(
        setup_module_deployment(
            "agent", 
            "reasoning_modules/configs/deployment.json", 
            node_url=os.getenv("NODE_URL"), 
            user_id=naptha.user.id
        )
    )

    with open('./reasoning_modules/test.jsonl', 'r') as f:
        lines = f.readlines()

    if lines:
        data = json.loads(random.choice(lines))
        question_text = data.get("question", "Prove that the sum of the angles in a triangle is 180 degrees.")
    else:
        question_text = "Prove that the sum of the angles in a triangle is 180 degrees."

    input_params = {
        "func_name": "reason",
        "problem": question_text
    }

    module_run = {
        "inputs": input_params,
        "deployment": deployment,
        "consumer_id": naptha.user.id,
        "signature": sign_consumer_id(naptha.user.id, get_private_key_from_pem(os.getenv("PRIVATE_KEY")))
    }

    response = asyncio.run(run(module_run))

    logger.info("Final Reasoning Output:")
    logger.info(response)