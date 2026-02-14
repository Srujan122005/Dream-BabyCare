from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_from_directory, abort
from functools import wraps
from datetime import datetime, timedelta
import os
import json
import sqlite3
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
        # Allow access if logged in via admin panel OR the logged-in user has is_admin flag in DB
        if session.get('admin_logged_in'):
            return f(*args, **kwargs)

        user_email = session.get('user_id')
        if user_email:
            try:
                response = supabase.table('users').select('is_admin').eq('email', user_email).execute()
                if response.data and len(response.data) > 0:
                    if int(response.data[0]['is_admin'] or 0) == 1:
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
            # Insert sample products
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

        # Check if doctors exist
        response = supabase.table('doctors').select('id').limit(1).execute()
        if not response.data:
            # Insert sample doctors
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
    # Also load user language if logged in (existing logic moved here/kept)
    if 'user_id' in session and 'language' not in session:
        load_user_language()

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
        conn = None
        try:
            conn = sqlite3.connect('babycare.db')
            c = conn.cursor()
            c.execute("SELECT SUM(quantity) FROM cart WHERE session_id = ?", (session['session_id'],))
            res = c.fetchone()
            if res and res[0]:
                cart_count = res[0]
        except:
            pass
        finally:
            if conn:
                conn.close()

    # Inject logo URL globally (ensure you have a file at static/images/Dream_Baby_Care_Logo (1).jpg)
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
                    entry['log_index'] = i  # Store position for undo reference
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
    # Requires SMTP settings in app.config: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_USE_TLS (optional), ADMIN_NOTIFICATION_EMAIL
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
        'linkedin_profile': 'https://www.linkedin.com/in/srujan-ss-9b7a1b336/',  # Corrected LinkedIn profile link
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
        # Update user's language preference in database if logged in
        if 'user_id' in session:
            try:
                conn = sqlite3.connect('babycare.db')
                c = conn.cursor()
                c.execute("UPDATE users SET language = ? WHERE email = ?", (lang, session['user_id']))
                conn.commit()
                conn.close()
            except Exception:
                pass
    return redirect(request.referrer or url_for('home'))

# Tips page
@app.route('/tips')
@login_required
def tips():
    # Get user's language preference from database (or session fallback)
    lang = session.get('language', 'en')
    
    if lang not in translations:
        lang = 'en'
    
    # Get translations for current language
    lang_data = translations[lang]
    
    # Tip categories mapping to translation keys
    tip_keys = ['feeding', 'diapering', 'sleep', 'bathing', 'crying']
    tips_content = {}
    for key in tip_keys:
        if key in lang_data['tips']:
            tips_content[key] = lang_data['tips'][key]
    
    # Look for videos in static/videos/<slug>/
    videos_by_category = {}
    categories = ['Feeding', 'Diapering', 'Health', 'Bathing', 'Soothing']
    for cat in categories:
        slug = cat.lower().replace(' ', '_')
        folder = os.path.join(app.root_path, 'static', 'videos', slug)
        video_list = []
        if os.path.isdir(folder):
            for fname in sorted(os.listdir(folder)):
                if fname.lower().endswith(('.mp4', '.webm', '.ogg')):
                    # Serve videos via protected endpoint to enforce subscription checks
                    url = url_for('protected_video', filename=f'videos/{slug}/{fname}')
                    video_list.append({'filename': fname, 'url': url})
        videos_by_category[cat] = video_list

    # Determine subscription state from session (keeps template simple)
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
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    products = c.fetchall()
    conn.close()
    
    # Group products by category
    categories = {}
    for product in products:
        # Convert tuple to list to make it mutable
        product_list = list(product)
        # Prepend the static path to the image filename
        if product_list[4].startswith('http'):
            product_list[4] = product_list[4]
        else:
            product_list[4] = url_for('static', filename=f'images/{product[4]}')
        category = product[5]  # category is at index 5
        if category not in categories:
            categories[category] = []
        categories[category].append(product_list)
    
    return render_template('shop.html', categories=categories)

# Product detail page
@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = c.fetchone()
    conn.close()
    
    if product:
        # Convert tuple to list to make it mutable
        product_list = list(product)
        # Prepend the static path to the image filename
        if product_list[4].startswith('http'):
            product_list[4] = product_list[4]
        else:
            product_list[4] = url_for('static', filename=f'images/{product[4]}')
        return render_template('product_detail.html', product=product_list)
    else:
        return "Product not found", 404

# Add to cart functionality
@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = c.fetchone()
    
    if product:
        conn.close()
        # Redirect to Blinkit search page for the product
        return redirect(f"https://blinkit.com/s/?q={quote(product[1])}")
    
    conn.close()
    return redirect(url_for('shop'))

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    if 'session_id' in session:
        conn = sqlite3.connect('babycare.db')
        c = conn.cursor()
        c.execute("DELETE FROM cart WHERE product_id = ? AND session_id = ?", (product_id, session['session_id']))
        conn.commit()
        conn.close()
        flash('Item removed from cart', 'info')
    return redirect(url_for('cart'))

@app.route('/checkout')
@login_required
def checkout():
    if 'session_id' in session:
        conn = sqlite3.connect('babycare.db')
        c = conn.cursor()
        # In a real app, you would create an order record here
        c.execute("DELETE FROM cart WHERE session_id = ?", (session['session_id'],))
        conn.commit()
        conn.close()
        flash('Order placed successfully! Thank you for shopping.', 'success')
    return redirect(url_for('shop'))

# View cart
@app.route('/cart')
def cart():
    if 'session_id' not in session:
        return render_template('cart.html', cart_items=[], total=0)
    
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    c.execute('''SELECT products.id, products.name, products.price, products.image, cart.quantity 
                 FROM cart 
                 JOIN products ON cart.product_id = products.id 
                 WHERE cart.session_id = ?''', (session['session_id'],))
    cart_items_raw = c.fetchall()
    cart_items = []
    for item in cart_items_raw:
        item_list = list(item)
        # Prepend static path to image
        if item_list[3].startswith('http'):
            item_list[3] = item_list[3]
        else:
            item_list[3] = url_for('static', filename=f'images/{item[3]}')
        cart_items.append(item_list)
    
    total = sum(item[2] * item[4] for item in cart_items)  # price * quantity
    
    conn.close()
    return render_template('cart.html', cart_items=cart_items, total=total)

# Contact page
@app.route('/contact', methods=['GET', 'POST'])
@login_required
def contact():
    # Require subscription to contact
    if not session.get('is_subscribed'):
        return redirect(url_for('subscribe'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Save to database
        conn = sqlite3.connect('babycare.db')
        c = conn.cursor()
        c.execute("INSERT INTO contacts (name, email, message, date) VALUES (?, ?, ?, ?)",
                  (name, email, message, date))
        conn.commit()
        conn.close()
        
        return redirect(url_for('contact_success'))

    # Fetch doctors for appointment/call section
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    c.execute("SELECT * FROM doctors")
    doctors = c.fetchall()
    conn.close()

    return render_template('contact.html', doctors=doctors)

@app.route('/book_appointment', methods=['POST'])
@login_required
def book_appointment():
    doctor_id = request.form.get('doctor_id')
    appt_time = request.form.get('appointment_time')
    appt_type = request.form.get('type') # video or voice
    
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    c.execute("INSERT INTO appointments (user_id, doctor_id, appointment_time, type, created_at) VALUES (?, ?, ?, ?, ?)",
              (session['user_id'], doctor_id, appt_time, appt_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    
    flash('Appointment request sent successfully!', 'success')
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
        conn = sqlite3.connect('babycare.db')
        c = conn.cursor()
        # Check if already subscribed
        c.execute("SELECT * FROM newsletter_subscribers WHERE email = ?", (email,))
        if c.fetchone():
            flash('You are already subscribed to our newsletter!', 'info')
        else:
            subscribed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO newsletter_subscribers (email, subscribed_at) VALUES (?, ?)", (email, subscribed_at))
            conn.commit()
            flash('Thank you for subscribing to our newsletter!', 'success')
        conn.close()
    except Exception:
        flash('An error occurred while subscribing.', 'danger')

    return redirect(request.referrer or url_for('home'))

@app.route('/admin/contacts')
@admin_required
def admin_contacts():
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    # Select columns including reply info if present
    try:
        c.execute("PRAGMA table_info('contacts')")
        cols = [r[1] for r in c.fetchall()]
        if 'admin_reply' in cols:
            c.execute("SELECT id, name, email, message, date, admin_reply, replied_at, replied_by FROM contacts ORDER BY date DESC")
        else:
            c.execute("SELECT id, name, email, message, date, NULL, NULL, NULL FROM contacts ORDER BY date DESC")
        contacts = c.fetchall()
    except Exception:
        contacts = []
    conn.close()
    return render_template('admin_contacts.html', contacts=contacts)


@app.route('/admin/reply_contact/<int:contact_id>', methods=['POST'])
@admin_required
def admin_reply_contact(contact_id):
    reply = request.form.get('reply')
    if not reply:
        flash('Reply cannot be empty.', 'warning')
        return redirect(request.referrer or url_for('admin_contacts'))

    try:
        conn = sqlite3.connect('babycare.db')
        c = conn.cursor()
        # Update contact with reply, replied_at and replied_by
        replied_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        admin_user = session.get('admin_user') or session.get('user_id') or 'admin'
        c.execute("UPDATE contacts SET admin_reply = ?, replied_at = ?, replied_by = ? WHERE id = ?",
                  (reply, replied_at, admin_user, contact_id))
        conn.commit()
        # Optionally send email to user (best-effort)
        try:
            c.execute("SELECT email FROM contacts WHERE id = ?", (contact_id,))
            row = c.fetchone()
            if row and app.config.get('SMTP_HOST') and app.config.get('ADMIN_NOTIFICATION_EMAIL'):
                to_email = row[0]
                subject = 'Reply to your message on Dream Baby Care'
                body = f"Dear user,\n\nAn admin has replied to your message:\n\n{reply}\n\n--\nDream Baby Care"
                send_admin_notification(subject, body)
        except Exception:
            pass
        conn.close()
        flash('Reply saved and user notified (if SMTP configured).', 'success')
    except Exception:
        flash('Failed to save reply.', 'danger')

    return redirect(request.referrer or url_for('admin_contacts'))

@app.route('/admin/doctors')
@admin_required
def admin_doctors():
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    c.execute("SELECT * FROM doctors")
    doctors = c.fetchall()
    conn.close()
    return render_template('admin_doctors.html', doctors=doctors)

@app.route('/admin/doctor/add', methods=['POST'])
@admin_required
def admin_add_doctor():
    name = request.form.get('name')
    spec = request.form.get('specialization')
    email = request.form.get('email')
    password = request.form.get('password')
    image = request.form.get('image')
    phone = request.form.get('phone')
    video = request.form.get('video_link')

    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    c.execute("INSERT INTO doctors (name, specialization, email, password, image, phone, video_link) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (name, spec, email, password, image, phone, video))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_doctors'))

@app.route('/admin/doctor/delete/<int:doctor_id>', methods=['POST'])
@admin_required
def admin_delete_doctor(doctor_id):
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    c.execute("DELETE FROM doctors WHERE id = ?", (doctor_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_doctors'))

@app.route('/admin/appointments')
@admin_required
def admin_appointments():
    status_filter = request.args.get('status')
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    
    query = """
        SELECT a.id, u.parent_name, u.email, d.name, a.appointment_time, a.type, a.status, a.created_at
        FROM appointments a
        LEFT JOIN users u ON a.user_id = u.email
        LEFT JOIN doctors d ON a.doctor_id = d.id
    """
    params = []
    if status_filter and status_filter != 'All':
        query += " WHERE a.status = ?"
        params.append(status_filter)
    
    query += " ORDER BY a.appointment_time DESC"
    
    c.execute(query, tuple(params))
    appointments = c.fetchall()
    conn.close()
    return render_template('admin_appointments.html', appointments=appointments, current_status=status_filter)

@app.route('/admin/appointment/status/<int:appt_id>', methods=['POST'])
@admin_required
def admin_update_appointment_status(appt_id):
    status = request.form.get('status')
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    c.execute("UPDATE appointments SET status = ? WHERE id = ?", (status, appt_id))
    conn.commit()
    conn.close()
    flash(f'Appointment status updated to {status}', 'success')
    return redirect(url_for('admin_appointments'))

# ===== DOCTOR AUTH & DASHBOARD =====

@app.route('/doctor/login', methods=['GET', 'POST'])
def doctor_login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        conn = sqlite3.connect('babycare.db')
        c = conn.cursor()
        c.execute("SELECT * FROM doctors WHERE email = ? AND password = ?", (email, password))
        doctor = c.fetchone()
        conn.close()
        if doctor:
            session['doctor_id'] = doctor[0]
            session['doctor_name'] = doctor[1]
            return redirect(url_for('doctor_dashboard'))
        else:
            error = 'Invalid doctor credentials. Please try again.'
    return render_template('doctor_login.html', error=error)

@app.route('/doctor/dashboard')
@doctor_required
def doctor_dashboard():
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()

    # Fetch doctor's details
    c.execute("SELECT name, specialization FROM doctors WHERE id = ?", (session['doctor_id'],))
    doctor_details = c.fetchone()

    # Fetch upcoming appointments for the logged-in doctor
    c.execute("""
        SELECT a.id, u.parent_name, u.email, a.appointment_time, a.type, a.status, u.phone
        FROM appointments a
        JOIN users u ON a.user_id = u.email
        WHERE a.doctor_id = ? AND a.status IN ('Confirmed', 'Pending')
        ORDER BY a.appointment_time ASC
    """, (session['doctor_id'],))
    appointments = c.fetchall()
    conn.close()

    # Calculate stats
    stats = {
        'total_upcoming': len(appointments),
        'pending': len([appt for appt in appointments if appt[5] == 'Pending']),
        'confirmed': len([appt for appt in appointments if appt[5] == 'Confirmed'])
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
    notes = request.form.get('notes')
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    
    if status == 'Completed' and notes:
        c.execute("UPDATE appointments SET status = ?, notes = ? WHERE id = ? AND doctor_id = ?", (status, notes, appt_id, session['doctor_id']))
    else:
        c.execute("UPDATE appointments SET status = ? WHERE id = ? AND doctor_id = ?", (status, appt_id, session['doctor_id']))
    conn.commit()
    conn.close()
    flash(f'Appointment marked as {status}', 'success')
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
        
        # Calculate baby age from DOB
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
        
        # Check if email already exists
        conn = sqlite3.connect('babycare.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        if c.fetchone():
            conn.close()
            return render_template('register.html', error="Email already registered")
        
        # Insert new user
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        language = request.form.get('language', 'en')  # Get language from form (default 'en')
        c.execute('''INSERT INTO users (email, password, parent_name, baby_name, baby_dob, baby_age, phone, address, created_at, language)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (email, password, parent_name, baby_name, baby_dob, baby_age, phone, address, created_at, language))
        conn.commit()
        conn.close()
        
        session['user_id'] = email
        session['user_name'] = parent_name
        session['language'] = language  # Set language in session
        return redirect(url_for('home'))
    
    return render_template('register.html')

# User Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = sqlite3.connect('babycare.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_id'] = email
            session['user_name'] = user[3]
            # Fetch language and subscription status from DB (safe checks)
            try:
                conn2 = sqlite3.connect('babycare.db')
                c2 = conn2.cursor()
                c2.execute("PRAGMA table_info('users')")
                cols = [r[1] for r in c2.fetchall()]
                # language
                if 'language' in cols:
                    c2.execute("SELECT language FROM users WHERE email = ?", (email,))
                    res = c2.fetchone()
                    session['language'] = res[0] if res and res[0] else 'en'
                else:
                    session['language'] = 'en'
                # is_admin
                if 'is_admin' in cols:
                    c2.execute("SELECT is_admin FROM users WHERE email = ?", (email,))
                    res_admin = c2.fetchone()
                    session['is_admin'] = 1 if res_admin and res_admin[0] else 0
                else:
                    session['is_admin'] = 0
                # is_subscribed
                if 'is_subscribed' in cols:
                    c2.execute("SELECT is_subscribed FROM users WHERE email = ?", (email,))
                    res2 = c2.fetchone()
                    session['is_subscribed'] = 1 if res2 and res2[0] else 0
                else:
                    session['is_subscribed'] = 0
                # subscription_pending
                if 'subscription_pending' in cols:
                    c2.execute("SELECT subscription_pending FROM users WHERE email = ?", (email,))
                    res3 = c2.fetchone()
                    session['subscription_pending'] = 1 if res3 and res3[0] else 0
                else:
                    session['subscription_pending'] = 0
                conn2.close()
            except Exception:
                session['language'] = 'en'
                session['is_subscribed'] = 0

            return redirect(url_for('home'))
        else:
            return render_template('login.html', error="Invalid email or password")
    
    return render_template('login.html')

# User Dashboard
@app.route('/user/dashboard')
@login_required
def user_dashboard():
    
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (session['user_id'],))
    user = c.fetchone()
    
    # Fetch recent tracking data
    c.execute("""SELECT * FROM baby_tracker WHERE user_id = ? ORDER BY created_at DESC LIMIT 10""", 
              (session['user_id'],))
    tracking_data = c.fetchall()

    # Fetch user contact messages and any admin replies
    try:
        c.execute("PRAGMA table_info('contacts')")
        contact_cols = [r[1] for r in c.fetchall()]
        if 'admin_reply' in contact_cols:
            c.execute("SELECT id, name, email, message, date, admin_reply, replied_at, replied_by FROM contacts WHERE email = ? ORDER BY date DESC", (session['user_id'],))
        else:
            c.execute("SELECT id, name, email, message, date, NULL, NULL, NULL FROM contacts WHERE email = ? ORDER BY date DESC", (session['user_id'],))
        user_contacts = c.fetchall()
    except Exception:
        user_contacts = []
    
    # Fetch appointments
    try:
        c.execute("""
            SELECT a.id, d.name, a.appointment_time, a.type, a.status, d.video_link, a.notes
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            WHERE a.user_id = ?
            ORDER BY a.appointment_time DESC
        """, (session['user_id'],))
        appointments = c.fetchall()
    except Exception:
        appointments = []

    conn.close()
    
    if user:
        user_data = {
            'id': user[0],
            'email': user[1],
            'parent_name': user[3],
            'baby_name': user[4],
            'baby_dob': user[5],
            'baby_age': user[6],
            'phone': user[7],
            'address': user[8],
            'created_at': user[9]
        }
        # pass subscription flags explicitly
        is_sub = session.get('is_subscribed', 0)
        sub_pending = session.get('subscription_pending', 0)
        return render_template('user_dashboard.html', user=user_data, tracking_data=tracking_data,
                       is_subscribed=is_sub, subscription_pending=sub_pending, user_contacts=user_contacts, appointments=appointments)
    
    return redirect(url_for('login'))

# User Logout
@app.route('/user/logout')
def user_logout():
    session.clear()
    return redirect(url_for('landing'))

# ===== BABY TRACKER =====

# Add tracking event
@app.route('/tracker/add', methods=['POST'])
@login_required
def add_tracker():
    activity_type = request.form.get('activity_type')
    notes = request.form.get('notes', '')
    
    if not activity_type:
        return jsonify({'error': 'Activity type is required'}), 400
    
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute("""INSERT INTO baby_tracker (user_id, activity_type, start_time, created_at, notes)
                 VALUES (?, ?, ?, ?, ?)""",
              (session['user_id'], activity_type, start_time, created_at, notes))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': f'{activity_type} started!'}), 201

# End tracking event
@app.route('/tracker/end/<int:tracker_id>', methods=['POST'])
@login_required
def end_tracker(tracker_id):
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    
    # Verify ownership
    c.execute("SELECT * FROM baby_tracker WHERE id = ? AND user_id = ?", (tracker_id, session['user_id']))
    tracker = c.fetchone()
    
    if not tracker:
        conn.close()
        return jsonify({'error': 'Tracker not found'}), 404
    
    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("UPDATE baby_tracker SET end_time = ? WHERE id = ?", (end_time, tracker_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': f'{tracker[2]} ended!'}), 200

# Delete tracker entry
@app.route('/tracker/delete/<int:tracker_id>', methods=['POST'])
@login_required
def delete_tracker(tracker_id):
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    
    # Verify ownership
    c.execute("SELECT * FROM baby_tracker WHERE id = ? AND user_id = ?", (tracker_id, session['user_id']))
    tracker = c.fetchone()
    
    if not tracker:
        conn.close()
        return jsonify({'error': 'Tracker not found'}), 404
    
    c.execute("DELETE FROM baby_tracker WHERE id = ?", (tracker_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Entry deleted!'}), 200

# ===== ADMIN PANEL =====

# Reminder Routes
@app.route('/tracker/reminder/add', methods=['POST'])
@login_required
def add_reminder():
    message = request.form.get('message')
    remind_time = request.form.get('remind_time')
    
    if not message or not remind_time:
        return jsonify({'error': 'Message and time are required'}), 400

    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO reminders (user_id, message, remind_time, created_at) VALUES (?, ?, ?, ?)",
              (session['user_id'], message, remind_time, created_at))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Reminder set!'})

@app.route('/tracker/reminder/delete/<int:reminder_id>', methods=['POST'])
@login_required
def delete_reminder(reminder_id):
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    c.execute("DELETE FROM reminders WHERE id = ? AND user_id = ?", (reminder_id, session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Reminder deleted!'})

# Tracker page (separate full page)
@app.route('/tracker')
@login_required
def tracker_page():
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    
    # Optional date filtering
    date_filter = request.args.get('date')
    if date_filter:
        c.execute("SELECT * FROM baby_tracker WHERE user_id = ? AND start_time LIKE ? ORDER BY created_at DESC", 
                 (session['user_id'], f"{date_filter}%"))
    else:
        c.execute("SELECT * FROM baby_tracker WHERE user_id = ? ORDER BY created_at DESC", (session['user_id'],))
        
    raw_data = c.fetchall()

    # Fetch reminders
    c.execute("SELECT * FROM reminders WHERE user_id = ? ORDER BY remind_time ASC", (session['user_id'],))
    reminders = c.fetchall()
    conn.close()
    
    # Process data for statistics and better display
    today_str = datetime.now().strftime("%Y-%m-%d")
    display_date = date_filter if date_filter else today_str
    
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
        # row: id(0), user_id(1), activity_type(2), start_time(3), end_time(4), notes(5), created_at(6)
        try:
            start_dt = datetime.strptime(row[3], "%Y-%m-%d %H:%M:%S")
            end_dt = datetime.strptime(row[4], "%Y-%m-%d %H:%M:%S") if row[4] else None
            
            duration_str = ""
            if end_dt:
                diff = end_dt - start_dt
                total_seconds = diff.total_seconds()
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
                
                if start_dt.strftime("%Y-%m-%d") == display_date and row[2] == 'Sleep':
                    stats['sleep_duration'] += total_seconds
            
            if start_dt.strftime("%Y-%m-%d") == display_date:
                if row[2] == 'Feeding': stats['feed_count'] += 1
                elif row[2] == 'Diaper': stats['diaper_count'] += 1

            formatted_activities.append({
                'id': row[0],
                'type': row[2],
                'start_time': start_dt.strftime("%I:%M %p"),
                'date': start_dt.strftime("%b %d"),
                'end_time': end_dt.strftime("%I:%M %p") if end_dt else None,
                'duration': duration_str,
                'notes': row[5],
                'icon': icons.get(row[2], 'fas fa-circle'),
                'is_active': row[4] is None and row[2] == 'Sleep'
            })
        except Exception:
            continue

    # Format sleep duration
    sleep_hours = int(stats['sleep_duration'] // 3600)
    sleep_minutes = int((stats['sleep_duration'] % 3600) // 60)
    stats['sleep_display'] = f"{sleep_hours}h {sleep_minutes}m"

    return render_template('tracker.html', 
                         tracking_data=raw_data, 
                         activities=formatted_activities, 
                         stats=stats,
                         current_date=display_date,
                         reminders=reminders)


# Simple analyzer for activities to produce health insights
def analyze_activities_for_health(activities, stats):
    """Return a concise analysis dict given today's activities and stats.
    This is a local heuristic analyzer. If an external AI service is desired,
    you can extend this to call OpenAI (ENV var OPENAI_API_KEY) for richer suggestions.
    """
    insights = []
    score = 0

    # Sleep analysis
    try:
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
    except Exception:
        pass

    # Feeding analysis
    feeds = stats.get('feed_count', 0)
    if feeds >= 8:
        insights.append(('Feeding', 'Frequent feeds recorded — hydration and growth cues look normal.'))
        score += 1
    elif feeds >= 4:
        insights.append(('Feeding', 'Feeding frequency is within normal range.'))
    else:
        insights.append(('Feeding', 'Fewer feeds logged — watch for signs of low intake.'))
        score -= 1

    # Diaper analysis
    diapers = stats.get('diaper_count', 0)
    if diapers >= 6:
        insights.append(('Diaper', 'Diaper changes are frequent — hydration is likely good.'))
        score += 1
    elif diapers >= 3:
        insights.append(('Diaper', 'Diaper changes are normal.'))
    else:
        insights.append(('Diaper', 'Low diaper changes — monitor urine output and consult if worried.'))
        score -= 1

    # Check for concerning activity notes (fever, high temp, excessive crying)
    notes_alerts = []
    crying_count = 0
    for a in activities:
        t = (a.get('type') or '').lower()
        notes = (a.get('notes') or '').lower()
        if 'cry' in t:
            crying_count += 1
        if 'fever' in notes or 'temp' in notes or '°c' in notes or 'c' in notes:
            notes_alerts.append('Temperature noted in entry — check for fever and consult pediatrician if >38°C.')
        if 'refuse' in notes or 'not feeding' in notes or 'dehydrat' in notes:
            notes_alerts.append('Feeding concerns noted — monitor intake closely.')

    if crying_count >= 3:
        insights.append(('Crying', 'Several crying episodes recorded — could indicate discomfort or colic.'))
        score -= 1

    for na in notes_alerts:
        insights.append(('Note', na))

    # Final recommendation based on score
    if score >= 3:
        final = 'Overall: Baby looks well today.'
    elif score >= 0:
        final = 'Overall: Mostly normal but keep an eye on the few low metrics.'
    else:
        final = 'Overall: Some caution advised — monitor symptoms and consider contacting your pediatrician.'

    return {'insights': insights, 'summary': final, 'score': score}


# Endpoint to analyze activities for a selected date (returns JSON)
@app.route('/tracker/analyze', methods=['GET'])
@login_required
def tracker_analyze():
    date_filter = request.args.get('date')
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    try:
        if date_filter:
            c.execute("SELECT * FROM baby_tracker WHERE user_id = ? AND start_time LIKE ? ORDER BY created_at DESC",
                      (session['user_id'], f"{date_filter}%"))
        else:
            today = datetime.now().strftime('%Y-%m-%d')
            c.execute("SELECT * FROM baby_tracker WHERE user_id = ? AND start_time LIKE ? ORDER BY created_at DESC",
                      (session['user_id'], f"{today}%"))
        rows = c.fetchall()
    except Exception:
        rows = []
    finally:
        conn.close()

    # Build activities and stats like tracker_page
    activities = []
    stats = {'sleep_duration': 0, 'feed_count': 0, 'diaper_count': 0}
    for row in rows:
        try:
            start_dt = datetime.strptime(row[3], "%Y-%m-%d %H:%M:%S")
            end_dt = datetime.strptime(row[4], "%Y-%m-%d %H:%M:%S") if row[4] else None
            if end_dt and row[2] == 'Sleep':
                stats['sleep_duration'] += (end_dt - start_dt).total_seconds()
            if row[2] == 'Feeding': stats['feed_count'] += 1
            if row[2] == 'Diaper': stats['diaper_count'] += 1

            activities.append({'type': row[2], 'start_time': row[3], 'end_time': row[4], 'notes': row[5]})
        except Exception:
            continue

    analysis = analyze_activities_for_health(activities, stats)
    return jsonify({'success': True, 'analysis': analysis})


def _user_is_subscribed(user_email):
    try:
        conn = sqlite3.connect('babycare.db')
        c = conn.cursor()
        c.execute("PRAGMA table_info('users')")
        cols = [r[1] for r in c.fetchall()]
        if 'is_subscribed' in cols:
            c.execute("SELECT is_subscribed FROM users WHERE email = ?", (user_email,))
            r = c.fetchone()
            conn.close()
            return bool(r and int(r[0]) == 1)
        conn.close()
    except Exception:
        pass
    return False


def generate_ai_answer(question, user_email=None, history=None):
    """Advanced AI Responder.
    1. Tries Google Gemini API (if GEMINI_API_KEY env var is set)
    2. Tries OpenAI API (if OPENAI_API_KEY env var is set)
    3. Falls back to Advanced Local Heuristics (Regex based)
    """
    q = (question or '').strip().lower()
    history = history or []
    
    # Build context string for APIs
    context_str = "You are Dream Baby AI, a helpful, warm, and evidence-based pediatric assistant. Keep answers concise (max 3-4 sentences) and supportive. Always advise seeing a doctor for emergencies.\n\nConversation History:\n"
    for turn in history[-5:]: # Keep last 5 turns for context
        context_str += f"User: {turn['user']}\nAI: {turn['ai']}\n"
    
    full_prompt = f"{context_str}\nUser: {question}\nAI:"

    # 1. Try Google Gemini
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

    # 2. Try OpenAI
    try:
        import os
        openai_key = os.environ.get('OPENAI_API_KEY')
        if openai_key:
            try:
                import openai
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
    except Exception:
        pass

    # 3. Advanced Local Heuristics (Regex based fallback)
    import re
    patterns = {
        r'fever|temp|hot|warm': "For babies <3 months, a temp >100.4°F (38°C) is an emergency—call a doctor. For older babies, monitor behavior. If they are playing and drinking, they may just need rest. Keep them hydrated.",
        r'vomit|puke|throw up': "Spit-up is normal. Projectile vomiting or green/bloody vomit requires a doctor. Keep baby upright after feeds. If vomiting persists, watch for dehydration (dry lips, no tears).",
        r'sleep|nap|awake|night': "Newborns sleep 14-17h/day. Establish a 'Bath, Book, Bed' routine. Ensure the room is cool and dark. If baby wakes often, check hunger/diaper, but try to let them self-soothe.",
        r'feed|milk|breast|bottle|hungry': "Newborns feed every 2-3 hours. Look for hunger cues like rooting. 6+ wet diapers/day means they are getting enough. If latching hurts, consult a lactation expert.",
        r'poop|constipat|diarrhea|stool': "Breastfed poop is yellow/seedy; formula is tan. Hard pellets mean constipation—consult a doctor. Watery diarrhea risks dehydration. Call a doctor if there's blood in stool.",
        r'cry|colic|fuss|scream': "Check the basics: Hunger, Diaper, Sleep. Try the 5 S's: Swaddle, Side-position, Shush, Swing, Suck. If crying is inconsolable for hours, it might be colic.",
        r'rash|skin|acne|red': "Baby acne usually clears up alone. For diaper rash, use zinc cream and air time. If a rash doesn't fade when pressed or comes with fever, seek medical help.",
        r'cough|cold|sneeze|nose': "Saline drops and a bulb syringe help with congestion. A cool-mist humidifier can ease breathing. Watch for rapid breathing or chest retractions—that's urgent.",
        r'solid|food|eat': "Start solids around 6 months when baby can sit up. Start with single-ingredient purees (sweet potato, avocado) or soft finger foods. Introduce allergens one by one.",
        r'hello|hi|hey': "Hello! I'm Dream Baby AI. I can help with sleep, feeding, health, and development. What's on your mind?",
        r'thank': "You're very welcome! You're doing a great job. Let me know if you need anything else."
    }
    
    for pattern, response in patterns.items():
        if re.search(pattern, q):
            return response

    return "I can help with general baby care (sleep, feeding, health). Since I'm an AI, for specific medical diagnoses, please see your pediatrician. Could you rephrase your question?"


@app.route('/ai')
@login_required
def ai_page():
    # Only allow subscribed users
    user = session.get('user_id')
    if not user or not _user_is_subscribed(user):
        flash('AI Assistant is available to subscribed users only. Please subscribe to access this feature.', 'warning')
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

    # Get history
    history = session.get('ai_history', [])

    try:
        answer = generate_ai_answer(question, user_email=user, history=history)
        
        # Update history
        history.append({'user': question, 'ai': answer})
        if len(history) > 20: # Keep last 20 turns
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


# API to check subscription status for current user (used by client polling)
@app.route('/subscription_status')
@login_required
def subscription_status():
    try:
        conn = sqlite3.connect('babycare.db')
        c = conn.cursor()
        c.execute("PRAGMA table_info('users')")
        cols = [r[1] for r in c.fetchall()]
        is_subscribed = 0
        subscription_pending = 0
        if 'is_subscribed' in cols:
            c.execute("SELECT is_subscribed FROM users WHERE email = ?", (session['user_id'],))
            r = c.fetchone()
            is_subscribed = 1 if r and r[0] else 0
        if 'subscription_pending' in cols:
            c.execute("SELECT subscription_pending FROM users WHERE email = ?", (session['user_id'],))
            r2 = c.fetchone()
            subscription_pending = 1 if r2 and r2[0] else 0
        conn.close()
        # keep session in sync
        session['is_subscribed'] = is_subscribed
        session['subscription_pending'] = subscription_pending
        return jsonify({'is_subscribed': is_subscribed, 'subscription_pending': subscription_pending})
    except Exception:
        return jsonify({'error': 'Unable to determine status'}), 500


# Protected video endpoint: checks subscription before serving files from static/videos
@app.route('/protected_video/<path:filename>')
@login_required
def protected_video(filename):
    # only serve files under the videos/ folder
    if not filename.startswith('videos/'):
        return abort(404)

    file_path = os.path.join(app.root_path, 'static', filename)
    if not os.path.isfile(file_path):
        return abort(404)

    try:
        conn = sqlite3.connect('babycare.db')
        c = conn.cursor()
        c.execute("SELECT is_subscribed FROM users WHERE email = ?", (session['user_id'],))
        row = c.fetchone()
        conn.close()
        if not row or int(row[0]) != 1:
            flash('You must be subscribed to access this content.', 'warning')
            return redirect(url_for('subscribe'))
    except Exception:
        return abort(500)

    directory = os.path.join(app.root_path, 'static')
    return send_from_directory(directory, filename)


# Subscribe page (simulated)
@app.route('/subscribe', methods=['GET', 'POST'])
@login_required
def subscribe():
    # Show UPI QR / instructions. When user POSTs, mark subscription as pending for admin approval.
    if request.method == 'POST':
        # Ensure user is logged in (login_required decorator handles this)
        try:
            conn = sqlite3.connect('babycare.db')
            c = conn.cursor()
            # Mark subscription request as pending; admin will approve manually
            c.execute("UPDATE users SET subscription_pending = 1 WHERE email = ?", (session['user_id'],))
            conn.commit()
            conn.close()
            session['subscription_pending'] = 1
        except Exception:
            pass
        # Send admin notification (best-effort)
        try:
            subject = f"Subscription request: {session.get('user_id')}"
            # Send admin to the comprehensive admin panel
            body = f"User {session.get('user_id')} has requested subscription access. Please verify payment and approve in the admin panel: {request.url_root}admin/manage_subscriptions"
            send_admin_notification(subject, body)
        except Exception:
            pass

        return redirect(url_for('user_dashboard'))

    # GET: render subscribe instructions and QR
    return render_template('subscribe.html', price=99)

# Admin Dashboard - View all users
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    
    # Get all users
    c.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = c.fetchall()
    
    # Get stats
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM contacts")
    total_contacts = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM products")
    total_products = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM cart")
    total_orders = c.fetchone()[0]
    
    # Fetch recent contact messages (last 5)
    c.execute("SELECT name, email, message, date FROM contacts ORDER BY date DESC LIMIT 5")
    recent_contacts = c.fetchall()

    conn.close()
    
    users_list = []
    pending_count = 0
    subscribed_count = 0
    for user in users:
        is_sub = 0
        sub_pending = 0
        # users table may have these columns added via migration
        try:
            # columns: id, email, password, parent_name, baby_name, baby_dob, baby_age, phone, address, created_at, language?, is_admin?, is_subscribed?, subscription_pending?
            # Safely extract by position if present
            # try to read by name where possible - fall back to positions
            is_sub = int(user[10]) if len(user) > 10 and user[10] is not None else 0
        except Exception:
            is_sub = 0
        try:
            sub_pending = int(user[11]) if len(user) > 11 and user[11] is not None else 0
        except Exception:
            sub_pending = 0

        if is_sub:
            subscribed_count += 1
        if sub_pending:
            pending_count += 1

        users_list.append({
            'id': user[0],
            'email': user[1],
            'parent_name': user[3],
            'baby_name': user[4],
            'baby_dob': user[5],
            'baby_age': user[6],
            'phone': user[7],
            'address': user[8],
            'created_at': user[9],
            'is_subscribed': is_sub,
            'subscription_pending': sub_pending
        })
    
    stats = {
        'total_users': total_users,
        'total_contacts': total_contacts,
        'total_products': total_products,
        'total_orders': total_orders
    }
    
    # add counts to stats for convenience
    stats['pending_requests'] = pending_count
    stats['subscribed_users'] = subscribed_count

    return render_template('admin_dashboard.html', users=users_list, stats=stats, recent_contacts=recent_contacts)


# Admin - Manage users page
@app.route('/admin/users')
@admin_required
def admin_manage_users():
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    c.execute("SELECT id, email, parent_name, baby_name, baby_dob, baby_age, phone, address, created_at, is_admin FROM users ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()

    users = []
    for r in rows:
        users.append({
            'id': r[0],
            'email': r[1],
            'parent_name': r[2],
            'baby_name': r[3],
            'baby_dob': r[4],
            'baby_age': r[5],
            'phone': r[6],
            'address': r[7],
            'created_at': r[8],
            'is_admin': int(r[9]) if r[9] is not None else 0
        })

    return render_template('admin_manage_users.html', users=users)


# Promote user to admin
@app.route('/admin/promote/<int:user_id>', methods=['POST'])
@admin_required
def admin_promote_user(user_id):
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    c.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_manage_users'))


# Demote user from admin
@app.route('/admin/demote/<int:user_id>', methods=['POST'])
@admin_required
def admin_demote_user(user_id):
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    c.execute("UPDATE users SET is_admin = 0 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_manage_users'))


# --- Subscription requests management for admin ---
@app.route('/admin/subscriptions')
@admin_required
def admin_subscriptions():
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    # Fetch users who have a pending subscription request
    try:
        c.execute("SELECT id, email, parent_name, created_at FROM users WHERE subscription_pending = 1")
        requests = c.fetchall()
    except Exception:
        requests = []
    conn.close()
    return render_template('admin_subscriptions.html', requests=requests)


@app.route('/admin/approve_subscription/<int:user_id>', methods=['POST'])
@admin_required
def admin_approve_subscription(user_id):
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    # Get current state for logging
    try:
        c.execute("SELECT email, is_subscribed, subscription_pending FROM users WHERE id = ?", (user_id,))
        row = c.fetchone()
        user_email = row[0] if row else str(user_id)
        prev_is_sub = int(row[1]) if row and row[1] is not None else 0
        prev_pending = int(row[2]) if row and row[2] is not None else 0
    except Exception:
        user_email = str(user_id)
        prev_is_sub = 0
        prev_pending = 0

    # Approve: set is_subscribed=1 and clear pending flag
    try:
        new_is_sub = 1
        new_pending = 0
        c.execute("UPDATE users SET is_subscribed = ?, subscription_pending = ? WHERE id = ?", (new_is_sub, new_pending, user_id))
        conn.commit()
        flash(f"Approved subscription for {user_email}", 'success')
        try:
            log_admin_action('approve', user_id, user_email, prev_is_sub, prev_pending, new_is_sub, new_pending)
        except Exception:
            pass
    except Exception:
        flash(f"Failed to approve subscription for {user_email}", 'danger')
    finally:
        conn.close()

    # Redirect back to referring page if possible, else to manage_subscriptions
    ref = request.referrer
    return redirect(ref or url_for('admin_manage_subscriptions'))


@app.route('/admin/reject_subscription/<int:user_id>', methods=['POST'])
@admin_required
def admin_reject_subscription(user_id):
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    try:
        c.execute("SELECT email, is_subscribed, subscription_pending FROM users WHERE id = ?", (user_id,))
        row = c.fetchone()
        user_email = row[0] if row else str(user_id)
        prev_is_sub = int(row[1]) if row and row[1] is not None else 0
        prev_pending = int(row[2]) if row and row[2] is not None else 0
    except Exception:
        user_email = str(user_id)
        prev_is_sub = 0
        prev_pending = 0

    try:
        new_is_sub = 0
        new_pending = 0
        c.execute("UPDATE users SET subscription_pending = ?, is_subscribed = ? WHERE id = ?", (new_pending, new_is_sub, user_id))
        conn.commit()
        flash(f"Rejected subscription request for {user_email}", 'warning')
        try:
            log_admin_action('reject', user_id, user_email, prev_is_sub, prev_pending, new_is_sub, new_pending)
        except Exception:
            pass
    except Exception:
        flash(f"Failed to reject subscription for {user_email}", 'danger')
    finally:
        conn.close()

    ref = request.referrer
    return redirect(ref or url_for('admin_manage_subscriptions'))


# --- Comprehensive Admin Subscription Management ---
@app.route('/admin/manage_subscriptions')
@admin_required
def admin_manage_subscriptions():
    """Admin page to manage all user subscriptions: grant, revoke, approve pending requests."""
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    
    # Pending requests
    try:
        c.execute("""SELECT id, email, parent_name, baby_name, created_at 
                     FROM users WHERE subscription_pending = 1 ORDER BY created_at DESC""")
        pending_requests = []
        for row in c.fetchall():
            pending_requests.append({
                'id': row[0],
                'email': row[1],
                'parent_name': row[2],
                'baby_name': row[3],
                'created_at': row[4]
            })
    except Exception:
        pending_requests = []
    
    # Subscribed users
    try:
        c.execute("""SELECT id, email, parent_name, baby_name, created_at 
                     FROM users WHERE is_subscribed = 1 ORDER BY created_at DESC""")
        subscribed_users = []
        for row in c.fetchall():
            subscribed_users.append({
                'id': row[0],
                'email': row[1],
                'parent_name': row[2],
                'baby_name': row[3],
                'created_at': row[4]
            })
    except Exception:
        subscribed_users = []
    
    # All users with subscription status
    try:
        c.execute("""SELECT id, email, parent_name, baby_name, is_subscribed, subscription_pending 
                     FROM users ORDER BY created_at DESC""")
        all_users = []
        for row in c.fetchall():
            all_users.append({
                'id': row[0],
                'email': row[1],
                'parent_name': row[2],
                'baby_name': row[3],
                'is_subscribed': int(row[4]) if row[4] else 0,
                'subscription_pending': int(row[5]) if row[5] else 0
            })
    except Exception:
        all_users = []
    
    conn.close()
    
    pending_count = len(pending_requests)
    subscribed_count = len(subscribed_users)
    
    return render_template('admin_manage_subscriptions.html',
                          pending_requests=pending_requests,
                          subscribed_users=subscribed_users,
                          all_users=all_users,
                          pending_count=pending_count,
                          subscribed_count=subscribed_count)


@app.route('/admin/undo_last_action', methods=['POST'])
@admin_required
def admin_undo_last_action():
    last = read_last_admin_action()
    if not last:
        flash('No admin actions to undo.', 'info')
        return redirect(url_for('admin_dashboard'))

    user_id = last.get('user_id')
    prev_is_sub = int(last.get('prev_is_subscribed', 0))
    prev_pending = int(last.get('prev_subscription_pending', 0))
    try:
        conn = sqlite3.connect('babycare.db')
        c = conn.cursor()
        c.execute("UPDATE users SET is_subscribed = ?, subscription_pending = ? WHERE id = ?", (prev_is_sub, prev_pending, user_id))
        conn.commit()
        conn.close()
        flash(f"Reverted last admin action for user ID {user_id}", 'success')
        # Log the undo as an action referencing the original
        try:
            log_admin_action('undo', user_id, last.get('user_email', ''), last.get('new_is_subscribed', 0), last.get('new_subscription_pending', 0), prev_is_sub, prev_pending)
        except Exception:
            pass
    except Exception:
        flash('Failed to undo last admin action.', 'danger')

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/grant_subscription/<int:user_id>', methods=['POST'])
@admin_required
def admin_grant_subscription(user_id):
    """Grant subscription access to a user (manually by admin)."""
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    try:
        c.execute("SELECT email, is_subscribed, subscription_pending FROM users WHERE id = ?", (user_id,))
        row = c.fetchone()
        user_email = row[0] if row else str(user_id)
        prev_is_sub = int(row[1]) if row and row[1] is not None else 0
        prev_pending = int(row[2]) if row and row[2] is not None else 0
    except Exception:
        user_email = str(user_id)
        prev_is_sub = 0
        prev_pending = 0

    try:
        new_is_sub = 1
        new_pending = 0
        c.execute("UPDATE users SET is_subscribed = ?, subscription_pending = ? WHERE id = ?", (new_is_sub, new_pending, user_id))
        conn.commit()
        flash(f"Granted subscription access to {user_email}", 'success')
        try:
            log_admin_action('grant', user_id, user_email, prev_is_sub, prev_pending, new_is_sub, new_pending)
        except Exception:
            pass
    except Exception:
        flash(f"Failed to grant subscription to {user_email}", 'danger')
    finally:
        conn.close()

    return redirect(url_for('admin_manage_subscriptions'))


@app.route('/admin/revoke_subscription/<int:user_id>', methods=['POST'])
@admin_required
def admin_revoke_subscription(user_id):
    """Revoke subscription access from a user."""
    conn = sqlite3.connect('babycare.db')
    c = conn.cursor()
    try:
        c.execute("SELECT email, is_subscribed, subscription_pending FROM users WHERE id = ?", (user_id,))
        row = c.fetchone()
        user_email = row[0] if row else str(user_id)
        prev_is_sub = int(row[1]) if row and row[1] is not None else 0
        prev_pending = int(row[2]) if row and row[2] is not None else 0
    except Exception:
        user_email = str(user_id)
        prev_is_sub = 0
        prev_pending = 0

    try:
        new_is_sub = 0
        new_pending = 0
        c.execute("UPDATE users SET is_subscribed = ?, subscription_pending = ? WHERE id = ?", (new_is_sub, new_pending, user_id))
        conn.commit()
        flash(f"Revoked subscription access from {user_email}", 'warning')
        try:
            log_admin_action('revoke', user_id, user_email, prev_is_sub, prev_pending, new_is_sub, new_pending)
        except Exception:
            pass
    except Exception:
        flash(f"Failed to revoke subscription for {user_email}", 'danger')
    finally:
        conn.close()

    return redirect(url_for('admin_manage_subscriptions'))


# Admin action log viewer
@app.route('/admin/action_log')
@admin_required
def admin_action_log():
    """Display all admin actions with per-action undo buttons."""
    all_actions = read_all_admin_actions()
    # Reverse to show newest first
    all_actions.reverse()
    return render_template('admin_action_log.html', actions=all_actions, total_actions=len(all_actions))


@app.route('/admin/undo_action/<int:log_index>', methods=['POST'])
@admin_required
def admin_undo_action(log_index):
    """Undo a specific admin action by log index."""
    all_actions = read_all_admin_actions()
    if log_index < 0 or log_index >= len(all_actions):
        flash('Action not found in log.', 'danger')
        return redirect(url_for('admin_action_log'))

    target = all_actions[log_index]
    user_id = target.get('user_id')
    prev_is_sub = int(target.get('prev_is_subscribed', 0))
    prev_pending = int(target.get('prev_subscription_pending', 0))

    try:
        conn = sqlite3.connect('babycare.db')
        c = conn.cursor()
        c.execute("UPDATE users SET is_subscribed = ?, subscription_pending = ? WHERE id = ?", (prev_is_sub, prev_pending, user_id))
        conn.commit()
        conn.close()
        flash(f"Reverted action on user ID {user_id}: {target.get('action')}", 'success')
        try:
            log_admin_action('undo', user_id, target.get('user_email', ''), target.get('new_is_subscribed', 0), target.get('new_subscription_pending', 0), prev_is_sub, prev_pending)
        except Exception:
            pass
    except Exception:
        flash('Failed to undo action.', 'danger')

    return redirect(url_for('admin_action_log'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)