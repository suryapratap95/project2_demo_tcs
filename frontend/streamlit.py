import streamlit as st
import requests
import time
import uuid
import os

FASTAPI_URL = os.environ.get("FASTAPI_URL", "http://localhost:8000")


def response_generator(text):
    for word in text.split():
        yield word + " "
        time.sleep(0.05)


st.set_page_config(page_title="FinBot - SecureBank", page_icon="🏦", layout="wide")
st.title("SecureBank FinBot")

# --- Sidebar: Role selection and HITL controls ---
with st.sidebar:
    st.header("Settings")
    user_role = st.selectbox(
        "User Role",
        ["customer", "junior_analyst", "senior_analyst", "compliance_officer", "admin"],
        help="Role-based access control - determines which documents you can access",
    )

    st.divider()
    st.header("Approval Queue")
    if st.button("Check Pending Approvals"):
        try:
            resp = requests.get(
                f"{FASTAPI_URL}/hitl/pending/{st.session_state.get('session_id', 'default')}",
                timeout=10,
            )
            if resp.status_code == 200:
                pending = resp.json().get("requests", [])
                if pending:
                    for req in pending:
                        st.warning(f"**{req['action_type']}**: {req['description']}")
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Approve", key=f"approve_{req['request_id']}"):
                                requests.post(f"{FASTAPI_URL}/hitl/decide", json={
                                    "request_id": req["request_id"],
                                    "decision": "approved",
                                    "approver": user_role,
                                })
                                st.success("Approved!")
                        with col2:
                            if st.button("Reject", key=f"reject_{req['request_id']}"):
                                requests.post(f"{FASTAPI_URL}/hitl/decide", json={
                                    "request_id": req["request_id"],
                                    "decision": "rejected",
                                    "approver": user_role,
                                    "reason": "Rejected by supervisor",
                                })
                                st.error("Rejected")
                else:
                    st.info("No pending approvals")
        except Exception as e:
            st.error(f"Could not connect: {e}")

    st.divider()
    if st.button("Reset Session"):
        try:
            requests.post(
                f"{FASTAPI_URL}/reset",
                json={"session_id": st.session_state.get("session_id", "default")},
                timeout=10,
            )
            st.session_state.messages = []
            st.success("Session reset!")
        except Exception as e:
            st.error(f"Error: {e}")

# --- Main chat area ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if user_input := st.chat_input("Ask FinBot about your banking needs..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                resp = requests.post(
                    f"{FASTAPI_URL}/chat",
                    json={
                        "message": user_input,
                        "session_id": st.session_state.session_id,
                        "user_role": user_role,
                    },
                    timeout=60,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    response_text = data["response"]
                    if data.get("cached"):
                        st.caption("(cached response)")
                else:
                    response_text = f"Error: {resp.status_code}"
            except Exception as e:
                response_text = f"Connection error: {e}"

        response = st.write_stream(response_generator(response_text))
    st.session_state.messages.append({"role": "assistant", "content": response_text})
