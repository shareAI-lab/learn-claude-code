#!/usr/bin/env python
"""v0_bash_agent_mini.py - Mini Claude Code (Compact)"""
from openai import OpenAI; from dotenv import load_dotenv; import json, subprocess as sp, sys, os
load_dotenv(override=True); C = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL")); M = os.getenv("MODEL_ID", "claude-sonnet-4-5-20250929")
T = [{"type":"function","function":{"name":"bash","description":"Shell cmd. Read:cat/grep/find/rg/ls. Write:echo>/sed. Subagent(for complex subtask): python v0_bash_agent_mini.py 'task'","parameters":{"type":"object","properties":{"command":{"type":"string"}},"required":["command"]}}}]
S = f"CLI agent at {os.getcwd()}. Use bash to solve problems. Spawn subagent for complex subtasks: python v0_bash_agent_mini.py 'task'. Subagent isolates context and returns summary. Be concise."

def chat(p, h=[]):
    h.append({"role":"user","content":p})
    while True:
        r=C.chat.completions.create(model=M,messages=[{"role":"system","content":S}]+h,tools=T,max_tokens=8000);m=r.choices[0].message
        if not m.tool_calls:
            h.append({"role":"assistant","content":m.content or ""});return m.content or ""
        h.append({"role":"assistant","content":m.content,"tool_calls":[{"id":tc.id,"type":"function","function":{"name":tc.function.name,"arguments":tc.function.arguments}}for tc in m.tool_calls]})
        for tc in m.tool_calls:
            a=json.loads(tc.function.arguments);cmd=a["command"];print(f"\033[33m$ {cmd}\033[0m");o=sp.run(cmd,shell=1,capture_output=1,text=1,timeout=300);out=o.stdout+o.stderr;print(out or"(empty)");h.append({"role":"tool","tool_call_id":tc.id,"content":(out)[:50000]})

if __name__=="__main__":[print(chat(sys.argv[1]))]if len(sys.argv)>1 else[print(chat(q,h))for h in[[]]for _ in iter(int,1)if(q:=input("\033[36m>> \033[0m"))not in("q","")]
