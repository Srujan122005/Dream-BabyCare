from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_from_directory, abort
from functools import wraps
from datetime import datetime, timedelta
import os
import json
from translations import translations
import smtplib
from email.message import EmailMessage
from urllib.parse import quote
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Initialize Supabase
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables are required")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this in production
# Admin credentials (change in production or use env vars)
app.config['ADMIN_USER'] = 'admin'
app.config['ADMIN_PASS'] = 'admin123'

# Jinja filter to format numbers as Indian Rupees
def format_inr(value):
    try:
        val = float(value)
    except Exception:
        return value
    return f"\u20B9{val:,.2f}"

app.jinja_env.filters['inr'] = format_inr

# Helper decorator to require login for certain routes
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Helper decorator to require doctor login
def doctor_required(f):
    @wraps(f)
    def decorated_doctor(*args, **kwargs):
        if 'doctor_id' not in session:
            return redirect(url_for('doctor_login'))
        return f(*args, **kwargs)
    return decorated_doctor

# Helper decorator to require admin login for admin routes
def admin_required(f):
    @wraps(f)
    def decorated_admin(*args, **kwargs):
        if session.get('admin_logged_in'):
            return f(*args, **kwargs)

        user_email = session.get('user_id')
        if user_email:
            try:
                response = supabase.table('users').select('is_admin').eq('email', user_email).execute()
                if response.data and len(response.data) > 0:
                    if int(response.data[0].get('is_admin') or 0) == 1:
                        return f(*args, **kwargs)
            except Exception:
                pass

        return redirect(url_for('admin_login'))
    return decorated_admin

# Initialize database (Supabase tables already created)
def init_db():
    """
    Supabase tables are already created via SQL.
    This function now just inserts sample data if needed.
    """
    try:
        # Check if products exist
        response = supabase.table('products').select('id').limit(1).execute()
        if not response.data:
            sample_products = [
                {'name': 'Diapers - Newborn Size', 'description': 'Soft, absorbent diapers for newborns (30 count)', 'price': 350.00, 'image': 'https://images.unsplash.com/photo-1519689680058-324335c77eba?auto=format&fit=crop&w=500', 'category': 'Diapering'},
                {'name': 'Baby Wipes', 'description': 'Gentle, hypoallergenic wipes for sensitive skin (80 count)', 'price': 150.00, 'image': 'https://images.unsplash.com/photo-1556228720-19875c4b84b2?auto=format&fit=crop&w=500', 'category': 'Diapering'},
                {'name': 'Baby Bottles Set', 'description': 'BPA-free bottles with anti-colic system (3 pack)', 'price': 450.00, 'image': 'https://images.unsplash.com/photo-1595347097560-69238724e7bd?auto=format&fit=crop&w=500', 'category': 'Feeding'},
                {'name': 'Baby Formula', 'description': 'Nutritious formula for newborns (400g)', 'price': 650.00, 'image': 'https://images.unsplash.com/photo-1632053009503-2b28537e3824?auto=format&fit=crop&w=500', 'category': 'Feeding'},
                {'name': 'Onesies - 5 Pack', 'description': 'Soft cotton onesies in assorted colors (Newborn size)', 'price': 999.00, 'image': 'https://images.unsplash.com/photo-1522771753035-0a15395031b2?auto=format&fit=crop&w=500', 'category': 'Clothing'},
                {'name': 'Baby Blanket', 'description': 'Soft, warm blanket for swaddling and comfort', 'price': 550.00, 'image': 'https://images.unsplash.com/photo-1513159446162-54eb8bdaa79b?auto=format&fit=crop&w=500', 'category': 'Bedding'},
                {'name': 'Baby Shampoo & Body Wash', 'description': 'Tear-free, gentle cleanser for baby', 'price': 250.00, 'image': 'https://images.unsplash.com/photo-1556228578-0d85b1a4d571?auto=format&fit=crop&w=500', 'category': 'Bathing'},
                {'name': 'Baby Lotion', 'description': 'Moisturizing lotion for delicate skin', 'price': 220.00, 'image': 'https://images.unsplash.com/photo-1608248597279-f99d160bfbc8?auto=format&fit=crop&w=500', 'category': 'Bathing'},
                {'name': 'Pacifiers - 2 Pack', 'description': 'Orthodontic pacifiers for newborns', 'price': 200.00, 'image': 'https://images.unsplash.com/photo-1596464716127-f9a0859d0437?auto=format&fit=crop&w=500', 'category': 'Comfort'},
                {'name': 'Baby Thermometer', 'description': 'Digital thermometer for accurate temperature reading', 'price': 300.00, 'image': 'https://images.unsplash.com/photo-1584634731339-252c581abfc5?auto=format&fit=crop&w=500', 'category': 'Health'},
            ]
            supabase.table('products').insert(sample_products).execute()

        response = supabase.table('doctors').select('id').limit(1).execute()
        if not response.data:
            sample_doctors = [
                {'name': 'Dr. Sarah Smith', 'specialization': 'Pediatrician', 'email': 'sarah.smith@clinic.com', 'password': 'doc123', 'image': 'https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&w=500', 'phone': '+1234567890', 'video_link': 'https://meet.google.com/abc-defg-hij'},
                {'name': 'Dr. John Doe', 'specialization': 'Child Psychologist', 'email': 'john.doe@clinic.com', 'password': 'doc123', 'image': 'https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?auto=format&fit=crop&w=500', 'phone': '+1987654321', 'video_link': 'https://meet.google.com/xyz-uvwx-yz'}
            ]
            supabase.table('doctors').insert(sample_doctors).execute()
    except Exception as e:
        print(f"Error initializing database: {e}")

# Ensure session_id exists for cart operations
@app.before_request
def ensure_session_id():
    if 'session_id' not in session:
        session['session_id'] = os.urandom(16).hex()

# Global language loader
@app.before_request
def load_user_language():
    if 'user_id' in session:
        try:
            response = supabase.table('users').select('language').eq('email', session['user_id']).execute()
            if response.data and len(response.data) > 0:
                lang = response.data[0].get('language')
                if lang:
                    session['language'] = lang
        except Exception:
            pass

@app.context_processor
def inject_language():
    lang = session.get('language', 'en')
    if lang not in translations:
        lang = 'en'
    
    # Inject cart count
    cart_count = 0
    if 'session_id' in session:
        try:
            response = supabase.table('cart').select('quantity').eq('session_id', session['session_id']).execute()
            if response.data:
                cart_count = sum(item['quantity'] for item in response.data)
        except:
            pass

    logo = 'https://res.cloudinary.com/duucdndfx/image/upload/v1767200335/WhatsApp_Image_2025-11-23_at_10.59.52_PM_nwqgbo.jpg'

    return dict(lang=lang, lang_data=translations.get(lang, {}), cart_count=cart_count, logo=logo)

# Admin actions logging helpers
def get_client_ip():
    """Extract client IP from request, accounting for proxies."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or 'unknown'

def log_admin_action(action, user_id, user_email, prev_is_sub, prev_pending, new_is_sub, new_pending):
    """Log admin action with IP, admin user, and full state change info."""
    entry = {
        'timestamp': datetime.now().isoformat(),
        'action': action,
        'user_id': user_id,
        'user_email': user_email,
        'prev_is_subscribed': int(prev_is_sub),
        'prev_subscription_pending': int(prev_pending),
        'new_is_subscribed': int(new_is_sub),
        'new_subscription_pending': int(new_pending),
        'admin': session.get('admin_user') or session.get('user_id') or 'unknown',
        'ip': get_client_ip()
    }
    try:
        with open('admin_actions.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass

def read_all_admin_actions():
    """Read all admin actions from log and return as list with log_index for per-entry undo."""
    if not os.path.exists('admin_actions.log'):
        return []
    try:
        with open('admin_actions.log', 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
            actions = []
            for i, line in enumerate(lines):
                try:
                    entry = json.loads(line)
                    entry['log_index'] = i
                    actions.append(entry)
                except Exception:
                    pass
            return actions
    except Exception:
        return []

def read_last_admin_action():
    """Read the last admin action from log (for legacy undo)."""
    actions = read_all_admin_actions()
    return actions[-1] if actions else None

# Helper: send notification email to admin when a user requests subscription
def send_admin_notification(subject, body):
    host = app.config.get('SMTP_HOST')
    admin_email = app.config.get('ADMIN_NOTIFICATION_EMAIL')
    if not host or not admin_email:
        return False
    try:
        port = app.config.get('SMTP_PORT', 587)
        user = app.config.get('SMTP_USER')
        passwd = app.config.get('SMTP_PASS')
        use_tls = app.config.get('SMTP_USE_TLS', True)

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = user if user else admin_email
        msg['To'] = admin_email
        msg.set_content(body)

        if use_tls:
            server = smtplib.SMTP(host, port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP(host, port, timeout=10)

        if user and passwd:
            server.login(user, passwd)

        server.send_message(msg)
        server.quit()
        return True
    except Exception:
        return False

# ===== ROUTES START HERE =====

# Home page
@app.route('/')
def landing():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('landing.html')

@app.route('/home')
@login_required
def home():
    return render_template('index.html', hero_image="https://images.unsplash.com/photo-1555252333-9f8e92e65df4?auto=format&fit=crop&w=1000")

# About page
@app.route('/about')
@login_required
def about():
    about_info = {
        'title': 'About Dream Baby Care',
        'linkedin_profile': 'https://www.linkedin.com/in/srujan-ss-9b7a1b336/',
        'description': 'Dream Baby Care is your trusted companion in the beautiful journey of parenthood. We provide smart tracking tools, expert tips, and a curated shop to make your life easier and your baby happier.',
        'mission': 'To empower every parent with the technology, knowledge, and support they need to raise happy, healthy babies.',
        'features': [
            {'icon': 'fas fa-baby-carriage', 'title': 'Smart Tracking', 'desc': 'Effortlessly track sleep, feeding, diaper changes, and health metrics.'},
            {'icon': 'fas fa-shopping-bag', 'title': 'Curated Shop', 'desc': 'Access high-quality, safe, and essential products for your newborn.'},
            {'icon': 'fas fa-lightbulb', 'title': 'Expert Guidance', 'desc': 'Get reliable tips on health, hygiene, soothing, and more.'},
            {'icon': 'fas fa-shield-alt', 'title': 'Secure & Private', 'desc': 'Your family data is kept safe and private.'}
        ],
        'values': [
            {'title': 'Compassion', 'desc': 'We care deeply about the well-being of every family.'},
            {'title': 'Integrity', 'desc': 'We provide honest, evidence-based information.'},
            {'title': 'Community', 'desc': 'We are building a supportive community for parents.'}
        ]
    }
    return render_template('about.html', info=about_info)

# Set language preference
@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in translations:
        session['language'] = lang
        if 'user_id' in session:
            try:
                supabase.table('users').update({'language': lang}).eq('email', session['user_id']).execute()
            except Exception:
                pass
    return redirect(request.referrer or url_for('home'))

# Tips page
@app.route('/tips')
@login_required
def tips():
    lang = session.get('language', 'en')
    if lang not in translations:
        lang = 'en'
    
    lang_data = translations[lang]
    
    tip_keys = ['feeding', 'diapering', 'sleep', 'bathing', 'crying']
    tips_content = {}
    for key in tip_keys:
        if key in lang_data.get('tips', {}):
            tips_content[key] = lang_data['tips'][key]
    
    videos_by_category = {}
    categories = ['Feeding', 'Diapering', 'Health', 'Bathing', 'Soothing']
    for cat in categories:
        slug = cat.lower().replace(' ', '_')
        folder = os.path.join(app.root_path, 'static', 'videos', slug)
        video_list = []
        if os.path.isdir(folder):
            for fname in sorted(os.listdir(folder)):
                if fname.lower().endswith(('.mp4', '.webm', '.ogg')):
                    url = url_for('protected_video', filename=f'videos/{slug}/{fname}')
                    video_list.append({'filename': fname, 'url': url})
        videos_by_category[cat] = video_list

    is_sub = session.get('is_subscribed', 0)
    sub_pending = session.get('subscription_pending', 0)

    return render_template('tips.html', 
                         lang=lang,
                         lang_data=lang_data,
                         tips_content=tips_content,
                         categories=categories,
                         videos_by_category=videos_by_category,
                         is_subscribed=is_sub,
                         subscription_pending=sub_pending)

# Shop page
@app.route('/shop')
@login_required
def shop():
    try:
        response = supabase.table('products').select('*').execute()
        products = response.data if response.data else []
    except Exception:
        products = []
    
    categories = {}
    for product in products:
        category = product.get('category', 'Other')
        if category not in categories:
            categories[category] = []
        categories[category].append(product)
    
    return render_template('shop.html', categories=categories)

# Product detail page
@app.route('/product/<int:product_id>')
def product_detail(product_id):
    try:
        response = supabase.table('products').select('*').eq('id', product_id).execute()
        product = response.data[0] if response.data else None
    except Exception:
        product = None
    
    if product:
        return render_template('product_detail.html', product=product)
    else:
        return "Product not found", 404

# Add to cart functionality
@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    try:
        response = supabase.table('products').select('name').eq('id', product_id).execute()
        if response.data:
            product = response.data[0]
            return redirect(f"https://blinkit.com/s/?q={quote(product['name'])}")
    except Exception:
        pass
    
    return redirect(url_for('shop'))

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    if 'session_id' in session:
        try:
            supabase.table('cart').delete().eq('product_id', product_id).eq('session_id', session['session_id']).execute()
            flash('Item removed from cart', 'info')
        except Exception:
            pass
    return redirect(url_for('cart'))

@app.route('/checkout')
@login_required
def checkout():
    if 'session_id' in session:
        try:
            supabase.table('cart').delete().eq('session_id', session['session_id']).execute()
            flash('Order placed successfully! Thank you for shopping.', 'success')
        except Exception:
            pass
    return redirect(url_for('shop'))

# View cart
@app.route('/cart')
def cart():
    if 'session_id' not in session:
        return render_template('cart.html', cart_items=[], total=0)
    
    try:
        response = supabase.table('cart').select('product_id, quantity').eq('session_id', session['session_id']).execute()
        cart_data = response.data if response.data else []
        
        cart_items = []
        total = 0
        for item in cart_data:
            prod_resp = supabase.table('products').select('*').eq('id', item['product_id']).execute()
            if prod_resp.data:
                product = prod_resp.data[0]
                cart_items.append({
                    'id': product['id'],
                    'name': product['name'],
                    'price': product['price'],
                    'image': product['image'],
                    'quantity': item['quantity']
                })
                total += product['price'] * item['quantity']
    except Exception:
        cart_items = []
        total = 0
    
    return render_template('cart.html', cart_items=cart_items, total=total)

# Contact page
@app.route('/contact', methods=['GET', 'POST'])
@login_required
def contact():
    if not session.get('is_subscribed'):
        return redirect(url_for('subscribe'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            supabase.table('contacts').insert({
                'name': name,
                'email': email,
                'message': message,
                'date': date
            }).execute()
        except Exception:
            flash('Error submitting contact form', 'danger')
            return redirect(url_for('contact'))
        
        return redirect(url_for('contact_success'))

    try:
        response = supabase.table('doctors').select('*').execute()
        doctors = response.data if response.data else []
    except Exception:
        doctors = []

    return render_template('contact.html', doctors=doctors)

@app.route('/book_appointment', methods=['POST'])
@login_required
def book_appointment():
    doctor_id = request.form.get('doctor_id')
    appt_time = request.form.get('appointment_time')
    appt_type = request.form.get('type')
    
    try:
        supabase.table('appointments').insert({
            'user_id': session['user_id'],
            'doctor_id': int(doctor_id),
            'appointment_time': appt_time,
            'type': appt_type,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }).execute()
        flash('Appointment request sent successfully!', 'success')
    except Exception:
        flash('Error booking appointment', 'danger')
    
    return redirect(url_for('contact'))

# Contact success page
@app.route('/contact_success')
def contact_success():
    return render_template('contact_success.html')

@app.route('/subscribe_newsletter', methods=['POST'])
def subscribe_newsletter():
    email = request.form.get('email')
    if not email:
        flash('Email is required.', 'warning')
        return redirect(request.referrer or url_for('home'))

    try:
        response = supabase.table('newsletter_subscribers').select('email').eq('email', email).execute()
        if response.data:
            flash('You are already subscribed to our newsletter!', 'info')
        else:
            supabase.table('newsletter_subscribers').insert({
                'email': email,
                'subscribed_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }).execute()
            flash('Thank you for subscribing to our newsletter!', 'success')
    except Exception:
        flash('An error occurred while subscribing.', 'danger')

    return redirect(request.referrer or url_for('home'))

@app.route('/admin/contacts')
@admin_required
def admin_contacts():
    try:
        response = supabase.table('contacts').select('*').order('date', desc=True).execute()
        contacts = response.data if response.data else []
    except Exception:
        contacts = []
    
    return render_template('admin_contacts.html', contacts=contacts)

@app.route('/admin/reply_contact/<int:contact_id>', methods=['POST'])
@admin_required
def admin_reply_contact(contact_id):
    reply = request.form.get('reply')
    if not reply:
        flash('Reply cannot be empty.', 'warning')
        return redirect(request.referrer or url_for('admin_contacts'))

    try:
        replied_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        admin_user = session.get('admin_user') or session.get('user_id') or 'admin'
        supabase.table('contacts').update({
            'admin_reply': reply,
            'replied_at': replied_at,
            'replied_by': admin_user
        }).eq('id', contact_id).execute()
        flash('Reply saved and user notified.', 'success')
    except Exception:
        flash('Failed to save reply.', 'danger')

    return redirect(request.referrer or url_for('admin_contacts'))

@app.route('/admin/doctors')
@admin_required
def admin_doctors():
    try:
        response = supabase.table('doctors').select('*').execute()
        doctors = response.data if response.data else []
    except Exception:
        doctors = []
    
    return render_template('admin_doctors.html', doctors=doctors)

@app.route('/admin/doctor/add', methods=['POST'])
@admin_required
def admin_add_doctor():
    try:
        supabase.table('doctors').insert({
            'name': request.form.get('name'),
            'specialization': request.form.get('specialization'),
            'email': request.form.get('email'),
            'password': request.form.get('password'),
            'image': request.form.get('image'),
            'phone': request.form.get('phone'),
            'video_link': request.form.get('video_link')
        }).execute()
    except Exception:
        flash('Error adding doctor', 'danger')
    
    return redirect(url_for('admin_doctors'))

@app.route('/admin/doctor/delete/<int:doctor_id>', methods=['POST'])
@admin_required
def admin_delete_doctor(doctor_id):
    try:
        supabase.table('doctors').delete().eq('id', doctor_id).execute()
    except Exception:
        flash('Error deleting doctor', 'danger')
    
    return redirect(url_for('admin_doctors'))

@app.route('/admin/appointments')
@admin_required
def admin_appointments():
    status_filter = request.args.get('status')
    try:
        response = supabase.table('appointments').select('*').execute()
        appointments = response.data if response.data else []
        
        if status_filter and status_filter != 'All':
            appointments = [a for a in appointments if a.get('status') == status_filter]
    except Exception:
        appointments = []
    
    return render_template('admin_appointments.html', appointments=appointments, current_status=status_filter)

@app.route('/admin/appointment/status/<int:appt_id>', methods=['POST'])
@admin_required
def admin_update_appointment_status(appt_id):
    status = request.form.get('status')
    try:
        supabase.table('appointments').update({'status': status}).eq('id', appt_id).execute()
        flash(f'Appointment status updated to {status}', 'success')
    except Exception:
        flash('Error updating appointment', 'danger')
    
    return redirect(url_for('admin_appointments'))

# ===== DOCTOR AUTH & DASHBOARD =====

@app.route('/doctor/login', methods=['GET', 'POST'])
def doctor_login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            response = supabase.table('doctors').select('*').eq('email', email).eq('password', password).execute()
            if response.data and len(response.data) > 0:
                doctor = response.data[0]
                session['doctor_id'] = doctor['id']
                session['doctor_name'] = doctor['name']
                return redirect(url_for('doctor_dashboard'))
            else:
                error = 'Invalid doctor credentials. Please try again.'
        except Exception:
            error = 'Login error'
    
    return render_template('doctor_login.html', error=error)

@app.route('/doctor/dashboard')
@doctor_required
def doctor_dashboard():
    try:
        doctor_response = supabase.table('doctors').select('name, specialization').eq('id', session['doctor_id']).execute()
        doctor_details = doctor_response.data[0] if doctor_response.data else None

        appt_response = supabase.table('appointments').select('*').eq('doctor_id', session['doctor_id']).execute()
        appointments = appt_response.data if appt_response.data else []
        appointments = [a for a in appointments if a.get('status') in ['Confirmed', 'Pending']]
    except Exception:
        doctor_details = None
        appointments = []

    stats = {
        'total_upcoming': len(appointments),
        'pending': len([a for a in appointments if a.get('status') == 'Pending']),
        'confirmed': len([a for a in appointments if a.get('status') == 'Confirmed'])
    }

    return render_template('doctor_dashboard.html', appointments=appointments, doctor=doctor_details, stats=stats)

@app.route('/doctor/logout')
def doctor_logout():
    session.pop('doctor_id', None)
    session.pop('doctor_name', None)
    return redirect(url_for('doctor_login'))

@app.route('/doctor/appointment/status/<int:appt_id>', methods=['POST'])
@doctor_required
def doctor_update_appointment_status(appt_id):
    status = request.form.get('status')
    notes = request.form.get('notes', '')
    
    try:
        update_data = {'status': status}
        if notes:
            update_data['notes'] = notes
        supabase.table('appointments').update(update_data).eq('id', appt_id).eq('doctor_id', session['doctor_id']).execute()
        flash(f'Appointment marked as {status}', 'success')
    except Exception:
        flash('Error updating appointment', 'danger')
    
    return redirect(url_for('doctor_dashboard'))

# Admin Login
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == app.config.get('ADMIN_USER') and password == app.config.get('ADMIN_PASS'):
            session['admin_logged_in'] = True
            session['admin_user'] = username
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Invalid admin credentials'
    return render_template('admin_login.html', error=error)

# Admin logout
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_user', None)
    return redirect(url_for('admin_login'))

# ===== USER AUTH ROUTES =====

# User Registration Page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        parent_name = request.form.get('parent_name')
        baby_name = request.form.get('baby_name')
        baby_dob = request.form.get('baby_dob')
        phone = request.form.get('phone')
        address = request.form.get('address')
        language = request.form.get('language', 'en')
        
        try:
            dob = datetime.strptime(baby_dob, '%Y-%m-%d')
            today = datetime.now()
            age_days = (today - dob).days
            if age_days < 30:
                baby_age = f"{age_days} days"
            elif age_days < 365:
                baby_age = f"{age_days // 30} months"
            else:
                baby_age = f"{age_days // 365} years"
        except:
            baby_age = "Unknown"
        
        try:
            response = supabase.table('users').select('email').eq('email', email).execute()
            if response.data:
                return render_template('register.html', error="Email already registered")
            
            supabase.table('users').insert({
                'email': email,
                'password': password,
                'parent_name': parent_name,
                'baby_name': baby_name,
                'baby_dob': baby_dob,
                'baby_age': baby_age,
                'phone': phone,
                'address': address,
                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'language': language,
                'is_subscribed': 0,
                'subscription_pending': 0,
                'is_admin': 0
            }).execute()
            
            session['user_id'] = email
            session['user_name'] = parent_name
            session['language'] = language
            return redirect(url_for('home'))
        except Exception as e:
            return render_template('register.html', error=str(e))
    
    return render_template('register.html')

# User Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            response = supabase.table('users').select('*').eq('email', email).eq('password', password).execute()
            if response.data and len(response.data) > 0:
                user = response.data[0]
                session['user_id'] = email
                session['user_name'] = user.get('parent_name')
                session['language'] = user.get('language', 'en')
                session['is_admin'] = 1 if user.get('is_admin') else 0
                session['is_subscribed'] = 1 if user.get('is_subscribed') else 0
                session['subscription_pending'] = 1 if user.get('subscription_pending') else 0

                return redirect(url_for('home'))
            else:
                return render_template('login.html', error="Invalid email or password")
        except Exception:
            return render_template('login.html', error="Login error")
    
    return render_template('login.html')

# User Dashboard
@app.route('/user/dashboard')
@login_required
def user_dashboard():
    try:
        user_response = supabase.table('users').select('*').eq('email', session['user_id']).execute()
        user = user_response.data[0] if user_response.data else None

        tracker_response = supabase.table('baby_tracker').select('*').eq('user_id', session['user_id']).order('created_at', desc=True).limit(10).execute()
        tracking_data = tracker_response.data if tracker_response.data else []

        contacts_response = supabase.table('contacts').select('*').eq('email', session['user_id']).order('date', desc=True).execute()
        user_contacts = contacts_response.data if contacts_response.data else []

        appt_response = supabase.table('appointments').select('*').eq('user_id', session['user_id']).order('appointment_time', desc=True).execute()
        appointments = appt_response.data if appt_response.data else []
    except Exception:
        user = None
        tracking_data = []
        user_contacts = []
        appointments = []
    
    if user:
        is_sub = session.get('is_subscribed', 0)
        sub_pending = session.get('subscription_pending', 0)
        return render_template('user_dashboard.html', user=user, tracking_data=tracking_data,
                       is_subscribed=is_sub, subscription_pending=sub_pending, user_contacts=user_contacts, appointments=appointments)
    
    return redirect(url_for('login'))

# User Logout
@app.route('/user/logout')
def user_logout():
    session.clear()
    return redirect(url_for('landing'))

# ===== BABY TRACKER =====

@app.route('/tracker/add', methods=['POST'])
@login_required
def add_tracker():
    activity_type = request.form.get('activity_type')
    notes = request.form.get('notes', '')
    
    if not activity_type:
        return jsonify({'error': 'Activity type is required'}), 400
    
    try:
        supabase.table('baby_tracker').insert({
            'user_id': session['user_id'],
            'activity_type': activity_type,
            'start_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'notes': notes,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }).execute()
        return jsonify({'success': True, 'message': f'{activity_type} started!'}), 201
    except Exception:
        return jsonify({'error': 'Error adding tracker'}), 500

@app.route('/tracker/end/<int:tracker_id>', methods=['POST'])
@login_required
def end_tracker(tracker_id):
    try:
        response = supabase.table('baby_tracker').select('*').eq('id', tracker_id).eq('user_id', session['user_id']).execute()
        if not response.data:
            return jsonify({'error': 'Tracker not found'}), 404
        
        supabase.table('baby_tracker').update({'end_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}).eq('id', tracker_id).execute()
        return jsonify({'success': True, 'message': f'{response.data[0].get("activity_type")} ended!'}), 200
    except Exception:
        return jsonify({'error': 'Error ending tracker'}), 500

@app.route('/tracker/delete/<int:tracker_id>', methods=['POST'])
@login_required
def delete_tracker(tracker_id):
    try:
        response = supabase.table('baby_tracker').select('*').eq('id', tracker_id).eq('user_id', session['user_id']).execute()
        if not response.data:
            return jsonify({'error': 'Tracker not found'}), 404
        
        supabase.table('baby_tracker').delete().eq('id', tracker_id).execute()
        return jsonify({'success': True, 'message': 'Entry deleted!'}), 200
    except Exception:
        return jsonify({'error': 'Error deleting tracker'}), 500

# Reminder Routes
@app.route('/tracker/reminder/add', methods=['POST'])
@login_required
def add_reminder():
    message = request.form.get('message')
    remind_time = request.form.get('remind_time')
    
    if not message or not remind_time:
        return jsonify({'error': 'Message and time are required'}), 400

    try:
        supabase.table('reminders').insert({
            'user_id': session['user_id'],
            'message': message,
            'remind_time': remind_time,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }).execute()
        return jsonify({'success': True, 'message': 'Reminder set!'})
    except Exception:
        return jsonify({'error': 'Error adding reminder'}), 500

@app.route('/tracker/reminder/delete/<int:reminder_id>', methods=['POST'])
@login_required
def delete_reminder(reminder_id):
    try:
        supabase.table('reminders').delete().eq('id', reminder_id).eq('user_id', session['user_id']).execute()
        return jsonify({'success': True, 'message': 'Reminder deleted!'})
    except Exception:
        return jsonify({'error': 'Error deleting reminder'}), 500

# Tracker page
@app.route('/tracker')
@login_required
def tracker_page():
    try:
        date_filter = request.args.get('date')
        if date_filter:
            response = supabase.table('baby_tracker').select('*').eq('user_id', session['user_id']).like('start_time', f"{date_filter}%").order('created_at', desc=True).execute()
        else:
            response = supabase.table('baby_tracker').select('*').eq('user_id', session['user_id']).order('created_at', desc=True).execute()
        
        raw_data = response.data if response.data else []

        reminders_response = supabase.table('reminders').select('*').eq('user_id', session['user_id']).order('remind_time').execute()
        reminders = reminders_response.data if reminders_response.data else []
    except Exception:
        raw_data = []
        reminders = []
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    display_date = request.args.get('date') if request.args.get('date') else today_str
    
    stats = {
        'sleep_duration': 0,
        'feed_count': 0,
        'diaper_count': 0
    }
    
    formatted_activities = []
    icons = {
        'Feeding': 'fas fa-baby-bottle',
        'Sleep': 'fas fa-moon',
        'Diaper': 'fas fa-baby',
        'Health': 'fas fa-heartbeat',
        'Bath': 'fas fa-bath'
    }
    
    for row in raw_data:
        try:
            start_dt = datetime.strptime(row['start_time'], "%Y-%m-%d %H:%M:%S")
            end_dt = datetime.strptime(row['end_time'], "%Y-%m-%d %H:%M:%S") if row.get('end_time') else None
            
            duration_str = ""
            if end_dt:
                diff = end_dt - start_dt
                total_seconds = diff.total_seconds()
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                
                if start_dt.strftime("%Y-%m-%d") == display_date and row['activity_type'] == 'Sleep':
                    stats['sleep_duration'] += total_seconds
            
            if start_dt.strftime("%Y-%m-%d") == display_date:
                if row['activity_type'] == 'Feeding': stats['feed_count'] += 1
                elif row['activity_type'] == 'Diaper': stats['diaper_count'] += 1

            formatted_activities.append({
                'id': row['id'],
                'type': row['activity_type'],
                'start_time': start_dt.strftime("%I:%M %p"),
                'date': start_dt.strftime("%b %d"),
                'end_time': end_dt.strftime("%I:%M %p") if end_dt else None,
                'duration': duration_str,
                'notes': row.get('notes'),
                'icon': icons.get(row['activity_type'], 'fas fa-circle'),
            })
        except Exception:
            continue

    sleep_hours = int(stats['sleep_duration'] // 3600)
    sleep_minutes = int((stats['sleep_duration'] % 3600) // 60)
    stats['sleep_display'] = f"{sleep_hours}h {sleep_minutes}m"

    return render_template('tracker.html', 
                         tracking_data=raw_data, 
                         activities=formatted_activities, 
                         stats=stats,
                         current_date=display_date,
                         reminders=reminders)

def analyze_activities_for_health(activities, stats):
    """Simple health analysis based on activities"""
    insights = []
    score = 0

    sleep_secs = stats.get('sleep_duration', 0)
    sleep_hours = sleep_secs / 3600
    if sleep_hours >= 12:
        insights.append(('Sleep', 'Great sleep — baby had a long restful period.'))
        score += 2
    elif sleep_hours >= 8:
        insights.append(('Sleep', 'Good amount of sleep for the day.'))
        score += 1
    else:
        insights.append(('Sleep', 'Sleep is low today — consider a calmer pre-sleep routine.'))
        score -= 1

    feeds = stats.get('feed_count', 0)
    if feeds >= 8:
        insights.append(('Feeding', 'Frequent feeds recorded — hydration and growth cues look normal.'))
        score += 1
    elif feeds >= 4:
        insights.append(('Feeding', 'Feeding frequency is within normal range.'))
    else:
        insights.append(('Feeding', 'Fewer feeds logged — watch for signs of low intake.'))
        score -= 1

    diapers = stats.get('diaper_count', 0)
    if diapers >= 6:
        insights.append(('Diaper', 'Diaper changes are frequent — hydration is likely good.'))
        score += 1
    elif diapers >= 3:
        insights.append(('Diaper', 'Diaper changes are normal.'))
    else:
        insights.append(('Diaper', 'Low diaper changes — monitor urine output and consult if worried.'))
        score -= 1

    if score >= 3:
        final = 'Overall: Baby looks well today.'
    elif score >= 0:
        final = 'Overall: Mostly normal but keep an eye on the few low metrics.'
    else:
        final = 'Overall: Some caution advised — monitor symptoms and consider contacting your pediatrician.'

    return {'insights': insights, 'summary': final, 'score': score}

@app.route('/tracker/analyze', methods=['GET'])
@login_required
def tracker_analyze():
    date_filter = request.args.get('date')
    try:
        if date_filter:
            response = supabase.table('baby_tracker').select('*').eq('user_id', session['user_id']).like('start_time', f"{date_filter}%").order('created_at', desc=True).execute()
        else:
            today = datetime.now().strftime('%Y-%m-%d')
            response = supabase.table('baby_tracker').select('*').eq('user_id', session['user_id']).like('start_time', f"{today}%").order('created_at', desc=True).execute()
        rows = response.data if response.data else []
    except Exception:
        rows = []

    activities = []
    stats = {'sleep_duration': 0, 'feed_count': 0, 'diaper_count': 0}
    for row in rows:
        try:
            start_dt = datetime.strptime(row['start_time'], "%Y-%m-%d %H:%M:%S")
            end_dt = datetime.strptime(row['end_time'], "%Y-%m-%d %H:%M:%S") if row.get('end_time') else None
            if end_dt and row['activity_type'] == 'Sleep':
                stats['sleep_duration'] += (end_dt - start_dt).total_seconds()
            if row['activity_type'] == 'Feeding': stats['feed_count'] += 1
            if row['activity_type'] == 'Diaper': stats['diaper_count'] += 1

            activities.append({'type': row['activity_type'], 'start_time': row['start_time'], 'end_time': row.get('end_time'), 'notes': row.get('notes')})
        except Exception:
            continue

    analysis = analyze_activities_for_health(activities, stats)
    return jsonify({'success': True, 'analysis': analysis})

def _user_is_subscribed(user_email):
    try:
        response = supabase.table('users').select('is_subscribed').eq('email', user_email).execute()
        if response.data and len(response.data) > 0:
            return bool(response.data[0].get('is_subscribed'))
    except Exception:
        pass
    return False

def generate_ai_answer(question, user_email=None, history=None):
    """Advanced AI Responder using Google Gemini or OpenAI"""
    q = (question or '').strip().lower()
    history = history or []
    
    context_str = "You are Dream Baby AI, a helpful, warm, and evidence-based pediatric assistant. Keep answers concise (max 3-4 sentences) and supportive. Always advise seeing a doctor for emergencies.\n\nConversation History:\n"
    for turn in history[-5:]:
        context_str += f"User: {turn['user']}\nAI: {turn['ai']}\n"
    
    full_prompt = f"{context_str}\nUser: {question}\nAI:"

    # Try Google Gemini
    try:
        import google.generativeai as genai
        gemini_key = os.environ.get('GEMINI_API_KEY')
        if gemini_key:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(full_prompt)
            if response.text:
                return response.text.strip()
    except Exception:
        pass

    # Try OpenAI
    try:
        import openai
        openai_key = os.environ.get('OPENAI_API_KEY')
        if openai_key:
            openai.api_key = openai_key
            messages = [{"role": "system", "content": "You are a helpful pediatric assistant."}]
            for turn in history[-5:]:
                messages.append({"role": "user", "content": turn['user']})
                messages.append({"role": "assistant", "content": turn['ai']})
            messages.append({"role": "user", "content": question})
            
            resp = openai.ChatCompletion.create(model='gpt-3.5-turbo', messages=messages, max_tokens=300)
            text = resp.choices[0].message.content.strip()
            return text
    except Exception:
        pass

    # Local fallback
    import re
    patterns = {
        r'fever|temp|hot|warm': "For babies <3 months, a temp >100.4°F (38°C) is an emergency—call a doctor.",
        r'vomit|puke': "Spit-up is normal. Projectile vomiting or green/bloody vomit requires a doctor.",
        r'sleep|nap': "Newborns sleep 14-17h/day. Establish a routine.",
        r'feed|milk': "Newborns feed every 2-3 hours. Look for hunger cues.",
        r'poop|diarrhea': "Breastfed poop is yellow/seedy. Watery diarrhea risks dehydration.",
        r'cry|colic': "Check: Hunger, Diaper, Sleep. Try the 5 S's.",
        r'hello|hi': "Hello! I'm Dream Baby AI. How can I help?",
    }
    
    for pattern, response in patterns.items():
        if re.search(pattern, q):
            return response

    return "I can help with general baby care. For specific medical diagnoses, please see your pediatrician."

@app.route('/ai')
@login_required
def ai_page():
    user = session.get('user_id')
    if not user or not _user_is_subscribed(user):
        flash('AI Assistant is available to subscribed users only.', 'warning')
        return redirect(url_for('subscribe'))
    history = session.get('ai_history', [])
    return render_template('ai_assistant.html', history=history)

@app.route('/ai/ask', methods=['POST'])
@login_required
def ai_ask():
    user = session.get('user_id')
    if not user or not _user_is_subscribed(user):
        return jsonify({'success': False, 'error': 'Subscription required'}), 403

    data = request.get_json() or {}
    question = data.get('question') or data.get('q') or request.form.get('question')
    if not question:
        return jsonify({'success': False, 'error': 'Question is required'}), 400

    history = session.get('ai_history', [])

    try:
        answer = generate_ai_answer(question, user_email=user, history=history)
        
        history.append({'user': question, 'ai': answer})
        if len(history) > 20:
            history.pop(0)
        session['ai_history'] = history
        session.modified = True

        return jsonify({'success': True, 'answer': answer})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/ai/clear', methods=['POST'])
@login_required
def ai_clear():
    session['ai_history'] = []
    return jsonify({'success': True})

@app.route('/subscription_status')
@login_required
def subscription_status():
    try:
        response = supabase.table('users').select('is_subscribed, subscription_pending').eq('email', session['user_id']).execute()
        if response.data:
            user = response.data[0]
            is_subscribed = 1 if user.get('is_subscribed') else 0
            subscription_pending = 1 if user.get('subscription_pending') else 0
            session['is_subscribed'] = is_subscribed
            session['subscription_pending'] = subscription_pending
            return jsonify({'is_subscribed': is_subscribed, 'subscription_pending': subscription_pending})
    except Exception:
        pass
    
    return jsonify({'error': 'Unable to determine status'}), 500

@app.route('/protected_video/<path:filename>')
@login_required
def protected_video(filename):
    if not filename.startswith('videos/'):
        return abort(404)

    file_path = os.path.join(app.root_path, 'static', filename)
    if not os.path.isfile(file_path):
        return abort(404)

    try:
        response = supabase.table('users').select('is_subscribed').eq('email', session['user_id']).execute()
        if not response.data or not response.data[0].get('is_subscribed'):
            flash('You must be subscribed to access this content.', 'warning')
            return redirect(url_for('subscribe'))
    except Exception:
        return abort(500)

    directory = os.path.join(app.root_path, 'static')
    return send_from_directory(directory, filename)

@app.route('/subscribe', methods=['GET', 'POST'])
@login_required
def subscribe():
    if request.method == 'POST':
        try:
            supabase.table('users').update({'subscription_pending': 1}).eq('email', session['user_id']).execute()
            session['subscription_pending'] = 1
        except Exception:
            pass

        try:
            subject = f"Subscription request: {session.get('user_id')}"
            body = f"User {session.get('user_id')} has requested subscription access. Please verify payment and approve in the admin panel."
            send_admin_notification(subject, body)
        except Exception:
            pass

        return redirect(url_for('user_dashboard'))

    return render_template('subscribe.html', price=99)

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    try:
        users_response = supabase.table('users').select('*').order('created_at', desc=True).execute()
        users = users_response.data if users_response.data else []

        contacts_response = supabase.table('contacts').select('*').limit(5).order('date', desc=True).execute()
        recent_contacts = contacts_response.data if contacts_response.data else []

        total_users = len(users)
        total_contacts = len(supabase.table('contacts').select('id').execute().data or [])
        total_products = len(supabase.table('products').select('id').execute().data or [])
        total_orders = len(supabase.table('cart').select('id').execute().data or [])
    except Exception:
        users = []
        recent_contacts = []
        total_users = total_contacts = total_products = total_orders = 0
    
    pending_count = len([u for u in users if u.get('subscription_pending')])
    subscribed_count = len([u for u in users if u.get('is_subscribed')])
    
    stats = {
        'total_users': total_users,
        'total_contacts': total_contacts,
        'total_products': total_products,
        'total_orders': total_orders,
        'pending_requests': pending_count,
        'subscribed_users': subscribed_count
    }

    return render_template('admin_dashboard.html', users=users, stats=stats, recent_contacts=recent_contacts)

@app.route('/admin/users')
@admin_required
def admin_manage_users():
    try:
        response = supabase.table('users').select('*').order('created_at', desc=True).execute()
        users = response.data if response.data else []
    except Exception:
        users = []
    
    return render_template('admin_manage_users.html', users=users)

@app.route('/admin/promote/<int:user_id>', methods=['POST'])
@admin_required
def admin_promote_user(user_id):
    try:
        supabase.table('users').update({'is_admin': 1}).eq('id', user_id).execute()
    except Exception:
        flash('Error promoting user', 'danger')
    
    return redirect(url_for('admin_manage_users'))

@app.route('/admin/demote/<int:user_id>', methods=['POST'])
@admin_required
def admin_demote_user(user_id):
    try:
        supabase.table('users').update({'is_admin': 0}).eq('id', user_id).execute()
    except Exception:
        flash('Error demoting user', 'danger')
    
    return redirect(url_for('admin_manage_users'))

@app.route('/admin/subscriptions')
@admin_required
def admin_subscriptions():
    try:
        response = supabase.table('users').select('id, email, parent_name, created_at').eq('subscription_pending', 1).execute()
        requests = response.data if response.data else []
    except Exception:
        requests = []
    
    return render_template('admin_subscriptions.html', requests=requests)

@app.route('/admin/approve_subscription/<int:user_id>', methods=['POST'])
@admin_required
def admin_approve_subscription(user_id):
    try:
        response = supabase.table('users').select('email, is_subscribed, subscription_pending').eq('id', user_id).execute()
        if response.data:
            user = response.data[0]
            supabase.table('users').update({'is_subscribed': 1, 'subscription_pending': 0}).eq('id', user_id).execute()
            flash(f"Approved subscription for {user.get('email')}", 'success')
    except Exception:
        flash('Error approving subscription', 'danger')
    
    return redirect(request.referrer or url_for('admin_manage_subscriptions'))

@app.route('/admin/reject_subscription/<int:user_id>', methods=['POST'])
@admin_required
def admin_reject_subscription(user_id):
    try:
        response = supabase.table('users').select('email').eq('id', user_id).execute()
        if response.data:
            user = response.data[0]
            supabase.table('users').update({'subscription_pending': 0, 'is_subscribed': 0}).eq('id', user_id).execute()
            flash(f"Rejected subscription request for {user.get('email')}", 'warning')
    except Exception:
        flash('Error rejecting subscription', 'danger')
    
    return redirect(request.referrer or url_for('admin_manage_subscriptions'))

@app.route('/admin/manage_subscriptions')
@admin_required
def admin_manage_subscriptions():
    try:
        users_response = supabase.table('users').select('id, email, parent_name, baby_name, is_subscribed, subscription_pending').order('created_at', desc=True).execute()
        all_users = users_response.data if users_response.data else []
        
        pending_requests = [u for u in all_users if u.get('subscription_pending')]
        subscribed_users = [u for u in all_users if u.get('is_subscribed')]
    except Exception:
        all_users = []
        pending_requests = []
        subscribed_users = []
    
    return render_template('admin_manage_subscriptions.html',
                          pending_requests=pending_requests,
                          subscribed_users=subscribed_users,
                          all_users=all_users,
                          pending_count=len(pending_requests),
                          subscribed_count=len(subscribed_users))

@app.route('/admin/grant_subscription/<int:user_id>', methods=['POST'])
@admin_required
def admin_grant_subscription(user_id):
    try:
        supabase.table('users').update({'is_subscribed': 1, 'subscription_pending': 0}).eq('id', user_id).execute()
        flash('Subscription granted', 'success')
    except Exception:
        flash('Error granting subscription', 'danger')
    
    return redirect(url_for('admin_manage_subscriptions'))

@app.route('/admin/revoke_subscription/<int:user_id>', methods=['POST'])
@admin_required
def admin_revoke_subscription(user_id):
    try:
        supabase.table('users').update({'is_subscribed': 0, 'subscription_pending': 0}).eq('id', user_id).execute()
        flash('Subscription revoked', 'warning')
    except Exception:
        flash('Error revoking subscription', 'danger')
    
    return redirect(url_for('admin_manage_subscriptions'))

@app.route('/admin/action_log')
@admin_required
def admin_action_log():
    all_actions = read_all_admin_actions()
    all_actions.reverse()
    return render_template('admin_action_log.html', actions=all_actions, total_actions=len(all_actions))

@app.route('/admin/undo_action/<int:log_index>', methods=['POST'])
@admin_required
def admin_undo_action(log_index):
    all_actions = read_all_admin_actions()
    if log_index < 0 or log_index >= len(all_actions):
        flash('Action not found in log.', 'danger')
        return redirect(url_for('admin_action_log'))

    target = all_actions[log_index]
    user_id = target.get('user_id')
    prev_is_sub = int(target.get('prev_is_subscribed', 0))
    prev_pending = int(target.get('prev_subscription_pending', 0))

    try:
        supabase.table('users').update({'is_subscribed': prev_is_sub, 'subscription_pending': prev_pending}).eq('id', user_id).execute()
        flash(f"Reverted action on user ID {user_id}", 'success')
    except Exception:
        flash('Failed to undo action.', 'danger')

    return redirect(url_for('admin_action_log'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
