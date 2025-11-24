import streamlit as st
import requests
import base64
import io
import time
import json
from PIL import Image


# --- API Configuration ---
# NOTE: The API key is left empty as required. The Canvas environment will provide it at runtime.
API_KEY = "AIzaSyCRMH47PfEyXi3pehylBhcJpI2M8-WYck0" 
MODEL_NAME = "gemini-2.5-flash-preview-09-2025"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

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
    
    return "Failed to get a response after all retries.", [] # Should not be reached if logic is perfect

# --- Streamlit App UI and Logic ---

st.set_page_config(
    page_title="Cedrick Vision: Grounded Image Analyzer",
    layout="wide",
    initial_sidebar_state="auto"
)

# Custom CSS for a strong, modern look
st.markdown("""
<style>
    /* 1. Define the animation for gradient shift */
    @keyframes gradient_shift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* 2. Apply the animated background to the main app container */
    .stApp {
        /* Use a larger background size for the shift */
        background: linear-gradient(135deg, #1d2b64, #30507a, #1d2b64, #30507a);
        background-size: 400% 400%; 
        /* Apply the animation: 20s duration, smooth easing, infinite loop */
        animation: gradient_shift 20s ease infinite; 
        color: #ffffff;
        min-height: 100vh;
    }
    
    /* Header and Title Styling */
    h1 {
        color: #f7f7f7;
        text-align: center;
        margin-bottom: 0.2em;
        font-weight: 800;
        text-shadow: 2px 2px 5px rgba(0,0,0,0.3);
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
    
    /* Button Styling */
    .stButton button {
        background-color: #4CAF50; /* Green */
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
    
    /* Result Box (Grounded Text) */
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
        color: #1d2b64;
    }
    .source-list a {
        color: #30507a;
        text-decoration: none;
    }
    .source-list a:hover {
        text-decoration: underline;
    }

</style>
""", unsafe_allow_html=True)


def main():
    st.title("Cedrick Vision Image Analyzer")
    st.markdown("Use AI to analyze any image and fetch real-time context from the web.")
    st.caption("Model: Gemini 2.5 Flash with Google Search Grounding")
    
    st.markdown("---")

    # --- Input Section ---
    
    col_img, col_prompt = st.columns([1, 2])
    
    with col_img:
        uploaded_file = st.file_uploader(
            "Upload an Image",
            type=["png", "jpg", "jpeg"],
            key="image_uploader"
        )
        
    with col_prompt:
        prompt = st.text_area(
            "Ask a question about the image or describe what you want the AI to talk about:",
            height=150,
            placeholder="Describe the item, tell me its historical context, and find the current market price or comparable items.",
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
            analysis_text, sources = call_gemini_api_with_grounding(prompt, base64_data, mime_type)

        # --- Output Section ---
        
        st.markdown("<div class='analysis-output'>", unsafe_allow_html=True)
        st.subheader("🤖 Chatbot Analysis")
        st.markdown(analysis_text)
        
        if sources:
            st.markdown("<div class='source-list'>", unsafe_allow_html=True)
            st.markdown("**🌐 Sources from Google Search:**")
            for i, source in enumerate(sources):
                st.markdown(f"**{i+1}.** [{source['title']}]({source['uri']})")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            # If the grounding failed or the model chose not to use sources, this message is shown.
            st.caption("No external search results were used for grounding this response, or the model deemed the response sufficient without external data.")
            
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Optional: Display the image again in the output section
        st.subheader("Uploaded Image")
        img = Image.open(uploaded_file)
        # FIX: Replaced deprecated use_column_width with use_container_width
        st.sidebar.image(img, use_container_width=True)


if __name__ == "__main__":
    main()