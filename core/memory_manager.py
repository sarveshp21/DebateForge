class DebateMemory:
    def __init__(self):
        self.memory = {}

    def store(self, key, value):   
        self.memory[key] = value

    def get(self, key):
        return self.memory.get(key, None)

    def get_all(self):
        return self.memory
    
# Entire debate history is returned
# What is Memory?
# Just a dictionary (key-value store):
# {
#   "pro_opening": {...},
#   "against_opening": {...}
# }

# Why Memory?
# So agents can use past information