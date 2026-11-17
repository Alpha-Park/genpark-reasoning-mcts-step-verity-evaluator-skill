# -*- coding: utf-8 -*-
"""
GenPark Reasoning MCTS Step Verity Evaluator MCP Server
Exposes MCTS tree search and step process reward tools via JSON-RPC 2.0 over STDIO.
"""

import sys
import json
from client import GenParkReasoningMCTSStepVerityEvaluator

def handle_request(req):
    method = req.get("method")
    req_id = req.get("id")

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "search_and_evaluate_tree",
                        "description": "Evaluates reasoning thought chains using Upper Confidence Bounds (UCB1) and Process Reward Model (PRM) verity scoring to prune hallucinated branches.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "thought_tree": {
                                    "type": "array",
                                    "items": {"type": "object"}
                                },
                                "root_node_id": {"type": "string"}
                            },
                            "required": ["thought_tree"]
                        }
                    }
                ]
            }
        }
    elif method == "tools/call":
        params = req.get("params", {})
        tool_name = params.get("name")
        args = params.get("arguments", {})

        if tool_name == "search_and_evaluate_tree":
            evaluator = GenParkReasoningMCTSStepVerityEvaluator()
            res = evaluator.search_and_evaluate_tree(
                thought_tree=args.get("thought_tree", []),
                root_node_id=args.get("root_node_id", "root")
            )
            return {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}}
        else:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Tool '{tool_name}' not found"}}
    else:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32600, "message": f"Method '{method}' not supported"}}

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("MCP Server Discovery Test OK")
        e = GenParkReasoningMCTSStepVerityEvaluator()
        tree = [
            {"id": "root", "visits": 10},
            {"id": "step-1", "step_text": "Let x = 5, then 2x + 3 = 13", "prm_confidence": 0.95, "visits": 4},
            {"id": "step-2", "step_text": "Clearly therefore x = 99", "prm_confidence": 0.25, "visits": 1}
        ]
        test_res = e.search_and_evaluate_tree(tree, "root")
        print(f"Test Pruned: {test_res['total_branches_pruned']}")
        return

    for line in sys.stdin:
        if not line.strip(): continue
        try:
            try:
                req = json.loads(line)
            except json.JSONDecodeError as exc:
                print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}), flush=True)
                continue
            if not isinstance(req, dict) or req.get("jsonrpc") != "2.0" or not isinstance(req.get("method"), str):
                print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}}), flush=True)
                continue
            # JSON-RPC notifications never receive a response or execute request-only tools.
            if "id" not in req:
                continue
            if req["method"] == "initialize":
                print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "result": {
                    "protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                    "serverInfo": {"name": 'genpark-reasoning-mcts-step-verity-evaluator-skill', "version": "1.0.0"}
                }}), flush=True)
                continue
            if req["method"] == "ping":
                print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "result": {}}), flush=True)
                continue
            if req["method"] not in ("tools/list", "tools/call"):
                print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32601, "message": "Method not found"}}), flush=True)
                continue
            if req["method"] == "tools/call":
                params = req.get("params")
                if not isinstance(params, dict) or not isinstance(params.get("arguments", {}), dict) or params.get("name") not in ('search_and_evaluate_tree',):
                    print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32602, "message": "Unknown tool or invalid arguments"}}), flush=True)
                    continue
            resp = handle_request(req)
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err = {"jsonrpc": "2.0", "id": req.get("id") if isinstance(req, dict) else None, "error": {"code": -32700, "message": str(e)}}
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
