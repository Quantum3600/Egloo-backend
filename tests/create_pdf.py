import fitz
import os

def create_test_pdf(path, text_content):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text_content)
    doc.save(path)
    doc.close()

if __name__ == "__main__":
    os.makedirs("tests/data", exist_ok=True)
    create_test_pdf("tests/data/test.pdf", "This is a test PDF for Egloo ingestion. It contains information about Project Alpha.")
    print("Created test.pdf")
