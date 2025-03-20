import streamlit as st
import google.generativeai as genai
import os
import fitz  # PyMuPDF for text and color extraction
from dotenv import load_dotenv
import json
import re  # Import regex to clean AI output

def get_gemini_response(input):
    model = genai.GenerativeModel('gemini-1.5-pro-latest')  # Gemini 2 model
    response = model.generate_content(input, stream=False)  # Ensures full response
    return response.text

def input_pdf_text(uploaded_file):
    doc = fitz.open(stream=uploaded_file.getbuffer(), filetype="pdf")
    text = "\n".join([page.get_text("text") for page in doc])
    return text.strip()

def calculate_luminance(color):
    """Calculate luminance of an RGB color."""
    r = (color >> 16) & 0xFF
    g = (color >> 8) & 0xFF
    b = color & 0xFF
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255  # Normalize to [0,1] range

def detect_hidden_text(uploaded_file, contrast_threshold=0.1, font_size_threshold=3):
    """Detects hidden text based on contrast, opacity, and font size without saving the file."""
    doc = fitz.open(stream=uploaded_file.getbuffer(), filetype="pdf")
    hidden_words = []
    
    for page in doc:
        for text in page.get_text("dict")["blocks"]:
            if "lines" in text:
                for line in text["lines"]:
                    for span in line["spans"]:
                        text_color = span["color"]
                        bg_color = span.get("background", 16777215)  # Default to white
                        font_size = span["size"]
                        opacity = span.get("opacity", 1.0)  # Default opacity is 1.0 (fully visible)
                        
                        text_luminance = calculate_luminance(text_color)
                        bg_luminance = calculate_luminance(bg_color)
                        contrast_ratio = abs(text_luminance - bg_luminance)
                        
                        # Detect hidden text (low contrast, zero opacity, or tiny font size)
                        if contrast_ratio < contrast_threshold or opacity == 0 or font_size < font_size_threshold:
                            hidden_words.append(span["text"])
    
    return hidden_words

st.set_page_config(page_title="Jobfy - Your Career Assistant", layout="centered")

st.markdown(
    """
    <style>
        .stApp {
            background-color: #E3F2FD; /* Light blue background */
        }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🚀 JOBFY - AI Career Assistant")

tab1, tab2 = st.tabs(["📄 Resume Matcher", "🎓 Certification Recommender"])

with tab1:
    st.subheader("📄 Resume ATS Matcher")
    
    uploaded_file = st.file_uploader("Upload your resume (PDF)", type="pdf")
    job_description = st.text_area("Paste the Job Description")
    
    if st.button("Analyze Resume"):
        if uploaded_file and job_description:
            st.write("Processing... ⏳")
            
            # Detect hidden text without saving file
            hidden_texts = detect_hidden_text(uploaded_file)
            
            if len(hidden_texts) > 5:  # Flag if too many hidden words
                st.error("⚠️ Hidden text detected! This resume may be flagged as manipulated.")
                st.text_area("Detected Hidden Text", "\n".join(hidden_texts))
            else:
                # Proceed with ATS analysis
                resume_text = input_pdf_text(uploaded_file)
                input_prompt = f"""
                Act as an ATS (Applicant Tracking System) with expertise in software engineering, data science, and big data engineering.
                Your task:
                1. Analyze the resume and compare it with the job description.
                2. Assign a **matching percentage** based on JD.
                3. List **missing keywords** required for the role.
                4. Generate a **profile summary**.

                Resume:
                {resume_text}

                Job Description:
                {job_description}

                Return the response **strictly in JSON format**:

                {{
                  "JD Match": "XX%",
                  "MissingKeywords": ["keyword1", "keyword2"],
                  "Profile Summary": "Your profile summary goes here."
                }}
                """
                
                # Get AI response
                response_text = get_gemini_response(input_prompt)
                
                try:
                    cleaned_response = re.sub(r"```json|```", "", response_text).strip()
                    response_json = json.loads(cleaned_response)
                    
                    st.markdown("### Results")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**ATS Match Score:** {response_json['JD Match']}")
                        
                    with col2:
                        st.markdown(f"**Missing Keywords:** {', '.join(response_json['MissingKeywords'])}")
                        
                    st.markdown(f"**Profile Summary:** {response_json['Profile Summary']}")
                except json.JSONDecodeError:
                    st.error("AI response is not in valid JSON format. Please try again.")
                    st.text_area("Raw AI Response", response_text)
