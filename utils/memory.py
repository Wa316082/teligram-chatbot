from langchain_classic.memory import ConversationBufferWindowMemory

_user_memories: dict[str, ConversationBufferWindowMemory] = {}


def get_memory(user_id: str) -> ConversationBufferWindowMemory:
    if user_id not in _user_memories:
        _user_memories[user_id] = ConversationBufferWindowMemory(
            k=10,
            return_messages=True,
            memory_key="chat_history"
        )
    return _user_memories[user_id]


def clear_memory(user_id: str):
    if user_id in _user_memories:
        del _user_memories[user_id]