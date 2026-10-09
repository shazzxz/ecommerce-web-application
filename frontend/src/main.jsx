import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const request = async (path, options = {}, token = "") => {
  const headers = { ...(options.body ? { "Content-Type": "application/json" } : {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(path, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Request failed.");
  return data;
};
const money = value => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(Number(value || 0));
const sampleShipping = { name: "", email: "", phone: "", address: "" };

function App() {
  const [products, setProducts] = useState([]);
  const [token, setToken] = useState(() => localStorage.getItem("shoplite_token") || "");
  const [user, setUser] = useState(null);
  const [authMode, setAuthMode] = useState("login");
  const [authForm, setAuthForm] = useState({ name: "", email: "", password: "" });
  const [authOpen, setAuthOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All");
  const [cart, setCart] = useState([]);
  const [cartOpen, setCartOpen] = useState(false);
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [shipping, setShipping] = useState(sampleShipping);
  const [orders, setOrders] = useState([]);
  const [adminProducts, setAdminProducts] = useState([]);
  const [adminOrders, setAdminOrders] = useState([]);
  const [productForm, setProductForm] = useState({ name: "", description: "", category: "General", price: "", stock: "", image_url: "" });
  const [adminOpen, setAdminOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const loadProducts = async () => {
    try {
      const params = new URLSearchParams();
      if (search.trim()) params.set("search", search.trim());
      if (category !== "All") params.set("category", category);
      const data = await request(`/api/products?${params}`);
      setProducts(data.products || []);
    } catch (error) { setMessage(error.message); }
  };
  const loadOrders = async authToken => {
    try { const data = await request("/api/orders", {}, authToken); setOrders(data.orders || []); }
    catch (error) { setMessage(error.message); }
  };
  const loadAdmin = async authToken => {
    try {
      const [p, o] = await Promise.all([request("/api/admin/products", {}, authToken), request("/api/admin/orders", {}, authToken)]);
      setAdminProducts(p.products || []); setAdminOrders(o.orders || []);
    } catch (error) { setMessage(error.message); }
  };

  useEffect(() => { loadProducts(); }, [search, category]);
  useEffect(() => {
    if (!token) return;
    request("/api/auth/me", {}, token).then(data => {
      setUser(data.user);
      setShipping(s => ({ ...s, name: data.user.name, email: data.user.email }));
      loadOrders(token);
      if (data.user.role === "admin") loadAdmin(token);
    }).catch(() => logout());
  }, [token]);

  const logout = () => {
    localStorage.removeItem("shoplite_token");
    setToken(""); setUser(null); setOrders([]); setAdminProducts([]); setAdminOrders([]);
    setMessage("You have been logged out.");
  };
  const cartTotal = useMemo(() => cart.reduce((sum, item) => sum + item.price * item.quantity, 0), [cart]);
  const cartCount = cart.reduce((sum, item) => sum + item.quantity, 0);
  const categories = ["All", ...new Set(products.map(product => product.category))];

  const authenticate = async event => {
    event.preventDefault(); setMessage("");
    try {
      const endpoint = authMode === "register" ? "/api/auth/register" : "/api/auth/login";
      const data = await request(endpoint, { method: "POST", body: JSON.stringify(authForm) });
      localStorage.setItem("shoplite_token", data.token);
      setToken(data.token); setUser(data.user); setAuthOpen(false);
      setShipping(s => ({ ...s, name: data.user.name, email: data.user.email }));
      setAuthForm({ name: "", email: "", password: "" });
      if (data.user.role === "admin") loadAdmin(data.token);
      else loadOrders(data.token);
      setMessage("Welcome to ShopLite.");
    } catch (error) { setMessage(error.message); }
  };
  const addToCart = product => {
    if (product.stock < 1) return setMessage("This item is out of stock.");
    setCart(items => {
      const existing = items.find(item => item.id === product.id);
      if (existing) return items.map(item => item.id === product.id ? { ...item, quantity: Math.min(item.quantity + 1, product.stock) } : item);
      return [...items, { ...product, quantity: 1 }];
    });
    setMessage(`${product.name} added to cart.`);
  };
  const setQuantity = (id, quantity) => setCart(items => items.map(item => item.id === id ? { ...item, quantity: Math.max(1, Math.min(item.stock, Number(quantity) || 1)) } : item));
  const removeItem = id => setCart(items => items.filter(item => item.id !== id));

  const checkout = async event => {
    event.preventDefault();
    if (!token || !user) { setCheckoutOpen(false); setAuthMode("login"); setAuthOpen(true); return setMessage("Log in before placing an order."); }
    setBusy(true);
    try {
      const data = await request("/api/orders", {
        method: "POST",
        body: JSON.stringify({ shipping, items: cart.map(item => ({ product_id: item.id, quantity: item.quantity })) })
      }, token);
      setCart([]); setCheckoutOpen(false); setCartOpen(false);
      setMessage(`Order #${data.order.id} placed successfully.`);
      await loadOrders(token); await loadProducts();
      if (user.role === "admin") await loadAdmin(token);
    } catch (error) { setMessage(error.message); }
    finally { setBusy(false); }
  };
  const createProduct = async event => {
    event.preventDefault();
    try {
      await request("/api/admin/products", { method: "POST", body: JSON.stringify({ ...productForm, price: Number(productForm.price), stock: Number(productForm.stock) }) }, token);
      setProductForm({ name: "", description: "", category: "General", price: "", stock: "", image_url: "" });
      await loadAdmin(token); await loadProducts(); setMessage("Product saved.");
    } catch (error) { setMessage(error.message); }
  };
  const updateProduct = async (product, key, value) => {
    try {
      await request(`/api/admin/products/${product.id}`, { method: "PATCH", body: JSON.stringify({ [key]: ["price", "stock"].includes(key) ? Number(value) : value }) }, token);
      await loadAdmin(token); await loadProducts();
    } catch (error) { setMessage(error.message); }
  };
  const deleteProduct = async product => {
    if (!confirm(`Delete ${product.name}?`)) return;
    try { await request(`/api/admin/products/${product.id}`, { method: "DELETE" }, token); await loadAdmin(token); await loadProducts(); }
    catch (error) { setMessage(error.message); }
  };
  const changeOrderStatus = async (order, status) => {
    try { await request(`/api/admin/orders/${order.id}`, { method: "PATCH", body: JSON.stringify({ status }) }, token); await loadAdmin(token); setMessage(`Order #${order.id} updated.`); }
    catch (error) { setMessage(error.message); }
  };

  return <div className="app">
    <header className="header">
      <a className="brand" href="#"><span className="brand-mark">S</span><span>shop<span>lite</span><small>GOOD FINDS, EVERY DAY</small></span></a>
      <label className="search"><span>⌕</span><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search products, brands and more" /></label>
      <div className="header-actions">
        {user ? <button className="text-btn" onClick={() => { setAuthOpen(false); user.role === "admin" ? (loadAdmin(token), setAdminOpen(true)) : (loadOrders(token), setAdminOpen(false)); }}>{user.role === "admin" ? "Admin" : "My orders"}</button> : <button className="text-btn" onClick={() => { setAuthMode("login"); setAuthOpen(v => !v); }}>{authOpen ? "Close" : "Sign in"}</button>}
        {user && <button className="text-btn" onClick={logout}>Log out</button>}
        <button className="cart-btn" onClick={() => setCartOpen(true)}>Bag <b>{cartCount}</b></button>
      </div>
    </header>

    <section className="hero">
      <div className="hero-copy"><p className="kicker">THE EVERYDAY EDIT · 2026</p><h1>Good things.<br/><i>Better finds.</i></h1><p>Thoughtfully picked essentials for the way you live, work and move.</p><a href="#catalog" className="shop-link">Explore the collection <span>↘</span></a></div>
      <div className="hero-image"><div className="hero-stamp">LESS BUT<br/>BETTER.</div><img src="https://images.unsplash.com/photo-1490312278390-ab64016e0aa9?auto=format&fit=crop&w=1400&q=85" alt="Minimal lifestyle goods"/></div>
      <div className="hero-index">01 / EVERYDAY OBJECTS</div>
    </section>

    {message && <button className="notice" onClick={() => setMessage("")}>{message}<span>×</span></button>}
    {authOpen && <section className="auth-panel"><div><p className="kicker">YOUR SHOPLITE ACCOUNT</p><h2>{authMode === "login" ? "Welcome back." : "Make it yours."}</h2><p>Sign in to follow your orders and check out faster.</p></div><form onSubmit={authenticate}>{authMode === "register" && <input required placeholder="Full name" value={authForm.name} onChange={e => setAuthForm({ ...authForm, name: e.target.value })}/>}<input required type="email" placeholder="Email address" value={authForm.email} onChange={e => setAuthForm({ ...authForm, email: e.target.value })}/><input required minLength="8" type="password" placeholder="Password (8+ characters)" value={authForm.password} onChange={e => setAuthForm({ ...authForm, password: e.target.value })}/><button className="dark-btn">{authMode === "login" ? "Sign in" : "Create account"}</button><button type="button" className="text-btn" onClick={() => setAuthMode(authMode === "login" ? "register" : "login")}>{authMode === "login" ? "New here? Create an account" : "Already a member? Sign in"}</button></form></section>}

    <main id="catalog" className="catalog">
      <div className="section-head"><div><p className="kicker">CURATED FOR YOU</p><h2>The good shelf<span>®</span></h2></div><span>{products.length} pieces to explore</span></div>
      <div className="categories">{categories.map(item => <button key={item} className={category === item ? "selected" : ""} onClick={() => setCategory(item)}>{item}</button>)}</div>
      <div className="product-grid">{products.map((product, i) => <article className="product" key={product.id}><div className="product-image"><img src={product.image_url || "https://images.unsplash.com/photo-1490312278390-ab64016e0aa9?auto=format&fit=crop&w=900&q=80"} alt={product.name}/><span className="product-number">{String(i + 1).padStart(2, "0")}</span><button className="add-btn" disabled={product.stock < 1} onClick={() => addToCart(product)}>{product.stock < 1 ? "Sold out" : "Add to bag + "}</button></div><div className="product-info"><div><span>{product.category}</span><h3>{product.name}</h3><p>{product.description}</p></div><strong>{money(product.price)}</strong></div><div className="stock">{product.stock ? `${product.stock} in stock` : "Currently unavailable"}</div></article>)}</div>
      {!products.length && <p className="empty">No products match that search. Try another term.</p>}
    </main>

    {user && <section className="orders-section"><div className="section-head"><div><p className="kicker">{user.role === "admin" ? "BACK OFFICE" : "YOUR ACCOUNT"}</p><h2>{user.role === "admin" && adminOpen ? "Orders & products" : "Your orders"}<span>®</span></h2></div><span>Signed in as {user.name}</span></div>
      {user.role === "admin" && adminOpen ? <div className="admin-layout">
        <form className="admin-form" onSubmit={createProduct}><h3>Add a product</h3><input required placeholder="Product name" value={productForm.name} onChange={e => setProductForm({ ...productForm, name: e.target.value })}/><textarea placeholder="Description" value={productForm.description} onChange={e => setProductForm({ ...productForm, description: e.target.value })}/><input placeholder="Category" value={productForm.category} onChange={e => setProductForm({ ...productForm, category: e.target.value })}/><div className="two-fields"><input required type="number" min="0" step="0.01" placeholder="Price" value={productForm.price} onChange={e => setProductForm({ ...productForm, price: e.target.value })}/><input required type="number" min="0" step="1" placeholder="Stock" value={productForm.stock} onChange={e => setProductForm({ ...productForm, stock: e.target.value })}/></div><input placeholder="Image URL (optional)" value={productForm.image_url} onChange={e => setProductForm({ ...productForm, image_url: e.target.value })}/><button className="dark-btn">Add product</button></form>
        <div className="admin-list"><h3>Inventory</h3>{adminProducts.map(p => <div className="admin-row" key={p.id}><span>{p.name}<small>{money(p.price)} · stock {p.stock}</small></span><button onClick={() => { const name = prompt("Product name", p.name); if (name === null) return; const price = prompt("Price", String(p.price)); if (price === null) return; const category = prompt("Category", p.category); if (category === null) return; const description = prompt("Description", p.description); if (description === null) return; const stock = prompt("Stock quantity", String(p.stock)); if (stock === null) return; const image_url = prompt("Image URL", p.image_url); if (image_url === null) return; request(`/api/admin/products/${p.id}`, { method: "PATCH", body: JSON.stringify({ name, price: Number(price), category, description, stock: Number(stock), image_url }) }, token).then(async () => { await loadAdmin(token); await loadProducts(); setMessage("Product updated."); }).catch(error => setMessage(error.message)); }}>Edit</button><button onClick={() => deleteProduct(p)}>Delete</button></div>)}<h3>Orders</h3>{adminOrders.map(order => <div className="admin-row" key={order.id}><span>#{order.id} · {order.customer_name}<small>{money(order.total)} · {order.items.map(i => `${i.product_name} ×${i.quantity}`).join(", ")}</small></span><select value={order.status} onChange={e => changeOrderStatus(order, e.target.value)}>{["pending","processing","shipped","completed","cancelled"].map(status => <option key={status}>{status}</option>)}</select></div>)}</div>
      </div> : <div className="customer-orders">{orders.length ? orders.map(order => <article className="order-card" key={order.id}><div><span>ORDER #{order.id}</span><h3>{order.items.map(item => `${item.product_name} × ${item.quantity}`).join(" · ")}</h3><small>{new Date(order.created_at).toLocaleString()}</small></div><div><b>{money(order.total)}</b><span className={`order-status ${order.status}`}>{order.status}</span></div></article>) : <p className="empty">Your orders will show up here after checkout.</p>}</div>}
    </section>}

    <footer><div className="brand"><span className="brand-mark">S</span><span>shop<span>lite</span><small>GOOD FINDS, EVERY DAY</small></span></div><p>Everyday goods, thoughtfully picked.</p><span>© 2026 ShopLite</span></footer>

    {cartOpen && <div className="overlay" onMouseDown={e => e.target === e.currentTarget && setCartOpen(false)}><aside className="drawer"><div className="drawer-head"><div><p className="kicker">YOUR PICKS</p><h2>Your bag <span>({cartCount})</span></h2></div><button onClick={() => setCartOpen(false)}>×</button></div>{cart.length ? <><div className="cart-list">{cart.map(item => <article className="cart-item" key={item.id}><img src={item.image_url} alt={item.name}/><div className="cart-item-info"><h3>{item.name}</h3><span>{money(item.price)}</span><div className="qty"><button onClick={() => setQuantity(item.id, item.quantity - 1)}>−</button><b>{item.quantity}</b><button onClick={() => setQuantity(item.id, item.quantity + 1)}>+</button><button className="remove" onClick={() => removeItem(item.id)}>Remove</button></div></div></article>)}</div><div className="drawer-total"><span>Subtotal</span><b>{money(cartTotal)}</b></div><p className="fine">Shipping and payment are not charged in this demo.</p><button className="dark-btn full" onClick={() => { setCartOpen(false); setCheckoutOpen(true); if (!user) { setAuthMode("login"); setAuthOpen(true); } }}>Continue to checkout</button></> : <div className="empty"><h3>Your bag is taking a breather.</h3><p>Add something you like and it will appear here.</p></div>}</aside></div>}

    {checkoutOpen && <div className="overlay" onMouseDown={e => e.target === e.currentTarget && setCheckoutOpen(false)}><form className="checkout" onSubmit={checkout}><div className="drawer-head"><div><p className="kicker">ALMOST YOURS</p><h2>Checkout</h2></div><button type="button" onClick={() => setCheckoutOpen(false)}>×</button></div>{cart.map(item => <div className="checkout-line" key={item.id}><span>{item.name} × {item.quantity}</span><b>{money(item.price * item.quantity)}</b></div>)}<div className="checkout-line total"><span>Total</span><b>{money(cartTotal)}</b></div><label>Name<input required value={shipping.name} onChange={e => setShipping({ ...shipping, name: e.target.value })}/></label><label>Email<input required type="email" value={shipping.email} onChange={e => setShipping({ ...shipping, email: e.target.value })}/></label><label>Phone<input required value={shipping.phone} onChange={e => setShipping({ ...shipping, phone: e.target.value })}/></label><label>Shipping address<textarea required rows="3" value={shipping.address} onChange={e => setShipping({ ...shipping, address: e.target.value })}/></label><p className="fine">Demo checkout places an order in the database. No payment is collected.</p><button className="dark-btn full" disabled={busy || !cart.length}>{busy ? "Placing order…" : "Place order"}</button></form></div>}
  </div>;
}

createRoot(document.getElementById("root")).render(<App />);
