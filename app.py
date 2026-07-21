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

    cur.execute("PRAGMA table_info(items)")
    cols = [c[1] for c in cur.fetchall()]
    if 'user_id' not in cols:
        cur.execute("ALTER TABLE items ADD COLUMN user_id INTEGER;")
        cur.execute("UPDATE items SET user_id = 1;")

    conn.commit()
    conn.close()

init_db()

# ---------- ÉTAT GLOBAL ----------
current_user_id = 1
current_tab = 'items'
tri_mode_items = 'Alphabétique'
tri_mode_needs = 'Alphabétique'

# Nouveaux états pour expansions
exp_user_open = False
exp_cat_open = False

# ---------- DB HELPERS ----------
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

# ---------- PANNEAU UTILISATEUR ----------
def user_panel():
    global current_user_id, exp_user_open

    with ui.expansion('Utilisateur', icon='person', value=exp_user_open).classes('bg-white text-black'):
        users = get_users()
        if not users:
            add_user('Utilisateur 1')
            users = get_users()

        user_names = {u[1]: u[0] for u in users}
        names_list = list(user_names.keys())

        def on_user_change(e):
            global current_user_id, exp_user_open
            current_user_id = user_names[e.value]
            exp_user_open = False
            ui.open('/')

        ui.select(
            names_list,
            value=names_list[0],
            label='Choisir un utilisateur',
            on_change=on_user_change
        )

        new_name_input = ui.input('Nouveau nom')
        ui.button('Renommer', on_click=lambda: (
            rename_user(current_user_id, new_name_input.value),
            globals().__setitem__('exp_user_open', False),
            ui.open('/')
        ))

        new_user_input = ui.input('Nouvel utilisateur')
        ui.button('Créer utilisateur', on_click=lambda: (
            add_user(new_user_input.value),
            globals().__setitem__('exp_user_open', False),
            ui.open('/')
        ))

# ---------- PANNEAU CATÉGORIES ----------
def categories_panel():
    global exp_cat_open

    with ui.expansion('Catégories', icon='folder', value=exp_cat_open).classes('bg-white text-black'):
        new_cat_input = ui.input('Nouvelle catégorie')
        ui.button('Ajouter', on_click=lambda: (
            add_category(new_cat_input.value),
            globals().__setitem__('exp_cat_open', False),
            ui.open('/')
        ))

        ui.separator()

        categories = get_categories()
        for cid, name in categories:
            with ui.row().classes('items-center justify-between mt-1'):
                ui.label(name)
                ui.button('🗑️', on_click=lambda cat_id=cid: (
                    delete_category(cat_id),
                    globals().__setitem__('exp_cat_open', False),
                    ui.open('/')
                )).props('flat color=red')

# ---------- PANNEAU AJOUT ITEM ----------
def add_item_panel():
    ui.label('Ajouter un item').classes('text-lg font-bold')

    categories = get_categories()
    cat_dict = {name: cid for cid, name in categories}
    cat_names = list(cat_dict.keys())

    item_name_input = ui.input('Nom de l’item')
    item_cat_select = ui.select(cat_names, label='Catégorie')
    item_needed_checkbox = ui.checkbox('J’en ai besoin')

    ui.button('Ajouter item', on_click=lambda: (
        add_item(item_name_input.value, cat_dict[item_cat_select.value], 1 if item_needed_checkbox.value else 0, current_user_id),
        ui.open('/')
    ))

# ---------- LISTE DES ITEMS ----------
def items_panel():
    global tri_mode_items

    ui.label('Tous les items').classes('text-lg font-bold')

    ui.select(
        ['Alphabétique', 'Ordre d’ajout', 'Catégorie', 'Besoin'],
        value=tri_mode_items,
        label='Trier par',
        on_change=lambda e: (
            globals().__setitem__('tri_mode_items', e.value),
            ui.open('/')
        )
    )

    categories = get_categories()
    cat_dict = {name: cid for cid, name in categories}
    cat_names = list(cat_dict.keys())

    all_items = get_items(current_user_id)

    if tri_mode_items == 'Alphabétique':
        all_items = sorted(all_items, key=lambda x: x[1].lower())
    elif tri_mode_items == 'Catégorie':
        all_items = sorted(all_items, key=lambda x: (x[2] or '').lower())
    elif tri_mode_items == 'Besoin':
        all_items = sorted(all_items, key=lambda x: x[3], reverse=True)

    for iid, name, cat, needed in all_items:
        with ui.row().classes('items-center justify-between bg-gray-100 rounded-lg px-3 py-2 mt-2'):
            ui.label(name).classes('font-bold')

            ui.button('✔️' if needed else '❌',
                      on_click=lambda item_id=iid: (
                          toggle_needed(item_id),
                          ui.open('/')
                      )).props('flat color=white')

            ui.select(
                cat_names,
                value=cat or (cat_names[0] if cat_names else None),
                on_change=lambda e, item_id=iid: (
                    update_item_category(item_id, cat_dict[e.value]),
                    ui.open('/')
                )
            ).classes('w-32')

            ui.button('🗑️',
                      on_click=lambda item_id=iid: (
                          delete_item(item_id),
                          ui.open('/')
                      )).props('flat color=red')

# ---------- BESOINS ----------
def needs_panel():
    global tri_mode_needs

    ui.label('Besoins').classes('text-lg font-bold')

    ui.select(
        ['Alphabétique', 'Ordre d’ajout'],
        value=tri_mode_needs,
        label='Trier par',
        on_change=lambda e: (
            globals().__setitem__('tri_mode_needs', e.value),
            ui.open('/')
        )
    )

    needed_items = get_items(current_user_id, only_needed=True)

    grouped = {}
    for iid, name, cat, needed in needed_items:
        grouped.setdefault(cat or 'Sans catégorie', []).append((iid, name))

    if not grouped:
        ui.label("Aucun item marqué comme besoin.")
        return

    for cat, items in grouped.items():
        ui.label(f'📂 {cat}').classes('text-lg font-bold mt-3')

        if tri_mode_needs == 'Alphabétique':
            items = sorted(items, key=lambda x: x[1])

        for iid, name in items:
            with ui.row().classes('items-center gap-3 mt-1'):
                ui.button('❌',
                          on_click=lambda item_id=iid: (
                              toggle_needed(item_id),
                              ui.open('/')
                          )).props('flat color=red')
                ui.label(name).classes('font-bold')

# ---------- NAVIGATION BAS ----------
def bottom_nav():
    global current_tab

    with ui.row().classes('fixed bottom-0 left-0 w-full justify-around bg-gray-800 text-white py-2 border-t border-gray-700'):
        ui.button('📝 Items', on_click=lambda: (
            globals().__setitem__('current_tab', 'items'),
            ui.open('/')
        )).props('flat color=white')

        ui.button('❤️ Besoins', on_click=lambda: (
            globals().__setitem__('current_tab', 'besoins'),
            ui.open('/')
        )).props('flat color=white')

        ui.button('📂 Catégories', on_click=lambda: (
            globals().__setitem__('current_tab', 'categories'),
            ui.open('/')
        )).props('flat color=white')

# ---------- PAGE PRINCIPALE ----------
@ui.page('/')
def main_page():

    with ui.row().classes('w-full justify-center mt-4'):
        # Colonne gauche
        with ui.column().classes('w-full max-w-sm bg-white text-black p-4 rounded-lg shadow-md'):
            user_panel()
            categories_panel()

        # Colonne droite
        with ui.column().classes('w-full max-w-sm bg-white text-black p-4 rounded-lg shadow-md ml-4'):
            add_item_panel()
            ui.separator()
            if current_tab == 'items':
                items_panel()
            elif current_tab == 'besoins':
                needs_panel()
            elif current_tab == 'categories':
                categories_panel()

    bottom_nav()

# ---------- LANCEMENT ----------
ui.run(title='Liste d’achats', reload=False)
