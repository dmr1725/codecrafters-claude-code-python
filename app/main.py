import argparse
import os
import sys
import json
import subprocess

from openai import OpenAI

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")

def call_llm(messages: list):
    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    chat = client.chat.completions.create(
        model="anthropic/claude-haiku-4.5",
        messages=messages,
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "Read",
                    "description": "Read and return the contents of a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                            "type": "string",
                            "description": "The path to the file to read"
                            }
                        },
                        "required": ["file_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "Write",
                    "description": "Write content to a file",
                    "parameters": {
                        "type": "object",
                        "required": ["file_path", "content"],
                        "properties": {
                            "file_path": {
                            "type": "string",
                            "description": "The path of the file to write to"
                            },
                            "content": {
                            "type": "string",
                            "description": "The content to write to the file"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "Bash",
                    "description": "Execute a shell command",
                    "parameters": {
                    "type": "object",
                    "required": ["command"],
                    "properties": {
                        "command": {
                        "type": "string",
                        "description": "The command to execute"
                        }
                    }
                    }
                }
            }
        ]
    )

    if not chat.choices or len(chat.choices) == 0:
        raise RuntimeError("no choices in response")

    return chat.choices[0].message

def execute_tool_call(tool_call):
    tool_id = tool_call.id
    tool_args = json.loads(tool_call.function.arguments)
    print(f"Tool id: {tool_id}, tool args: {tool_args}", file=sys.stderr)

    if tool_call.function.name == "Read":
        with open(tool_args["file_path"]) as f:
            content = f.read()
            return {
                "role": "tool",
                "tool_call_id": tool_id,
                "content": content
            }
    
    if tool_call.function.name == "Write":
        content = tool_args["content"]
        with open(tool_args["file_path"], "w") as f:
            f.write(content)
            return {
                "role": "tool",
                "tool_call_id": tool_id,
                "content": content
            }
    
    if tool_call.function.name == "Bash":
        command = tool_args["command"]
        result = subprocess.run(command)
        return {
            "role": "tool",
            "tool_call_id": tool_id,
            "content": result
        }
            



def main():
    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()

    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    messages = [{"role": "user", "content": args.p}]
    response = call_llm(messages)


    while response.tool_calls:
        messages.append(response)
        for tool_call in response.tool_calls:
            tool_response = execute_tool_call(tool_call)
            messages.append(tool_response)
        
        response = call_llm(messages)
    
    print(response.content)


if __name__ == "__main__":
    main()
