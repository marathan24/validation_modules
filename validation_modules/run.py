import logging
import os
import re
from dotenv import load_dotenv
from typing import Dict, List, Tuple
import asyncio
import json, random

from naptha_sdk.inference import InferenceClient
from naptha_sdk.schemas import AgentDeployment, AgentRunInput
from naptha_sdk.user import sign_consumer_id, get_private_key_from_pem

from validation_modules.schemas import InputSchema, SystemPromptSchema, ValidationResult
from validation_modules.prompt import verifier_prompt, score_prompt, vote_prompt, compare_prompt

logger = logging.getLogger(__name__)

class ValidationAgent:
    async def create(self, deployment: AgentDeployment, *args, **kwargs):
        self.deployment = deployment
        self.system_prompt = SystemPromptSchema(role=self.deployment.config.system_prompt["role"])
        self.inference_client = InferenceClient(self.deployment.node)
    
    async def run(self, module_run: AgentRunInput, *args, **kwargs):
        # Handle problem with better error recovery
        problem = module_run.inputs.problem
        if isinstance(problem, str):
            # Clean up the problem string in case it has issues
            problem = problem.rstrip(',').strip()
        
        # Process thoughts - directly use them without trying to decode
        thoughts = module_run.inputs.thoughts
        processed_thoughts = []
        
        # Clean up and process thoughts
        for thought in thoughts:
            if isinstance(thought, str):
                # Clean up any problematic characters
                thought = thought.replace('\\"', '"').strip()
            processed_thoughts.append(thought)
        
        logger.info(f"Starting validation for {len(processed_thoughts)} thoughts")
        
        # Step 1: Verify each thought
        valid_thoughts = []
        verification_details = []
        
        for i, thought in enumerate(processed_thoughts):
            is_valid, verification = await self._verify_reasoning(thought, problem)
            verification_details.append(verification)
            
            if is_valid:
                valid_thoughts.append(thought)
                logger.info(f"Thought {i+1} is valid")
            else:
                logger.info(f"Thought {i+1} is invalid: {verification}")
        
        # Step 2: Score each valid thought (or all thoughts if none are valid)
        thoughts_to_score = valid_thoughts if valid_thoughts else processed_thoughts
        scores = []
        
        for thought in thoughts_to_score:
            score = await self._score_thought(thought, problem)
            scores.append(score)
            logger.info(f"Thought scored {score}/10")
        
        # Step 3: If we have multiple valid thoughts, select the best one using voting
        best_thought_index = 0
        best_thought = ""
        
        if len(thoughts_to_score) > 1:
            sorted_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            top_indices = sorted_indices[:min(3, len(sorted_indices))]
            
            if len(top_indices) >= 2:
                # Compare top two thoughts
                winner = await self._compare_thoughts(
                    thoughts_to_score[top_indices[0]], 
                    thoughts_to_score[top_indices[1]], 
                    problem
                )
                
                if winner == 1:
                    best_thought_index = top_indices[0]
                elif winner == 2:
                    best_thought_index = top_indices[1]
                else:  
                    best_thought_index = top_indices[0]  
            else:
                best_thought_index = top_indices[0]
                
            # Use voting as a backup or validation
            if len(thoughts_to_score) >= 3:
                vote_result = await self._vote_on_thoughts(thoughts_to_score, problem)
                if vote_result != best_thought_index and scores[vote_result] >= scores[best_thought_index]:
                    best_thought_index = vote_result
        elif len(thoughts_to_score) == 1:
            best_thought_index = 0
        else:
            # No valid thoughts, return the highest scoring one from all thoughts
            best_thought_index = scores.index(max(scores)) if scores else 0
            
        # Map the index back to the original thoughts list as needed accordingly
        if valid_thoughts:
            original_index = processed_thoughts.index(thoughts_to_score[best_thought_index])
            best_thought = processed_thoughts[original_index]
        else:
            best_thought = processed_thoughts[best_thought_index]
            
        logger.info(f"Selected best thought (index {best_thought_index})")
        
        final_answer = self._extract_answer(best_thought)
        logger.info(f"Final answer: {final_answer}")
        
        result = {
            "valid_thoughts": valid_thoughts,
            "scores": scores,
            "best_thought": best_thought,
            "best_thought_index": best_thought_index,
            "verification_details": verification_details,
            "final_answer": final_answer
        }
        
        return result
    
    async def _verify_reasoning(self, reasoning: str, question: str) -> Tuple[bool, str]:
        """Verify if the reasoning is valid"""
        verify_prompt = f"{verifier_prompt}\n\nQuestion: {question}\n\nReasoning to verify:\n{reasoning}\n\nVerification:"
        
        messages = [
            {"role": "system", "content": self.system_prompt.role},
            {"role": "user", "content": verify_prompt}
        ]
        
        response = await self.inference_client.run_inference({
            "model": self.deployment.config.llm_config.model,
            "messages": messages,
            "temperature": 0.3,  
            "max_tokens": self.deployment.config.llm_config.max_tokens
        })
        
        verification = response.choices[0].message.content
        is_valid = "reasoning is valid" in verification.lower()
        
        return is_valid, verification
    
    async def _score_thought(self, thought: str, question: str) -> int:
        """Score the thought on a scale of 1-10"""
        score_prompt_text = f"{score_prompt}\n\nQuestion: {question}\n\nSolution to analyze:\n{thought}\n\nAnalysis:"
        
        messages = [
            {"role": "system", "content": self.system_prompt.role},
            {"role": "user", "content": score_prompt_text}
        ]
        
        response = await self.inference_client.run_inference({
            "model": self.deployment.config.llm_config.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": self.deployment.config.llm_config.max_tokens
        })
        
        score_text = response.choices[0].message.content
        
        match = re.search(r"correctness score is (\d+)", score_text)
        if match:
            score = int(match.group(1))
            return min(max(score, 1), 10)  # Ensure score is between 1 and 10
        else:
            logger.warning(f"Failed to extract score from: {score_text}")
            return 5  # Default score if extraction fails (This needs to be improved)
    
    async def _compare_thoughts(self, thought1: str, thought2: str, question: str) -> int:
        """Compare two thoughts and return 1 if first is better, 2 if second is better, 0.5 if equal"""
        compare_prompt_text = f"{compare_prompt}\n\nQuestion: {question}\n\nSolution 1:\n{thought1}\n\nSolution 2:\n{thought2}\n\nComparison:"
        
        messages = [
            {"role": "system", "content": self.system_prompt.role},
            {"role": "user", "content": compare_prompt_text}
        ]
        
        response = await self.inference_client.run_inference({
            "model": self.deployment.config.llm_config.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": self.deployment.config.llm_config.max_tokens
        })
        
        compare_text = response.choices[0].message.content.lower()
        
        if "more correct solution is 1" in compare_text:
            return 1
        elif "more correct solution is 2" in compare_text:
            return 2
        else:
            return 0.5  # Both solutions are similarly correct
    
    async def _vote_on_thoughts(self, thoughts: List[str], question: str) -> int:
        """Vote on multiple thoughts and return the index of the best one"""
        vote_prompt_text = vote_prompt
        for i, thought in enumerate(thoughts, 1):
            vote_prompt_text += f"\nChoice {i}:\nQuestion: {question}\n\n{thought}\n"
        
        messages = [
            {"role": "system", "content": self.system_prompt.role},
            {"role": "user", "content": vote_prompt_text}
        ]
        
        response = await self.inference_client.run_inference({
            "model": self.deployment.config.llm_config.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": self.deployment.config.llm_config.max_tokens
        })
        
        vote_text = response.choices[0].message.content
        
        # Extract the vote
        match = re.search(r"best choice is (\d+)", vote_text, re.IGNORECASE)
        if match:
            vote = int(match.group(1)) - 1  
            if 0 <= vote < len(thoughts):
                return vote
        
        logger.warning(f"Failed to extract vote from: {vote_text}")
        return 0  # Default to first thought if extraction fails
    
    def _extract_answer(self, thought: str) -> str:
        """Extract the numeric answer from the thought"""
        # Define the pattern to search for a numeric answer after "the answer is"
        pattern = r"the answer is[^\d]*(\d+[\d,]*)"
        match = re.search(pattern, thought, re.IGNORECASE)
        
        if match:
            numeric_answer = match.group(1).replace(',', '')
            return numeric_answer
        
        return ""  # Return empty string if no answer found

async def run(module_run: Dict, *args, **kwargs):
    try:
        # Convert module_run to AgentRunInput
        module_run = AgentRunInput(**module_run)
        
        # Validate without using json.loads
        try:
            # Make a copy of inputs for validation to avoid modifying original
            validation_inputs = {}
            for key, value in module_run.inputs.__dict__.items():
                if key == "problem" and isinstance(value, str):
                    validation_inputs[key] = value.rstrip(',').strip()
                elif key == "thoughts" and isinstance(value, list):
                    validation_inputs[key] = [
                        t.replace('\\"', '"').strip() if isinstance(t, str) else t 
                        for t in value
                    ]
                else:
                    validation_inputs[key] = value
                
            # Create InputSchema instance with cleaned data
            module_run.inputs = InputSchema(**validation_inputs)
        except Exception as e:
            logger.error(f"Failed to validate input schema: {e}")
            # Create a more detailed error message
            error_details = f"Input validation error: {str(e)}\nInputs: {module_run.inputs}"
            raise ValueError(error_details)
        
        # Create and run the validation agent
        validation_agent = ValidationAgent()
        await validation_agent.create(module_run.deployment)
        result = await validation_agent.run(module_run)
        return result
    except Exception as e:
        logger.error(f"Error in run function: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

if __name__ == "__main__":
    import asyncio
    import traceback
    from naptha_sdk.client.naptha import Naptha
    from naptha_sdk.configs import setup_module_deployment

    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    naptha = Naptha()

    deployment = asyncio.run(
        setup_module_deployment(
            "agent", 
            "validation_modules/configs/deployment.json", 
            node_url=os.getenv("NODE_URL"), 
            user_id=naptha.user.id
        )
    )
    thought1 = "Strategy:\nI'll calculate the sum of the first 100 positive integers.\n\nAnswer:\nI can use the arithmetic sequence formula: S = n/2 * (a₁ + aₙ), where n is the number of terms, a₁ is the first term, and aₙ is the last term.\nS = 100/2 * (1 + 100)\nS = 50 * 101\nS = 5050\nThe answer is 5050"
    # Example thoughts for testing
    thoughts = [        
        thought1,
        "Strategy:\nFirst, determine how many plants Toni has by calculating 60% more than the number of plants Frederick has. Since Frederick has 10 plants, we find 60% of 10, which is 6. Then, we add this to Frederick's 10 plants to find Toni's total. After finding Toni's number of plants, we subtract 7 from Toni's total to find out how many plants Shondra has.\n\nAnswer:\nFrederick has 10 plants. Therefore, 60% of 10 is 6. Adding this to Frederick's 10 gives Toni 16 plants (10 + 6 = 16). Shondra has 7 fewer plants than Toni, which means Shondra has 9 plants (16 - 7 = 9). Therefore, the answer is 9."
    ]

    for i in range(len(thoughts)):
        print(f"Thought {i+1}: {thoughts[i]}")
    input_params = {
        "func_name": "validate",
        "problem": "What is the sum of all integers from 1 to 100?",
        "thoughts": thoughts
    }

    module_run = {
        "inputs": input_params,
        "deployment": deployment,
        "consumer_id": naptha.user.id,
        "signature": sign_consumer_id(naptha.user.id, get_private_key_from_pem(os.getenv("PRIVATE_KEY")))
    }

    response = asyncio.run(run(module_run))

    logger.info("Final Validation Output:")
    logger.info(response)