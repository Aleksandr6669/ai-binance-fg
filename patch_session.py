with open("mcp_server.py", "r") as f:
    content = f.read()

# Replace the wrong query string matching
old_match = """            query_string = scope.get("query_string", b"").decode("utf-8")
            if "sessionId=" in query_string:
                import urllib.parse
                parsed_query = urllib.parse.parse_qs(query_string)
                if "sessionId" in parsed_query:
                    session_id = parsed_query["sessionId"][0]
                    global_session_map[session_id] = client_id"""

new_match = """            query_string = scope.get("query_string", b"").decode("utf-8")
            if "session_id=" in query_string:
                import urllib.parse
                parsed_query = urllib.parse.parse_qs(query_string)
                if "session_id" in parsed_query:
                    session_id = parsed_query["session_id"][0]
                    global_session_map[session_id] = client_id"""

content = content.replace(old_match, new_match)

with open("mcp_server.py", "w") as f:
    f.write(content)
print("Done")
