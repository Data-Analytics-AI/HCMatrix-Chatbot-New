
import streamlit as st
import pyperclip
import tempfile
from send_request import chat_endpoint
from streamlit_webrtc import webrtc_streamer, WebRtcMode, ClientSettings

# Streamlit UI components
st.set_page_config(layout="wide")
st.title("Snapnet HCMatrix ChatBot")
st.text(" **Note, this chatbot is currently experimental and might return incorrect queries from time to time.** "
        " **Should that be the case, kindly retry or meet with your organization human resource manager.**")

# Contextual Summarization
with st.expander("## **HCMatrix Chatbot**"):
    # input_type = st.radio("Select Query Type:", ["General", "Database"], index=0)
    company_id = st.radio("Select a dummy company id", ["53", "39"], index=0)
    if company_id == "53":
        employee_id = st.radio("Select a dummy employee id", ["372", "373"], index=0)

    elif company_id == "39":
        employee_id = st.radio("Select a dummy employee id", ["329", "341"], index=0)

    audio = st.radio("To get output as audio", ["True", "False"], index=1)

    user_input = st.text_area("Enter query here:")

    employee_metadata = {
        "department_id": "43",
        "role_id": "323",
        "group_id": "54",
        "company_id": company_id,
        "id": employee_id
    }

    if st.button("Send"):
        with st.spinner("Querying the model for the best answer... Sip a cuppa tea 🤗"):
            bot_response = chat_endpoint(user_input, employee_metadata, bool(audio))

            if bool(audio):
                st.markdown("#### Audio Response: \n")
                st.audio(bot_response['audio'])
            print (bot_response)
            print ()
            print ()
            summary = bot_response['answer']

            st.markdown("#### Answer: \n")
            st.markdown(summary)
