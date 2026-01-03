from fastapi import FastAPI, Body, Query, Path, Depends
from fastapi.responses import  StreamingResponse
from pydantic import BaseModel
from typing import Annotated, Literal
from workflow import builder
from langchain_core.messages import AIMessage, HumanMessage
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver


app = FastAPI(version="1.0.0", debug=True)

def is_alive_patch(self):
    return True

if not hasattr(aiosqlite.Connection, "is_alive"):
    setattr(aiosqlite.Connection, "is_alive", is_alive_patch)


async def get_chat_model():
    conn = await aiosqlite.connect("memory.db")
    checkpointer = AsyncSqliteSaver(conn)
    chat_model = builder.compile(checkpointer=checkpointer)
    return chat_model


# define model for chat api input
class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: Annotated[str, "content of message"]

@app.get("/")
async def main():
    return {"message":"server is working ...."}

@app.post("/chat")
async def chat(
        messages: Annotated[list[Message], Body()],
        thread_id: Annotated[str, Body()],
        chat_model = Depends(get_chat_model)
):
    return StreamingResponse(response(chat_model, {"messages":[HumanMessage(messages[-1].content)]}, thread_id), media_type="text/plain")

async def response(chat_model, input, thread_id):

    async for chunk, metadata in chat_model.astream(input, stream_mode="messages", config={"configurable":{"thread_id":thread_id}}):
        if isinstance(chunk, AIMessage) and chunk.content:
            yield chunk.content

@app.get("/chat/history/{thread_id}")
async def chat_history(thread_id: str, chat_model = Depends(get_chat_model)):

    state = await chat_model.aget_state(
        config={"configurable": {"thread_id": thread_id}}
    )
    messages = []
    for msg in state.values["messages"]:

        if isinstance(msg, AIMessage):
            messages.append({"role":"assistant", "content":msg.content})

        elif isinstance(msg, HumanMessage):
            messages.append({"role": "user", "content": msg.content})

        else:
            continue

    return messages

@app.get("/chat/get_threads")
async def get_thread_ids(db_path="memory.db"):
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("""
        SELECT DISTINCT THREAD_ID
        FROM checkpoints
        WHERE THREAD_ID IS NOT NULL
        """) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

@app.put("/chat/delete/{thread_id}")
async def delete_thread(thread_id: Annotated[str, Path()], db_path: str="memory.db"):
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "DELETE FROM checkpoints WHERE thread_id = ?",
            (thread_id,)
        )
        await db.execute(
            "DELETE FROM writes WHERE thread_id = ?",
            (thread_id,)
        )
        await db.commit()





