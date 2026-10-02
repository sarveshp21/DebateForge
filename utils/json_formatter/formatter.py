import json
import re

def parse_json_response(response):
    try:
        # Remove markdown ```json ```
        cleaned = re.sub(r"```json|```", "", response).strip()
        
        # Extract JSON block
        json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        
        if json_match:
            return json.loads(json_match.group())
        
        return {"arguments": [cleaned]}
    
    except Exception as e:
        return {"arguments": [response]}
    

# Output:
# {
#   "arguments": ["point1", "point2", "point3"]
# }