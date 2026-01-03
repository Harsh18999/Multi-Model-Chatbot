import streamlit as st
import requests
import uuid

from main import response

# define session variables

if "curr_thread" not in st.session_state:
    st.session_state.curr_thread = ""

if "messages" not in st.session_state:
    st.session_state.messages = {"":[]}

    with requests.get("http://127.0.0.1:8000/chat/get_threads") as r:
        if r.status_code == 200:
            threads = r.json()

    for thread in threads:

        if not st.session_state.curr_thread:
            st.session_state.curr_thread = thread

        with requests.get(f"http://127.0.0.1:8000/chat/history/{thread}") as r:
            if r.status_code == 200:
                st.session_state.messages[thread] = r.json()


if "curr_response" not in st.session_state:
    st.session_state.curr_response = ""

with st.sidebar.container(key="new_chat_container", border=True):
    st.write("**Create New Chat**")
    if st.button("Create", key="new_chat_button", use_container_width=True):
        new_thread = str(uuid.uuid4())
        st.session_state.messages[new_thread] = []
        st.session_state.curr_thread = new_thread

def delete_thread(thread_id: str):
    response = requests.put(f"http://127.0.0.1:8000/chat/delete/{thread_id}")

    if response.status_code == 200:
        del st.session_state.messages[thread_id]
        st.sidebar.success(f"successfully deleted {thread_id}")

        if st.session_state.curr_thread == thread_id:
            st.session_state.curr_thread=""
        st.rerun()

    else:
        st.sidebar.error(f"can't deleted {thread_id}")

for thread in list(st.session_state.messages.keys()):

    if thread == "": continue

    with st.sidebar.container(key=thread+"_container", border=True):
        st.write(f"**{thread}**")

        if st.button("USE", key=thread+"_use", use_container_width=True):
            st.session_state.curr_thread = thread

        if st.button("DELETE", key=thread+"_delete", use_container_width=True):
            delete_thread(thread)


print(st.session_state.messages[st.session_state.curr_thread])
for message in st.session_state.messages[st.session_state.curr_thread]:

    if message["role"] == "user":
        st.chat_message("user").write(message["content"])
    else:
        st.chat_message("assistant").write(message["content"])

def stream_reponse():
    with requests.post("http://127.0.0.1:8000/chat", json={"messages":st.session_state.messages[st.session_state.curr_thread], "thread_id":st.session_state.curr_thread}, stream=True) as r:
        for chunk in r.iter_content():
            if chunk:
                txt = chunk.decode("utf-8", errors="ignore")
                st.session_state.curr_response += txt
                yield txt

if st.session_state.curr_thread:
    user_input = st.chat_input("Enter Your Query ....")

else:
    user_input = st.chat_input("Enter Your Query ....", disabled=True)

if user_input:
    st.session_state.messages[st.session_state.curr_thread].append({"role":"user", "content":user_input})
    st.chat_message("user").write(user_input)
    st.chat_message("assistant").write_stream(stream_reponse)
    st.session_state.messages[st.session_state.curr_thread].append({"role":"assistant", "content":st.session_state.curr_response})
    st.session_state.curr_response = ""
