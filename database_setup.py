from main import app, db

# Criar a base de dados dentro do contexto correto da aplicação
with app.app_context():
    db.create_all()
    print("Base de dados criada com sucesso!")
