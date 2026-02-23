import os

from dotenv import load_dotenv

load_dotenv()

ds_key = os.getenv('DS_KEY')
qwen_key = os.getenv('QWEN_KEY')
kimi_key = os.getenv('KIMI_KEY')
gemini_key = os.getenv('GEMINI_KEY')
gpt_key = os.getenv('GPT_KEY')

if __name__ == '__main__':
    print(ds_key)
    print(qwen_key)