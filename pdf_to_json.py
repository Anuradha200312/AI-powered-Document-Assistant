import json
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.schema import Document
from langchain_community.document_loaders import PyPDFLoader

# ---------- Step 1: Load PDF ----------
pdf_path = r"C:\Users\Anuradha\Downloads\2202487.pdf"
loader = PyPDFLoader(pdf_path)
pages = loader.load()

# Combine all pages into one text
pdf_text = "\n".join([p.page_content for p in pages])

# ---------- Step 2: Define LLM ----------
# Make sure you set your GROQ_API_KEY in your environment variables
llm = ChatGroq(model="llama3-70b-8192", temperature=0,api_key="YOUR_GROQ_API_KEY")

# ---------- Step 3: Create Prompt ----------
prompt_template = PromptTemplate(
    input_variables=["text"],
    template="""
You are an expert at extracting structured invoice data from raw text.
From the given invoice text, extract and return ONLY valid JSON in the exact format below:

{{
  "supplier": "<supplier name>",
  "invoice_number": "<invoice number>",
  "invoice_date": "<dd/mm/yyyy>",
  "delivery_date": "<dd/mm/yyyy>",
  "customer": "<customer name>",
  "items": [
    {{ "product_code": "<code>", "item_name": "<name>", "quantity": <float>, "unit_price": <float>, "total_price": <float> }}
  ],
  "net_total": <float>,
  "vat_total": <float>,
  "grand_total": <float>
}}

Rules:
- Return only valid JSON without comments or extra text.
- Ensure numeric values are numbers, not strings.
- Match the invoice exactly.
- Use the same product order as in the invoice.

Invoice Text:
{text}
"""
)

# ---------- Step 4: Run LLM ----------
prompt = prompt_template.format(text=pdf_text)
response = llm.invoke(prompt)

# ---------- Step 5: Save JSON ----------
try:
    invoice_data = json.loads(response.content)
    with open("invoice_data.json", "w") as f:
        json.dump(invoice_data, f, indent=2)
    print("✅ JSON extracted and saved as invoice_data.json")
except json.JSONDecodeError:
    print("❌ Failed to decode JSON from LLM output. Raw output:")
    print(response.content)


'''
{
  "supplier": "Billfields of London Limited",
  "invoice_number": "2202487",
  "invoice_date": "24/06/2025",
  "delivery_date": "24/06/2025",
  "customer": "CHISHURU LTD",
  "items": [
    { "product_code": "01MB0101", "item_name": "BEEF BONES", "quantity": 3.98, "unit_price": 2.10, "total_price": 8.36 },
    { "product_code": "02B0101", "item_name": "LAMB BREAST", "quantity": 13.22, "unit_price": 11.25, "total_price": 148.73 },
    { "product_code": "06DH0101", "item_name": "DUCK HEART", "quantity": 2.40, "unit_price": 8.95, "total_price": 21.48 },
    { "product_code": "06TRP0101", "item_name": "TRIPE", "quantity": 5.00, "unit_price": 7.50, "total_price": 37.50 },
    { "product_code": "06VCF0112", "item_name": "CALF FEET HOLLAND", "quantity": 2.50, "unit_price": 4.25, "total_price": 10.63 },
    { "product_code": "123CW0101", "item_name": "3 JOINT CHICKEN WINGS", "quantity": 2.10, "unit_price": 3.25, "total_price": 6.83 },
    { "product_code": "12C0101", "item_name": "CHICKEN CARCASS", "quantity": 2.40, "unit_price": 1.85, "total_price": 4.44 },
    { "product_code": "12CF0101", "item_name": "CHICKEN FEET", "quantity": 1.10, "unit_price": 4.25, "total_price": 4.68 },
    { "product_code": "13GF0109", "item_name": "FRENCH GUINEA FOWL FRANCE", "quantity": 22.90, "unit_price": 8.95, "total_price": 204.96 }
  ],
  "net_total": 447.61,
  "vat_total": 0.00,
  "grand_total": 447.61
}
'''