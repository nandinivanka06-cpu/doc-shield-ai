from flask import Flask, render_template, request, jsonify, send_file
import os
import sqlite3
import re
from datetime import datetime
from werkzeug.utils import secure_filename

import pytesseract
from PIL import Image, ImageStat, ImageFilter

# PDF generation
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER


# =========================================================
# FLASK APPLICATION
# =========================================================

app = Flask(__name__)


# =========================================================
# TESSERACT CONFIGURATION
# =========================================================

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


# =========================================================
# FOLDERS
# =========================================================

UPLOAD_FOLDER = "uploads"
REPORT_FOLDER = "reports"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)


# =========================================================
# DATABASE
# =========================================================

DATABASE = "docshield.db"


def init_database():

    conn = sqlite3.connect(DATABASE)

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scans (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            filename TEXT,

            risk_score INTEGER,

            status TEXT,

            reasons TEXT,

            extracted_text TEXT,

            scan_time TEXT

        )
    """)

    conn.commit()
    conn.close()


init_database()


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    return render_template("index.html")


# =========================================================
# HELPER - RISK CLASSIFICATION
# =========================================================

def classify_risk(score):

    if score <= 30:

        return "LOW RISK - Document appears normal"

    elif score <= 60:

        return "MEDIUM RISK - Needs Review"

    else:

        return "HIGH RISK - Suspicious Document"


# =========================================================
# HELPER - SAFE TEXT
# =========================================================

def clean_text(text):

    if not text:

        return ""

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


# =========================================================
# DOCUMENT TYPE DETECTION
# =========================================================

def detect_document_type(text):

    text_lower = text.lower()

    document_types = {

        "Aadhaar / Identity Document": [
            "aadhaar",
            "uidai",
            "government of india",
            "unique identification"
        ],

        "PAN Card": [
            "income tax department",
            "permanent account number",
            "pan"
        ],

        "Driving Licence": [
            "driving licence",
            "driving license",
            "transport department",
            "dl no"
        ],

        "Passport": [
            "passport",
            "republic of india",
            "nationality"
        ],

        "Educational Certificate": [
            "certificate",
            "university",
            "college",
            "degree",
            "marks",
            "examination"
        ]

    }

    for document_type, keywords in document_types.items():

        matched = 0

        for keyword in keywords:

            if keyword in text_lower:

                matched += 1

        if matched >= 2:

            return document_type

    return "General Document"


# =========================================================
# FIELD EXTRACTION
# =========================================================

def extract_fields(text):

    fields = {

        "name": "Not detected",

        "document_number": "Not detected",

        "date": "Not detected"

    }

    if not text:

        return fields


    # -----------------------------------------------------
    # NAME
    # -----------------------------------------------------

    name_patterns = [

        r"name\s*[:\-]\s*([A-Za-z .]{3,60})",

        r"name\s+([A-Za-z .]{3,60})"

    ]

    for pattern in name_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            fields["name"] = (
                match.group(1)
                .strip()
            )

            break


    # -----------------------------------------------------
    # DOCUMENT NUMBER
    # -----------------------------------------------------

    number_patterns = [

        r"\b\d{4}\s\d{4}\s\d{4}\b",

        r"\b[A-Z]{5}\d{4}[A-Z]\b",

        r"\b[A-Z]{2}\d{2}\s?\d{4,12}\b",

        r"\b[A-Z0-9]{8,16}\b"

    ]

    for pattern in number_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            fields["document_number"] = (
                match.group(0)
            )

            break


    # -----------------------------------------------------
    # DATE
    # -----------------------------------------------------

    date_patterns = [

        r"\b\d{2}[/-]\d{2}[/-]\d{4}\b",

        r"\b\d{2}[/-]\d{2}[/-]\d{2}\b",

        r"\b\d{4}[/-]\d{2}[/-]\d{2}\b"

    ]

    for pattern in date_patterns:

        match = re.search(
            pattern,
            text
        )

        if match:

            fields["date"] = (
                match.group(0)
            )

            break


    return fields


# =========================================================
# OCR CONFIDENCE ANALYSIS
# =========================================================

def analyze_ocr_confidence(image):

    try:

        data = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT
        )

        confidences = []

        for value in data["conf"]:

            try:

                confidence = float(value)

                if confidence >= 0:

                    confidences.append(
                        confidence
                    )

            except:

                pass


        if not confidences:

            return 0


        average_confidence = (
            sum(confidences)
            / len(confidences)
        )

        return round(
            average_confidence,
            2
        )

    except Exception:

        return 0


# =========================================================
# IMAGE QUALITY ANALYSIS
# =========================================================

def analyze_image_quality(image):

    width, height = image.size

    megapixels = (
        width * height
    ) / 1000000


    # -----------------------------------------------------
    # RESOLUTION
    # -----------------------------------------------------

    if width < 300 or height < 200:

        resolution_status = (
            "⚠️ Review"
        )

    elif width < 800 or height < 500:

        resolution_status = (
            "⚠️ Moderate"
        )

    else:

        resolution_status = (
            "✅ Good"
        )


    # -----------------------------------------------------
    # BRIGHTNESS
    # -----------------------------------------------------

    try:

        grayscale = image.convert(
            "L"
        )

        brightness = ImageStat.Stat(
            grayscale
        ).mean[0]

    except:

        brightness = 128


    if brightness < 40:

        brightness_status = (
            "⚠️ Too dark"
        )

    elif brightness > 225:

        brightness_status = (
            "⚠️ Overexposed"
        )

    else:

        brightness_status = (
            "✅ Normal"
        )


    # -----------------------------------------------------
    # CONTRAST
    # -----------------------------------------------------

    try:

        contrast = ImageStat.Stat(
            grayscale
        ).stddev[0]

    except:

        contrast = 0


    if contrast < 20:

        contrast_status = (
            "⚠️ Low contrast"
        )

    else:

        contrast_status = (
            "✅ Good contrast"
        )


    return {

        "width": width,

        "height": height,

        "megapixels":
            round(
                megapixels,
                2
            ),

        "resolution":
            resolution_status,

        "brightness":
            brightness_status,

        "contrast":
            contrast_status,

        "brightness_value":
            round(
                brightness,
                2
            ),

        "contrast_value":
            round(
                contrast,
                2
            )

    }


# =========================================================
# TEXT CONSISTENCY ANALYSIS
# =========================================================

def analyze_text_consistency(
    text,
    fields
):

    issues = []

    if not text:

        return issues


    # -----------------------------------------------------
    # EXCESSIVE SPECIAL CHARACTERS
    # -----------------------------------------------------

    characters = len(text)

    if characters > 20:

        special_characters = len(
            re.findall(
                r"[^A-Za-z0-9\s.,:/()\-]",
                text
            )
        )

        ratio = (
            special_characters /
            characters
        )

        if ratio > 0.20:

            issues.append(
                "Unusually high number of special characters detected"
            )


    # -----------------------------------------------------
    # REPEATED TEXT
    # -----------------------------------------------------

    words = text.lower().split()

    if len(words) > 20:

        unique_words = set(words)

        repetition_ratio = (
            len(unique_words) /
            len(words)
        )

        if repetition_ratio < 0.30:

            issues.append(
                "High text repetition detected"
            )


    # -----------------------------------------------------
    # FIELD COMPLETENESS
    # -----------------------------------------------------

    missing = []

    for key, value in fields.items():

        if value == "Not detected":

            missing.append(key)


    if len(missing) >= 2:

        issues.append(
            "Multiple expected document fields could not be identified"
        )


    return issues


# =========================================================
# SUSPICIOUS CONTENT ANALYSIS
# =========================================================

def analyze_suspicious_content(text):

    suspicious_words = [

        "fake",

        "dummy",

        "sample",

        "testing",

        "software testing",

        "not a real",

        "for testing only",

        "demo document",

        "test document",

        "invalid document",

        "mock document"

    ]

    detected = []

    text_lower = text.lower()


    for word in suspicious_words:

        if word in text_lower:

            detected.append(
                word
            )


    return detected


# =========================================================
# IMAGE INTEGRITY ANALYSIS
# =========================================================

def analyze_image_integrity(image):

    try:

        image_copy = image.copy()

        image_copy.verify()

        return {

            "status":
                "✅ Passed",

            "message":
                "Image file integrity check completed."

        }

    except Exception:

        return {

            "status":
                "⚠️ Review",

            "message":
                "Image integrity requires manual review."

        }


# =========================================================
# DOCUMENT STRUCTURE ANALYSIS
# =========================================================

def analyze_document_structure(
    extension,
    text,
    document_type
):

    issues = []


    if extension not in [
        ".jpg",
        ".jpeg",
        ".png",
        ".pdf"
    ]:

        issues.append(
            "Unsupported document format"
        )


    if not text:

        issues.append(
            "No readable document content was detected"
        )


    if document_type == "General Document":

        if len(text) < 30:

            issues.append(
                "Insufficient recognizable document information"
            )


    if issues:

        return (
            "⚠️ Review",
            issues
        )


    return (
        "✅ Passed",
        []
    )


# =========================================================
# DOCUMENT VERIFICATION
# =========================================================

@app.route(
    "/verify",
    methods=["POST"]
)
def verify():

    # -----------------------------------------------------
    # CHECK FILE
    # -----------------------------------------------------

    if "document" not in request.files:

        return jsonify({

            "error":
                "No document uploaded"

        }), 400


    file = request.files["document"]


    if file.filename == "":

        return jsonify({

            "error":
                "No file selected"

        }), 400


    # -----------------------------------------------------
    # SECURE FILE NAME
    # -----------------------------------------------------

    filename = secure_filename(
        file.filename
    )


    # Prevent empty filename

    if not filename:

        return jsonify({

            "error":
                "Invalid file name"

        }), 400


    filepath = os.path.join(

        app.config[
            "UPLOAD_FOLDER"
        ],

        filename

    )


    file.save(filepath)


    # =====================================================
    # INITIAL VALUES
    # =====================================================

    score = 0

    reasons = []

    extracted_text = ""

    ocr_status = "⚠️ Review"

    structure_status = "⚠️ Review"

    image_status = "⚠️ Review"

    text_status = "⚠️ Review"

    tampering_status = "⚠️ Review"


    document_type = "Unknown"

    fields = {

        "name": "Not detected",

        "document_number":
            "Not detected",

        "date":
            "Not detected"

    }


    ocr_confidence = 0

    image_details = {

        "width": 0,

        "height": 0,

        "megapixels": 0,

        "resolution":
            "⚠️ Review",

        "brightness":
            "⚠️ Review",

        "contrast":
            "⚠️ Review"

    }


    # =====================================================
    # FILE TYPE
    # =====================================================

    allowed_extensions = [

        ".jpg",

        ".jpeg",

        ".png",

        ".pdf"

    ]


    extension = os.path.splitext(
        filename
    )[1].lower()


    if extension in allowed_extensions:

        structure_status = "✅ Passed"

        score += 5

    else:

        structure_status = "⚠️ Review"

        score += 25

        reasons.append(
            "Unsupported document format"
        )


    # =====================================================
    # FILE SIZE
    # =====================================================

    file_size = os.path.getsize(
        filepath
    )


    if file_size < 20 * 1024:

        score += 15

        reasons.append(
            "Document file size is unusually small"
        )

    elif file_size < 50 * 1024:

        score += 8

        reasons.append(
            "Document file size is relatively small"
        )

    else:

        score += 2


    # =====================================================
    # IMAGE PROCESSING
    # =====================================================

    if extension in [
        ".jpg",
        ".jpeg",
        ".png"
    ]:

        try:

            image = Image.open(
                filepath
            )

            image_details = analyze_image_quality(
                    image
                )


            # ---------------------------------------------
            # RESOLUTION
            # ---------------------------------------------

            width = image_details[
                "width"
            ]

            height = image_details[
                "height"
            ]


            if width < 300 or height < 200:

                score += 15

                reasons.append(
                    "Image resolution is unusually low"
                )

                image_status = "⚠️ Review"

            elif width < 800 or height < 500:

                score += 5

                reasons.append(
                    "Image resolution is moderate"
                )

                image_status = "⚠️ Moderate"

            else:

                score += 2

                image_status = "✅ Passed"


            # ---------------------------------------------
            # BRIGHTNESS
            # ---------------------------------------------

            brightness = image_details[
                    "brightness_value"
                ]


            if brightness < 40:

                score += 8

                reasons.append(
                    "Image appears unusually dark"
                )

            elif brightness > 225:

                score += 8

                reasons.append(
                    "Image appears overexposed"
                )


            # ---------------------------------------------
            # CONTRAST
            # ---------------------------------------------

            contrast = image_details[
                    "contrast_value"
                ]


            if contrast < 20:

                score += 5

                reasons.append(
                    "Image has low visual contrast"
                )


        except Exception as error:

            print(
                "Image Analysis Error:",
                error
            )

            score += 10

            image_status = "⚠️ Review"

            reasons.append(
                "Image could not be fully analysed"
            )


    elif extension == ".pdf":

        image_status = "⚠️ Review"

        score += 3

        reasons.append(
            "Advanced image analysis is limited for PDF files"
        )


    # =====================================================
    # OCR
    # =====================================================

    if extension in [
        ".jpg",
        ".jpeg",
        ".png"
    ]:

        try:

            image = Image.open(
                filepath
            )


            # ---------------------------------------------
            # OCR
            # ---------------------------------------------

            extracted_text = pytesseract.image_to_string(
                    image
                ).strip()


            # ---------------------------------------------
            # OCR CONFIDENCE
            # ---------------------------------------------

            ocr_confidence = analyze_ocr_confidence(
                    image
                )


            if extracted_text:

                if ocr_confidence >= 70:

                    ocr_status = "✅ Passed"

                    score += 2

                elif ocr_confidence >= 45:

                    ocr_status = "⚠️ Moderate"

                    score += 7

                    reasons.append(
                        "OCR confidence is moderate"
                    )

                else:

                    ocr_status = "⚠️ Review"

                    score += 12

                    reasons.append(
                        "OCR confidence is low"
                    )

            else:

                ocr_status = "⚠️ Review"

                score += 15

                reasons.append(
                    "No readable text detected by OCR"
                )


        except Exception as error:

            print(
                "OCR Error:",
                error
            )

            ocr_status = "⚠️ Review"

            score += 15

            reasons.append(
                "OCR could not process the document"
            )


    elif extension == ".pdf":

        ocr_status = "⚠️ Review"

        score += 5

        reasons.append(
            "OCR text extraction is currently available for image documents"
        )


    # =====================================================
    # NORMALIZE TEXT
    # =====================================================

    extracted_text = clean_text(
            extracted_text
        )


    # =====================================================
    # DOCUMENT TYPE
    # =====================================================

    document_type = detect_document_type(
            extracted_text
        )


    # =====================================================
    # FIELD EXTRACTION
    # =====================================================

    fields = extract_fields(
            extracted_text
        )


    # =====================================================
    # DOCUMENT STRUCTURE
    # =====================================================

    structure_status, structure_issues = \
        analyze_document_structure(

            extension,

            extracted_text,

            document_type

        )


    for issue in structure_issues:

        if issue not in reasons:

            reasons.append(
                issue
            )

            score += 5


    # =====================================================
    # TEXT CONSISTENCY
    # =====================================================

    consistency_issues = analyze_text_consistency(

            extracted_text,

            fields

        )


    if consistency_issues:

        text_status = "⚠️ Review"

        score += (
            5 *
            len(consistency_issues)
        )

        for issue in consistency_issues:

            if issue not in reasons:

                reasons.append(
                    issue
                )

    else:

        if extracted_text:

            text_status = "✅ Passed"

            score += 2

        else:

            text_status = "⚠️ Review"


    # =====================================================
    # SUSPICIOUS TEXT
    # =====================================================

    detected_words = analyze_suspicious_content(
            extracted_text
        )


    if detected_words:

        score += min(
            20,
            5 * len(
                detected_words
            )
        )

        reasons.append(

            "Suspicious text detected: "
            +
            ", ".join(
                detected_words
            )

        )

        text_status = "⚠️ Review"


    # =====================================================
    # IMAGE INTEGRITY
    # =====================================================

    if extension in [
        ".jpg",
        ".jpeg",
        ".png"
    ]:

        try:

            image = Image.open(
                filepath
            )

            integrity = analyze_image_integrity(
                    image
                )

            tampering_status = integrity["status"]


            if (
                tampering_status
                == "⚠️ Review"
            ):

                score += 10

                reasons.append(
                    integrity["message"]
                )


        except Exception:

            tampering_status = "⚠️ Review"

            score += 10

            reasons.append(
                "Image integrity check requires review"
            )


    else:

        tampering_status = "⚠️ Review"


    # =====================================================
    # FIELD COMPLETENESS
    # =====================================================

    missing_fields = []


    for field_name, value in fields.items():

        if value == "Not detected":

            missing_fields.append(
                field_name
            )


    if extracted_text:

        if len(missing_fields) == 0:

            text_status = "✅ Passed"

            score += 3

        elif len(missing_fields) == 1:

            score += 5

            reasons.append(
                "One expected document field could not be identified: "
                +
                missing_fields[0]
            )

            text_status = "⚠️ Review"

        else:

            score += 10

            reasons.append(
                "Multiple expected fields could not be identified: "
                +
                ", ".join(
                    missing_fields
                )
            )

            text_status = "⚠️ Review"


    # =====================================================
    # TEXT LENGTH CHECK
    # =====================================================

    text_length = len(extracted_text)


    if text_length == 0:

        score += 5

    elif text_length < 30:

        score += 5

        reasons.append(
            "Very limited document text was extracted"
        )

    elif text_length > 100:

        score += 2


    # =====================================================
    # FINAL RISK SCORE
    # =====================================================

    risk_score = min(
            max(
                score,
                0
            ),
            100
        )


    status = classify_risk(
            risk_score
        )


    # =====================================================
    # DEFAULT REASON
    # =====================================================

    if not reasons:

        reasons.append(
            "No major automated risk indicators detected"
        )


    # =====================================================
    # SAVE DATABASE
    # =====================================================

    try:

        conn = sqlite3.connect(
                DATABASE
            )

        cursor = conn.cursor()


        cursor.execute("""

            INSERT INTO scans

            (
                filename,
                risk_score,
                status,
                reasons,
                extracted_text,
                scan_time
            )

            VALUES (?, ?, ?, ?, ?, ?)

        """, (

            filename,

            risk_score,

            status,

            " | ".join(
                reasons
            ),

            extracted_text,

            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        ))


        scan_id = cursor.lastrowid


        conn.commit()
        conn.close()


    except Exception as db_error:

        print(
            "Database Error:",
            db_error
        )


        return jsonify({

            "error":
                "Verification completed but database save failed."

        }), 500


    # =====================================================
    # SEND RESULT
    # =====================================================

    return jsonify({

        "message":
            "Document screened successfully!",

        "scan_id":
            scan_id,

        "id":
            scan_id,

        "filename":
            filename,

        "risk_score":
            risk_score,

        "status":
            status,

        "reasons":
            reasons,

        "extracted_text":
            extracted_text,

        "document_type":
            document_type,

        "fields":
            fields,

        "ocr_confidence":
            ocr_confidence,

        "image_details":
            image_details,

        "analysis": {

            "ocr":
                ocr_status,

            "structure":
                structure_status,

            "image":
                image_status,

            "text":
                text_status,

            "tampering":
                tampering_status

        }

    })


# =========================================================
# HISTORY
# =========================================================

@app.route("/history")
def history():

    try:

        conn = sqlite3.connect(
                DATABASE
            )

        cursor = conn.cursor()


        cursor.execute("""

            SELECT

                id,

                filename,

                risk_score,

                status,

                scan_time

            FROM scans

            ORDER BY id DESC

        """)


        rows = cursor.fetchall()


        conn.close()


        history_data = []


        for row in rows:

            history_data.append({

                "id":
                    row[0],

                "filename":
                    row[1],

                "risk_score":
                    row[2],

                "status":
                    row[3],

                "timestamp":
                    row[4],

                "scan_time":
                    row[4]

            })


        return jsonify({

            "history":
                history_data

        })


    except Exception as error:

        print(
            "History Error:",
            error
        )


        return jsonify({

            "history": [],

            "error":
                "Could not load history"

        }), 500


# =========================================================
# DELETE ONE VERIFICATION RECORD
# =========================================================

@app.route(
    "/delete-scan/<int:scan_id>",
    methods=["DELETE"]
)
def delete_scan(scan_id):

    try:

        conn = sqlite3.connect(
                DATABASE
            )

        cursor = conn.cursor()


        cursor.execute("""

            SELECT filename

            FROM scans

            WHERE id = ?

        """, (
            scan_id,
        ))


        record = cursor.fetchone()


        if not record:

            conn.close()

            return jsonify({

                "error":
                    "Verification record not found."

            }), 404


        filename = record[0]


        cursor.execute("""

            DELETE FROM scans

            WHERE id = ?

        """, (
            scan_id,
        ))


        conn.commit()
        conn.close()


        # -------------------------------------------------
        # DELETE UPLOAD
        # -------------------------------------------------

        if filename:

            upload_path = os.path.join(
                    UPLOAD_FOLDER,
                    filename
                )


            if os.path.exists(
                upload_path
            ):

                try:

                    os.remove(
                        upload_path
                    )

                except Exception as error:

                    print(
                        "Upload deletion error:",
                        error
                    )


        # -------------------------------------------------
        # DELETE REPORT
        # -------------------------------------------------

        report_filename = (

            f"DocShield_Report_{scan_id}.pdf"

        )


        report_path = os.path.join(
                REPORT_FOLDER,
                report_filename
            )


        if os.path.exists(
            report_path
        ):

            try:

                os.remove(
                    report_path
                )

            except Exception as error:

                print(
                    "Report deletion error:",
                    error
                )


        return jsonify({

            "message":
                "Verification record deleted successfully.",

            "scan_id":
                scan_id

        })


    except Exception as error:

        print(
            "Delete Scan Error:",
            error
        )


        return jsonify({

            "error":
                "Could not delete verification record."

        }), 500


# =========================================================
# DELETE ALL HISTORY
# =========================================================

@app.route(
    "/delete-all-history",
    methods=["DELETE"]
)
def delete_all_history():

    try:

        conn = sqlite3.connect(
                DATABASE
            )

        cursor = conn.cursor()


        cursor.execute("""

            SELECT id, filename

            FROM scans

        """)


        records = cursor.fetchall()


        cursor.execute("""

            DELETE FROM scans

        """)


        conn.commit()
        conn.close()


        # -------------------------------------------------
        # DELETE FILES
        # -------------------------------------------------

        for scan_id, filename in records:

            if filename:

                upload_path = os.path.join(
                        UPLOAD_FOLDER,
                        filename
                    )


                if os.path.exists(
                    upload_path
                ):

                    try:

                        os.remove(
                            upload_path
                        )

                    except Exception as error:

                        print(
                            "Upload deletion error:",
                            error
                        )


            report_filename = (

                f"DocShield_Report_{scan_id}.pdf"

            )


            report_path = os.path.join(
                    REPORT_FOLDER,
                    report_filename
                )


            if os.path.exists(
                report_path
            ):

                try:

                    os.remove(
                        report_path
                    )

                except Exception as error:

                    print(
                        "Report deletion error:",
                        error
                    )


        return jsonify({

            "message":
                "All verification history deleted successfully.",

            "deleted_count":
                len(records)

        })


    except Exception as error:

        print(
            "Delete All History Error:",
            error
        )


        return jsonify({

            "error":
                "Could not delete verification history."

        }), 500


# =========================================================
# GENERATE PDF REPORT
# =========================================================

@app.route(
    "/generate-report/<int:scan_id>"
)
def generate_report(scan_id):

    try:

        conn = sqlite3.connect(
                DATABASE
            )

        cursor = conn.cursor()


        cursor.execute("""

            SELECT

                id,

                filename,

                risk_score,

                status,

                reasons,

                extracted_text,

                scan_time

            FROM scans

            WHERE id = ?

        """, (
            scan_id,
        ))


        scan = cursor.fetchone()


        conn.close()


        if not scan:

            return jsonify({

                "error":
                    "Scan record not found"

            }), 404


        scan_id = scan[0]

        filename = scan[1]

        risk_score = scan[2]

        status = scan[3]

        reasons = scan[4]

        extracted_text = scan[5]

        scan_time = scan[6]


        # -------------------------------------------------
        # PDF PATH
        # -------------------------------------------------

        pdf_filename = f"DocShield_Report_{scan_id}.pdf"


        pdf_path = os.path.join(
                REPORT_FOLDER,
                pdf_filename
            )


        # -------------------------------------------------
        # PDF DOCUMENT
        # -------------------------------------------------

        document = SimpleDocTemplate(

                pdf_path,

                pagesize=A4,

                rightMargin=40,

                leftMargin=40,

                topMargin=40,

                bottomMargin=40

            )


        styles = getSampleStyleSheet()


        title_style = styles["Title"]


        title_style.alignment = TA_CENTER


        heading_style = styles["Heading2"]


        normal_style = styles["BodyText"]


        content = []


        # =================================================
        # TITLE
        # =================================================

        content.append(

            Paragraph(
                "DocShield AI",
                title_style
            )

        )


        content.append(

            Paragraph(
                "Document Verification Report",
                heading_style
            )

        )


        content.append(
            Spacer(1, 20)
        )


        # =================================================
        # DOCUMENT INFORMATION
        # =================================================

        content.append(

            Paragraph(
                "Document Information",
                heading_style
            )

        )


        document_data = [

            [
                "Report ID",
                str(scan_id)
            ],

            [
                "File Name",
                filename
            ],

            [
                "Scan Date",
                scan_time
            ],

            [
                "Risk Score",
                f"{risk_score}/100"
            ],

            [
                "Final Status",
                status
            ]

        ]


        table = Table(

                document_data,

                colWidths=[
                    150,
                    330
                ]

            )


        table.setStyle(

            TableStyle([

                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.lightgrey
                ),

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP"
                ),

                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    7
                )

            ])

        )


        content.append(table)

        content.append(
            Spacer(1, 20)
        )


        # =================================================
        # SCREENING SUMMARY
        # =================================================

        content.append(

            Paragraph(
                "Automated Screening Summary",
                heading_style
            )

        )


        screening_data = [

            [
                "Screening Component",
                "Result"
            ],

            [
                "OCR",
                "Automated"
            ],

            [
                "Document Structure",
                "Automated"
            ],

            [
                "Text Analysis",
                "Automated"
            ],

            [
                "Image Analysis",
                "Automated where applicable"
            ],

            [
                "Integrity Analysis",
                "Automated where applicable"
            ]

        ]


        screening_table = Table(

                screening_data,

                colWidths=[
                    250,
                    230
                ]

            )


        screening_table.setStyle(

            TableStyle([

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.lightgrey
                ),

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey
                ),

                (
                    "PADDING",
                    (0, 0),
                    (-1, -1),
                    7
                )

            ])

        )


        content.append(
            screening_table
        )


        content.append(
            Spacer(1, 20)
        )


        # =================================================
        # RISK INDICATORS
        # =================================================

        content.append(

            Paragraph(
                "Risk Indicators",
                heading_style
            )

        )


        if reasons:

            reason_list = reasons.split(
                    " | "
                )


            for reason in reason_list:

                safe_reason = (

                    reason

                    .replace(
                        "&",
                        "&amp;"
                    )

                    .replace(
                        "<",
                        "&lt;"
                    )

                    .replace(
                        ">",
                        "&gt;"
                    )

                )


                content.append(

                    Paragraph(
                        "• " +
                        safe_reason,
                        normal_style
                    )

                )


                content.append(
                    Spacer(1, 5)
                )


        else:

            content.append(

                Paragraph(
                    "No major risk indicators detected.",
                    normal_style
                )

            )


        content.append(
            Spacer(1, 20)
        )


        # =================================================
        # OCR TEXT
        # =================================================

        content.append(

            Paragraph(
                "Extracted OCR Text",
                heading_style
            )

        )


        if extracted_text:

            safe_text = (

                extracted_text

                .replace(
                    "&",
                    "&amp;"
                )

                .replace(
                    "<",
                    "&lt;"
                )

                .replace(
                    ">",
                    "&gt;"
                )

                .replace(
                    "\n",
                    "<br/>"
                )

            )


            content.append(

                Paragraph(
                    safe_text,
                    normal_style
                )

            )


        else:

            content.append(

                Paragraph(
                    "No OCR text was extracted.",
                    normal_style
                )

            )


        content.append(
            Spacer(1, 25)
        )


        # =================================================
        # DISCLAIMER
        # =================================================

        content.append(

            Paragraph(

                "<b>Prototype Notice:</b> "
                "DocShield AI is an automated document "
                "screening and risk-analysis prototype. "
                "The risk score is based on available "
                "document characteristics and automated "
                "checks. It should not be treated as "
                "definitive proof of document authenticity.",

                normal_style

            )

        )


        # =================================================
        # BUILD PDF
        # =================================================

        document.build(
            content
        )


        # =================================================
        # SEND PDF
        # =================================================

        return send_file(

            pdf_path,

            as_attachment=True,

            download_name= pdf_filename,

            mimetype= "application/pdf"

        )


    except Exception as error:

        print(
            "PDF Report Error:",
            error
        )


        return jsonify({

            "error":
                "Could not generate PDF report."

        }), 500


# =========================================================
# RUN FLASK
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
