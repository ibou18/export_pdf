import os
import pathlib
import re
import json
import fitz  # pip install PyMuPDF
from flask import Flask, request, jsonify
import logging


main = Flask(__name__)
log_filename = 'app.log'
logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')


def generate_json(file_name):
    pdf_document = fitz.open(file_name)

    payment_data = {}
    remittance_data = []
    current_entry = {}

    for page_num in range(pdf_document.page_count):
        print(f'INFO : Generating JSON for file {file_name.name}')
        page = pdf_document.load_page(page_num)
        text = page.get_text()
        logging.info(f'Generating JSON for file {file_name.name}')

        payment_payee = re.search(r'Payee:\s*(.+)', text).group(1)
        payment_number = re.search(r'Payment Number:\s*(.+)', text).group(1)
        payment_date = re.search(r'Payment Date:\s*(.+)', text).group(1)
        payment_currency = re.search(r'Payment Currency:\s*(.+)', text).group(1)
        payment_amount = re.search(r'Payment Amount:\s*([0-9,.]+)', text).group(1)
        total = re.search(r'Total:\s*([0-9,.$]+)', text).group(1)

        payment_data = {
                "payee": payment_payee.strip(),
                "payment_number": payment_number.strip(),
                "payment_date": payment_date.strip(),
                "payment_currency": payment_currency.strip(),
                "payment_amount": float(payment_amount.replace(',', '').strip()),
                "total": float(total.replace(',', '').replace('$','').strip()),
                "tab": []
        }

        remittance_lines = text.split('Product - Object Name - Object ID\nRemittance',maxsplit = 1)[-1].strip().split('\n')
        for line_number in range(0,len(remittance_lines)-3,4):
            current_entry["payout_reference"] = remittance_lines[line_number].strip()
            current_entry["payout_period_start"] = remittance_lines[line_number + 1].split('->')[0].strip()
            current_entry["payout_period_end"] = remittance_lines[line_number + 1].split('->')[1].strip()
            product_name, facebook_name, facebook_id = re.findall(r'(.+?) - \((.+?) - (\d+)\)', remittance_lines[line_number + 2].strip())[0]
            current_entry["product"] = product_name
            current_entry["facebook_name"] = facebook_name
            current_entry["facebook_Id"] = facebook_id
            current_entry["remittance"] = float(remittance_lines[line_number + 3].replace(',','').strip())
            remittance_data.append(current_entry.copy())

    pdf_document.close()
    payment_data["tab"] = remittance_data

    # Write the JSON data to a file
    out_file = os.path.join('output',f'{"".join(file_name.name.split(".")[0:-1])}.json')
    with open(out_file, 'w') as json_file:
        json.dump(payment_data, json_file, indent=4)

    print(f'INFO : JSON data has been generated and saved as {"".join(file_name.name.split(".")[0:-1])}.json')
    logging.info(f'JSON data has been generated and saved as {"".join(file_name.name.split(".")[0:-1])}.json')
    # Return the JSON data
    return payment_data

@main.route('/send', methods=['POST'])
def upload_and_process_pdf():
    try:
        uploaded_file = request.files['file']
        if uploaded_file.filename != '':
            # Save the uploaded PDF file
            file_path = os.path.join('input', uploaded_file.filename)
            uploaded_file.save(file_path)

            # Convert the 'file_path' string to a pathlib.Path object
            file_name = pathlib.Path(file_path)

            # Call your existing code to generate JSON with 'file_name' as a pathlib.Path object
            json_data = generate_json(file_name)

            # Return the JSON data as a response
            return jsonify(json_data)
        else:
            return jsonify({'error': 'No file uploaded'})

    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    pathlib.Path('input').mkdir(exist_ok=True)
    pathlib.Path('output').mkdir(exist_ok=True)
    # main.run(debug=True)
    port = int(os.environ.get("PORT", 5000))
    main.run(host="0.0.0.0", port=port)
