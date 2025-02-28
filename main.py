from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

# Configuração do Flask
app = Flask(__name__, static_folder="static", template_folder="templates")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///retech.db'  # Base de dados SQLite
app.config['SECRET_KEY'] = 'piteira-admin'

# Inicializar extensões
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Modelos da Base de Dados
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500), nullable=False)

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    product = db.relationship('Product')
    
    

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))




######################################################## Rotas de Site ########################################################


######## Página inicial########
@app.route('/')
def index():
    products = Product.query.all()
    return render_template('pagina_inicial.html', product_destaque=products)  # Correto!


########login/registo/logout########
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('profile'))
        flash('Login falhou. Verifica as credenciais.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        
        user = User(username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        
        flash('Conta criada com sucesso!')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    flash('Sessão terminada com sucesso!', 'success')
    return redirect(url_for('index'))

#####################################################Utilizador######################################################
##########Perfil do utilizador##########
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

############Editar perfil#############
@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.username = request.form['username']
        current_user.email = request.form['email']
        db.session.commit()
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('profile'))
    return render_template('edit_profile.html', user=current_user)

##############Eliminar conta##############
@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    db.session.delete(current_user)
    db.session.commit()
    logout_user()
    flash('Conta eliminada com sucesso!', 'success')
    return redirect(url_for('index'))

#######################################################Páginas de produtos############################################

############Produtos############
@app.route('/products', methods=['GET', 'POST'])
def products():
    products = Product.query.all()
    return render_template('products.html', products=products)

###########Detalhes do produto##############
@app.route('/product_details/<int:product_id>', methods=['GET', 'POST'])
def product_details(product_id):
    product = Product.query.get_or_404(product_id)
    recomendados = Product.query.filter(Product.id != product_id).limit(3).all()
    return render_template('product_details.html', product=product, recomendados=recomendados)


####################################################Carrinho de compras############################################

#################CARRINHO#################
cart = []
@app.route('/cart')
@login_required
def cart_page():
    cart = Cart.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price for item in cart)
    return render_template('cart.html', cart=cart, total=total)

#################Adicionar/Remover do carrinho#################
@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    item_existente = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if not item_existente:
        novo_item = Cart(user_id=current_user.id, product_id=product_id)
        db.session.add(novo_item)
        db.session.commit()
        return jsonify({'message': 'Produto adicionado ao carrinho!'})
    return jsonify({'message': 'Produto já está no carrinho!'})


@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    item = Cart.query.filter_by(user_id=current_user.id, id=product_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
        novo_total = sum(i.product.price for i in Cart.query.filter_by(user_id=current_user.id).all())
        return jsonify(success=True, novo_total=novo_total)
    return jsonify(success=False)


#################Finalizar compra#################
@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if request.method == 'POST':
        cart.clear()
        flash('Compra realizada com sucesso!', 'success')
        return redirect(url_for('pagina_inicial'))
    products = [Product.query.get(prod_id) for prod_id in cart]
    return render_template('cart.html', products=products)

####################################################Gestão/ADMIN############################################

######GESTÃO DE PRODUTOS########

# Adicionar produto
@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        nome = request.form.get('name')
        descricao = request.form.get('description')
        preco = float(request.form.get('price'))
        imagem = request.form.get('image_url')  # Pode ser melhorado com upload real
        new_product = Product(nome=nome, descricao=descricao, preco=preco, imagem=imagem)
        db.session.add(new_product)
        db.session.commit()
        flash('Produto adicionado com sucesso!', 'success')
        return redirect(url_for('index'))
    return render_template('add_product.html')

# Editar produto
@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    produto = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        produto.nome = request.form.get('name')
        produto.descricao = request.form.get('description')
        produto.preco = float(request.form.get('price'))
        produto.imagem = request.form.get('image_url')
        db.session.commit()
        flash('Produto atualizado com sucesso!', 'success')
        return redirect(url_for('index'))
    return render_template('edit_product.html', produto=produto)

# Eliminar produto
@app.route('/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    produto = Product.query.get_or_404(product_id)
    db.session.delete(produto)
    db.session.commit()
    flash('Produto removido!', 'success')
    return redirect(url_for('index'))


# Páginas adicionais###############TRABALHAR MAIS TARDE##################
@app.route('/categories')
def categories():
    return render_template('Categorias.html')

@app.route('/manage_users')
@login_required
def manage_users():
    return render_template('Gestaoutilizador.html')

@app.route('/portfolio')
def portfolio():
    return render_template('portfolio.html')

@app.route('/about')
def about():
    return render_template('Sobrenos.html')

@app.route('/contact')
def contact():
    return render_template('Contactos.html')

@app.route('/faqs')
def faqs():
    return render_template('Faqs.html')

@app.route('/legal')
def legal():
    return render_template('Legal.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
