from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import markdown
import re
import nltk
from nltk.tokenize import sent_tokenize
from heapq import nlargest
import os

# Ensure that necessary NLTK resources are downloaded
nltk.download('punkt')
nltk.download('stopwords')

app = Flask(__name__)

# Function to convert markdown to HTML
def markdown_to_html(markdown_text):
    return markdown.markdown(markdown_text)

# Function to extract text from HTML
def extract_text_from_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    return text

# Function to clean the extracted text
def clean_text(text):
    cleaned_text = re.sub(r'!\[.*\]\(.*\)', '', text)  # Remove images
    cleaned_text = re.sub(r'\[.*\]\(.*\)', '', cleaned_text)  # Remove links
    cleaned_text = re.sub(r'\n+', '\n', cleaned_text)  # Remove extra newlines
    cleaned_text = cleaned_text.strip()
    return cleaned_text

# Function to summarize the text using NLTK
def summarize_text_nltk(text, n=3):
    sentences = sent_tokenize(text)
    words = nltk.word_tokenize(text.lower())
    word_frequencies = {}

    # Calculate word frequencies excluding stopwords
    for word in words:
        if word not in nltk.corpus.stopwords.words('english') and word.isalnum():
            word_frequencies[word] = word_frequencies.get(word, 0) + 1

    # Rank sentences by word frequencies
    sentence_scores = {}
    for sentence in sentences:
        sentence_scores[sentence] = sum(word_frequencies.get(word, 0) for word in nltk.word_tokenize(sentence.lower()))

    # Get the top N sentences (adjust N to control summary size)
    summary = nlargest(n, sentence_scores, key=sentence_scores.get)
    
    # Sort summary sentences to maintain their order in the text
    summary_sorted = sorted(summary, key=lambda x: sentences.index(x))
    
    return '\n'.join(summary_sorted)  # Return summary as markdown formatted text

# Function to handle file input (either URL or local file)
def process_file(input_path, is_url=False):
    if is_url:
        response = requests.get(input_path)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            paragraphs = soup.find_all('p')

            markdown_content = '# Scraped Content\n\n'

            for heading in headings:
                markdown_content += f'## {heading.text.strip()}\n\n'

            for para in paragraphs:
                markdown_content += f'{para.text.strip()}\n\n'

            return markdown_content
        else:
            return None
    else:
        try:
            with open(input_path, 'r', encoding='utf-8') as file:
                markdown_content = file.read()
            return markdown_content
        except FileNotFoundError:
            return None

@app.route('/', methods=['GET', 'POST'])
def index():
    summary_text = ""
    debug_message = ""
    
    if request.method == 'POST':
        file_or_url = request.form.get('file_or_url')
        
        if file_or_url == 'file':
            # Handle file upload
            file = request.files['file']
            if file:
                # Save the uploaded file temporarily
                filename = os.path.join('uploads', file.filename)
                if not os.path.exists('uploads'):
                    os.makedirs('uploads')
                file.save(filename)
                
                # Process the local file
                markdown_content = process_file(filename, is_url=False)
                if markdown_content:
                    html_content = markdown_to_html(markdown_content)
                    extracted_text = extract_text_from_html(html_content)
                    cleaned_text = clean_text(extracted_text)
                    summary_text = summarize_text_nltk(cleaned_text)
                else:
                    summary_text = "Error: File could not be processed."
            else:
                summary_text = "No file uploaded."
        elif file_or_url == 'url':
            # Handle URL input
            url = request.form.get('url')
            markdown_content = process_file(url, is_url=True)
            if markdown_content:
                html_content = markdown_to_html(markdown_content)
                extracted_text = extract_text_from_html(html_content)
                cleaned_text = clean_text(extracted_text)
                summary_text = summarize_text_nltk(cleaned_text)
            else:
                summary_text = "Error: URL could not be processed."
        elif file_or_url == 'text':
            # Handle text input
            text = request.form.get('text')
            if text:
                cleaned_text = clean_text(text)
                summary_text = summarize_text_nltk(cleaned_text, n=3)  # Ensure the summary is shorter
            else:
                summary_text = "No text provided."
        
        # Debugging message (Optional)
        debug_message = f"Form submitted with file_or_url={file_or_url}"
        
    return render_template('index.html', summary_text=summary_text, debug_message=debug_message)

if __name__ == '__main__':
    app.run(debug=True)
