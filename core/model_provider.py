from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.deepseek import DeepSeekProvider
from pydantic_ai.providers.openai import OpenAIProvider

import envUtils

deepseek_model = OpenAIChatModel(
    'deepseek-chat',
    provider=DeepSeekProvider(api_key=envUtils.ds_key),
)

# 注意: 不同地域的base_url不通用（下方示例使用新加坡地域的base_url）
# - 新加坡: https://dashscope-intl.aliyuncs.com/compatible-mode/v1
# - 美国（弗吉尼亚）: https://dashscope-us.aliyuncs.com/compatible-mode/v1
# - 华北2（北京）: https://dashscope.aliyuncs.com/compatible-mode/v1
qwen_flash = OpenAIChatModel(
    'qwen-flash',
    provider=OpenAIProvider(
        base_url='https://dashscope.aliyuncs.com/compatible-mode/v1', api_key=envUtils.qwen_key
    ),
)
qwen_plus = OpenAIChatModel(
    'qwen-plus',
    provider=OpenAIProvider(
        base_url='https://dashscope.aliyuncs.com/compatible-mode/v1', api_key=envUtils.qwen_key
    ),
)
qwen_max = OpenAIChatModel(
    'qwen-max',
    provider=OpenAIProvider(
        base_url='https://dashscope.aliyuncs.com/compatible-mode/v1', api_key=envUtils.qwen_key
    ),
)

kimi_k2 = OpenAIChatModel(
    'kimi-k2-turbo-preview',
    provider=OpenAIProvider(
        base_url='https://api.moonshot.cn/v1', api_key=envUtils.kimi_key
    ),
)

gemini_3 = GoogleModel(
    'gemini-3-flash-preview',
    provider=GoogleProvider(
        api_key=envUtils.gemini_key
    ),
)

gpt_5_2 = OpenAIChatModel('gpt-5.2', provider=OpenAIProvider(api_key=envUtils.gpt_key))
gpt_5_mini = OpenAIChatModel('gpt-5-mini', provider=OpenAIProvider(api_key=envUtils.gpt_key))


use_model = deepseek_model
