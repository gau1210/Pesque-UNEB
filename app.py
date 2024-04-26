from flask import Flask, render_template, request, jsonify
import psycopg2  # pip install psycopg2
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


@app.route("/searchdata", methods=["POST", "GET"])
def searchdata():
    if request.method == 'POST':
        search_word = request.form['search_word']

        def removePontuacao(texto):
            pontuacao = ".,:;!-?"
            for p in pontuacao:
                texto = texto.replace(p, " ")
            return texto

        texto_limpo = removePontuacao(search_word)
        print("Texto limpo:", texto_limpo)

        def contaPalavras(texto):
            s = removePontuacao(texto)
            lista = s.split()
            print("lista de palvras buscada:", lista)
            return len(lista)

        num_palavras = contaPalavras(texto_limpo)
        print("Qntd de palavras dig:", num_palavras)

        if num_palavras >= 3:
            termos = texto_limpo.split()

            if len(termos) >= 2:
                termo1 = termos[0]
                termo2 = termos[1]

                cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                cur.execute(
                    "SELECT * FROM researcher WHERE search @@ websearch_to_tsquery('simple', %s || ' <-> ' || %s);",
                    (termo1, termo2))
                numrows = int(cur.rowcount)
                employee = cur.fetchall()
                print("Registros encontrados:", numrows)
                return jsonify({'data': render_template('response.html', employee=employee, numrows=numrows)})

        else:

            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cur.execute("SELECT * FROM researcher WHERE search @@ websearch_to_tsquery('simple', %s);", (texto_limpo,))
            numrows = int(cur.rowcount)
            employee = cur.fetchall()
            print(numrows)
            return jsonify({'data': render_template('response.html', employee=employee, numrows=numrows)})


if __name__ == "__main__":
    app.run(debug=True)