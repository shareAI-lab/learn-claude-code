import os
from anthropic import Anthropic
import type


# 读取当前目录或上级目录里的 .env 文件，并把里面的变量加载到 os.environ；如果系统环境变量里已经有同名变量，就用 .env 里的值覆盖它。
from dotenv import load_dotenv
load_dotenv(override=True)

# 单个tool，包含，工具名/描述/输入形式
TOOLS = [{
    "name": "bash",
    "description": "Run a shell command.",
    "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    },
}]

client = Anthropic(base_url= os.getenv("ANTHROPIC_BASE_URL"))
Model = os.environ["MODEL_ID"]
System = "你是 vibecoding 工具"

def run_bash() ->str:
    return ""


def Agent_loop(messages:list):
    while True:
        response = client.messages.create(model = Model,
                                          system = System,
                                          messages = messages,
                                          tools = TOOLS,
                                          max_tokens=8000)
        """
        response：Anthropic 返回的 Message 对象

        response.stop_reason：
            "end_turn"：普通回答结束
            "tool_use"：请求调用工具
            "max_tokens"：达到 token 上限

        response.content：
            if stop_reason =="end_turn"
            
            elif stop_reason =="tool_use"
                [TextBlock(...),                 # 可选，工具调用前的说明
                
                ToolUseBlock(
                type="tool_use",
                id="toolu_xxx",
                name="工具名称",
                input={"工具参数": "参数值"} )]
        """

        if response.stop_reason == tool_use:
            run_bash()
            pass
        pass    