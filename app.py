from flask import Flask, jsonify, send_from_directory, url_for, render_template, request
import psycopg2  # pip install psycopg2
import psycopg2.extras
import csv
import os
from nltk.corpus import stopwords 
from nltk.tokenize import word_tokenize
stop_words = set(stopwords.words('portuguese'))

#Precisa instalar essa biblioteca pelo cmd python
#import nltk
#nltk.download('punkt')

app = Flask(__name__)

app.config['DOWNLOAD_FOLDER'] = r'C:\caminho\para\seu\diretorio\de\downloads'

DB_HOST = "localhost"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "1989"


conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)

def removePontuacao(texto):
    pontuacao = ".,:;!?-"
    for p in pontuacao:
        texto = texto.replace(p, " ")
    return texto

def contaPalavras(texto):
    s = removePontuacao(texto)
    lista = s.split()
    print("lista de palvras buscada:", lista)
    return len(lista)

def removeStop(texto):
    palavras = word_tokenize(texto)
    palavras_filtradas = [palavra for palavra in palavras if palavra.lower() not in stop_words]

    return palavras_filtradas

def operadoresBoleanos(texto):

    operadores = ["and","or","not"]
    palavras = word_tokenize(texto.lower())
    operadores_boleanos = [palavra for palavra in palavras if palavra.lower() in operadores]

    return operadores_boleanos


@app.route('/')
def index():
    return render_template('index.html')

@app.route("/download_csv/<filename>")
def download_csv(filename):
    return send_from_directory(directory=app.config['DOWNLOAD_FOLDER'], path=filename, as_attachment=True)

@app.route("/searchdata", methods=["POST", "GET"])
def searchdata():
    if request.method == 'POST':
        search_word = request.form['search_word']
        texto_limpo = removePontuacao(search_word)
        print("Texto limpo:", texto_limpo)
        num_palavras = contaPalavras(texto_limpo)
        print("Qntd de palavras dig:", num_palavras)
        palavras_filtradas = removeStop(texto_limpo)
        operadores_boleanos = operadoresBoleanos(texto_limpo)

        if num_palavras <= 3:

            termos = palavras_filtradas
            operador = operadores_boleanos
            print("Termo sem StopWord:", termos)
            print("Operador selecionado:",operador)

            if len(termos) == 2:

                termo1 = termos[0]
                termo2 = termos[1]

                print('Termos selecionados:', termo1, termo2)

                cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                cur.execute(
                    "SELECT *, ts_rank_cd(document, websearch_to_tsquery('simple', %s || ' <-> ' || %s)) AS rank FROM "
                    "search_index WHERE document @@ websearch_to_tsquery('simple', %s || ' <-> ' || %s) ORDER BY rank "
                    "DESC;",
                    (termo1, termo2, termo1, termo2)
                )
                numrows = int(cur.rowcount)
                employee = cur.fetchall()

                csv_filename = 'relatorio.csv'
                csv_path = os.path.join(app.config['DOWNLOAD_FOLDER'], csv_filename)

                # Escreve os resultados no arquivo CSV, selecionando apenas as colunas desejadas
                with open(csv_path, "w", newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["name", "nome_programa"])  # Cabeçalho do CSV
                    for row in employee:
                        writer.writerow([row['name'], row['nome_programa']])

                print("Registros encontrados:", numrows)

                os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

                return jsonify({
                    'data': render_template('response.html', employee=employee, numrows=numrows),
                    'csv_url': url_for('download_csv', filename=csv_filename)
                })
             
            else:
                if operador == ['and']:

                    termo1 = termos[0]
                    termo2 = termos[2]

                    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                    cur.execute("SELECT * FROM search_index WHERE document @@ to_tsquery('simple', %s || ' & ' || %s);", (termo1,termo2))
                    print("Query procurada quando and")
                    numrows = int(cur.rowcount)
                    employee = cur.fetchall()
                    print(numrows)
                    return jsonify({'data': render_template('response.html', employee=employee, numrows=numrows)})
                
                else:
                    if operador == ['or']:
                
                        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                        cur.execute("SELECT * FROM search_index WHERE document @@ websearch_to_tsquery('simple', %s);", (texto_limpo,))
                        print("Query procurada quando or")
                        numrows = int(cur.rowcount)
                        employee = cur.fetchall()
                        print(numrows)
                        return jsonify({'data': render_template('response.html', employee=employee, numrows=numrows)})
                    else:
                        if operador == ['not']:

                            termo1 = termos[0]
                            termo2 = termos[2]

                            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                            cur.execute("SELECT * FROM search_index WHERE document @@ to_tsquery('simple', %s || ' & ! ' || %s);", (termo1,termo2))
                            print("Query procurada quando not")
                            numrows = int(cur.rowcount)
                            employee = cur.fetchall()
                            print(numrows)
                            return jsonify({'data': render_template('response.html', employee=employee, numrows=numrows)})
                        
                        else:

                            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                            cur.execute("SELECT * FROM search_index WHERE document @@ websearch_to_tsquery('simple', %s);", (texto_limpo,))
                            print("teste1")
                            numrows = int(cur.rowcount)
                            employee = cur.fetchall()
                            print(numrows)
                            return jsonify({'data': render_template('response.html', employee=employee, numrows=numrows)})       
        else:

            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cur.execute("SELECT * FROM search_index WHERE document @@ websearch_to_tsquery('simple', %s);", (texto_limpo,))
            print("teste2")
            numrows = int(cur.rowcount)
            employee = cur.fetchall()
            print(numrows)
            return jsonify({'data': render_template('response.html', employee=employee, numrows=numrows)})


if __name__ == "__main__":
    app.run(debug=True)
