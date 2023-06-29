from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
@app.route('/hello-world')
def index():
    exemplify_loop = list('abracadabra')
    return render_template('index.html', example_list=exemplify_loop)
