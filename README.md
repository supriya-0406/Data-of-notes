AI-Powered Chemical Fragrance Finder
📌 Project Description

The AI-Powered Chemical Fragrance Finder is a full-stack web application built using Flask, MySQL, and Google Gemini AI.
It automatically processes chemical compound names stored in a database, extracts fragrance-related properties using generative AI, allows manual editing through a web interface, and saves the enriched data back to the database.

This system is designed for perfumery research, fragrance classification, and chemical data enrichment.

Key Features
Automatically fetches unscraped chemical records from a MySQL database
Uses Google Gemini AI to infer:

Fragrance note (Top / Middle / Base)

Odour class (floral, woody, citrus, musky, etc.)

pH value

📊 Displays processed data in an editable web table

✏️ Allows manual correction or enhancement of AI-generated values

💾 Save All functionality to store data back into MySQL

✅ Marks records as scraped to avoid duplicate processing

🎨 Clean, responsive UI built with HTML, CSS, and Jinja2

🛠️ Technologies Used

Backend

Python

Flask

Google Gemini Generative AI

PyMySQL

MySQL

Frontend

HTML5

CSS3

Jinja2 Templates

AI

Gemini 2.5 Flash Lite Model
