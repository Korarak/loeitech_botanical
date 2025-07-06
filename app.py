from flask import Flask, render_template, request, redirect, url_for, flash, abort,send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
import os
import pandas as pd
from io import BytesIO
import uuid
import qrcode
import io
from flask import send_file, url_for

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_default_secret_key')
# app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///plants.db')
#app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:mysecretpassword@localhost:5432/postgres'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://admin:mysecretpassword@172.31.0.2:5432/postgres'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://admin:mysecretpassword@192.168.10.114:5432/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'flower')

# Initializing Flask extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), default='user')

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

# Location Model
class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location_name = db.Column(db.String(100), nullable=False)
    location_image = db.Column(db.String(200), nullable=True)



# Plant Model
class Plant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_flower = db.Column(db.String(100), nullable=False)
    local_name = db.Column(db.String(50), nullable=False)
    scientific_name = db.Column(db.String(100), nullable=False)
    family = db.Column(db.String(50), nullable=False)
    habit = db.Column(db.String(50), nullable=False)
    characteristics = db.Column(db.Text, nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)

    location = db.relationship('Location', backref='plants', lazy=True)
    images = db.relationship('PlantImage', backref='plant', lazy=True, cascade="all, delete-orphan")

# New: PlantImage Model (แยกรูปออกจาก Plant)
class PlantImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_url = db.Column(db.String(200), nullable=False)
    plant_id = db.Column(db.Integer, db.ForeignKey('plant.id'), nullable=False)


with app.app_context():
    db.create_all()
        # 🔐 Auto-create admin if none exists
"""     if not User.query.filter_by(email='admin@example.com').first():
        admin = User(
            username='admin',
            email='admin@example.com',
            role='admin'
        )
        admin.set_password('adminpassword')
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin created: admin@example.com / adminpassword") """


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid login credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/')
def home():
        return redirect(url_for('show_locations'))





@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = 'admin'
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already exists. Choose a different one.', 'danger')
            return redirect(url_for('register'))
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password=hashed_password,role=role)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route("/add_user", methods=['GET', 'POST'])
@login_required
def add_user():
    if current_user.role != 'admin':
        abort(403)  # Only admins can add users

    if request.method == 'POST':
        # Manually retrieve form data
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        # Hash the password before storing it
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Create a new user
        new_user = User(username=username, email=email, password=hashed_password, role=role)

        # Add the new user to the database
        db.session.add(new_user)
        db.session.commit()

        flash('New user added successfully!', 'success')
        return redirect(url_for('view_users'))  # Redirect to the user list page

    return render_template('add_user.html')


@app.route("/view_users")
@login_required
def view_users():
    if current_user.role != 'admin':
        abort(403)  # Only admins can view user list

    users = User.query.all()
    return render_template('view_users.html', users=users)

@app.route("/delete_user/<int:user_id>")
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        abort(403)  # Only admins can delete users

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.username} has been deleted!', 'danger')
    return redirect(url_for('view_users'))  # Redirect back to the user list

@app.route("/edit_user/<int:user_id>", methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'admin':
        abort(403)  # Only admins can edit users

    user = User.query.get_or_404(user_id)  # Get user by ID

    if request.method == 'POST':
        # Manually retrieve form data
        user.username = request.form['username']
        user.email = request.form['email']
        user.role = request.form['role']

        # Check if the password field has a value (if the user wants to update it)
        if request.form['password']:
            # Hash the new password before storing it
            hashed_password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
            user.password = hashed_password

        # Commit the changes to the database
        db.session.commit()

        flash(f'User {user.username} has been updated!', 'success')
        return redirect(url_for('view_users'))  # Redirect to the user list

    return render_template('edit_user.html', user=user)

@app.route("/edit_profile", methods=['GET', 'POST'])
@login_required
def edit_profile():
    user = current_user  # Get the currently logged-in user

    if request.method == 'POST':
        # Manually retrieve form data
        user.username = request.form['username']
        user.email = request.form['email']

        # Check if the password field has a value (if the user wants to update it)
        if request.form['password']:
            # Hash the new password before storing it
            hashed_password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
            user.password = hashed_password

        # Commit the changes to the database
        db.session.commit()

        flash(f'Your profile has been updated!', 'success')
        return redirect(url_for('profile'))  # Redirect to the profile page (or dashboard)

    return render_template('edit_profile.html', user=user)




# Function to validate image file types
def allowed_file(filename):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


@app.route('/edit/<int:plant_id>', methods=['GET', 'POST'])
@login_required
def edit_plant(plant_id):
    plant = Plant.query.get_or_404(plant_id)
    locations = Location.query.all()

    if request.method == 'POST':
        try:
            # --- อัปเดตข้อมูลพื้นฐานของพรรณไม้ ---
            plant.id_flower = request.form.get('id_flower', plant.id_flower)
            plant.local_name = request.form.get('local_name', plant.local_name)
            plant.scientific_name = request.form.get('scientific_name', plant.scientific_name)
            plant.family = request.form.get('family', plant.family)
            plant.habit = request.form.get('habit', plant.habit)
            plant.characteristics = request.form.get('characteristics', plant.characteristics)
            plant.location_id = request.form.get('location', plant.location_id)

            # --- อัปโหลดภาพใหม่ (ไม่ลบของเดิม) ---
            uploaded_images = request.files.getlist('images[]')
            for image_file in uploaded_images:
                if image_file and allowed_file(image_file.filename):
                    ext = os.path.splitext(image_file.filename)[1]
                    unique_filename = f"{uuid.uuid4().hex}{ext}"
                    image_filename = secure_filename(unique_filename)
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
                    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                    image_file.save(image_path)

                    image_url = f'flower/{image_filename}'

                    # บันทึกภาพใหม่ลงฐานข้อมูล
                    new_image = PlantImage(image_url=image_url, plant_id=plant.id)
                    db.session.add(new_image)

            db.session.commit()
            flash('แก้ไขข้อมูลพรรณไม้เรียบร้อยแล้ว!', 'success')
            return redirect(url_for('edit_plant', plant_id=plant.id))

        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')

    return render_template('edit_plant.html', plant=plant, locations=locations)



@app.route('/add_plant', methods=['GET', 'POST'])
@login_required
def add_plant():
    locations = Location.query.all()
    if request.method == 'POST':
        id_flower = request.form['id_flower']
        local_name = request.form['local_name']
        scientific_name = request.form['scientific_name']
        family = request.form['family']
        habit = request.form['habit']
        characteristics = request.form['characteristics']
        location_id = request.form['location']

        # เพิ่มข้อมูลลงตาราง Plant ก่อน
        new_plant = Plant(
            id_flower=id_flower,
            local_name=local_name,
            scientific_name=scientific_name,
            family=family,
            habit=habit,
            characteristics=characteristics,
            location_id=location_id
        )
        db.session.add(new_plant)
        db.session.commit()

        # รับไฟล์ภาพทั้งหมดจาก input multiple
        images = request.files.getlist('images[]')

        for image_file in images:
            if image_file and allowed_file(image_file.filename):
                ext = os.path.splitext(image_file.filename)[1]
                unique_filename = f"{uuid.uuid4().hex}{ext}"
                image_filename = secure_filename(unique_filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                image_file.save(image_path)

                image_url = f'flower/{image_filename}'  # หรือปรับตาม path ที่คุณใช้

                # เพิ่มเข้า PlantImage
                plant_image = PlantImage(image_url=image_url, plant_id=new_plant.id)
                db.session.add(plant_image)

        db.session.commit()

        flash('เพิ่มข้อมูลพรรณไม้และรูปภาพเรียบร้อยแล้ว!', 'success')
        return redirect(url_for('index'))

    return render_template('add_plant.html', locations=locations)



def allowed_file(filename):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/upload_excel', methods=['GET', 'POST'])
def upload_excel():
    if request.method == 'POST':
        # Get uploaded file
        file = request.files['file']

        # Check if file is valid
        if file and file.filename.endswith('.xlsx'):
            # Save the file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)

            # Process the file
            try:
                add_plants_from_excel(file_path)
                flash('Excel file uploaded and data added successfully!', 'success')
            except Exception as e:
                flash(f"An error occurred: {str(e)}", 'danger')
            return redirect(url_for('upload_excel'))
        else:
            flash('Invalid file type. Please upload an Excel file (.xlsx).', 'danger')

    return render_template('upload_excel.html')

def add_plants_from_excel(file_path):
    # อ่านไฟล์ Excel
    df = pd.read_excel(file_path)

    for _, row in df.iterrows():
        # เพิ่มข้อมูล Plant โดยกำหนด location_id เป็น 1 เสมอ
        plant = Plant(
            id_flower=row['id_flower'],
            local_name=row['local_name'],
            scientific_name=row['scientific_name'],
            family=row['family'],
            habit=row['habit'],
            characteristics=row['characteristics'],
            location_id=1,  # กำหนด location_id เป็น 1 เสมอ
            image_url=None  # ไม่ตรวจสอบหรือใช้รูปภาพ
        )
        db.session.add(plant)

    # บันทึกข้อมูลทั้งหมดลงในฐานข้อมูล
    db.session.commit()

@app.route('/delete_plant_image/<int:image_id>/<int:plant_id>', methods=['POST'])
@login_required
def delete_plant_image(image_id, plant_id):
    image = PlantImage.query.get_or_404(image_id)

    # ลบไฟล์จากระบบ (ถ้ามีอยู่จริง)
    try:
        image_path = os.path.join(app.static_folder, image.image_url)
        if os.path.exists(image_path):
            os.remove(image_path)
    except Exception as e:
        flash(f"เกิดข้อผิดพลาดในการลบไฟล์ภาพ: {e}", 'danger')

    # ลบ record ในฐานข้อมูล
    db.session.delete(image)
    db.session.commit()
    flash("ลบรูปภาพเรียบร้อยแล้ว", "success")
    return redirect(url_for('edit_plant', plant_id=plant_id))



#ลบต้นไม้
@app.route('/delete_plant/<int:id>', methods=['POST'])
@login_required
def delete_plant(id):
    # Find the plant by ID
    plant = Plant.query.get_or_404(id)
    
    # Delete the plant from the database
    db.session.delete(plant)
    db.session.commit()
    
    flash(f'Plant {plant.local_name} deleted successfully!', 'success')
    return redirect(url_for('index'))  # Redirect back to the index or wherever you want

@app.route('/plant_details/<int:id>', methods=['GET'])
def plant_details(id):
    plant = Plant.query.get_or_404(id)  # ดึงข้อมูลพรรณไม้จากฐานข้อมูล
    return render_template('plant_details.html', plant=plant)

@app.route('/about')
def about():
    return render_template('about.html')



@app.route('/add_location', methods=['GET', 'POST'])
def insert_location():
    if request.method == 'POST':
        location_name = request.form['location_name']
        
        # Check if an image was uploaded
        location_image = None
        if 'location_image' in request.files:
            image_file = request.files['location_image']
            if image_file.filename != '':
                # Define the image path in the flower folder
                image_filename = image_file.filename
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
                
                # Save the image in the flower folder
                image_file.save(image_path)
                
                # Store the relative path to the image in the database
                location_image = 'flower/' + image_filename  # Store path relative to static folder

        # Save location data to the database
        new_location = Location(location_name=location_name, location_image=location_image)
        db.session.add(new_location)
        db.session.commit()

        return redirect(url_for('show_locations'))

    return render_template('add_location.html')

@app.route('/manage_plant')
def manage_plant():
    plants = Plant.query.order_by(Plant.id_flower).all()
    return render_template('manage_plant.html', plants=plants)

@app.route('/index', methods=['GET'])
def index():
    query = request.args.get('q', '')
    if query:
        plants = Plant.query.filter(
            Plant.local_name.ilike(f'%{query}%') |
            Plant.scientific_name.ilike(f'%{query}%') |
            Plant.family.ilike(f'%{query}%')
        ).order_by(Plant.id_flower).all()
    else:
        plants = Plant.query.order_by(Plant.id_flower).all()

    return render_template('index.html', plants=plants)


@app.route('/contact')
def contact():
    return render_template('contact.html')

# Route: แสดงสถานที่ทั้งหมด
@app.route('/locations')
def show_locations():
    locations = Location.query.all()
    return render_template('locations.html', locations=locations)

@app.route('/location/<int:location_id>')
def show_plants_in_location(location_id):
    # ค้นหาข้อมูลสถานที่จากฐานข้อมูล
    location = Location.query.get_or_404(location_id)
    
    # ค้นหาพรรณไม้ที่เกี่ยวข้องกับสถานที่นั้น และเรียงตาม id_flower
    plants = Plant.query.filter_by(location_id=location.id).order_by(Plant.id_flower).all()
    
    return render_template('plants_in_location.html', location=location, plants=plants)


@app.route('/delete_location/<int:location_id>', methods=['POST'])
def delete_location(location_id):
    # ค้นหาสถานที่ในฐานข้อมูล
    location = Location.query.get(location_id)
    if location:
        try:
            # ลบสถานที่ออกจากฐานข้อมูล
            db.session.delete(location)
            db.session.commit()
            flash(f"สถานที่ '{location.location_name}' ถูกลบเรียบร้อยแล้ว", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"เกิดข้อผิดพลาดในการลบ: {str(e)}", "danger")
    else:
        flash("ไม่พบสถานที่ที่คุณต้องการลบ", "warning")
    return redirect(url_for('show_locations'))


@app.route('/edit_location/<int:location_id>', methods=['GET', 'POST'])
@login_required
def edit_location(location_id):
    location = Location.query.get(location_id)
    if not location:
        flash("ไม่พบสถานที่ที่คุณต้องการแก้ไข", "warning")
        return redirect(url_for('show_locations'))

    if request.method == 'POST':
        try:
            # รับค่าที่แก้ไขจากแบบฟอร์ม
            location_name = request.form['location_name']
            location_image = request.files.get('location_image')

            # อัปเดตข้อมูลสถานที่
            location.location_name = location_name

            # ตรวจสอบว่ามีการอัปโหลดรูปใหม่หรือไม่
            if location_image and location_image.filename != '':
                # เก็บรูปในโฟลเดอร์ flower
                image_filename = location_image.filename
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)

                # Save the image to the flower folder
                location_image.save(image_path)

                # อัปเดต URL รูปภาพในฐานข้อมูล (Relative path to static)
                location.location_image = f'flower/{image_filename}'

            # Commit the changes to the database
            db.session.commit()
            flash(f"สถานที่ '{location.location_name}' แก้ไขสำเร็จ", "success")

        except Exception as e:
            db.session.rollback()
            flash(f"เกิดข้อผิดพลาดในการแก้ไข: {str(e)}", "danger")

        return redirect(url_for('show_locations'))

    return render_template('edit_location.html', location=location)

@app.route('/location/<int:location_id>', methods=['GET'])
def display_plants_in_location(location_id):
    location = Location.query.get_or_404(location_id)
    plants = Plant.query.filter_by(location_id=location_id).all()
    return render_template('show_plants_in_location.html', location=location, plants=plants)


@app.route('/download_plants_excel')
def download_plants_excel():
    # Get all plants from the database
    plants = Plant.query.all()

    # Prepare data for Excel export (without images)
    data = []
    for plant in plants:
        data.append({
            "รหัสพรรณไม้": plant.id_flower,
            "ชื่อพื้นเมือง": plant.local_name,
            "ชื่อวิทยาศาสตร์": plant.scientific_name,
            "ชื่อวงศ์": plant.family,
            "ลักษณะวิสัย": plant.habit,
            "ลักษณะเด่น": plant.characteristics,
            "บริเวณที่พบ": plant.location.location_name,
        })

    # Convert to a DataFrame
    df = pd.DataFrame(data)

    # Save DataFrame to a BytesIO object as an Excel file
    output = BytesIO()
    df.to_excel(output, index=False, engine='openpyxl')
    output.seek(0)

    # Send the file as a response to the user
    return send_file(output, as_attachment=True, download_name="plants_data.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.route('/history')
def history():
    return render_template('history.html')

@app.route('/activities/2567')
def activities_2567():
    return render_template('activities_2567.html')

@app.route('/activities/2568')
def activities_2568():
    return render_template('activities_2568.html')

@app.route('/plant_qrcode/<int:id>')
def plant_qrcode(id):
    plant = Plant.query.get_or_404(id)
    url = url_for('plant_details', id=id, _external=True)  # ใช้ชื่อ endpoint = 'plant_details'

    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)

    return send_file(buf, mimetype='image/png')

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000,debug=True)
