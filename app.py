from flask import Flask, jsonify, send_from_directory, url_for, render_template, request
import psycopg2  # pip install psycopg2
import psycopg2.extras
from uuid import UUID  # Adicionando a importação da classe UUID
import csv
import os
from nltk.corpus import stopwords 
from nltk.tokenize import word_tokenize
stop_words = set(stopwords.words('portuguese'))

#Precisa instalar essa biblioteca pelo cmd python
#import nltk
#nltk.download('punkt')

app = Flask(__name__)

app.config['DOWNLOAD_FOLDER'] = r'C:\Pesque-UNEB\dados'

#app.config['DOWNLOAD_FOLDER'] = r'C:\caminho\para\seu\diretorio\de\downloads'

DB_HOST = "localhost"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "1989"


conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)

# Função para remover pontuações do texto
def removePontuacao(texto):
    pontuacao = ".,:;!?-"
    for p in pontuacao:
        texto = texto.replace(p, " ")
    return texto

# Função para contar o número de palavras no texto
def contaPalavras(texto):
    s = removePontuacao(texto)
    lista = s.split()
    print("lista de palvras buscada:", lista)
    return len(lista)

# Função para remover stopwords do texto
def removeStop(texto):
    palavras = word_tokenize(texto)
    palavras_filtradas = [palavra for palavra in palavras if palavra.lower() not in stop_words]

    return palavras_filtradas

# Função para identificar operadores booleanos no texto
def operadoresBoleanos(texto):

    operadores = ["and","or","not"]
    palavras = word_tokenize(texto.lower())
    operadores_boleanos = [palavra for palavra in palavras if palavra.lower() in operadores]

    return operadores_boleanos

# Rota para a página inicial
@app.route('/')
def index():
    return render_template('index.html')

# Rota para autocompletar sugestões de pesquisa
@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    search_query = request.args.get('q', '')

    # Extrair o último termo da consulta
    last_term = search_query.split()[-1]

    suggestions = []

    if last_term:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Remove o último termo da consulta original
        original_query = ' '.join(search_query.split()[:-1])

        # Função similarity() junto com a função <-> para ordenar os resultados pelo operador de distância de trigramas
        cur.execute("SELECT word FROM unique_lexeme WHERE similarity(word, %s) >= 0.5 ORDER BY word <-> %s;", (last_term, last_term))
        db_suggestions = [row['word'] for row in cur.fetchall()]

        # Concatenar o último termo da consulta com cada sugestão do banco de dados
        suggestions = [original_query + ' ' + suggestion for suggestion in db_suggestions]

    return jsonify(suggestions)

# Rota para obter detalhes de um item específico
@app.route("/get_details/<id>")
def get_details(id):
    try:
        uuid_obj = UUID(id, version=4)  # Verifica se o ID fornecido é um UUID válido
    except ValueError:
        return "ID inválido", 404  # Retorna um erro 404 se o ID não for um UUID válido

    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT * FROM search_index WHERE id = %s", (id,))
    details = cur.fetchone()
    return render_template('details.html', details=details)

# Rota para baixar um arquivo CSV    
@app.route("/download_csv/<filename>")
def download_csv(filename):
    return send_from_directory(directory=app.config['DOWNLOAD_FOLDER'], path=filename, as_attachment=True)

# Rota para lidar com a pesquisa de dados
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
                    writer.writerow(["name", "abstract"])  # Cabeçalho do CSV
                    for row in employee:
                        writer.writerow([row['name'], row['abstract']])

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
            
                    csv_filename = 'relatorio.csv'
                    csv_path = os.path.join(app.config['DOWNLOAD_FOLDER'], csv_filename)

                    # Certifique-se de que a pasta de download exista antes de criar o arquivo CSV
                    os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

                    with open(csv_path, "w", newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(["name", "abstract"]) 
                        for row in employee:
                            writer.writerow([row['name'], row['abstract']])

                    print("Registros encontrados:", numrows)

                    # Retorna um JSON com o URL para baixar o arquivo CSV
                    return jsonify({
                        'data': render_template('response.html', employee=employee, numrows=numrows),
                        'csv_url': url_for('download_csv', filename=csv_filename)
                    })
                                    
                else:
                    if operador == ['or']:
                
                        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                        cur.execute("SELECT * FROM search_index WHERE document @@ websearch_to_tsquery('simple', %s);", (texto_limpo,))
                        print("Query procurada quando or")
                        numrows = int(cur.rowcount)
                        employee = cur.fetchall()
                        
                        csv_filename = 'relatorio.csv'
                        csv_path = os.path.join(app.config['DOWNLOAD_FOLDER'], csv_filename)

                        with open(csv_path, "w", newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            writer.writerow(["name", "abstract"])  
                            for row in employee:
                                writer.writerow([row['name'], row['abstract']])

                        print("Registros encontrados:", numrows)

                        os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

                        return jsonify({
                            'data': render_template('response.html', employee=employee, numrows=numrows),
                            'csv_url': url_for('download_csv', filename=csv_filename)
                        })
                    else:
                        if operador == ['not']:

                            termo1 = termos[0]
                            termo2 = termos[2]

                            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                            cur.execute("SELECT * FROM search_index WHERE document @@ to_tsquery('simple', %s || ' & ! ' || %s);", (termo1,termo2))
                            print("Query procurada quando not")
                            numrows = int(cur.rowcount)
                            employee = cur.fetchall()
                            
                            csv_filename = 'relatorio.csv'
                            csv_path = os.path.join(app.config['DOWNLOAD_FOLDER'], csv_filename)

                            with open(csv_path, "w", newline='', encoding='utf-8') as f:
                                writer = csv.writer(f)
                                writer.writerow(["name", "abstract"])
                                for row in employee:
                                    writer.writerow([row['name'], row['abstract']])

                            print("Registros encontrados:", numrows)

                            os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

                            return jsonify({
                                'data': render_template('response.html', employee=employee, numrows=numrows),
                                'csv_url': url_for('download_csv', filename=csv_filename)
                            })
                        
                        else:

                            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
                            cur.execute("SELECT * FROM search_index WHERE document @@ websearch_to_tsquery('simple', %s);", (texto_limpo,))
                            print("teste1")
                            numrows = int(cur.rowcount)
                            employee = cur.fetchall()
                            
                            csv_filename = 'relatorio.csv'
                            csv_path = os.path.join(app.config['DOWNLOAD_FOLDER'], csv_filename)

                            with open(csv_path, "w", newline='', encoding='utf-8') as f:
                                writer = csv.writer(f)
                                writer.writerow(["name", "abstract"])
                                for row in employee:
                                    writer.writerow([row['name'], row['abstract']])

                            print("Registros encontrados:", numrows)

                            os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

                            return jsonify({
                                'data': render_template('response.html', employee=employee, numrows=numrows),
                                'csv_url': url_for('download_csv', filename=csv_filename)
                            })      
        else:

            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            #cur.execute("SELECT * FROM search_index WHERE document @@ websearch_to_tsquery('simple', %s);", (texto_limpo,))
            cur.execute(
                    "SELECT *, ts_rank_cd(document, websearch_to_tsquery('simple', %s)) AS rank FROM "
                    "search_index WHERE document @@ websearch_to_tsquery('simple', %s) ORDER BY rank "
                    "DESC;",
                    (texto_limpo,texto_limpo)
                )
            print("teste2")
            numrows = int(cur.rowcount)
            employee = cur.fetchall()
            
            csv_filename = 'relatorio.csv'
            csv_path = os.path.join(app.config['DOWNLOAD_FOLDER'], csv_filename)

            with open(csv_path, "w", newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["name", "abstract"])
                for row in employee:
                    writer.writerow([row['name'], row['abstract']])

            print("Registros encontrados:", numrows)

            os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

            return jsonify({
                'data': render_template('response.html', employee=employee, numrows=numrows),
                'csv_url': url_for('download_csv', filename=csv_filename)
        })
        
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)