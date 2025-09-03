import streamlit as st
from sqlalchemy.orm import sessionmaker
from models import Base, engine, User, Product
import utils
import os

# -----------------------
# Initialize DB
# -----------------------
Base.metadata.create_all(engine)
DB = sessionmaker(bind=engine)()

# -----------------------
# Seed Admin
# -----------------------
ADMIN_EMAIL = "vivv.plays@gmail.com"
if not DB.query(User).filter(User.email==ADMIN_EMAIL).first():
    admin = User(
        email=ADMIN_EMAIL,
        password_hash=utils.hash_password("adminpass"),
        role="admin",
        is_verified=True
    )
    DB.add(admin)
    DB.commit()
    print(f"Admin created: {ADMIN_EMAIL} / adminpass")

# -----------------------
# Ensure image folder exists
# -----------------------
UPLOAD_FOLDER = "images"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# -----------------------
# Session defaults
# -----------------------
for key, val in {
    "user_id": None,
    "user_role": None,
    "cart": {},
    "otp_code": None,
    "signup_email": "",
    "signup_pass": "",
    "signup_otp": ""
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# -----------------------
# Authentication
# -----------------------
def login():
    st.subheader("Login")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_pass")
    if st.button("Login"):
        user = DB.query(User).filter(User.email==email).first()
        if user and utils.verify_password(password, user.password_hash):
            st.session_state["user_id"] = user.id
            st.session_state["user_role"] = user.role
            st.success(f"Logged in as {user.role}")
            st.experimental_rerun()
        else:
            st.error("Invalid credentials")

def signup():
    st.subheader("Sign Up")
    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Password", type="password", key="signup_pass")
    
    if st.button("Send OTP"):
        if DB.query(User).filter(User.email==email).first():
            st.error("Email already registered. Please login.")
        else:
            otp_code = utils.create_and_send_otp(email)
            st.session_state["otp_code"] = otp_code
            st.info(f"OTP sent to your email. (Dev: {otp_code})")  # dev/testing

    otp = st.text_input("Enter OTP", key="signup_otp")
    if st.button("Verify & Sign Up"):
        if otp == st.session_state.get("otp_code"):
            if DB.query(User).filter(User.email==email).first():
                st.error("Email already registered. Please login.")
            else:
                new_user = User(
                    email=email,
                    password_hash=utils.hash_password(password),
                    is_verified=True
                )
                DB.add(new_user)
                DB.commit()
                st.success("Signup successful! Please login.")
                st.session_state.update({
                    "signup_email": "",
                    "signup_pass": "",
                    "signup_otp": "",
                    "otp_code": None
                })
                st.experimental_rerun()
        else:
            st.error("Invalid OTP")

# -----------------------
# Admin Dashboard
# -----------------------
def admin_dashboard():
    st.subheader("Admin Dashboard")
    st.write("### Add Products")

    with st.form("add_products_form"):
        name = st.text_input("Product Name")
        price = st.number_input("Price", min_value=0.0, step=1.0)
        desc = st.text_area("Description")
        img_file = st.file_uploader("Image (optional)", type=["png","jpg","jpeg"])
        submitted = st.form_submit_button("Add Product")
        if submitted:
            if DB.query(Product).filter(Product.name==name).first():
                st.warning("Product already exists. Skipped.")
            else:
                image_path = None
                if img_file:
                    image_path = os.path.join(UPLOAD_FOLDER, img_file.name)
                    with open(image_path, "wb") as f:
                        f.write(img_file.getbuffer())
                new_prod = Product(
                    name=name,
                    price=price,
                    description=desc,
                    image_path=image_path
                )
                DB.add(new_prod)
                DB.commit()
                st.success(f"Product '{name}' added!")

    st.write("---")
    st.write("### Delete Product")
    products = DB.query(Product).all()
    product_names = [p.name for p in products]
    if product_names:
        del_name = st.selectbox("Select product to delete", product_names)
        if st.button("Delete Product"):
            prod = DB.query(Product).filter(Product.name==del_name).first()
            DB.delete(prod)
            DB.commit()
            st.success(f"{del_name} deleted")
    else:
        st.info("No products to delete")

# -----------------------
# Customer Dashboard
# -----------------------
def customer_dashboard():
    st.subheader("Products")
    products = DB.query(Product).all()

    if not products:
        st.info("No products available yet.")
        return

    with st.form("add_to_cart_form"):
        qty_dict = {}
        for p in products:
            st.write(f"**{p.name}** - ₹{p.price}")
            st.write(p.description)
            if getattr(p, "image_path", None) and os.path.exists(p.image_path):
                st.image(p.image_path, width=200)
            qty_dict[p.id] = st.number_input(f"Qty for {p.name}", min_value=0, step=1, key=f"qty_{p.id}")
        submitted = st.form_submit_button("Add Selected Products to Cart")
        if submitted:
            for pid, qty in qty_dict.items():
                if qty > 0:
                    st.session_state["cart"][pid] = st.session_state["cart"].get(pid, 0) + qty
            st.success("Products added to cart!")

    st.write("---")
    st.subheader("Cart")
    if st.session_state["cart"]:
        total = 0
        for pid, qty in st.session_state["cart"].items():
            prod = DB.query(Product).filter(Product.id==pid).first()
            st.write(f"{prod.name} x {qty} = ₹{prod.price*qty}")
            total += prod.price*qty
        st.write(f"**Total: ₹{total}**")
    else:
        st.info("Cart is empty")

# -----------------------
# Main App
# -----------------------
st.title("Mini E-commerce App")

current_user = None
if st.session_state["user_id"]:
    current_user = DB.query(User).filter(User.id==st.session_state["user_id"]).first()

if current_user:
    if st.session_state["user_role"] == "admin":
        admin_dashboard()
    else:
        customer_dashboard()

    if st.button("Logout"):
        st.session_state["user_id"] = None
        st.session_state["user_role"] = None
        st.session_state["cart"] = {}
        st.experimental_rerun()
else:
    tab = st.radio("Choose", ["Login", "Sign Up"])
    if tab=="Login":
        login()
    else:
        signup()
