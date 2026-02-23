import os

from dotenv import load_dotenv

load_dotenv()

ds_key = os.getenv('DS_KEY')
qwen_key = os.getenv('QWEN_KEY')

if __name__ == '__main__':
    print(ds_key)
    print(qwen_key)