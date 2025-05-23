import streamlit as st
import google.generativeai as genai
import os
import fitz  # PyMuPDF for text and color extraction
from dotenv import load_dotenv
import json
import re  # For cleaning AI output

# Function to get response from Gemini Flash model
def get_gemini_response(input):
    # Change the model initialization to use Gemini 2.0 Flash model
    model = genai.GenerativeModel('gemini-2.0-flash')  # Switching to the 'gemini-2.0-flash' model
    response = model.generate_content(input, stream=False)
    return response.text

# Function to extract text from PDF
def input_pdf_text(uploaded_file):
    doc = fitz.open(stream=uploaded_file.getbuffer(), filetype="pdf")
    text = "\n".join([page.get_text("text") for page in doc])
    return text.strip()

# Function to calculate luminance
def calculate_luminance(color):
    r = (color >> 16) & 0xFF
    g = (color >> 8) & 0xFF
    b = color & 0xFF
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255

# Function to detect hidden text in a PDF
def detect_hidden_text(uploaded_file, contrast_threshold=0.1, font_size_threshold=3):
    doc = fitz.open(stream=uploaded_file.getbuffer(), filetype="pdf")
    hidden_words = []
    
    for page in doc:
        for text in page.get_text("dict")["blocks"]:
            if "lines" in text:
                for line in text["lines"]:
                    for span in line["spans"]:
                        text_color = span["color"]
                        bg_color = span.get("background", 16777215)
                        font_size = span["size"]
                        opacity = span.get("opacity", 1.0)
                        
                        text_luminance = calculate_luminance(text_color)
                        bg_luminance = calculate_luminance(bg_color)
                        contrast_ratio = abs(text_luminance - bg_luminance)
                        
                        if contrast_ratio < contrast_threshold or opacity == 0 or font_size < font_size_threshold:
                            hidden_words.append(span["text"])
    
    return hidden_words

# Function to get certifications for a specific field
def get_certifications(field):
    model = genai.GenerativeModel("gemini-2.0-flash")  # Switching to the 'gemini-2.0-flash' model
    prompt = f"Suggest some relevant certifications with their descriptions and links to enhance a resume for a career in {field}. Return a JSON list with certification name, description, and link."
    response = model.generate_content(prompt)
    return response.text if response and response.text else "No recommendations found."

# Streamlit configuration and interface
st.set_page_config(page_title="Jobfy - Your Career Assistant", layout="centered")

st.markdown("""
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
""", unsafe_allow_html=True)

st.title("🚀 JOBFY")

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

                # 💡 Fixed prompt: injecting real resume and JD
                input_prompt = f"""
Act as an Applicant Tracking System (ATS). Analyze the given resume and job description thoroughly. Identify the key skills, experiences, and qualifications in both documents. Match the candidate's profile with the job requirements and provide a detailed compatibility score. Highlight strong matches, missing skills, and potential areas for improvement in the resume. Suggest specific keywords or phrases that can be added to the resume to increase the chances of getting shortlisted. Present your analysis in a clear and structured format.

Resume:
{resume_text}

Job Description:
{job_description}

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
                certification_list = [
                f"<div class='card cert-card'><strong>{cert.get('name', 'CERTIFICATE')}</strong><br>"
                f"{cert.get('description', 'No Description Available')}<br>"
                f"<a href='{cert.get('link', '#')}' target='_blank'>Access Here</a></div>"
                for cert in recommendations_json
                ]
                st.markdown("".join(certification_list), unsafe_allow_html=True)
            except json.JSONDecodeError:
                st.error("AI response is not in valid JSON format. Please try again.")
                st.text_area("Raw AI Response", recommendations)
        else:
            st.warning("Please enter a field before getting recommendations.")
