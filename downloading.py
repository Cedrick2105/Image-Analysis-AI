import streamlit as st
import requests
import base64
import io
import time
import json
from PIL import Image

# --- API Configuration ---
# NOTE: The API key is left empty as required. The Canvas environment will provide it at runtime.
API_KEY = "AIzaSyD1JUiM1zI_FO5rBBOGVttk-zrpflTd6KI" 
MODEL_NAME = "gemini-2.5-flash-preview-09-2025"
# FIX: Ensured the API_URL is correctly formatted with the full HTTPS path and model endpoint.
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

# --- Session State Initialization ---
# Initialize state variables to store results persistently
if 'analysis_text' not in st.session_state:
    st.session_state.analysis_text = ""
if 'sources' not in st.session_state:
    st.session_state.sources = []
if 'show_help' not in st.session_state:
    st.session_state.show_help = False
# NEW: State for controlling the visibility of the "About" guide
if 'show_about' not in st.session_state:
    st.session_state.show_about = False

# --- Helper Functions ---

def image_to_base64(img_file):
    """Converts Streamlit UploadedFile to a base64 string."""
    try:
        # Read the file content
        image_bytes = img_file.getvalue()
        # Encode to base64
        base64_encoded = base64.b64encode(image_bytes).decode("utf-8")
        return base64_encoded, img_file.type
    except Exception as e:
        st.error(f"Error converting image: {e}")
        return None, None

def call_gemini_api_with_grounding(prompt, base64_data, mime_type, max_retries=5):
    """
    Calls the Gemini API with image, text, and Google Search grounding, 
    implementing exponential backoff and comprehensive error handling.
    """
    
    # 1. Define the content payload (text + image)
    contents = [
        {
            "role": "user",
            "parts": [
                {"text": prompt},
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": base64_data
                    }
                }
            ]
        }
    ]

    # 2. Define the full request payload
    payload = {
        "contents": contents,
        # This is the key that enables Google Search grounding!
        "tools": [{"google_search": {}}],
        # System instruction to guide the model's persona and response
        "systemInstruction": {
            # MODIFIED: Changed the persona to a conversational chatbot AI
            "parts": [{"text": "You are a friendly and conversational chatbot AI designed to analyze images. Respond directly to the user's query about the image. Use Google Search grounding to incorporate real-time, relevant information into your chat response. Keep the tone helpful and engaging."}]
        }
    }

    headers = {'Content-Type': 'application/json'}
    
    for attempt in range(max_retries):
        try:
            # The actual API call
            response = requests.post(API_URL, headers=headers, data=json.dumps(payload))
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            
            # Safely attempt JSON decoding
            try:
                result = response.json()
            except json.JSONDecodeError:
                return f"API response error: Could not decode JSON response from API. Raw content: {response.text}", []
            
            candidate = result.get('candidates', [{}])[0]
            
            if candidate:
                text = candidate.get('content', {}).get('parts', [{}])[0].get('text', 'No text generated.')
                
                # Extract grounding sources
                sources = []
                grounding_metadata = candidate.get('groundingMetadata')
                if grounding_metadata and grounding_metadata.get('groundingAttributions'):
                    sources = [
                        {
                            'uri': attr.get('web', {}).get('uri'),
                            'title': attr.get('web', {}).get('title')
                        }
                        for attr in grounding_metadata['groundingAttributions']
                        if attr.get('web', {}).get('uri') and attr.get('web', {}).get('title')
                    ]
                
                return text, sources
            
            return "API response error: Could not find generated content.", []

        except requests.exceptions.HTTPError as e:
            if response.status_code == 403:
                # Specific handler for 403 Forbidden error (API Key issue)
                error_message = (
                    f"Authorization Error (403 Forbidden). "
                    f"This usually means the API key is not correctly provided by the environment "
                    f"or lacks necessary permissions. Please check your deployment setup. "
                    f"API Endpoint: {API_URL}" 
                )
                return error_message, []
                
            if response.status_code in [429, 500, 503] and attempt < max_retries - 1:
                # Handle rate limiting or server errors with exponential backoff
                sleep_time = 2 ** attempt
                time.sleep(sleep_time)
            else:
                return f"HTTP Error after max retries: {e}", []
        
        except requests.exceptions.RequestException as e:
            # Handle general network/connectivity errors (DNS, timeout, connection refused, etc.)
            if attempt < max_retries - 1:
                sleep_time = 2 ** attempt
                time.sleep(sleep_time)
            else:
                return f"Network/Connection Error after max retries: {e}", []
        
        except Exception as e:
            return f"An unexpected error occurred: {e}", []
    
    return "Failed to get a response after all retries.", []

def copy_to_clipboard_js(text):
    """
    Injects JavaScript to copy text to clipboard.
    This is necessary because Python code runs on the server and cannot access 
    the client's clipboard directly.
    """
    # Robustly escape quotes and newlines for the JavaScript string
    safe_text = text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    
    js_code = f"""
    <script>
        function copyText() {{
            navigator.clipboard.writeText("{safe_text}").then(function() {{
                // Update a UI element to confirm copy (using st.toast for Streamlit-native feedback)
            }}, function(err) {{
                console.error('Could not copy text: ', err);
            }});
        }}
        copyText();
    </script>
    """
    st.markdown(js_code, unsafe_allow_html=True)


# --- Streamlit App UI and Logic ---

st.set_page_config(
    page_title="Cedrick Vision: Grounded Image Analyzer",
    layout="wide",
    initial_sidebar_state="auto"
)

# Custom CSS for a strong, modern look
st.markdown("""
<style>
    /* 1. Define the animation for gradient shift (Background) */
    @keyframes gradient_shift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* 2. Define the animation for the Title (Right to Left) */
    @keyframes slide_left {
        0% {
            transform: translateX(100%); /* Start off-screen right */
            opacity: 0;
        }
        10% {
            opacity: 1;
        }
        90% {
            opacity: 1;
        }
        100% {
            transform: translateX(-100%); /* End off-screen left */
            opacity: 0;
        }
    }

    /* 3. Apply the animated background to the main app container */
    .stApp {
        background: linear-gradient(135deg, #1d2b64, #30507a, #1d2b64, #30507a);
        background-size: 400% 400%; 
        animation: gradient_shift 10s ease infinite; 
        color: #ffffff;
        min-height: 100vh;
    }
    
    /* Header and Title Styling with Animation */
    h1 {
        color: #f7f7f7;
        text-align: center;
        margin-bottom: 0.2em;
        font-weight: 800;
        text-shadow: 2px 2px 5px rgba(0,0,0,0.3);
        
        /* NEW: Animation Properties */
        white-space: nowrap;       /* Force text to stay on one line */
        overflow: visible;         /* Allow it to move outside its box */
        
    }
    
    /* Hover effect to pause the title so users can read it easily if they want */
    h1:hover {
        animation-play-state: paused;
        cursor: default;
    }
    
    /* Main Content Card (Input/Output Area) */
    .stVerticalBlock {
        background-color: rgba(255, 255, 255, 0.08);
        padding: 30px;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
        margin-top: 20px;
    }

    /* Input Labels and Text Area */
    label, .stTextInput > div > div > input {
        color: #f7f7f7 !important;
    }
    .stTextArea label {
        color: #f7f7f7 !important;
    }
    
    /* Global Button Styling (Applies to main Analyze button) */
    .stButton button {
        background-color: #4CAF50; /* Primary Green */
        color: white;
        font-weight: bold;
        border: none;
        padding: 10px 20px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        transition-duration: 0.4s;
        cursor: pointer;
        border-radius: 8px;
    }
    .stButton button:hover {
        background-color: #45a049;
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
    }
    
    /* Styling for the File Uploader Button */
    div[data-testid="stFileUploader"] button {
        background-color: #3CB371; 
        color: white;
        font-weight: bold;
        border: none;
        border-radius: 8px;
        transition-duration: 0.4s;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
    }
    div[data-testid="stFileUploader"] button:hover {
        background-color: #4CAF50; 
    }

    /* Navigation Buttons Styling */
    div[data-testid="stHorizontalBlock"] > div:nth-child(1) .stButton button,
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) .stButton button,
    div[data-testid="stHorizontalBlock"] > div:nth-child(3) .stButton button,
    div[data-testid="stHorizontalBlock"] > div:nth-child(4) .stButton button {
        background-color: #30507a; 
        border: 1px solid #1d2b64;
    }

    div[data-testid="stHorizontalBlock"] > div:nth-child(1) .stButton button:hover,
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) .stButton button:hover,
    div[data-testid="stHorizontalBlock"] > div:nth-child(3) .stButton button:hover,
    div[data-testid="stHorizontalBlock"] > div:nth-child(4) .stButton button:hover {
        background-color: #1d2b64; 
    }

    /* Result Box */
    .analysis-output {
        background-color: rgba(255, 255, 255, 0.95);
        color: #1d2b64;
        padding: 20px;
        border-radius: 10px;
        margin-top: 15px;
        border-left: 5px solid #4CAF50;
    }
    .analysis-output h3 {
        color: #1d2b64;
    }
    
    /* Sources/Citations */
    .source-list {
        font-size: 0.85em;
        padding: 10px;
        border-top: 1px solid #ccc;
        margin-top: 10px;
        color: blue;
    }
    .source-list a {
        color: green;
        text-decoration: none;
    }
    .source-list a:hover {
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)

def main():
    st.title("🧠 Image Analyzer AI")
    st.markdown("Use AI to analyze any image and fetch real-time context from the web.")
    st.caption("Model: Gemini 2.5 Flash with Google Search Grounding")
   
    if not st.session_state.show_help and not st.session_state.show_about:
        col_img, col_prompt = st.columns([1, 2])
        
        with col_img:
            uploaded_file = st.file_uploader(
                "Upload an Image",
                type=["png", "jpg", "jpeg"],
                key="image_uploader"
            )
            # Optional: Display the image again in the output section
            if uploaded_file:
                st.subheader("Uploaded Image Preview")
                img = Image.open(uploaded_file)
                st.image(img, use_container_width=True)
            else:
                # Define uploaded_file as None if not uploaded so it's accessible outside the if block
                uploaded_file = None
            
        with col_prompt:
            prompt = st.text_area(
                "Ask a question about the image or describe what you want the AI to talk about:",
                height=150,
                value="Describe the item, tell me its historical context, and find the current market price or comparable items.",
                key="prompt_input"
            )
            
        st.markdown("---")
        
        if st.button("🚀 Analyze Image & Get Web Context"):
            if not uploaded_file:
                st.error("Please upload an image to start the analysis.")
                return
            
            if not prompt.strip():
                st.error("Please enter a prompt or question for the AI.")
                return

            with st.spinner("Analyzing image, searching the web, and generating a grounded report..."):
                
                # 1. Convert image to base64
                base64_data, mime_type = image_to_base64(uploaded_file)
                
                if not base64_data:
                    return

                # 2. Call the Gemini API with image and prompt
                # Store results in session state
                st.session_state.analysis_text, st.session_state.sources = call_gemini_api_with_grounding(prompt, base64_data, mime_type)

        # --- Output Section (Hidden if Help or About is active) ---
        # Only display output if analysis text is available in session state
        if st.session_state.analysis_text:
            st.markdown("<div class='analysis-output'>", unsafe_allow_html=True)
            st.subheader("🤖 Chatbot Analysis")
            st.markdown(st.session_state.analysis_text) # Display text from session state
            
            if st.session_state.sources:
                st.markdown("<div class='source-list'>", unsafe_allow_html=True)
                st.markdown("**🌐 Sources from Google Search:**")
                for i, source in enumerate(st.session_state.sources):
                    st.markdown(f"**{i+1}.** [{source['title']}]({source['uri']})")
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                # If the grounding failed or the model chose not to use sources, this message is shown.
                st.caption("No external search results were used for grounding this response, or the model deemed the response sufficient without external data.")
                
            st.markdown("</div>", unsafe_allow_html=True)
            
    # --- Navigation Bar ---
    st.markdown("---")
    # Only show Next Steps title when not in a guide view
    if not st.session_state.show_help and not st.session_state.show_about:
        st.markdown("### Other information ")
    
    col_nav1, col_nav2, col_nav3, col_nav4 = st.columns(4)
    
    with col_nav1:
        # NOTE: This button is always visible to allow navigation back to the main app view
        if st.button("🔄 Refresh", use_container_width=True, key="nav_new_analysis",help="Refresh the AI for image analysis"):
            # Clear state and rerun
            st.session_state.analysis_text = ""
            st.session_state.sources = []
            st.session_state.show_help = False
            st.session_state.show_about = False
            st.rerun()

    with col_nav2:
        # 🔗 Copy Text button logic
        is_text_available = bool(st.session_state.analysis_text) and not st.session_state.show_help and not st.session_state.show_about
        if st.button("🔗 Copy Text", use_container_width=True, key="nav_copy_text", disabled=not is_text_available, help="Copies the full analysis text to your clipboard."):
            copy_to_clipboard_js(st.session_state.analysis_text)
            st.toast("Analysis text copied to clipboard!", icon="📋")

    with col_nav3:
        # ❓ Get Help button logic
        button_label = "❌ Close Help" if st.session_state.show_help else "❓ Get Help"
        if st.button(button_label, use_container_width=True, key="nav_help", help="Opens or closes the Quick Start guide."):
            st.session_state.show_help = not st.session_state.show_help
            if st.session_state.show_help:
                st.toast("Opening Help Documentation...", icon="💡")
            # Ensure only one guide is open at a time
            st.session_state.show_about = False
            
    with col_nav4:
        # ℹ️ About This App button logic
        button_label = "❌ Close About" if st.session_state.show_about else "ℹ️ About This App"
        if st.button(button_label, use_container_width=True, key="nav_about", help="Learn about the technology powering this application."):
            st.session_state.show_about = not st.session_state.show_about
            if st.session_state.show_about:
                st.toast("Opening About Information...", icon="ℹ️")
            # Ensure only one guide is open at a time
            st.session_state.show_help = False
            
    # --- Guide Content Display ---

    # Display ONLY the Help guide if requested
    if st.session_state.show_help:
        st.markdown("---")
        
        # Friendly opening message from the assistant
        st.subheader("🤖 Quick Start Guide")
        st.info("Hello there! I'm your AI assistant for the Grounded Image Analyzer. Here are the three easy steps to get a powerful, web-grounded analysis of your image:")
        
        # Use columns to present the steps horizontally
        col_help1, col_help2, col_help3 = st.columns(3)
        
        with col_help1:
            st.markdown("### 1. ⬆️ Upload")
            st.markdown("Use the **Upload an Image** file picker (on the left) to select a JPEG or PNG file.")
            
        with col_help2:
            st.markdown("### 2. 📝 Prompt")
            st.markdown("Ask a specific question about the image (e.g., historical context, current value, identification, etc.).")
            
        with col_help3:
            st.markdown("### 3. 🚀 Analyze")
            st.markdown("Click **🚀 Analyze Image** to start the Gemini model, which also performs a live Google Search for grounding.")
            
        st.markdown("---")
        
    # Display ONLY the About guide if requested
    elif st.session_state.show_about:
        st.markdown("---")
        
        st.subheader("💡 About Cedrick Vision")
        st.info("This application is a demonstration of powerful multimodal AI and real-time information retrieval.")
        
        col_about1, col_about2, col_about3,col_about4 = st.columns(4)
        
        with col_about1:
            st.markdown("### 🧠 AI Model")
            st.markdown("**Gemini 2.5 Flash** is used for multimodal analysis, allowing it to interpret both the visual data (the image) and the text query.")
            
        with col_about2:
            st.markdown("### 🌐 Grounding")
            st.markdown("**Google Search Grounding** is enabled via the API, ensuring that the AI's response is backed by current, real-time web information and citations.")
            
        with col_about3:
            st.markdown("### 🛠️ Framework")
            st.markdown("The interactive user interface is built entirely using **Streamlit**, a Python library designed for creating data applications quickly.")
        
        
        with col_about4:
            st.markdown("### 📞 Communication")
            st.markdown("Phone:0796286762")
            st.markdown("Email:sangwaineza2@gmail.com")
            st.markdown("YouTube:Cedrick ETE engineer")    
        st.markdown("---")
    # --- END NAVIGATION BAR ---


if __name__ == "__main__":
    main()