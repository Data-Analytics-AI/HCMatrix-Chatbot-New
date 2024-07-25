
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

    user_input = st.text_area("Enter query here:")

    recorded_audio = None

    def audio_recorder_callback(audio_frame):
        nonlocal recorded_audio
        recorded_audio = audio_frame.to_ndarray()

    webrtc_ctx = webrtc_streamer(
        key="audio",
        mode=WebRtcMode.SENDONLY,
        client_settings=ClientSettings(
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={"audio": True, "video": False},
        ),
        audio_frame_callback=audio_recorder_callback,
        async_processing=True,
    )

    employee_metadata = {
        "departement_id": "43",
        "role_id": "323",
        "group_id": "54",
        "company_id": company_id,
        "id": employee_id
    }

    if st.button("Send"):
        with st.spinner("Querying the model for the best answer... Sip a cuppa tea 🤗"):
            if recorded_audio is not None:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio_file:
                    temp_audio_file.write(recorded_audio)
                    temp_audio_file.flush()
                    print (temp_audio_file.name)
                    print ()
                    bot_response = chat_endpoint(user_input, employee_metadata, temp_audio_file.name)
            else:
                bot_response = chat_endpoint(user_input, employee_metadata)

            bot_response = chat_endpoint(user_input, employee_metadata)
            print (bot_response)
            print ()
            print ()
            summary = bot_response['answer']

            st.markdown("#### Answer: \n")
            st.markdown(summary)

            if st.button("Copy to Clipboard"):
                pyperclip.copy(bot_response)
