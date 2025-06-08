from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello from M5Stack Python App!"

if __name__ == '__main__':
    app.run(debug=True)
