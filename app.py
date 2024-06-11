from flask import Flask, render_template, request, send_file, jsonify
import pandas as pd
import os
from werkzeug.utils import secure_filename
# import logging

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MERGED_FILE'] = 'merged/merged_file.csv'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

if not os.path.exists('merged'):
    os.makedirs('merged')

# Set up logging
# logging.basicConfig(level=logging.DEBUG)

# Define the required columns
REQUIRED_COLUMNS = ['Vendor Name', 'Spend Amount', 'Department', 'Invoice Description', 'Account Title']
CORPORATE_SUFFIXES = ['inc', 'corp', 'llc', 'ltd', 'co', 'llp', 'inc.', 'corp.', 'llc.', 'ltd.', 'co.', 'llp.']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    uploaded_files = request.files.getlist("file[]")
    if len(uploaded_files) == 0:
        return "No files uploaded", 400

    filenames = []
    columns_dict = {}
    for file in uploaded_files:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        # logging.debug(f"Saved file: {filepath}")
        df = pd.read_excel(filepath)
        filenames.append(filename)
        columns_dict[filename] = df.columns.tolist()
        # logging.debug(f"Columns in {filename}: {df.columns.tolist()}")

    return jsonify({"filenames": filenames, "columns": columns_dict})

@app.route('/merge', methods=['POST'])
def merge_files():
    mappings = request.json['mappings']
    dataframes = []

    # Process each file according to the mappings
    for filename in mappings:
        column_mapping = mappings[filename]
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        # logging.debug(f"Processing file: {filepath}")
        df = pd.read_excel(filepath)

        # Rename columns according to the mappings, add missing columns with NaN values
        new_columns = {}
        for attribute in REQUIRED_COLUMNS:
            if column_mapping[attribute]:
                new_columns[column_mapping[attribute]] = attribute
            else:
                df[attribute] = pd.NA  # Add missing columns with NaN

        # logging.debug(f"New columns mapping for {filename}: {new_columns}")
        df.rename(columns=new_columns, inplace=True)
        df = df[REQUIRED_COLUMNS]  # Ensure DataFrame columns are in the required order
        dataframes.append(df)

    # Merge all DataFrames
    merged_df = pd.concat(dataframes, ignore_index=True)

    # Remove duplicates based on the 'Account Title' column
    merged_df.drop_duplicates(subset=['Account Title'], inplace=True)

    # Process 'Vendor Name' column: remove corporate suffixes and convert to lowercase
    def clean_vendor_name(vendor_name):
        if pd.isna(vendor_name):
            return vendor_name
        vendor_name = vendor_name.lower()
        for suffix in CORPORATE_SUFFIXES:
            if vendor_name.endswith(suffix):
                vendor_name = vendor_name[:-len(suffix)].strip()
        return vendor_name

    merged_df['Vendor Name'] = merged_df['Vendor Name'].apply(clean_vendor_name)

    # Save the merged DataFrame to a CSV file
    merged_filepath = app.config['MERGED_FILE']
    merged_df.to_csv(merged_filepath, index=False)
    # logging.debug(f"Merged file saved to: {merged_filepath}")

    return send_file(
        merged_filepath,
        as_attachment=True,
        download_name='merged_file.csv',
        mimetype='text/csv'
    )

if __name__ == '__main__':
    app.run(debug=True)