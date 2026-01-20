# app.py
from flask import Flask, render_template, request, redirect, url_for
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai # type: ignore
import pymysql

app = Flask(__name__)

# --- Gemini AI setup ---
genai.configure(api_key="AIzaSyClVZKhvk5RkxFygbdOhMyt6ifSopa3KzY")
model = genai.GenerativeModel("models/gemini-2.5-flash-lite")

# --- MySQL connection ---
def get_connection():
    return pymysql.connect(
        host="localhost",
        user="root",           # change if needed
        password="12345",      # your MySQL password if any
        database="pubchem_cd"  # Database name
    )

# --- Scraping and AI extraction (using Gemini) ---
def get_chemical_notes(chemical):
    """
    Uses Gemini AI to extract note, odour class, and pH for a given chemical name.
    """
    prompt = f"""
    You are a perfumery expert. For the chemical '{chemical}', provide:
    1. Whether it is typically a Top, Middle, or Base note.
    2. Its Odour Class (floral, woody, citrus, musky, spicy, etc.).
    3. Its pH value (only value no sentence).
    If data is missing, infer realistic values based on its known properties.
    Return exactly in this format:
    Top/Middle/Base Note: ...
    Odour Class: ...
    pH value: ...
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Error calling Gemini for {chemical}: {e}")
        return "" # Return empty string on error

def parse_gemini_result(result_text):
    """
    Parses the result text from Gemini into note, odour, and pH.
    """
    note = None
    odour = None
    pH = None

    if not result_text:
        return note, odour, pH

    lines = result_text.splitlines()
    for line in lines:
        if line.startswith("Top/Middle/Base Note:"):
            note = line[len("Top/Middle/Base Note:"):].strip()
        elif line.startswith("Odour Class:"):
            odour = line[len("Odour Class:"):].strip()
        elif line.startswith("pH value:"):
            pH = line[len("pH value:"):].strip()

    return note, odour, pH

# --- Fetch ONE chemical name from database that needs scraping (scraped = 0) ---
def fetch_one_chemical_to_scrape():
    """
    Fetches ONE chemical name from the pubchem_cd table where scraped is 0 (integer).
    Assumes the column name for the chemical name is 'chemical_name'.
    """
    try:
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)
        # Use LIMIT 1 to get only one record at a time where scraped is the integer 0
        cur.execute("SELECT chemical_name FROM pubchem_cd WHERE scraped = 0 LIMIT 1")
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row['chemical_name'] if row else None # Return the name or None if not found
    except Exception as e:
        print(f"Error fetching one chemical to scrape from database: {e}")
        return None

# --- Update database record ---
def update_db_record(chemical_name, note, odour, pH):
    """
    Updates the database record for a chemical if fields are empty, AND sets scraped to 1.
    """
    try:
        conn = get_connection()
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # Fetch current values to check if they are empty and if it's marked as scraped
        cur.execute(
            "SELECT note, odour, pH, scraped FROM pubchem_cd WHERE chemical_name = %s",
            (chemical_name,)
        )
        row = cur.fetchone()

        if row:
            updates = []
            params = []

            # Only update if the database field is currently empty/None
            # Only proceed if scraped is not already 1
            if row['scraped'] != 1:
                if not row['note'] and note:
                    updates.append("note = %s")
                    params.append(note)
                if not row['odour'] and odour:
                    updates.append("odour = %s")
                    params.append(odour)
                if not row['pH'] and pH:
                    updates.append("pH = %s")
                    params.append(pH)

                # If any of the note, odour, pH were updated, mark as scraped
                if updates:
                    updates.append("scraped = 1")
                    params.append(chemical_name)
                    update_query = f"UPDATE pubchem_cd SET {', '.join(updates)} WHERE chemical_name = %s"
                    cur.execute(update_query, params)
                    conn.commit()
                    print(f"Updated record for '{chemical_name}' and marked as scraped (scraped=1).")
                    return True # Indicate success
                else:
                    print(f"No new data to update for '{chemical_name}', but marking as scraped (scraped=1).")
                    # If fields were already filled, still mark as scraped if it wasn't already
                    if row['scraped'] != 1:
                        cur.execute("UPDATE pubchem_cd SET scraped = 1 WHERE chemical_name = %s", (chemical_name,))
                        conn.commit()
                        print(f"Marked '{chemical_name}' as scraped (scraped=1).")
                    return True
            else:
                 print(f"Record for '{chemical_name}' is already marked as scraped (scraped=1). Skipping.")
                 return False # Indicate no update needed/already scraped
        else:
            print(f"Chemical '{chemical_name}' not found in database.")
            return False

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error updating database for {chemical_name}: {e}")
        return False


# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    chemical = None
    message = None
    # Removed: scraped_chemicals = []
    # Removed: scraped_chemicals = fetch_scraped_chemicals_from_db() # No longer fetching for display

    if request.method == "POST":
        # Handle Process Unscraped button click
        if "process_unscraped" in request.form:
            processed_count = 0
            processed_results = [] # Store results from this batch run
            
            # Loop to find and process chemicals with scraped=0
            while True:
                chemical_to_process = fetch_one_chemical_to_scrape() # Fetch ONE unscraped
                if not chemical_to_process:
                    # No more unscraped chemicals found, break the loop
                    print("No more unscraped chemicals found.")
                    break
                
                print(f"Processing: {chemical_to_process}")
                gemini_result = get_chemical_notes(chemical_to_process)
                note, odour, pH = parse_gemini_result(gemini_result)
                success = update_db_record(chemical_to_process, note, odour, pH)
                if success:
                    processed_count += 1
                    # Add the result to the list for display
                    processed_results.append({
                        'chemical_name': chemical_to_process,
                        'note': note,
                        'odour': odour,
                        'pH': pH
                    })
                # Optional: Add a small delay to be respectful to the API/database
                # import time
                # time.sleep(0.1) 

            message = f"✅ Processed unscraped chemicals found during the run. Successfully updated {processed_count} records."
            # Pass the results from this run to the template
            return render_template("index.html", result=result, message=message, chemicals=processed_results)

        # Handle Save All button click
        elif "save_all" in request.form:
            # Retrieve the list of chemicals and their data from the form
            names = request.form.getlist('chemical_name')
            notes = request.form.getlist('note')
            odours = request.form.getlist('odour')
            pHs = request.form.getlist('pH')

            saved_count = 0
            # Removed error_count variable

            for i in range(len(names)):
                chemical_name = names[i]
                note = notes[i].strip() or None
                odour = odours[i].strip() or None
                pH = pHs[i].strip() or None

                # Validate that the name exists
                if not chemical_name:
                    print(f"Warning: Skipping row {i} due to missing chemical name.")
                    continue

                # Use the existing update_db_record function to save
                success = update_db_record(chemical_name, note, odour, pH)
                if success: # Only increment if update_db_record returned True
                    saved_count += 1
                # Errors are now silently handled by update_db_record, no need to count them here

            # Generate message based on saved_count
            if saved_count > 0:
                message = f"✅ Successfully saved data for {saved_count} chemicals to the database."
            else:
                # Optional: You could still show a different message if nothing was saved
                # message = "ℹ️ No records needed updating or no valid records found to save."
                # Or, to ensure *some* positive message always appears if the button was pressed:
                message = f"✅ Save operation completed. {saved_count} records were processed."

            # After saving, reload the page with the same results
            processed_results = [
                {'chemical_name': names[i], 'note': notes[i], 'odour': odours[i], 'pH': pHs[i]}
                for i in range(len(names))
            ]
            return render_template("index.html", result=result, message=message, chemicals=processed_results)

    # Pass an empty list for chemicals when not processing
    return render_template("index.html", result=result, message=message, chemicals=[])


if __name__ == "__main__":
    app.run(debug=True)