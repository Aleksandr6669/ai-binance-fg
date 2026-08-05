import urllib.parse
query_string = "sessionId=12345&foo=bar"
parsed_query = urllib.parse.parse_qs(query_string)
if "sessionId" in parsed_query:
    print(parsed_query["sessionId"][0])
