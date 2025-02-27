vote_prompt = '''Given an instruction and several choices, decide which choice is most promising. Analyze each choice in detail, then conclude in the last line "The best choice is {s}", where s the integer id of the choice.
'''

compare_prompt = '''
Briefly analyze the correctness of the following two solutions. Conclude in the last line "The more correct solution is 1", "The more correct solution is 2", or "Both solutions are similarly correct".
'''

score_prompt = '''Analyze the following solution, then at the last line conclude "Thus the correctness score is {s}", where s is an integer from 1 to 10.
'''

verifier_prompt = '''
As a critical mathematical reasoning verifier, evaluate the following thought process, which builds upon previous steps to reach a final conclusion. Focus on:

1. **Question Relevance**:
   - Ensure the entire reasoning process directly addresses the original question.
   - Check if the final answer actually solves what was asked.

2. **Reasoning Progression**:
   - Assess logical flow and consistency, especially in final steps.
   - Verify mathematical operations' correctness and appropriateness.
   - Identify logical fallacies or unjustified leaps.

3. **Factual Accuracy**:
   - Check accuracy and relevance of facts and numbers, particularly in final calculations.
   - Spot any misuse of mathematical concepts.

4. **Completeness**:
   - Ensure all necessary aspects are addressed, particularly in concluding thoughts.
   - Identify significant omissions that could affect the result.

5. **Critical Assessment**:
   - Actively seek potential errors or weak points.
   - Don't hesitate to invalidate reasoning if significant issues are found.

Provide a holistic evaluation of the entire reasoning process, from start to finish. Conclude with "Reasoning is Valid" only if the entire process is relevant, logically sound, and error-free. Otherwise, conclude with "Reasoning is Invalid" and briefly explain why.
'''