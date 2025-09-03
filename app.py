import streamlit as st
from models import SessionLocal, Product

# DB session
db = SessionLocal()

# App UI
st.title("🛒 Mini E-Commerce Store")

# Navigation
page = st.sidebar.radio("Go to", ["Home", "Add Product", "Cart"])

# Home - Product Listing
if page == "Home":
    st.header("Available Products")
    products = db.query(Product).all()
    for p in products:
        st.subheader(f"{p.name} - ${p.price}")
        st.write(p.description)
        if st.button(f"Add {p.name} to Cart"):
            if "cart" not in st.session_state:
                st.session_state.cart = []
            st.session_state.cart.append(p)

# Add Product
elif page == "Add Product":
    st.header("Add a New Product")
    name = st.text_input("Name")
    price = st.number_input("Price", min_value=1.0)
    desc = st.text_area("Description")
    if st.button("Add"):
        new_product = Product(name=name, price=price, description=desc)
        db.add(new_product)
        db.commit()
        st.success("Product added!")

# Cart
elif page == "Cart":
    st.header("Your Cart")
    cart = st.session_state.get("cart", [])
    total = sum([item.price for item in cart])
    for item in cart:
        st.write(f"{item.name} - ${item.price}")
    st.subheader(f"Total: ${total}")
    if st.button("Checkout"):
        st.success("✅ Checkout complete (demo only)")
