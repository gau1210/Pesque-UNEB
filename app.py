from flask import Flask, render_template, request, jsonify
import psycopg2
import psycopg2.extras

app = Flask(__name__)

DB_HOST = "localhost"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "1989"

conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)


@app.route('/')
def index():
    return render_template('index.html')


@app.route("/ajaxlivesearch", methods=["POST", "GET"])
def ajaxlivesearch():
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        search_word = request.form['query']
        print(search_word)
        if search_word == '':
            query = "SELECT * from employee ORDER BY id"
            cur.execute(query)
            employee = cur.fetchall()
        else:
            cur.execute('SELECT * FROM employee WHERE name LIKE %(name)s', {'name': '%{}%'.format(search_word)})
            numrows = int(cur.rowcount)
            employee = cur.fetchall()
            print(numrows)
    return jsonify({'htmlresponse': render_template('response.html', employee=employee, numrows=numrows)})


if __name__ == "__main__":
    app.run(debug=True)