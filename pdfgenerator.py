import streamlit as st
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from datetime import datetime
import json

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image as RLImage

def get_nested(obj, path):
    """Simple nested key access with dot notation (supports list indices as digits)."""
    if not path or obj is None:
        return None
    keys = path.split('.')
    current = obj
    for key in keys:
        if key.isdigit() and isinstance(current, list):
            idx = int(key)
            if idx < len(current):
                current = current[idx]
            else:
                return None
        elif isinstance(current, dict):
            current = current.get(key)
        else:
            return None
        if current is None:
            return None
    return current

def generate_pdf(
    items,
    title,
    subtitle,
    primary_color,
    accent_color,
    group_key,
    name_key,
    desc_key,
    images_key,
    product_header,
    desc_header,
    image_header,
    additional
):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=40, rightMargin=40, topMargin=60, bottomMargin=60)
    styles = getSampleStyleSheet()

    header_style = ParagraphStyle(
        name='Header',
        parent=styles['Heading1'],
        fontSize=24,
        alignment=TA_CENTER,
        textColor=colors.HexColor(primary_color),
        spaceAfter=20
    )
    subtitle_style = ParagraphStyle(
        name='Subtitle',
        parent=styles['Heading2'],
        fontSize=16,
        alignment=TA_CENTER,
        textColor=colors.black,
        spaceAfter=30
    )
    dept_style = ParagraphStyle(
        name='Dept',
        fontSize=18,
        textColor=colors.HexColor(accent_color),
        spaceBefore=20,
        spaceAfter=12,
        alignment=TA_LEFT
    )
    end_dept_style = ParagraphStyle(
        name='EndDept',
        fontSize=10,
        textColor=colors.HexColor(primary_color),
        italic=True,
        alignment=TA_CENTER,
        spaceAfter=30
    )
    product_style = ParagraphStyle(
        name='Product',
        fontSize=10,
        leading=12
    )
    desc_item_style = ParagraphStyle(
        name='DescItem',
        fontSize=9,
        leading=11,
        leftIndent=15
    )

    elements = []
    elements.append(Paragraph(title, header_style))
    elements.append(Paragraph(subtitle, subtitle_style))
    elements.append(Spacer(1, 20))

    # Organize into groups
    if group_key:
        departments = {}
        for item in items:
            cat = get_nested(item, group_key)
            cat_name = str(cat) if cat is not None else "Uncategorized"
            departments.setdefault(cat_name, []).append(item)
        groups = list(departments.items())
    else:
        groups = [("All Products", items)]

    # Column widths
    num_extra = len(additional)
    base_widths = [130, 270, 100]  # Product, Description, Image
    extra_width = 60 if num_extra > 0 else 0
    col_widths = base_widths + [extra_width] * num_extra

    for group_name, products in groups:
        if group_key:
            elements.append(Paragraph(group_name, dept_style))
            elements.append(Spacer(1, 10))

        table_data = [[product_header, desc_header, image_header] + [col["header"] for col in additional]]

        for prod in products:
            # Product name
            name_val = get_nested(prod, name_key)
            prod_name = Paragraph(str(name_val or "Unnamed Product"), product_style)

            # Description (supports HTML bullet lists)
            desc_raw = get_nested(prod, desc_key)
            if desc_raw:
                desc_str = str(desc_raw)
                soup = BeautifulSoup(desc_str, "html.parser")
                li_tags = soup.find_all("li")
                if li_tags:
                    bullet_items = [
                        ListItem(Paragraph(tag.get_text(strip=True), desc_item_style))
                        for tag in li_tags if tag.get_text(strip=True)
                    ]
                    desc = ListFlowable(bullet_items, bulletType="bullet", leftIndent=10) if bullet_items else Paragraph("No description", desc_item_style)
                else:
                    clean_text = soup.get_text(separator=" ", strip=True)
                    desc = Paragraph(clean_text or "No description", desc_item_style)
            else:
                desc = Paragraph("No description", desc_item_style)

            # Image
            images_val = get_nested(prod, images_key)
            img_url = None
            if isinstance(images_val, list) and images_val:
                first = images_val[0]
                if isinstance(first, dict):
                    img_url = (first.get("product_image") or
                               first.get("product_image_md") or
                               first.get("image") or
                               first.get("src") or
                               first.get("url"))
                elif isinstance(first, str):
                    img_url = first
            elif isinstance(images_val, str):
                img_url = images_val

            img_io = None
            if img_url and str(img_url).startswith(("http://", "https://")):
                try:
                    r = requests.get(img_url, timeout=10)
                    r.raise_for_status()
                    img_io = BytesIO(r.content)
                except:
                    pass

            if img_io:
                try:
                    img_obj = RLImage(ImageReader(img_io), width=90, height=90)
                    img_obj.hAlign = "CENTER"
                except:
                    img_obj = Paragraph("Image failed to load", product_style)
            else:
                img_obj = Paragraph("No Image", product_style)

            # Additional columns
            extra_cells = [
                Paragraph(str(get_nested(prod, col["key"]) or "-"), product_style)
                for col in additional
            ]

            table_data.append([prod_name, desc, img_obj] + extra_cells)

        if len(table_data) > 1:
            table = Table(table_data, colWidths=col_widths, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(accent_color)),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Center images
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 30))

            if group_key:
                elements.append(Paragraph(f"End of {group_name} Department", end_dept_style))

    # Footer
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Generated on {datetime.now().strftime('%d %B %Y at %H:%M')}", styles["Normal"]))

    doc.build(elements)
    return buffer.getvalue()

# ====================== Streamlit App ======================

st.set_page_config(page_title="API to PDF Catalog Generator", layout="centered")
st.title("PDF Catalog Generator")
st.write("Turn a JSON API of products into a beautiful, branded PDF catalog. Fully configurable via the form below.")

with st.form("catalog_form"):
    st.subheader("General Settings")
    api_url = st.text_input("API Endpoint URL", value="https://accordmedical.co.ke/api/get_spdk_items.php")
    title = st.text_input("Catalog Title", value="ACCORD MEDICAL PRODUCTS CATALOG")
    subtitle = st.text_input("Catalog Subtitle", value="Product Catalog – Department Listing")
    pdf_filename = st.text_input("Output PDF Filename", value="medical_products_catalog.pdf")

    col1, col2 = st.columns(2)
    primary_color = col1.color_picker("Primary Brand Color (titles)", "#FF0000")
    accent_color = col2.color_picker("Accent Brand Color (tables/departments)", "#00aeef")

    st.subheader("Data Mapping")
    group_key = st.text_input("Group by key (leave blank for no departments)", value="category")
    name_key = st.text_input("Product name key", value="product_name")
    desc_key = st.text_input("Description key (HTML bullet lists supported)", value="product_description")
    images_key = st.text_input("Images key (list of dicts or URLs)", value="images")

    col1, col2, col3 = st.columns(3)
    product_header = col1.text_input("Product column header", value="Product")
    desc_header = col2.text_input("Description column header", value="Description")
    image_header = col3.text_input("Image column header", value="Image")

    st.subheader("Additional Columns (optional)")
    st.write("JSON array of objects with `header` and `key`. Example:")
    st.code('''[
  {"header": "Price", "key": "price"},
  {"header": "Code", "key": "product_code"}
]''')
    additional_json = st.text_area("Additional columns JSON", value="[]", height=150)

    submitted = st.form_submit_button("Generate PDF Catalog")

if submitted:
    # Validate additional columns
    try:
        additional = json.loads(additional_json)
        if not isinstance(additional, list):
            raise ValueError("Must be a JSON array")
        for col in additional:
            if not isinstance(col, dict) or "header" not in col or "key" not in col:
                raise ValueError("Each item must have 'header' and 'key'")
    except Exception as e:
        st.error(f"Invalid JSON for additional columns: {e}")
        st.stop()

    with st.spinner("Fetching data and generating PDF (this may take a minute for large catalogs)..."):
        try:
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()
            api_data = response.json()

            if api_data.get("status") != "success":
                st.error(f"API returned error: {api_data.get('message', 'Unknown error')}")
                st.stop()

            items = api_data.get("data", [])
            if not items:
                st.warning("No items found in API response.")
                st.stop()

            st.info(f"Fetched {len(items)} products from API.")

            pdf_bytes = generate_pdf(
                items=items,
                title=title,
                subtitle=subtitle,
                primary_color=primary_color,
                accent_color=accent_color,
                group_key=group_key or None,
                name_key=name_key,
                desc_key=desc_key,
                images_key=images_key,
                product_header=product_header,
                desc_header=desc_header,
                image_header=image_header,
                additional=additional
            )

            st.success("PDF catalog generated successfully!")
            st.download_button(
                label="📄 Download PDF Catalog",
                data=pdf_bytes,
                file_name=pdf_filename,
                mime="application/pdf"
            )

        except requests.exceptions.RequestException as e:
            st.error(f"Failed to fetch from API: {e}")
        except Exception as e:
            st.error(f"Error during generation: {e}")