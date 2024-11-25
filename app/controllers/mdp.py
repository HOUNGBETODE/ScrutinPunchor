import bcrypt
import tkinter as tk
from tkinter import simpledialog
from sqlalchemy.orm import sessionmaker
from models.database import engine, User

# Fonction pour demander le mot de passe
def demander_mot_de_passe():
    root = tk.Tk()
    root.withdraw()
    mot_de_passe = simpledialog.askstring("ScrutinPunchor", "Veuillez entrer votre mot de passe pour confirmer votre identité:", show="*")
    return mot_de_passe

def check_user_identity_on_confirm_box():
    with sessionmaker(bind=engine)() as session:
        user = session.query(User).filter_by(id = 1).one_or_none()
        if user and bcrypt.checkpw(demander_mot_de_passe().encode("utf-8"), user.password):
            print("Indeed you are")
            return True
        else:
            print("Not really you")
            return False

# print(check_user_identity_on_confirm_box())