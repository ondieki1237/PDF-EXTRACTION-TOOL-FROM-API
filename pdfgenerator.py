import requests
from io import BytesIO
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Image, Spacer, ListFlowable, ListItem
)
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from datetime import datetime
from bs4 import BeautifulSoup
import tempfile
import os

# --- Brand colors ---
BRAND_RED = colors.HexColor("#FF0000")
BRAND_BLUE = colors.HexColor("#00aeef")
BRAND_BLACK = colors.black
BRAND_WHITE = colors.white

# --- Temporary folder for images ---
temp_dir = tempfile.mkdtemp()

def download_image(url):
    """Download image to temporary folder, return local file path."""
    try:
        response = requests.get(url, timeout=5)
        ext = url.split('.')[-1].split('?')[0]
        if len(ext) > 4: ext = "jpg"
        filename = f"img_{int(datetime.now().timestamp()*1000)}.{ext}"
        filepath = os.path.join(temp_dir, filename)
        with open(filepath, "wb") as f:
            f.write(response.content)
        return filepath
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return None

# --- Fetch API data ---
api_url = "https://accordmedical.co.ke/api/get_spdk_items.php"
resp = requests.get(api_url)
data = resp.json()

if data["status"] != "success":
    raise Exception("Failed to fetch API data")

items = data["data"]

# --- Organize items by category ---
departments = {}
for item in items:
    category = item.get("category", "Other")
    departments.setdefault(category, []).append(item)

# --- PDF setup ---
pdf_file = "medical_products_catalog.pdf"
doc = SimpleDocTemplate(pdf_file, pagesize=A4)
styles = getSampleStyleSheet()

# Custom styles
header_style = ParagraphStyle('Header', fontSize=20, alignment=TA_CENTER, textColor=BRAND_RED, spaceAfter=12)
subtitle_style = ParagraphStyle('Subtitle', fontSize=14, alignment=TA_CENTER, textColor=BRAND_BLACK, spaceAfter=24)
dept_style = ParagraphStyle('Department', fontSize=16, textColor=BRAND_BLUE, spaceAfter=12)
end_dept_style = ParagraphStyle('EndDept', fontSize=10, textColor=BRAND_RED, italic=True, spaceAfter=24)
product_style = ParagraphStyle('Product', fontSize=9, leading=11, alignment=TA_LEFT)
desc_item_style = ParagraphStyle('DescItem', fontSize=8, leading=10, leftIndent=10, bulletIndent=5)

elements = []

# --- PDF Header ---
elements.append(Paragraph("ACCORD MEDICAL PRODUCTS CATALOG", header_style))
elements.append(Paragraph("Product Catalog – Department Listing", subtitle_style))

# --- Loop through departments ---
downloaded_images = []

for dept_name, products in departments.items():
    elements.append(Paragraph(dept_name, dept_style))
    elements.append(Spacer(1, 12))

    table_data = [["Product", "Description", "Image"]]

    for prod in products:
        # Product name
        prod_name = Paragraph(prod.get("product_name", ""), product_style)

        # Description as bullet points
        description_html = prod.get("product_description", "")
        soup = BeautifulSoup(description_html, "html.parser")
        bullet_points = []
        for li in soup.find_all("li"):
            text = li.get_text(strip=True)
            bullet_points.append(ListItem(Paragraph(text, desc_item_style)))
        if bullet_points:
            desc = ListFlowable(bullet_points, bulletType='bullet', start='•', leftIndent=10)
        else:
            desc_text = soup.get_text(strip=True)
            desc = Paragraph(desc_text, desc_item_style)

        # Image
        img_url = None
        if prod.get("images"):
            img_url = prod["images"][0].get("product_image") or prod["images"][0].get("product_image_md")

        if img_url:
            img_path = download_image(img_url)
            if img_path:
                downloaded_images.append(img_path)
                try:
                    img_obj = Image(img_path, width=80, height=80)
                except:
                    img_obj = Paragraph("No Image", product_style)
            else:
                img_obj = Paragraph("No Image", product_style)
        else:
            img_obj = Paragraph("No Image", product_style)

        table_data.append([prod_name, desc, img_obj])

    table = Table(table_data, colWidths=[120, 250, 100], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BRAND_BLUE),
        ('TEXTCOLOR', (0,0), (-1,0), BRAND_WHITE),
        ('GRID', (0,0), (-1,-1), 0.5, BRAND_BLACK),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"End of {dept_name}", end_dept_style))
    elements.append(Spacer(1, 24))

# --- Footer ---
date_text = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
footer = Paragraph(f"Generated on: {date_text} | System: Catalog PDF Generator", styles["Normal"])
elements.append(footer)

# --- Build PDF ---
doc.build(elements)

print(f"PDF generated successfully: {pdf_file}")

# --- Cleanup temporary images ---
for f in downloaded_images:
    if os.path.exists(f):
        os.remove(f)
os.rmdir(temp_dir)
