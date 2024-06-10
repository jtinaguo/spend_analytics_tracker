from flask import Flask, render_template, request, send_file, jsonify
import pandas as pd
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MERGED_FILE'] = 'merged/merged_file.csv'
# app.config['MERGED_FILE'] = 'merged/merged_file.xlsx'

if not os.path.exists('uploads'):
    os.makedirs('uploads')

if not os.path.exists('merged'):
    os.makedirs('merged')

# Define the required columns
REQUIRED_COLUMNS = ['Vendor Name', 'Spend Amount', 'Department', 'Invoice Description', 'Account Title']

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
        df = pd.read_excel(filepath)
        filenames.append(filename)
        columns_dict[filename] = df.columns.tolist()

    return jsonify({"filenames": filenames, "columns": columns_dict})

@app.route('/merge', methods=['POST'])
def merge_files():
    mappings = request.json['mappings']
    dataframes = []

    # Process each file according to the mappings
    for filename, column_mapping in mappings.items():
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        df = pd.read_excel(filepath)
        df.rename(columns=column_mapping, inplace=True)
       
        # Add missing columns with NaN values
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                df[col] = pd.NA

        # Ensure DataFrame columns are in the required order
        df = df[REQUIRED_COLUMNS]
        dataframes.append(df)

    # Merge all DataFrames
    merged_df = pd.concat(dataframes, ignore_index=True)

    # Remove duplicates based on the 'Account Title' column
    merged_df.drop_duplicates(subset=['Account Title'], inplace=True)

    # Save the merged DataFrame to a CSV file
    merged_filepath = app.config['MERGED_FILE']
    # with pd.ExcelWriter(merged_filepath, engine='openpyxl') as writer:
    #     merged_df.to_excel(writer, index=False)
    merged_df.to_csv(merged_filepath, index=False)

    # writer.close()

    return send_file(merged_filepath, mimetype='text/csv', as_attachment=True, download_name='merged_file.csv')
    # return send_file(merged_filepath, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, attachment_filename='merged_file.xlsx')
    
    
    # Remove llp,inc, etc suffixes
    # lowercase

if __name__ == '__main__':
    app.run(debug=True)