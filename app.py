from flask import Flask, render_template, request, jsonify
import psycopg2
import psycopg2.extras

app = Flask(__name__)

DB_HOST = "localhost"
DB_NAME = "tcc_db"
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
            query = "SELECT * from researcher ORDER BY id"
            cur.execute(query)
            employee = cur.fetchall()
        else:
            cur.execute('''
            SELECT id::uuid, name::varchar, citations::varchar, abstract::varchar,
                   abstract_en::varchar, other_information::varchar, qtt_publications::int,
                   ts_rank(search, websearch_to_tsquery('simple', %s)) +
                   ts_rank(search, websearch_to_tsquery('english', %s)) AS rank
            FROM researcher
            WHERE search @@ websearch_to_tsquery('simple', %s) OR
                  search @@ websearch_to_tsquery('english', %s)
            ORDER BY rank DESC;
            ''', (search_word, search_word, search_word, search_word))
            #cur.execute('SELECT abstract FROM researcher WHERE search @@ websearch_to_tsquery(%s)', (search_word,))
            #cur.execute('SELECT * FROM researcher WHERE name LIKE %s', ('%' + search_word + '%',))
            numrows = int(cur.rowcount)
            employee = cur.fetchall()
            print(numrows)
    return jsonify({'htmlresponse': render_template('response.html', employee=employee, numrows=numrows)})


if __name__ == "__main__":
    app.run(debug=True)