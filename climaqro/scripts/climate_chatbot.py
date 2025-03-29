# think about the possibility of relying for query refinement with previously scrapped docs. Essentially a RAG

# or query refinement with only client input, manually retrieved

# just combine CoT with self-consistency (multiple CoT)

import time
start_time = time.time()
import google.generativeai  as genai
from google import genai
import os
from dotenv import load_dotenv

print(f"Time to load libraries: {time.time() - start_time}")

def load_gemini():
    load_dotenv()
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    return


def fucklangChain(item, generator):
    
    context = f"Create a web-scrapping prompt for finding webpages interested in buying {item}."
    current_prompt = f"Find webpages interested in buying {item}."
    TemplatePrompt = f"[Context]: [{context}] | [Return this prompt improved for a search engine]: [{current_prompt}]"
    print(TemplatePrompt)
    res = generator(TemplatePrompt)
    return res


def main():
    model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    task = "text-generation"
    start_time = time.time()
    generator = load_huggingface(task, model_name)
    print(f"Time to load model: {time.time() - start_time}")
    item = "chairs"
    prompt = fucklangChain(item, generator)
    print(prompt)
    
main()