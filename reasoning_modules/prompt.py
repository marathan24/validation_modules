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

vote_prompt = '''Given an instruction and several choices, decide which choice is most promising. Analyze each choice in detail, then conclude in the last line "The best choice is {s}", where s the integer id of the choice.
'''

compare_prompt = '''
Briefly analyze the correctness of the following two solutions. Conclude in the last line "The more correct solution is 1", "The more correct solution is 2", or "Both solutions are similarly correct".
'''

score_prompt = '''Analyze the following solution, then at the last line conclude "Thus the correctness score is {s}", where s is an integer from 1 to 10.
'''
