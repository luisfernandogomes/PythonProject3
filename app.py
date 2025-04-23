from flask import Flask, jsonify, redirect, request
from flask_pydantic_spec import FlaskPydanticSpec
from datetime import date
from dateutil.relativedelta import relativedelta
from models import db_session, Livros, Emprestimos, Usuarios
from datetime import date
from dateutil.relativedelta import relativedelta
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, desc

app = Flask(__name__)
spec = FlaskPydanticSpec('Flask',
                         title='Flask API',
                         version='1.0.0')
spec.register(app)
app.secret_key = 'chave_secreta'

@app.route('/')
def index():
    return redirect('/consultar_livros')


@app.route('/consultar_usuarios', methods=['GET'])
def consultar_usuarios():
    try:
        usuarios = db_session.execute(select(Usuarios)).scalars().all()

        lista_usuarios = []
        for usuario in usuarios:
            lista_usuarios.append(usuario.get_usuario())

        return jsonify({'usuarios_cadastrados': lista_usuarios})
    except Exception as e:
        return jsonify({'error': 'Erro ao consultar usuários', 'detalhes': str(e)}), 500


@app.route('/consultar_livros')
def consultar_livros():
    try:
        lista_livros = select(Livros)
        lista_livros = db_session.execute(lista_livros).scalars()
        result = []
        for livro in lista_livros:
            result.append(livro.get_livro())
        db_session.close()


        result_disponiveis = []
        lista_livros_disponiveis = select(Livros)
        lista_livros_disponiveis = db_session.execute(lista_livros_disponiveis.filter(Livros.status)).scalars()
        for livros in lista_livros_disponiveis:
            result_disponiveis.append(livros.get_livro())
        db_session.close()



        return jsonify({'livros no catalogo da biblioteca': result},
                       {'livros disponiveis para emprestimos': result_disponiveis})
    except IntegrityError as e:
        return jsonify({'error': str(e)})

@app.route('/cadastrar_livro', methods=['POST'])
def cadastrar_livro():
    if request.method == 'POST':

        titulo = request.form.get('titulo')
        autor = request.form.get('autor')
        resumo = request.form.get('resumo')
        isbn = request.form.get('ISBN')
        isbn_existente = select(Livros)
        isbn_existente = db_session.execute(isbn_existente.filter_by(ISBN=isbn)).first()
        if isbn_existente:
            return jsonify({'isbn já existente': isbn_existente})
        if not titulo:
            return jsonify({"error": 'campo titulo vazio'}, 400)
        if not autor:
            return jsonify({"error": 'campo autor vazio'}, 400)
        if not resumo:
            return jsonify({"error": 'campo resumo vazio'}, 400)
        if not isbn:
            return jsonify({"error": 'campo ISBN vazio'}, 400)
        else:
            try:
                isbn = int(isbn)
                livro_salvado = Livros(titulo=titulo,
                                       autor=autor,
                                       resumo=resumo,
                                       ISBN=isbn,
                                       status=True)
                livro_salvado.save()
                if livro_salvado.status:
                    status_emprestimo = 'Está disponivel para emprestimo'
                else:
                    status_emprestimo = 'Livro não está disponivel para emprestimo'
                return jsonify({
                    'titulo': livro_salvado.titulo,
                    'autor': livro_salvado.autor,
                    'resumo': livro_salvado.resumo,
                    'status': status_emprestimo,
                    'ISBN': livro_salvado.ISBN
                })
            except IntegrityError as e:
                return jsonify({'error': str(e)})

@app.route('/cadastrar_usuario', methods=['POST'])
def cadastrar_usuario():
    if request.method == 'POST':
        nome = request.form.get('nome')
        cpf = request.form.get('cpf')
        endereco = request.form.get('endereco')

        cpf_ja_cadastrado = select(Usuarios)
        cpf_ja_cadastrado = db_session.execute(cpf_ja_cadastrado.filter_by(CPF=cpf)).first()
        if cpf_ja_cadastrado:
            return jsonify({"error": 'CPF ja cadastrado'})

        endereco_ja_cadastrado = select(Usuarios)
        endereco_ja_cadastrado = db_session.execute(endereco_ja_cadastrado.filter_by(endereco=endereco)).first()
        if endereco_ja_cadastrado:
            return jsonify({"error": 'endereco ja cadastrado'})
        if not nome:
            return jsonify({"error": 'campo nome vazio'}, 400)
        if not cpf:
            return jsonify({"error": 'campo cpf vazio'}, 400)
        if not endereco:
            return jsonify({"error": 'campo endereco vazio'}, 400)
        else:
            try:
                usuario_salvado = Usuarios(nome=nome,
                                           CPF=cpf,
                                           endereco=endereco)
                usuario_salvado.save()
                return jsonify({
                    'titulo': usuario_salvado.nome,
                    'autor': usuario_salvado.CPF,
                    'resumo': usuario_salvado.endereco})
            except IntegrityError as e:
                return jsonify({'error': str(e)})

@app.route('/cadastrar_emprestimo', methods=['POST'])
def cadastrar_emprestimo():
    try:
        data_emprestimo = date.today()
        data_de_devolucao = data_emprestimo + relativedelta(weeks=5)

        isbn = request.form.get('isbn')
        id_usuario = request.form.get('id_usuario')

        if not isbn or not id_usuario:
            return jsonify({'error': 'Campos ISBN e id_usuario são obrigatórios'}), 400

        isbn = int(isbn)
        id_usuario = int(id_usuario)

        livro = db_session.execute(select(Livros).filter_by(ISBN=isbn)).scalar()
        if not livro:
            return jsonify({'error': 'Livro não encontrado'}), 404

        if not livro.status:
            return jsonify({'error': 'Livro não está disponível para empréstimo'}), 400

        usuario = db_session.get(Usuarios, id_usuario)
        if not usuario:
            return jsonify({'error': 'Usuário não encontrado'}), 404

        # Cadastrar empréstimo
        emprestimo = Emprestimos(
            data_emprestimo=data_emprestimo,
            data_de_devolucao=data_de_devolucao,
            ISBN_livro=isbn,
            id_usuario=id_usuario
        )
        emprestimo.save()

        # Atualiza status do livro para indisponível
        livro.status = False
        livro.save()

        return jsonify({
            'data_emprestimo': emprestimo.data_emprestimo,
            'data_de_devolucao': emprestimo.data_de_devolucao,
            'ISBN_livro': emprestimo.ISBN_livro,
            'id_usuario': emprestimo.id_usuario
        })
    except IntegrityError as e:
        db_session.rollback()
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': 'Erro ao cadastrar empréstimo', 'detalhes': str(e)}), 500


@app.route('/atualizar_usuario/<int:id>', methods=['PUT'])
def atualizar_usuario(id):
    usuario = db_session.get(Usuarios, id)
    if not usuario:
        return jsonify({'error': 'Usuário não encontrado'}), 404

    nome = request.form.get('nome')
    cpf = request.form.get('cpf')
    endereco = request.form.get('endereco')

    if nome:
        usuario.nome = nome
    if cpf:
        usuario.CPF = cpf
    if endereco:
        usuario.endereco = endereco

    usuario.save()
    return jsonify({'mensagem': 'Usuário atualizado com sucesso', 'dados': usuario.get_usuario()})


@app.route('/atualizar_livro/<int:id>', methods=['PUT'])
def atualizar_livro(id):
    livro = db_session.get(Livros, id)
    if not livro:
        return jsonify({'error': 'Livro não encontrado'}), 404

    titulo = request.form.get('titulo')
    autor = request.form.get('autor')
    resumo = request.form.get('resumo')
    status = request.form.get('status')  # True ou False como string

    if titulo:
        livro.titulo = titulo
    if autor:
        livro.autor = autor
    if resumo:
        livro.resumo = resumo
    if status is not None:
        livro.status = status.lower() == 'true'

    livro.save()
    return jsonify({'mensagem': 'Livro atualizado com sucesso', 'dados': livro.get_livro()})

@app.route('/excluir_livro/<int:id>', methods=['DELETE'])
def excluir_livro(id):
    livro = db_session.get(Livros, id)
    if not livro:
        return jsonify({'error': 'Livro não encontrado'}), 404

    emprestado = db_session.query(Emprestimos).filter_by(ISBN_livro=livro.ISBN).first()
    if emprestado:
        return jsonify({'error': 'Livro não pode ser excluído, pois está emprestado'}), 400

    livro.delete()
    return jsonify({'mensagem': 'Livro excluído com sucesso'})

@app.route('/emprestimos_por_usuario/<int:id_usuario>', methods=['GET'])
def emprestimos_por_usuario(id_usuario):
    emprestimos = db_session.query(Emprestimos).filter_by(id_usuario=id_usuario).all()
    if not emprestimos:
        return jsonify({'mensagem': 'Nenhum empréstimo encontrado para este usuário'})

    lista_emprestimos = [e.get_emprestimo() for e in emprestimos]
    return jsonify({'emprestimos': lista_emprestimos})


'''
Atendimento à biblioteca: A API deve fornecer funcionalidades para:
a. Cadastro de novos livros; ✅
b. Cadastro de novos usuários;✅
c. Realização de empréstimos;✅
d. Consulta de livros disponíveis e emprestados;✅
e. Consulta de histórico de empréstimos por usuário;❌
f. Atualização de informações de livros e usuários;❌
g. Exclusão de livros e usuários (com regras de negócio adequadas).❌
'''
if __name__ == '__main__':
    app.run(debug=True)