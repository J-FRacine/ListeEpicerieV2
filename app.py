import sqlite3
import os
from nicegui import ui

# ---------- BASE DE DONNÉES (persistante dans GitHub) ----------
DB_PATH = '/opt/render/project/src/items.db'

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    if os.path.exists(DB_PATH):
        return

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

    conn.commit()
    conn.close()

init_db()

# ---------- ÉTAT GLOBAL ----------
current_user_id = 1
current_tab = 'items'
tri_mode_items = 'Ordre d’ajout'
tri_mode_needs = 'Ordre d’ajout'

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

def delete_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM items WHERE user_id = ?", (user_id,))
    cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
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

# ---------- ONGLET : UTILISATEURS ----------
def users_panel():
    ui.label('Gestion des utilisateurs').classes('text-xl font-bold')

    users = get_users()
    user_names = {u[1]: u[0] for u in users}

    ui.label('Utilisateur actif').classes('mt-3')
    ui.select(
        list(user_names.keys()),
        value=[name for name, uid in user_names.items() if uid == current_user_id][0],
        on_change=lambda e: (
            globals().__setitem__('current_user_id', user_names[e.value]),
            ui.open('/')
        )
    ).classes('w-full')

    ui.separator()

    new_name = ui.input('Nouveau nom').classes('w-full')
    ui.button('Renommer', on_click=lambda: (
        rename_user(current_user_id, new_name.value),
        ui.open('/')
    )).classes('w-full mt-2')

    ui.separator()

    new_user = ui.input('Nouvel utilisateur').classes('w-full')
    ui.button('Créer utilisateur', on_click=lambda: (
        add_user(new_user.value),
        ui.open('/')
    )).classes('w-full mt-2')

# ---------- ONGLET : CATÉGORIES ----------
def categories_panel():
    ui.label('Gestion des catégories').classes('text-xl font-bold')

    new_cat_input = ui.input('Nouvelle catégorie').classes('w-full')
    ui.button('Ajouter', on_click=lambda: (
        add_category(new_cat_input.value),
        ui.open('/')
    )).classes('w-full mt-2')

    ui.separator()

    categories = get_categories()
    for cid, name in categories:
        with ui.row().classes('items-center justify-between mt-1'):
            ui.label(name)
            ui.button('🗑️', on_click=lambda cat_id=cid: (
                delete_category(cat_id),
                ui.open('/')
            )).props('flat color=red')

# ---------- AJOUT ITEM ----------
def add_item_panel():
    ui.label('Ajouter un item').classes('text-xl font-bold')

    categories = get_categories()
    cat_dict = {name: cid for cid, name in categories}
    cat_names = list(cat_dict.keys())

    default_cat = 'Épicerie' if 'Épicerie' in cat_names else (cat_names[0] if cat_names else None)

    item_name_input = ui.input('Nom de l’item').classes('w-full')
    item_cat_select = ui.select(cat_names, value=default_cat, label='Catégorie').classes('w-full')
    item_needed_checkbox = ui.checkbox('J’en ai besoin')

    ui.button('Ajouter item', on_click=lambda: (
        add_item(item_name_input.value, cat_dict[item_cat_select.value], 1 if item_needed_checkbox.value else 0, current_user_id),
        ui.open('/')
    )).classes('w-full mt-2')

# ---------- ITEMS ----------
def items_panel():
    global tri_mode_items

    # Sélecteur utilisateur en haut
    users = get_users()
    user_names = {u[1]: u[0] for u in users}

    ui.select(
        list(user_names.keys()),
        value=[name for name, uid in user_names.items() if uid == current_user_id][0],
        label='Utilisateur',
        on_change=lambda e: (
            globals().__setitem__('current_user_id', user_names[e.value]),
            ui.open('/')
        )
    ).classes('w-full')

    ui.separator()

    ui.label('Tous les items').classes('text-xl font-bold')

    ui.select(
        ['Alphabétique', 'Ordre d’ajout', 'Catégorie', 'Besoin'],
        value=tri_mode_items,
        label='Trier par',
        on_change=lambda e: (
            globals().__setitem__('tri_mode_items', e.value),
            ui.open('/')
        )
    ).classes('w-full')

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
        with ui.row().classes('items-center justify-between bg-gray-100 rounded-lg px-3 py-2 mt-2 gap-2'):

            # Nom + besoin
            with ui.row().classes('items-center gap-2'):
                ui.label(name).classes('font-bold')
                ui.button('✔️' if needed else '❌',
                          on_click=lambda item_id=iid: (
                              toggle_needed(item_id),
                              ui.open('/')
                          )).props('flat color=white')

            # Catégorie + poubelle sur la même ligne
            with ui.row().classes('items-center gap-2'):
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

    # Sélecteur utilisateur en haut
    users = get_users()
    user_names = {u[1]: u[0] for u in users}

    ui.select(
        list(user_names.keys()),
        value=[name for name, uid in user_names.items() if uid == current_user_id][0],
        label='Utilisateur',
        on_change=lambda e: (
            globals().__setitem__('current_user_id', user_names[e.value]),
            ui.open('/')
        )
    ).classes('w-full')

    ui.separator()

    ui.label('Besoins').classes('text-xl font-bold')

    ui.select(
        ['Alphabétique', 'Ordre d’ajout'],
        value=tri_mode_needs,
        label='Trier par',
        on_change=lambda e: (
            globals().__setitem__('tri_mode_needs', e.value),
            ui.open('/')
        )
    ).classes('w-full')

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

        ui.button('👤 Utilisateurs', on_click=lambda: (
            globals().__setitem__('current_tab', 'users'),
            ui.open('/')
        )).props('flat color=white')

# ---------- PAGE PRINCIPALE ----------
@ui.page('/')
def main_page():

    with ui.row().classes('w-full justify-center mt-4'):
        with ui.column().classes('w-full max-w-md bg-white text-black p-4 rounded-lg shadow-md'):
            if current_tab == 'items':
                add_item_panel()
                ui.separator()
                items_panel()
            elif current_tab == 'besoins':
                needs_panel()
            elif current_tab == 'categories':
                categories_panel()
            elif current_tab == 'users':
                users_panel()

    bottom_nav()

# ---------- LANCEMENT ----------
ui.run(title='Liste d’achats', reload=False)
