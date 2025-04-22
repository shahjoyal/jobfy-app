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

def get_certifications(field):
    model = genai.GenerativeModel("gemini-1.5-pro")
    prompt = f"Suggest some relevant certifications with their descriptions and links to enhance a resume for a career in {field}. Return a JSON list with certification name, description, and link."
    response = model.generate_content(prompt)
    return response.text if response and response.text else "No recommendations found."

st.set_page_config(page_title="Jobfy - Your Career Assistant", layout="centered")

st.markdown(
    """
    <style>
        .stApp { background-color: #E3F2FD; }
        .glow { font-size: 24px; font-weight: bold; padding: 10px; border-radius: 10px; animation: glow 1.5s infinite alternate; }
        .gold { background: linear-gradient(45deg, #FFD700, #FFAA00); color: black; }
        .silver { background: linear-gradient(45deg, #C0C0C0, #A9A9A9); color: black; }
        .bronze { background: linear-gradient(45deg, #CD7F32, #8B4513); color: white; }
        .card { padding: 20px; border-radius: 12px; box-shadow: 4px 6px 15px rgba(0, 0, 0, 0.3); margin: 15px; transition: transform 0.3s; }
        .card:hover { transform: scale(1.05); }
        .card1 { background-color: #26C2EC; }
        .card2 { background-color: #F4CE0E; }
        .card3 { background-color: #F4CE0E; }
        .cert-card { background-color: #F4CE0E; }
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
            hidden_texts = detect_hidden_text(uploaded_file)
            
            if len(hidden_texts) > 5:
                st.error("⚠️ Hidden text detected! This resume may be flagged as manipulated.")
                st.text_area("Detected Hidden Text", "\n".join(hidden_texts))
            else:
                resume_text = input_pdf_text(uploaded_file)
                input_prompt = f"""
                Act as an Applicant tracking system. Analyze the resume and job description.
                Return the response strictly in JSON format:
                {{ "JD Match": "XX%", "MissingKeywords": ["keyword1", "keyword2"], "Profile Summary": "Summary here." }}
                """
                response_text = get_gemini_response(input_prompt)
                
                try:
                    cleaned_response = re.sub(r"```json|```", "", response_text).strip()
                    response_json = json.loads(cleaned_response)
                    
                    match_score = int(response_json["JD Match"].replace('%', '').strip())
                    color_class = "gold" if match_score >= 70 else "silver" if match_score >= 50 else "bronze"
                    
                    st.markdown(f"<div class='card glow {color_class} card1'>ATS Match Score: {response_json['JD Match']}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='card card2'>Missing Keywords: {', '.join(response_json['MissingKeywords'])}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='card card3'>Profile Summary: {response_json['Profile Summary']}</div>", unsafe_allow_html=True)
                except (json.JSONDecodeError, KeyError, ValueError):
                    st.error("AI response is not in valid JSON format. Please try again.")
                    st.text_area("Raw AI Response", response_text)

with tab2:
    st.subheader("🎓 Find Certifications to Boost Your Resume")
    field = st.text_input("Enter your field of interest:")
    
    if st.button("Get Recommendations"):
        if field:
            recommendations = get_certifications(field)
            try:
                cleaned_recommendations = re.sub(r"```json|```", "", recommendations).strip()
                recommendations_json = json.loads(cleaned_recommendations)
                certification_list = [f"<div class='card cert-card'><strong>{cert['name']}</strong><br>{cert['description']}<br><a href='{cert['link']}' target='_blank'>Access Here</a></div>" for cert in recommendations_json]
                st.markdown("".join(certification_list), unsafe_allow_html=True)
            except json.JSONDecodeError:
                st.error("AI response is not in valid JSON format. Please try again.")
                st.text_area("Raw AI Response", recommendations)
        else:
            st.warning("Please enter a field before getting recommendations.")
