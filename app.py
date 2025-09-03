import streamlit as st
from sqlalchemy.orm import sessionmaker
from models import Base, engine, User, Product, Address, Order, OrderItem
import utils
import datetime

# -----------------------
# Initialize DB and seed admin
# -----------------------
Base.metadata.create_all(engine)
DB = sessionmaker(bind=engine)()

# Seed admin
if not DB.query(User).filter(User.email=="admin@example.com").first():
    admin = User(
        email="admin@example.com",
        password_hash=utils.hash_password("adminpass"),
        role="admin",
        is_verified=True
    )
    DB.add(admin)
    DB.commit()
    print("Admin created: admin@example.com / adminpass")

# -----------------------
# Session state defaults
# -----------------------
defaults = {
    "user": None,
    "cart": {},
    "otp_code": None,
    "signup_email": "",
    "signup_pass": "",
    "signup_otp": ""
}
for key, val in defaults.items():
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
            st.session_state["user"] = user
            st.success(f"Logged in as {user.role}")
            st.experimental_rerun()  # <-- triggers dashboard reload
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
            st.info(f"OTP sent to your email. (Dev: {otp_code})")  # for dev/testing

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
                # clear session state keys
                st.session_state["signup_email"] = ""
                st.session_state["signup_pass"] = ""
                st.session_state["signup_otp"] = ""
                st.session_state["otp_code"] = None
                st.experimental_rerun()  # <-- reload to login screen
        else:
            st.error("Invalid OTP")

# -----------------------
# Admin Dashboard
# -----------------------
def admin_dashboard():
    st.subheader("Admin Dashboard")

    st.write("Add Product")
    name = st.text_input("Product Name", key="prod_name")
    price = st.number_input("Price", min_value=0.0, key="prod_price")
    desc = st.text_area("Description", key="prod_desc")
    if st.button("Add Product"):
        if DB.query(Product).filter(Product.name==name).first():
            st.error("Product with this name already exists.")
        else:
            prod = Product(name=name, price=price, description=desc)
            DB.add(prod)
            DB.commit()
            st.success("Product added")

    st.write("---")
    st.write("Delete Product")
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
    for p in products:
        st.write(f"**{p.name}** - ₹{p.price}")
        st.write(p.description)
        if st.button(f"Add to Cart: {p.name}"):
            st.session_state["cart"][p.id] = st.session_state["cart"].get(p.id, 0)+1

    st.write("---")
    st.subheader("Cart")
    if st.session_state["cart"]:
        total = 0
        for pid, qty in st.session_state["cart"].items():
            prod = DB.query(Product).filter(Product.id==pid).first()
            st.write(f"{prod.name} x {qty} = ₹{prod.price*qty}")
            total += prod.price*qty
        st.write(f"**Total: ₹{total}**")

        st.write("---")
        st.subheader("Checkout / Payment")
        vpa = st.text_input("Enter UPI VPA (e.g., example@upi)")
        name = st.text_input("Name on UPI")
        if st.button("Generate UPI QR"):
            buf = utils.generate_upi_qr(vpa, name, total)
            st.image(buf)
    else:
        st.info("Cart is empty")

# -----------------------
# Main App
# -----------------------
st.title("Mini E-commerce App")

if st.session_state["user"]:
    if st.session_state["user"].role == "admin":
        admin_dashboard()
    else:
        customer_dashboard()
    if st.button("Logout"):
        st.session_state["user"] = None
        st.session_state["cart"] = {}
        st.experimental_rerun()  # <-- reload login/signup
else:
    tab = st.radio("Choose", ["Login", "Sign Up"])
    if tab=="Login":
        login()
    else:
        signup()
