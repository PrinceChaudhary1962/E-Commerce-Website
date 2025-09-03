%%writefile app.py
import streamlit as st
from models import SessionLocal, User, Product, Address, Order, OrderItem
import utils
import datetime

DB = SessionLocal()

# --- Session State ---
if "user" not in st.session_state:
    st.session_state.user = None
if "cart" not in st.session_state:
    st.session_state.cart = {}

# --- Authentication ---
def login():
    st.subheader("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = DB.query(User).filter(User.email==email).first()
        if user and utils.verify_password(password, user.password_hash):
            st.session_state.user = user
            st.success(f"Logged in as {user.role}")
        else:
            st.error("Invalid credentials")

def signup():
    st.subheader("Sign Up")
    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Password", type="password", key="signup_pass")
    if st.button("Send OTP"):
        otp_data = utils.create_and_send_otp(email)
        st.session_state.otp_code = otp_data["code"]
        st.info("OTP sent to your email (check console if dev)")
    otp = st.text_input("Enter OTP", key="signup_otp")
    if st.button("Verify & Sign Up"):
        if otp == st.session_state.get("otp_code"):
            new_user = User(email=email, password_hash=utils.hash_password(password), is_verified=True)
            DB.add(new_user)
            DB.commit()
            st.success("Signup successful! Please login.")
        else:
            st.error("Invalid OTP")

# --- Admin Dashboard ---
def admin_dashboard():
    st.subheader("Admin Dashboard")
    st.write("Add Product")
    name = st.text_input("Product Name", key="prod_name")
    price = st.number_input("Price", min_value=0.0, key="prod_price")
    desc = st.text_area("Description", key="prod_desc")
    if st.button("Add Product"):
        prod = Product(name=name, price=price, description=desc)
        DB.add(prod)
        DB.commit()
        st.success("Product added")

    st.write("---")
    st.write("Delete Product")
    products = DB.query(Product).all()
    product_names = [p.name for p in products]
    del_name = st.selectbox("Select product to delete", product_names)
    if st.button("Delete Product"):
        prod = DB.query(Product).filter(Product.name==del_name).first()
        DB.delete(prod)
        DB.commit()
        st.success(f"{del_name} deleted")

# --- Customer Dashboard ---
def customer_dashboard():
    st.subheader("Products")
    products = DB.query(Product).all()
    for p in products:
        st.write(f"**{p.name}** - ₹{p.price}")
        st.write(p.description)
        if st.button(f"Add to Cart: {p.name}"):
            st.session_state.cart[p.id] = st.session_state.cart.get(p.id, 0)+1
