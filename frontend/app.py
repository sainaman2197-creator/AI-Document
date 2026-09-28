import io
import re
import time
import json
import requests
import streamlit as st
from PIL import Image, ImageDraw

# -------------------------------------------------------------------
# Page Configuration & Metadata
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Documents Analyser | Multi-Document Parser",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Aapka FastAPI Backend URLs
BACKEND_URL = "http://127.0.0.1:8000/extract/"
CHATBOT_URL = "http://127.0.0.1:8000/chatbot/ask"   # <-- naya AI chatbot endpoint
EXTRACT_FIELDS_URL = "http://127.0.0.1:8000/chatbot/extract_fields"  # <-- clean structured fields

# Session State Initialization
if "history" not in st.session_state:
    st.session_state.history = []
if "current_result" not in st.session_state:
    st.session_state.current_result = None
if "current_file_name" not in st.session_state:
    st.session_state.current_file_name = None
if "uploaded_image_bytes" not in st.session_state:
    st.session_state.uploaded_image_bytes = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_query" not in st.session_state:
    st.session_state.last_query = None
if "matched_fields" not in st.session_state:
    st.session_state.matched_fields = None
if "structured_fields" not in st.session_state:
    st.session_state.structured_fields = None

# -------------------------------------------------------------------
# Custom CSS & Glassmorphism Styling
# -------------------------------------------------------------------
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        background-color: #0F172A;
        color: #F8FAFC;
    }

    [data-testid="stSidebar"] {
        display: none !important;
    }

    /* App Header Container */
    .app-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 16px 24px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        margin-bottom: 24px;
        color: #ffffff;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    /* Left & Right sections take equal space to keep center balanced */
    .header-left, .header-right {
        flex: 1;
        display: flex;
        align-items: center;
    }

    .header-right {
        justify-content: flex-end;
    }

    /* Center Section */
    .header-center {
        flex: 2;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
    }

    /* App Title Styling */
    .app-title {
        font-size: 1.25rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        margin: 0;
        color: #f8fafc;
        background: linear-gradient(to right, #ffffff, #cbd5e1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Subtext / Version Tag */
    .engine-badge-sub {
        font-size: 0.75rem;
        color: #94a3b8;
        background: rgba(255, 255, 255, 0.05);
        padding: 3px 8px;
        border-radius: 6px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* Logo Icon Box */
    .logo-icon {
        background: rgba(59, 130, 246, 0.1);
        color: #60a5fa;
        padding: 8px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* Engine Online Status Badge */
    .engine-status {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.85rem;
        font-weight: 500;
        color: #4ade80;
        background: rgba(74, 222, 128, 0.1);
        padding: 6px 12px;
        border-radius: 20px;
        border: 1px solid rgba(74, 222, 128, 0.2);
    }

    .status-dot {
        width: 8px;
        height: 8px;
        background-color: #4ade80;
        border-radius: 50%;
        box-shadow: 0 0 8px #4ade80;
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { transform: scale(0.95); opacity: 0.8; }
        50% { transform: scale(1.1); opacity: 1; }
        100% { transform: scale(0.95); opacity: 0.8; }
    }

    .metric-card {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(51, 65, 85, 0.8);
        border-radius: 12px;
        padding: 1rem 1.25rem;
        backdrop-filter: blur(8px);
    }
    .metric-label {
        font-size: 0.75rem;
        color: #94A3B8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 1.125rem;
        color: #F8FAFC;
        font-weight: 700;
        margin-top: 0.25rem;
    }

    [data-testid="stFileUploadDropzone"] {
        border: 2px dashed rgba(51, 65, 85, 0.8) !important;
        background-color: rgba(30, 41, 59, 0.4) !important;
        border-radius: 16px !important;
        transition: all 0.3s ease;
    }
    [data-testid="stFileUploadDropzone"]:hover {
        border-color: rgba(37, 99, 235, 0.6) !important;
        background-color: rgba(30, 41, 59, 0.7) !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(30, 41, 59, 0.6);
        padding: 6px;
        border-radius: 12px;
        border: 1px solid rgba(51, 65, 85, 0.5);
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        border-radius: 8px;
        font-weight: 600;
        color: #94A3B8;
    }
    .stTabs [aria-selected="true"] {
        background-color: #334155 !important;
        color: #F8FAFC !important;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------
# Helper Functions: Dynamic Extraction & Processing
# -------------------------------------------------------------------
def classify_document(raw_text, backend_doc_type=""):
    text_upper = raw_text.upper() if raw_text else ""
    backend_upper = backend_doc_type.upper() if backend_doc_type else ""
    
    if "PASSPORT" in text_upper or "REPUBLIC OF INDIA" in text_upper or "P<IND" in text_upper or "PASSPORT" in backend_upper:
        return "Indian Passport"
    elif "INCOME TAX" in text_upper or "PERMANENT ACCOUNT NUMBER" in text_upper or "PAN" in backend_upper:
        return "PAN Card"
    elif "AADHAAR" in text_upper or "UNIQUE IDENTIFICATION" in text_upper or "AADHAAR" in backend_upper:
        return "Aadhaar Card"
    elif "DRIVING LICENCE" in text_upper or "DRIVING LICENSE" in text_upper or "DL" in backend_upper:
        return "Driving License"
    
    return backend_doc_type.title() if backend_doc_type else "General Document"

def extract_dynamic_fields(fields_input, raw_text=""):
    extracted_fields = []
    ignored_keys = {"status", "detected_type", "document_type", "raw_text", "message", "ocr_text_preview", "filename"}
    
    if isinstance(fields_input, list):
        for item in fields_input:
            if isinstance(item, dict):
                lbl = item.get("label", item.get("key", "Field"))
                val = item.get("value", item.get("text", ""))
                box = item.get("box_2d", item.get("bounding_box", None))
                
                if str(lbl).lower() in ignored_keys:
                    continue
                    
                if val and str(val).strip():
                    extracted_fields.append({
                        "label": str(lbl).replace("_", " ").title(), 
                        "value": str(val).strip(), 
                        "box_2d": box
                    })
                    
    elif isinstance(fields_input, dict):
        for k, v in fields_input.items():
            if str(k).lower() in ignored_keys:
                continue
                
            if isinstance(v, dict):
                val = v.get("value", v.get("text", ""))
                box = v.get("box_2d", v.get("bounding_box", None))
            else:
                val = str(v)
                box = None
                
            if val and str(val).strip():
                extracted_fields.append({
                    "label": str(k).replace("_", " ").title(), 
                    "value": str(val).strip(), 
                    "box_2d": box
                })

    if not extracted_fields and raw_text:
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
        for line in lines:
            if len(line) >= 3:
                extracted_fields.append({"label": "Detected Text", "value": line, "box_2d": None})
                break
        if not extracted_fields:
            extracted_fields.append({"label": "OCR Snippet", "value": raw_text[:100] + "...", "box_2d": None})

    return extracted_fields

def draw_bounding_boxes_on_image(image, extracted_fields):
    img_copy = image.copy().convert("RGB")
    draw = ImageDraw.Draw(img_copy)
    w, h = img_copy.size
    
    for item in extracted_fields:
        bbox = item.get("box_2d")
        if bbox and len(bbox) == 4:
            ymin_norm, xmin_norm, ymax_norm, xmax_norm = bbox
            
            if xmax_norm <= 1000 and ymax_norm <= 1000:
                xmin = int((xmin_norm / 1000.0) * w)
                ymin = int((ymin_norm / 1000.0) * h)
                xmax = int((xmax_norm / 1000.0) * w)
                ymax = int((ymax_norm / 1000.0) * h)
            else:
                xmin, ymin, xmax, ymax = int(xmin_norm), int(ymin_norm), int(xmax_norm), int(ymax_norm)
            
            draw.rectangle([xmin, ymin, xmax, ymax], outline="#00FF66", width=3)
            
    return img_copy

def get_ai_chatbot_response(user_query, raw_text, doc_type):
    """
    Calls the FastAPI /chatbot/ask endpoint (Gemini-powered) with the
    already-extracted raw_text, and returns a real AI-generated answer.
    This REPLACES the old rule-based keyword matching.
    """
    try:
        data = {
            "raw_text": raw_text or "",
            "query": user_query,
            "doc_type": doc_type or "generic",
        }
        response = requests.post(CHATBOT_URL, data=data, timeout=120)

        if response.status_code == 200:
            res = response.json()
            return res.get("ai_answer", "Could not get an answer from the AI.")
        else:
            return f"Chatbot backend error: HTTP {response.status_code} - {response.text}"

    except requests.exceptions.ConnectionError:
        return "❌ Connection Error: Could not reach the chatbot backend (`http://127.0.0.1:8000/chatbot/ask`). Make sure your FastAPI server is running and `chatbot.py` router is included in `main.py`."
    except Exception as ex:
        return f"Error while getting AI answer: {str(ex)}"

def get_structured_fields_from_backend(raw_text, doc_type):
    """
    Calls /chatbot/extract_fields to get clean, meaningful fields
    (Name, PAN Number, DOB, etc.) instead of raw noisy per-word OCR
    fragments.
    """
    try:
        data = {"raw_text": raw_text or "", "doc_type": doc_type or "generic"}
        response = requests.post(EXTRACT_FIELDS_URL, data=data, timeout=120)
        if response.status_code == 200:
            res = response.json()
            return res.get("fields", [])
        return []
    except Exception:
        return []

def find_matching_boxes(user_query, ai_answer, fields):
    """
    Purely for highlighting. Tries to find the AI's answer as a CONTIGUOUS
    sequence of OCR word-boxes (in the order OCR read them), so multi-word
    answers like "SATENDRA MISHRA" match only that exact occurrence - not
    every box that shares a word (e.g. "MISHRA" also appearing in
    "RAHUL MISHRA"). Falls back to single-word matching only if no
    sequential match is found.
    """
    answer_words = [w.lower() for w in re.findall(r'\w+', ai_answer) if len(w) > 1]
    if not answer_words:
        return []

    field_values = [str(f.get("value", "")).lower() for f in fields]
    n = len(answer_words)

    def words_equal(a, b):
        if a == b:
            return True
        if len(a) > 3 and len(b) > 3 and (a in b or b in a):
            return True
        return False

    # 1) Try exact contiguous sequence match first (best for names, numbers
    #    with multiple words/parts).
    if n >= 1:
        for i in range(len(field_values) - n + 1):
            window = field_values[i:i + n]
            if all(words_equal(window[j], answer_words[j]) for j in range(n)):
                return fields[i:i + n]

    # 2) Fallback: no exact sequence found (OCR splitting may differ from
    #    the answer). Match individual meaningful words, but require a
    #    fairly specific (longer) word to avoid over-matching common terms.
    stopwords = {
        "is", "the", "a", "an", "of", "on", "in", "to", "and", "what",
        "who", "this", "that", "please", "give", "me", "your", "you",
        "are", "as", "it", "for", "with", "does", "do", "can", "tell",
        "show", "answer", "based", "provided", "not", "no", "yes",
        "here", "was", "be", "has", "have", "will", "would", "should",
        "found", "value", "read", "says", "detail", "details",
    }
    specific_words = {w for w in answer_words if len(w) > 3 and w not in stopwords}
    if not specific_words:
        return []

    # Ambiguity guard: agar koi word document me ek se zyada jagah aata hai
    # (jaise "MISHRA" naam aur father's naam dono me), to use fallback me
    # match hi nahi karenge - warna galat jagah highlight ho jayega.
    value_counts = {}
    for v in field_values:
        value_counts[v] = value_counts.get(v, 0) + 1

    matches = []
    for field, val_lower in zip(fields, field_values):
        if val_lower in specific_words and value_counts.get(val_lower, 0) == 1:
            matches.append(field)
    return matches

# -------------------------------------------------------------------
# Header Navigation Component
# -------------------------------------------------------------------
st.markdown("""
    <header class="app-header">
        <!-- Left Side: Logo Icon -->
        <div class="header-left">
            <div class="logo-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                    <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
            </div>
        </div>
        <!-- Center: AI Documents Analyser -->
        <div class="header-center">
            <h1 class="app-title">AI Documents Analyser</h1>
            <span class="engine-badge-sub">v3.9 OCR Engine</span>
        </div>
        <!-- Right Side: Engine Online & Status -->
        <div class="header-right">
            <div class="engine-status">
                <span class="status-dot"></span> Engine Online
            </div>
        </div>
    </header>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------
# Main Layout Columns
# -------------------------------------------------------------------
left_col, right_col = st.columns([1, 1], gap="large")

with left_col:
    st.markdown("#### 1. Input Workspace")
    
    uploaded_file = st.file_uploader(
        "Upload source file",
        type=["pdf", "png", "jpg", "jpeg"],
        help="Supported formats: Images, Bills, Invoices, IDs",
        label_visibility="collapsed"
    )

    if uploaded_file is not None:
        file_size_mb = round(uploaded_file.size / (1024 * 1024), 2)
        file_type_str = uploaded_file.type.split("/")[-1].upper()
        
        st.session_state.uploaded_image_bytes = uploaded_file.getvalue()
        
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Filename</div><div class="metric-value" style="font-size: 0.95rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{uploaded_file.name}</div></div>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Format</div><div class="metric-value">{file_type_str}</div></div>', unsafe_allow_html=True)
        with m3:
            st.markdown(f'<div class="metric-card"><div class="metric-label">File Size</div><div class="metric-value">{file_size_mb} MB</div></div>', unsafe_allow_html=True)

        st.write("")
        
        with st.expander("👁️ Source Visual Canvas Preview", expanded=True):
            if uploaded_file.type.startswith("image"):
                image = Image.open(io.BytesIO(st.session_state.uploaded_image_bytes))

                # Agar chatbot me pehle se koi sawal poocha ja chuka hai aur
                # us result ke boxes maujood hain, to seedha isi original
                # image par highlight kar dein - koi alag copy image nahi
                # dikhani.
                boxes_for_preview = st.session_state.get("matched_fields")
                if boxes_for_preview:
                    image = draw_bounding_boxes_on_image(image, boxes_for_preview)
                    st.caption(f"Highlighted for: \"{st.session_state.last_query}\"")

                st.image(image, use_container_width=True)
            elif uploaded_file.type == "application/pdf":
                st.info("📄 PDF Document Loaded. Ready for analysis.")
        
        st.write("")
        analyze_btn = st.button("🚀 Run Text Detection & Extraction", type="primary", use_container_width=True)
        
        if analyze_btn:
            start_time = time.time()
            with st.spinner("Detecting text from image via OCR..."):
                try:
                    files = {"file": (uploaded_file.name, st.session_state.uploaded_image_bytes, uploaded_file.type)}
                    response = requests.post(BACKEND_URL, files=files, timeout=300)
                    latency = round(time.time() - start_time, 2)

                    if response.status_code == 200:
                        res = response.json()
                        st.session_state.current_result = res
                        st.session_state.current_file_name = uploaded_file.name
                        st.session_state.messages = []
                        st.session_state.last_query = None
                        st.session_state.matched_fields = None

                        # Naya step: raw OCR text se clean, meaningful fields
                        # nikalte hain (Name, PAN Number, DOB, etc.) - taaki
                        # UI me har noisy OCR word alag field jaisa na dikhe.
                        temp_doc_analysis = res.get("document_analysis", res)
                        temp_raw_text = temp_doc_analysis.get("raw_text", "")
                        temp_doc_type = temp_doc_analysis.get("document_type", "generic")
                        with st.spinner("Extracting clean fields..."):
                            st.session_state.structured_fields = get_structured_fields_from_backend(
                                temp_raw_text, temp_doc_type
                            )
                        
                        st.session_state.history.append({
                            "filename": uploaded_file.name,
                            "timestamp": time.strftime("%H:%M:%S"),
                            "latency": f"{latency}s",
                            "data": res
                        })
                        
                        st.toast(f"Text detected successfully in {latency}s!", icon="⚡")
                        st.rerun()
                    else:
                        st.error(f"Backend HTTP {response.status_code}: {response.text}")

                except requests.exceptions.ConnectionError:
                    st.error("❌ Connection Error: FastAPI backend (`http://127.0.0.1:8000`) se connect nahi ho pa raha hai.")
                except Exception as e:
                    st.error(f"Processing Error: {str(e)}")

with right_col:
    st.markdown("#### 2. Processed Insights & Detected Text")
    
    if st.session_state.current_result:
        res_tab1, res_tab2, res_tab3, res_tab4 = st.tabs([
            "📊 Extracted Fields", 
            "💬 Document Chatbot", 
            "💻 Raw JSON", 
            "📜 Session Audit"
        ])
        
        data_content = st.session_state.current_result
        doc_analysis = data_content.get("document_analysis", data_content)
        raw_fields = doc_analysis.get("fields", [])
        raw_text_val = doc_analysis.get("raw_text", "")
        backend_type_str = doc_analysis.get("document_type", "")
        doc_type = classify_document(raw_text_val, backend_type_str)
        extracted_fields = extract_dynamic_fields(raw_fields, raw_text_val)

        # TAB 1: RENDERED EXTRACTION
        with res_tab1:
            st.markdown(f"**Target File:** `{st.session_state.current_file_name}`")
            st.divider()

            if st.session_state.uploaded_image_bytes:
                # Agar user ne chatbot me kuch poocha hai, sirf uske answer se
                # related boxes highlight karein - warna saare words dikhayein.
                boxes_to_draw = (
                    st.session_state.matched_fields
                    if st.session_state.matched_fields is not None
                    else extracted_fields
                )
                box_title = f"🖼️ Document Copy with Bounding Boxes ({st.session_state.last_query})" if st.session_state.last_query else "🖼️ Document Copy with Bounding Boxes on Text"
                with st.expander(box_title, expanded=True):
                    try:
                        orig_img = Image.open(io.BytesIO(st.session_state.uploaded_image_bytes))
                        annotated_img = draw_bounding_boxes_on_image(orig_img, boxes_to_draw)
                        st.image(annotated_img, use_container_width=True, caption="Highlighted Text with Bounding Boxes")
                    except Exception as img_err:
                        st.warning(f"Could not render image bounding boxes: {img_err}")

            st.write("")

            col_meta1, col_meta2 = st.columns(2)
            with col_meta1:
                st.markdown(f'''
                    <div class="metric-card">
                        <div class="metric-label">Document Type</div>
                        <div class="metric-value" style="color: #60A5FA;">{doc_type}</div>
                    </div>
                ''', unsafe_allow_html=True)
            with col_meta2:
                st.markdown(f'''
                    <div class="metric-card">
                        <div class="metric-label">Engine Method</div>
                        <div class="metric-value" style="font-size: 0.9rem;">Tesseract OCR</div>
                    </div>
                ''', unsafe_allow_html=True)
            
            st.write("")
            st.markdown("##### 🔑 Detected Information & Fields")

            # Structured (AI-cleaned) fields dikhayein agar available hain -
            # warna purane raw OCR word-level fields par fallback karein.
            display_fields = st.session_state.structured_fields or extracted_fields

            if display_fields:
                grid_cols = st.columns(2)
                for idx, item in enumerate(display_fields):
                    label_name = item.get("label", f"Field {idx+1}")
                    val_text = item.get("value", "")

                    with grid_cols[idx % 2]:
                        st.markdown(f'''
                            <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(51, 65, 85, 0.8); border-left: 4px solid #2563EB; border-radius: 8px; padding: 0.85rem 1rem; margin-bottom: 0.75rem;">
                                <div style="font-size: 0.75rem; color: #94A3B8; font-weight: 600; text-transform: uppercase;">{label_name}</div>
                                <div style="font-size: 1rem; color: #F8FAFC; font-weight: 700; margin-top: 0.25rem;">{val_text}</div>
                            </div>
                        ''', unsafe_allow_html=True)
            else:
                st.warning("No structured fields found.")

            if raw_text_val:
                with st.expander("📄 View Full Detected Raw Text From Image", expanded=False):
                    st.text_area("Detected Text", value=raw_text_val, height=200, disabled=True)
            else:
                st.info("No text detected in this image.")
                
            st.divider()

        # TAB 2: DOCUMENT CHATBOT
        with res_tab2:
            st.markdown(f"##### 💬 Document Assistant ({doc_type})")
            st.caption("Ask questions directly about the detected text. Answers are generated by AI.")
            
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            if user_prompt := st.chat_input("Ask a question about this document..."):
                st.session_state.messages.append({"role": "user", "content": user_prompt})
                with st.chat_message("user"):
                    st.markdown(user_prompt)

                with st.spinner("Thinking..."):
                    # AI-generated answer (Gemini) using the already-extracted raw_text.
                    # No need to re-run OCR on every question.
                    bot_reply = get_ai_chatbot_response(user_prompt, raw_text_val, doc_type)
                    st.session_state.last_query = user_prompt
                    # Find which OCR boxes correspond to this answer, so the
                    # image preview can highlight just those (not every word).
                    st.session_state.matched_fields = find_matching_boxes(
                        user_prompt, bot_reply, extracted_fields
                    )

                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                with st.chat_message("assistant"):
                    st.markdown(bot_reply)
                
                st.rerun()

        # TAB 3: RAW JSON
        with res_tab3:
            st.json(st.session_state.current_result)
            
        # TAB 4: SESSION AUDIT
        with res_tab4:
            st.markdown("##### Recent Session Activity")
            if st.session_state.history:
                for idx, item in enumerate(reversed(st.session_state.history)):
                    st.caption(f"**{item['filename']}** | Processed at {item['timestamp']} ({item['latency']})")
                    st.divider()

    else:
        st.markdown("""
            <div style="background: rgba(30, 41, 59, 0.4); border: 1px dashed rgba(51, 65, 85, 0.8); border-radius: 16px; padding: 3rem 2rem; text-align: center; color: #94A3B8; margin-top: 2rem;">
                <p style="font-size: 1.1rem; margin-bottom: 0.5rem;">👉 Upload an image/document and click</p>
                <p style="font-weight: 600; color: #60A5FA;">Run Text Detection & Extraction</p>
                <p style="font-size: 0.9rem;">to see structured insights and analytics here.</p>
            </div>
        """, unsafe_allow_html=True)    