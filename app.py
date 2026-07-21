import sqlite3
from nicegui import ui

DB_PATH = 'items.db'

# ---------- BASE DE DONNÉES ----------
def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER,
            needed INTEGER DEFAULT 0,
            user_id INTEGER,
            FOREIGN KEY(category_id) REFERENCES categories(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # colonne user_id si manquante
    cur.execute("PRAGMA table_info(items)")
    cols = [c[1] for c in cur.fetchall()]
    if 'user_id' not in cols:
        cur.execute("ALTER TABLE items ADD COLUMN user_id INTEGER;")
        cur.execute("UPDATE items SET user_id = 1;")

    conn.commit()
    conn.close()

def get_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM users ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return rows

def add_user(name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO users(name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

def rename_user(user_id, new_name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET name = ? WHERE id = ?", (new_name, user_id))
    conn.commit()
    conn.close()

def get_categories():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM categories ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows

def add_category(name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO categories(name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

def delete_category(cat_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM items WHERE category_id = ?", (cat_id,))
    cur.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()

def add_item(name, category_id, needed, user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO items(name, category_id, needed, user_id) VALUES (?, ?, ?, ?)",
        (name, category_id, needed, user_id)
    )
    conn.commit()
    conn.close()

def get_items(user_id, only_needed=False):
    conn = get_conn()
    cur = conn.cursor()
    if only_needed:
        cur.execute("""
            SELECT items.id, items.name, categories.name, items.needed
            FROM items
            LEFT JOIN categories ON items.category_id = categories.id
            WHERE items.user_id = ? AND items.needed = 1
            ORDER BY items.id
        """, (user_id,))
    else:
        cur.execute("""
            SELECT items.id, items.name, categories.name, items.needed
            FROM items
            LEFT JOIN categories ON items.category_id = categories.id
            WHERE items.user_id = ?
            ORDER BY items.id
        """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def toggle_needed(item_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT needed FROM items WHERE id = ?", (item_id,))
    row = cur.fetchone()
    if row:
        new_val = 0 if row[0] == 1 else 1
        cur.execute("UPDATE items SET needed = ? WHERE id = ?", (new_val, item_id))
    conn.commit()
    conn.close()

def delete_item(item_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

def update_item_category(item_id, category_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE items SET category_id = ? WHERE id = ?", (category_id, item_id))
    conn.commit()
    conn.close()

# ---------- INIT DB ----------
init_db()

# ---------- ÉTAT GLOBAL ----------
current_user_id = 1
current_tab = 'items'
tri_mode_items = 'Ordre d’ajout'
tri_mode_needs = 'Ordre d’ajout'

# ---------- UI UTILISATEURS ----------
def user_panel():
    global current_user_id

    with ui.column().classes('w-full max-w-md'):
        ui.label('Utilisateur').classes('text-lg font-bold')

        users = get_users()
        if not users:
            add_user('Utilisateur 1')
            users = get_users()

        user_names = {u[1]: u[0] for u in users}
        names_list = list(user_names.keys())

        def on_user_change(e):
            global current_user_id
            current_user_id = user_names[e.value]
            ui.open('/')

        ui.select(
            names_list,
            value=names_list[0],
            label='Choisir un utilisateur',
            on_change=on_user_change
        )

        new_name_input = ui.input('Nouveau nom').classes('w-full')
        def do_rename():
            name = new_name_input.value.strip()
            if name:
                rename_user(current_user_id, name)
                ui.open('/')
        ui.button('Renommer', on_click=do_rename).classes('mt-2')

        new_user_input = ui.input('Nouvel utilisateur').classes('w-full')
        def do_add_user():
            name = new_user_input.value.strip()
            if name:
                add_user(name)
                ui.open('/')
        ui.button('Créer utilisateur', on_click=do_add_user).classes('mt-2')

# ---------- UI ONGLET BAS ----------
def bottom_nav():
    global current_tab

    with ui.row().classes('fixed bottom-0 left-0 w-full justify-around bg-black text-white py-2 border-t border-gray-700'):
        def set_tab(tab):
            global current_tab
            current_tab = tab
            ui.open('/')

        ui.button('📝 Items', on_click=lambda: set_tab('items')).props('flat color=white')
        ui.button('❤️ Besoins', on_click=lambda: set_tab('besoins')).props('flat color=white')
        ui.button('📂 Catégories', on_click=lambda: set_tab('categories')).props('flat color=white')

# ---------- UI ITEMS ----------
def change_cat(item_id, new_cat_name, cat_dict):
    if new_cat_name in cat_dict:
        update_item_category(item_id, cat_dict[new_cat_name])
        ui.open('/')

def items_tab():
    global tri_mode_items

    ui.label('Gestion de liste d’items').classes('text-xl font-bold')

    categories = get_categories()
    cat_dict = {name: cid for cid, name in categories}
    cat_names = list(cat_dict.keys()) if cat_dict else []

    with ui.card().classes('w-full max-w-md'):
        ui.label('Ajouter un item').classes('text-lg font-bold')

        item_name_input = ui.input('Nom de l’item').classes('w-full')
        item_cat_select = ui.select(cat_names, label='Catégorie').classes('w-full')
        item_needed_checkbox = ui.checkbox('J’en ai besoin')

        def add_item_action():
            name = item_name_input.value.strip()
            cat_name = item_cat_select.value
            needed = 1 if item_needed_checkbox.value else 0
            if name and cat_name:
                add_item(name, cat_dict[cat_name], needed, current_user_id)
                ui.open('/')

        ui.button('Ajouter item', on_click=add_item_action).classes('mt-2 w-full')

    ui.separator()
    ui.label('Tous les items').classes('text-lg font-bold')

    def set_tri_items(mode):
        global tri_mode_items
        tri_mode_items = mode
        ui.open('/')

    ui.select(
        ['Alphabétique', 'Ordre d’ajout', 'Catégorie', 'Besoin'],
        value=tri_mode_items,
        label='Trier les items par',
        on_change=lambda e: set_tri_items(e.value)
    ).classes('w-full max-w-md')

    all_items = get_items(current_user_id, only_needed=False)

    if tri_mode_items == 'Alphabétique':
        all_items = sorted(all_items, key=lambda x: x[1].lower())
    elif tri_mode_items == 'Catégorie':
        all_items = sorted(all_items, key=lambda x: (x[2] or '').lower())
    elif tri_mode_items == 'Besoin':
        all_items = sorted(all_items, key=lambda x: x[3], reverse=True)

    for iid, name, cat, needed in all_items:
        with ui.row().classes('items-center w-full max-w-md justify-between bg-[#1e1e1e] rounded-lg px-3 py-2 mt-2'):
            ui.label(name).classes('text-base font-bold')

            def toggle(item_id=iid):
                toggle_needed(item_id)
                ui.open('/')

            ui.button('✔️' if needed else '❌', on_click=toggle).props('flat color=white')

            cat_select = ui.select(
                cat_names,
                value=cat or (cat_names[0] if cat_names else None),
                on_change=lambda e, item_id=iid: change_cat(item_id, e.value, cat_dict)
            ).classes('w-32')

            def delete(item_id=iid):
                delete_item(item_id)
                ui.open('/')

            ui.button('🗑️', on_click=delete).props('flat color=red')

# ---------- UI CATEGORIES ----------
def delete_cat_action(cat_id):
    delete_category(cat_id)
    ui.open('/')

def categories_tab():
    ui.label('Gestion des catégories').classes('text-xl font-bold')

    new_cat_input = ui.input('Nouvelle catégorie').classes('w-full max-w-md')

    def add_cat_action():
        name = new_cat_input.value.strip()
        if name:
            add_category(name)
            ui.open('/')

    ui.button('Ajouter', on_click=add_cat_action).classes('mt-2 w-full max-w-md')

    ui.separator()
    ui.label('Catégories existantes').classes('text-lg font-bold')

    categories = get_categories()
    for cid, name in categories:
        with ui.row().classes('items-center w-full max-w-md justify-between mt-1'):
            ui.label(name)
            ui.button('🗑️', on_click=lambda cat_id=cid: delete_cat_action(cat_id)).props('flat color=red')

# ---------- UI BESOINS ----------
def besoins_tab():
    global tri_mode_needs

    ui.label('Besoins par catégorie').classes('text-xl font-bold')

    def set_tri_needs(mode):
        global tri_mode_needs
        tri_mode_needs = mode
        ui.open('/')

    ui.select(
        ['Alphabétique', 'Ordre d’ajout'],
        value=tri_mode_needs,
        label='Mode de tri',
        on_change=lambda e: set_tri_needs(e.value)
    ).classes('w-full max-w-md')

    needed_items = get_items(current_user_id, only_needed=True)

    grouped = {}
    for iid, name, cat, needed in needed_items:
        grouped.setdefault(cat or 'Sans catégorie', []).append((iid, name))

    if not grouped:
        ui.label("Aucun item marqué comme 'Besoin'.").classes('mt-2')
    else:
        for cat, items in grouped.items():
            ui.label(f'📂 {cat}').classes('text-lg font-bold mt-3')

            if tri_mode_needs == 'Alphabétique':
                items = sorted(items, key=lambda x: x[1])

            for iid, name in items:
                with ui.row().classes('items-center w-full max-w-md justify-start gap-3 mt-1'):
                    def toggle_need(item_id=iid):
                        toggle_needed(item_id)
                        ui.open('/')

                    ui.button('❌', on_click=toggle_need).props('flat color=red')
                    ui.label(name).classes('text-base font-bold')

# ---------- PAGE PRINCIPALE ----------
@ui.page('/')
def main_page():
    with ui.row().classes('w-full justify-center mt-2'):
        user_panel()
    ui.separator()
    if current_tab == 'items':
        items_tab()
    elif current_tab == 'besoins':
        besoins_tab()
    elif current_tab == 'categories':
        categories_tab()
    bottom_nav()

# ---------- LANCEMENT ----------
ui.run(title='Liste d’achats', reload=False)
