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

# Seed admin account
if not DB.query(User).filter(User.email=="vivv.plays@egmail.com").first():
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
            st.stop()  # refresh UI safely
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
                # reset session state for signup
                st.session_state["signup_email"] = ""
                st.session_state["signup_pass"] = ""
                st.session_state["signup_otp"] = ""
                st.session_state["otp_code"] = None
                st.stop()
        else:
            st.error("Invalid OTP")

# -----------------------
# Admin Dashboard
# -----------------------
def admin_dashboard():
    st.subheader("Admin Dashboard")

    st.write("### Add Products in Bulk")
    num_products = st.number_input("How many products to add?", min_value=1, max_value=10, step=1, key="num_products")
    
    with st.form("add_products_form"):
        product_entries = []
        for i in range(num_products):
            st.write(f"**Product {i+1}**")
            name = st.text_input(f"Name {i+1}", key=f"name_{i}")
            price = st.number_input(f"Price {i+1}", min_value=0.0, step=1.0, key=f"price_{i}")
            desc = st.text_area(f"Description {i+1}", key=f"desc_{i}")
            img_file = st.file_uploader(f"Image {i+1} (optional)", type=["png","jpg","jpeg"], key=f"img_{i}")
            product_entries.append({
                "name": name,
                "price": price,
                "desc": desc,
                "img": img_file
            })
        submitted = st.form_submit_button("Add Products")
        if submitted:
            for prod in product_entries:
                if prod["name"].strip() == "":
                    continue
                if DB.query(Product).filter(Product.name==prod["name"]).first():
                    st.warning(f"Product '{prod['name']}' already exists. Skipped.")
                    continue
                new_prod = Product(
                    name=prod["name"],
                    price=prod["price"],
                    description=prod["desc"]
                )
                DB.add(new_prod)
            DB.commit()
            st.success("Products added successfully!")

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

    with st.form("add_to_cart_form"):
        qty_dict = {}
        for p in products:
            st.write(f"**{p.name}** - ₹{p.price}")
            st.write(p.description)
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
        st.stop()  # clean rerun
else:
    tab = st.radio("Choose", ["Login", "Sign Up"])
    if tab=="Login":
        login()
    else:
        signup()
