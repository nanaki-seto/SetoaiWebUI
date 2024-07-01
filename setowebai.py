from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import requests
import webbrowser
import re
from transformers import AutoTokenizer, AutoModelForCausalLM

# Load the CodeT5 model and tokenizer
model_name = "codeparrot/codeparrot-small-multi"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Load or initialize knowledge base
knowledge_file = "knowledge_base.json"

def load_knowledge_base():
    try:
        with open(knowledge_file, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_knowledge_base(data):
    with open(knowledge_file, 'w') as file:
        json.dump(data, file, indent=4)

# Load knowledge base at start
knowledge_base = load_knowledge_base()

def generate_code(prompt):
    inputs = tokenizer.encode(prompt, return_tensors="pt", max_length=512, truncation=True)
    outputs = model.generate(inputs, max_length=256, num_return_sequences=1, temperature=0.7)
    code = tokenizer.decode(outputs[0], skip_special_tokens=True)
    code_lines = code.split('\n')
    code = '\n'.join(line for line in code_lines if not line.startswith('#') and line.strip())
    return code.strip()

def handle_math(query):
    try:
        result = eval(query)
        return str(result)
    except Exception as e:
        return f"Error in calculation: {str(e)}"

def handle_general_query(query):
    responses = {
        "hi": "Hello! How can I assist you today?",
        "how are you": "I'm just a computer program, but I'm here to help you!",
        "what's your name": "I'm SetoAI, your assistant.",
        "hello": "Hi there! How can I assist you?",
        "thanks": "You're welcome! Anything else I can help with?",
        "goodbye": "Goodbye! Have a great day!",
        "help": "I'm here to assist you with your inquiries. You can ask me about weather, math calculations, code generation, PubMed searches, or web scraping."
    }
    return responses.get(query.lower(), "I'm here to assist you with your inquiries. How can I help today?")

def get_weather(location):
    api_key = "43baab3cc93535014e2d61b94fa444fd"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=imperial"
    try:
        response = requests.get(url)
        data = response.json()
        if data.get("weather"):
            description = data["weather"][0]["description"]
            temperature = data["main"]["temp"]
            weather_info = f"Weather in {location}: {description}, Temperature: {temperature}°F"
            return weather_info
        else:
            return "Weather data not found. Please check the location name."
    except Exception as e:
        return f"Unable to retrieve weather data. Error: {str(e)}"

def search_pubmed(query):
    if query in knowledge_base:
        return knowledge_base[query]
    
    api_key = "840a8f7fb9d5c94b07dcd0b2ec86f0e23f09"
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={query}&retmode=json&retmax=20&apikey={api_key}"
    try:
        response = requests.get(url)
        data = response.json()
        if "esearchresult" in data and "idlist" in data["esearchresult"]:
            ids = data["esearchresult"]["idlist"]
            results = []
            for pmid in ids:
                fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid}&retmode=json"
                fetch_response = requests.get(fetch_url)
                fetch_data = fetch_response.json()
                if "result" in fetch_data and pmid in fetch_data["result"]:
                    title = fetch_data["result"][pmid]["title"]
                    link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}"
                    results.append({"title": title, "link": link})
            
            knowledge_base[query] = results
            save_knowledge_base(knowledge_base)
            
            return results
        else:
            return "No results found on PubMed."
    except Exception as e:
        return f"Error retrieving PubMed data: {str(e)}"

def web_scrape(url):
    if url in knowledge_base:
        return knowledge_base[url]
    
    if not url.startswith("http://") and not url.startswith("https://"):
        return "Invalid URL. Ensure it starts with 'http://' or 'https://'."
    try:
        headers = {'User-Agent': 'SetoAIv1/1.0'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        text_content = response.text
        
        text_content = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', text_content)
        text_content = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', text_content)
        text_content = re.sub('<[^<]+?>', '', text_content)
        text_content = re.sub(r'\s+','', text_content).strip()
        
        knowledge_base[url] = text_content
        save_knowledge_base(knowledge_base)
        
        return text_content
    except Exception as e:
        return f"Failed to scrape the website. Error: {str(e)}"

def retrieve_stored_info(query):
    parts = re.split(r'\b(and|or)\b', query.lower())
    matches = []

    for part in parts:
        part = part.strip()
        for key, value in knowledge_base.items():
            if part in key.lower():
                if isinstance(value, list):
                    matches.extend(value)
                else:
                    matches.append(value)
    
    if matches:
        return "\n".join(str(match) for match in matches)
    else:
        return f"No stored information found matching '{query}'."

def generate_response(message, conversation_history):
    if message.lower().startswith("retrieve"):
        query = message[9:].strip()
        response = retrieve_stored_info(query)
    elif message.lower().startswith("weather in"):
        location = message[11:].strip()
        response = get_weather(location)
    elif "calculate" in message.lower() or re.match(r"^\d+[\+\-\*/]\d+", message.lower()):
        query = re.findall(r"(\d+[\+\-\*/]\d+)", message.lower())
        response = handle_math(query[0] if query else message)
    elif message.lower().startswith("search pubmed for"):
        search_term = message[18:].strip()
        results = search_pubmed(search_term)
        response = "\n".join([f"{result['title']}\n{result['link']}" for result in results])
    elif message.lower().startswith("generate code"):
        prompt = message[14:].strip()
        response = generate_code(prompt)
    elif message.lower().startswith("scrape"):
        url = message[7:].strip()
        response = web_scrape(url)
    else:
        response = handle_general_query(message)
    
    return response

class RequestHandler(BaseHTTPRequestHandler):
    conversation_history = []

    def do_GET(self):
        if self.path == "/":
            self.serve_file('index.html', 'text/html')
        elif self.path == "/style.css":
            self.serve_file('style.css', 'text/css')
        elif self.path == "/script.js":
            self.serve_file('script.js', 'application/javascript')
        else:
            self.send_error(404, "File not found")

    def serve_file(self, filename, content_type):
        try:
            with open(filename, 'rb') as file:
                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.end_headers()
                self.wfile.write(file.read())
        except FileNotFoundError:
            self.send_error(404, "File not found")

    def do_POST(self):
        if self.path == "/ai":
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                user_input = json.loads(post_data.decode())['userInput']
                response = generate_response(user_input, self.conversation_history)
                self.conversation_history.append(('User', user_input))
                self.conversation_history.append(('AI', response))

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'prediction': response}).encode())
            except Exception as e:
                self.send_error(500, f"Internal Server Error: {e}")

def run(server_class=HTTPServer, handler_class=RequestHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting server on port {port}...')
    httpd.serve_forever()

if __name__ == "__main__":
    run()